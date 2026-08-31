# -*- coding: utf-8 -*-
"""증빙 → 전기 계획(PostingPlan) 수립."""
from __future__ import annotations

from .accounts import AccountRules
from .builders import build, idempotency_key
from .doc_types import KR_NAME
from .kifrs import Recognition, apply_to_document, assess
from .mapping import route_for
from .models import BapiCall, PostingContext, PostingPlan, VoucherDocument
from .sap.bapi_defs import BAPIS, NO_STANDARD_BAPI
from .validation import validate


def _skip_optional(builder_name: str, doc: VoucherDocument) -> bool:
    """선택 단계를 건너뛸지 판단한다."""
    if builder_name == "doc_attach":
        return not doc.source_file
    if builder_name == "acc_import_vat":
        return doc.tax_total <= 0
    return False


def plan(doc: VoucherDocument, ctx: PostingContext,
         rules: AccountRules | None = None) -> PostingPlan:
    """K-IFRS 판단 → 검증 → 경로 선택 → BAPI 파라미터 생성 (SAP 호출 없음).

    입력 문서는 변경하지 않는다. K-IFRS 재분류(자본화·계약부채)와 기간 배분에
    따른 라인 분할은 내부 사본에만 적용하므로 같은 문서로 여러 번 계획을 세워도
    결과가 달라지지 않는다.
    """
    rules = rules or AccountRules()
    route = route_for(doc.doc_type)

    # ① K-IFRS 회계판단 - 세법상 증빙 형식이 아니라 거래의 실질에 따른다
    work = doc.model_copy(deep=True)
    kifrs = assess(work, ctx, rules)
    apply_to_document(work, kifrs, rules)
    doc = work

    issues = validate(doc, ctx, rules)

    p = PostingPlan(
        doc_type=doc.doc_type,
        kr_name=KR_NAME[doc.doc_type],
        posting_kind=route.posting_kind,
        notes=route.notes,
        idempotency_key=idempotency_key(doc),
        validation_errors=[str(i) for i in issues if i.blocking],
        validation_warnings=[str(i) for i in issues if not i.blocking],
        kifrs_recognition=kifrs.recognition.kr,
        kifrs_substance=kifrs.substance,
        kifrs_standards=kifrs.standard_texts(),
        kifrs_rationale=list(kifrs.rationale),
        kifrs_judgments=[str(j) for j in kifrs.judgments],
        amortization_schedule=[
            {"period": e.period, "posting_date": e.posting_date.isoformat(),
             "amount": str(e.amount), "description": e.description}
            for d in kifrs.deferrals for e in d.schedule],
    )
    if route.caveat and route.caveat in NO_STANDARD_BAPI:
        p.validation_warnings.append(
            f"[경고:BAPI000] {NO_STANDARD_BAPI[route.caveat]}")

    reasons: list[str] = []
    for j in kifrs.blocking_judgments:
        reasons.append(f"K-IFRS {j.standard} 회계판단 필요: {j.question}")
    if route.always_approve:
        reasons.append(f"{p.kr_name}은(는) 항상 사람 승인이 필요한 문서 유형")
    if abs(doc.gross_total) > ctx.approval_threshold:
        reasons.append(f"금액 {doc.gross_total}원 > 자동전기 한도 "
                       f"{ctx.approval_threshold}원")
    if doc.doc_type_confidence < 0.7:
        reasons.append(f"문서 분류 신뢰도 낮음({doc.doc_type_confidence:.2f})")
    p.requires_approval = bool(reasons)
    p.approval_reasons = reasons

    if p.validation_errors:
        return p     # 차단 오류가 있으면 파라미터를 만들지 않는다

    # K-IFRS 인식 결론과 전기 경로의 정합성 점검
    if kifrs.recognition is Recognition.NO_ENTRY:
        fi_steps = [s.bapi for s in route.steps_for(doc)
                    if s.bapi.startswith("BAPI_ACC_DOCUMENT")]
        if fi_steps:
            p.validation_warnings.append(
                f"[경고:IFRS001] K-IFRS 상 인식 대상이 아닌 문서인데 회계전표 "
                f"전기({', '.join(fi_steps)})가 계획되었습니다. 거래의 실질을 "
                "재확인하십시오.")
    if kifrs.deferrals:
        total_deferred = sum(d.deferred_portion for d in kifrs.deferrals)
        p.validation_warnings.append(
            f"[경고:IFRS002] 발생주의에 따라 {total_deferred:,.0f}원을 선급비용으로 "
            f"이연했습니다. 매월 상각 전기 {len(p.amortization_schedule)}건이 "
            "필요합니다(SAP 발생/이연 엔진 ACACTREE01 또는 반복전표 FBD1 활용).")

    for step in route.steps_for(doc):
        if step.optional and _skip_optional(step.builder, doc):
            continue
        try:
            params = build(step.builder, doc, ctx, rules)
        except Exception as exc:                       # 빌더 실패는 차단 오류
            p.validation_errors.append(
                f"[오류:BLD001] {step.bapi} 파라미터 생성 실패({step.builder}): {exc}")
            continue
        bd = BAPIS.get(step.bapi)
        p.calls.append(BapiCall(
            bapi=step.bapi, params=params, purpose=step.purpose,
            commit=step.commit and (bd.needs_commit if bd else True),
            check_bapi=(bd.check_bapi if bd else None),
        ))
    _uniquify_references(p)
    return p


#: 참조번호(XBLNR)를 담는 헤더 구조와 필드
_REF_FIELDS = (("DOCUMENTHEADER", "REF_DOC_NO"), ("HEADERDATA", "REF_DOC_NO"),
               ("GOODSMVT_HEADER", "REF_DOC_NO"),
               ("ENTRYSHEETHEADER", "REF_DOC_NO"))


def _uniquify_references(p: PostingPlan) -> None:
    """한 계획이 문서를 둘 이상 만들면 참조번호가 겹치지 않게 한다.

    중복 전기 차단은 참조번호(XBLNR, 16자)로 이루어지므로, 같은 증빙에서
    나온 두 문서가 같은 참조번호를 쓰면 두 번째 전기가 자기 자신의 첫 번째
    문서와 충돌해 실패한다(예: 수입신고필증의 관세 송장 + 수입 부가세 전표).
    """
    seen: set[str] = set()
    for idx, call in enumerate(p.calls, 1):
        for struct, field in _REF_FIELDS:
            header = call.params.get(struct)
            if not isinstance(header, dict):
                continue
            ref = header.get(field)
            if not ref:
                continue
            if ref not in seen:
                seen.add(ref)
                continue
            suffix = f"-{idx}"
            new_ref = ref[:16 - len(suffix)] + suffix
            header[field] = new_ref
            seen.add(new_ref)


def explain(p: PostingPlan) -> str:
    """사람이 읽을 수 있는 전기 계획 요약."""
    lines = [
        f"■ 증빙 유형 : {p.kr_name} ({p.doc_type.value})",
        f"■ 전기 성격 : {p.posting_kind}",
        f"■ 멱등 키   : {p.idempotency_key}",
        "",
        f"■ K-IFRS 인식 : {p.kifrs_recognition}",
        f"■ 거래의 실질 : {p.kifrs_substance}",
    ]
    if p.kifrs_standards:
        lines.append("■ 적용 기준서")
        lines += [f"   - {t}" for t in p.kifrs_standards]
    if p.kifrs_rationale:
        lines.append("■ 회계처리 근거")
        lines += [f"   - {r}" for r in p.kifrs_rationale]
    if p.kifrs_judgments:
        lines.append("■ 회계 판단 필요")
        lines += [f"   - {j}" for j in p.kifrs_judgments]
    if p.amortization_schedule:
        lines.append(f"■ 기간배분 스케줄 ({len(p.amortization_schedule)}건)")
        for e in p.amortization_schedule[:3]:
            lines.append(f"   - {e['period']} {float(e['amount']):,.0f}원 "
                         f"({e['posting_date']})")
        if len(p.amortization_schedule) > 3:
            lines.append(f"   - … 외 {len(p.amortization_schedule) - 3}건")
    lines += ["", "■ BAPI 호출 계획"]
    if not p.calls:
        lines.append("   (없음 - 검증 오류로 계획을 생성하지 못했습니다)")
    for i, c in enumerate(p.calls, 1):
        bd = BAPIS.get(c.bapi)
        tcode = f" / {bd.tcode}" if bd else ""
        lines.append(f"   {i}. {c.bapi}{tcode}")
        lines.append(f"      → {c.purpose}")
        if c.check_bapi:
            lines.append(f"      사전검증: {c.check_bapi}")
    if p.requires_approval:
        lines += ["", "■ 사람 승인 필요"]
        lines += [f"   - {r}" for r in p.approval_reasons]
    if p.validation_errors:
        lines += ["", "■ 차단 오류"] + [f"   - {e}" for e in p.validation_errors]
    if p.validation_warnings:
        lines += ["", "■ 경고"] + [f"   - {w}" for w in p.validation_warnings]
    if p.notes:
        lines += ["", f"■ 처리 원칙 : {p.notes}"]
    return "\n".join(lines)
