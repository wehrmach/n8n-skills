# -*- coding: utf-8 -*-
"""증빙 → 전기 계획(PostingPlan) 수립."""
from __future__ import annotations

from .accounts import AccountRules
from .builders import build, idempotency_key
from .doc_types import KR_NAME
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
    """검증 → 경로 선택 → BAPI 파라미터 생성까지 수행한다(SAP 호출 없음)."""
    rules = rules or AccountRules()
    route = route_for(doc.doc_type)
    issues = validate(doc, ctx, rules)

    p = PostingPlan(
        doc_type=doc.doc_type,
        kr_name=KR_NAME[doc.doc_type],
        posting_kind=route.posting_kind,
        notes=route.notes,
        idempotency_key=idempotency_key(doc),
        validation_errors=[str(i) for i in issues if i.blocking],
        validation_warnings=[str(i) for i in issues if not i.blocking],
    )
    if route.caveat and route.caveat in NO_STANDARD_BAPI:
        p.validation_warnings.append(
            f"[경고:BAPI000] {NO_STANDARD_BAPI[route.caveat]}")

    reasons: list[str] = []
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
    return p


def explain(p: PostingPlan) -> str:
    """사람이 읽을 수 있는 전기 계획 요약."""
    lines = [
        f"■ 증빙 유형 : {p.kr_name} ({p.doc_type.value})",
        f"■ 전기 성격 : {p.posting_kind}",
        f"■ 멱등 키   : {p.idempotency_key}",
        "",
        "■ BAPI 호출 계획",
    ]
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
