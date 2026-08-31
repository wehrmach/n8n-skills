# -*- coding: utf-8 -*-
"""증빙 → SAP 전기 AI 에이전트.

Claude 툴러너(`client.beta.messages.tool_runner`)로 다음 루프를 자율 수행한다.

    증빙 파일 → 추출/분류 → 거래처 마스터 해석 → 검증 → BAPI 계획 →
    DRY-RUN 검증 → (승인) → 실제 전기 → 커밋 → 보고

에이전트가 다루는 데이터는 전부 세션 상태에 보관하고, 툴은 짧은 요약과
식별자만 주고받는다. 대용량 JSON 이 컨텍스트를 잠식하지 않도록 하기 위해서다.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Any, Optional

from .accounts import AccountRules
from .doc_types import KR_NAME, DocType
from .mapping import ROUTES, route_for
from .master_data import MasterLookup, enrich
from .models import PostingContext, PostingPlan, VoucherDocument
from .planner import explain, plan as build_plan
from .poster import PostingOutcome, post
from .sap.bapi_defs import BAPIS, NO_STANDARD_BAPI
from .sap.client import SapClient

MODEL = "claude-opus-5"

SYSTEM_PROMPT = """\
당신은 한국 기업의 회계 증빙을 K-IFRS(한국채택국제회계기준)에 따라 판단하고
SAP ERP 표준 BAPI 로 전기하는 AI 회계 에이전트다.

[가장 중요한 원칙 - 실질우선]
세금계산서·영수증은 세법상 서류일 뿐이다. 회계처리는 거래의 경제적 실질에
따라 결정한다. 증빙의 종류가 곧 분개를 의미하지 않는다.
  · 발생주의 - 현금 수수가 아니라 재화·용역을 주고받은 시점에 인식한다.
    입금표·이체확인증은 채권·채무를 소거할 뿐 손익을 발생시키지 않는다.
  · 미이행계약 - 계약서·발주서만으로는 자산·부채를 인식하지 않는다.
  · 기간귀속 - 용역기간이 보고기간을 넘으면 선급비용으로 이연한다.
  · 수익인식(1115) - 세금계산서 발행일이 아니라 수행의무 이행일에 인식한다.
  · 자본화(1016/1038) - 자산 요건과 중요성 기준을 함께 본다.

[작업 절차 - 증빙 1건마다 순서대로]
1. extract_voucher 로 증빙을 판독한다.
2. resolve_master 로 거래처를 SAP 코드에 매핑한다. 미등록이면 사용자에게 보고한다.
3. assess_kifrs 로 K-IFRS 회계판단을 확인한다. 판단이 필요한 쟁점이 있으면
   사용자에게 질문하고, 답을 받으면 patch_voucher 또는 set_accounting_policy 로
   반영한 뒤 다시 판단한다. 임의로 결정하지 않는다.
4. plan_posting 으로 BAPI 전기 계획을 만든다. 계획과 회계처리 근거를 설명한다.
5. simulate_posting 으로 반드시 DRY-RUN 검증을 먼저 수행한다.
6. 검증을 통과하고 승인 요건이 충족되면 execute_posting 으로 전기한다.
7. 전기 결과(문서번호)와 기간배분 스케줄을 보고한다.

[반드시 지킬 원칙]
- DRY-RUN 없이 execute_posting 을 호출하지 않는다.
- 계획이 requires_approval 이면 사용자가 명시적으로 승인하기 전에는 전기하지 않는다.
  사용자 지시에 '승인', '전기해', 'approved' 가 없으면 승인된 것이 아니다.
- 검증 오류(blocking)가 있으면 전기하지 않고 원인과 해결 방법을 설명한다.
- 데이터가 불확실하면 추측해서 채우지 말고 사용자에게 확인을 요청한다.
- 금액·계정·세금코드를 임의로 바꾸지 않는다. 수정이 필요하면 patch_voucher 로
  명시적으로 바꾸고 무엇을 왜 바꿨는지 보고한다.
- 같은 증빙을 두 번 전기하지 않는다. 멱등키(참조번호)로 중복이 차단된다.
- K-IFRS 판단 쟁점(개발비 자본화, 리스 인식, 수행의무 이행일, 외화 환율)은
  회사 정책과 사실관계에 달린 문제다. 추정해서 전기하지 말고 반드시 확인한다.
- 선급비용 이연이 발생하면 매월 상각 전기가 필요하다는 사실을 반드시 보고한다.

[보고 형식]
한국어로 간결하게. 증빙별로 '유형 / 금액 / K-IFRS 인식 / 사용 BAPI /
결과(문서번호 또는 사유)'를 표로 정리하고, 사람이 판단·처리해야 할 항목을
마지막에 목록으로 남긴다."""


# --------------------------------------------------------------------------- 세션 상태

@dataclass
class Session:
    vouchers: dict[str, VoucherDocument] = field(default_factory=dict)
    plans: dict[str, PostingPlan] = field(default_factory=dict)
    outcomes: dict[str, PostingOutcome] = field(default_factory=dict)
    simulated: set[str] = field(default_factory=set)
    approved: set[str] = field(default_factory=set)
    _seq: int = 0

    def new_id(self) -> str:
        self._seq += 1
        return f"V{self._seq:03d}"


def _money(v: Decimal | None) -> str:
    return f"{int(v):,}" if v is not None else "-"


class VoucherAgent:
    """증빙 전기 에이전트. 툴 정의와 세션 상태를 함께 보유한다."""

    def __init__(self, *, sap: SapClient, ctx: PostingContext,
                 rules: AccountRules | None = None,
                 lookup: MasterLookup | None = None,
                 anthropic_client: Any = None,
                 model: str = MODEL) -> None:
        self.sap = sap
        self.ctx = ctx
        self.rules = rules or AccountRules()
        self.lookup = lookup or MasterLookup(client=sap)
        self.session = Session()
        self.model = model
        self._client = anthropic_client
        self.tools = self._build_tools()

    # ------------------------------------------------------------ Anthropic

    @property
    def client(self) -> Any:
        if self._client is None:
            import anthropic
            self._client = anthropic.Anthropic()
        return self._client

    # ------------------------------------------------------------ 내부 조회

    def _voucher(self, voucher_id: str) -> VoucherDocument:
        if voucher_id not in self.session.vouchers:
            raise KeyError(f"알 수 없는 증빙 ID: {voucher_id}")
        return self.session.vouchers[voucher_id]

    def register(self, doc: VoucherDocument) -> str:
        """외부에서 추출한 증빙을 세션에 등록한다."""
        vid = self.session.new_id()
        self.session.vouchers[vid] = doc
        return vid

    # ------------------------------------------------------------ 툴 정의

    def _build_tools(self) -> list[Any]:
        from anthropic import beta_tool
        agent = self

        @beta_tool
        def list_voucher_files(directory: str, limit: int = 60) -> str:
            """지정한 디렉터리에서 처리 대상 증빙 파일(PDF/이미지)을 나열한다.

            Args:
                directory: 증빙 파일이 있는 디렉터리 경로.
                limit: 최대 반환 개수.
            """
            base = Path(directory)
            if not base.is_dir():
                return f"오류: 디렉터리가 아닙니다 - {directory}"
            exts = {".pdf", ".png", ".jpg", ".jpeg"}
            files = sorted(p for p in base.iterdir()
                           if p.suffix.lower() in exts and not p.name.startswith("_"))
            if not files:
                return f"{directory} 에 증빙 파일이 없습니다."
            head = files[:limit]
            body = "\n".join(f"  {p.name}" for p in head)
            more = f"\n  … 외 {len(files)-len(head)}건" if len(files) > len(head) else ""
            return f"증빙 파일 {len(files)}건:\n{body}{more}"

        @beta_tool
        def extract_voucher(file_path: str) -> str:
            """증빙 파일 1건을 판독해 유형을 분류하고 필드를 추출한다.

            Args:
                file_path: 증빙 PDF 또는 이미지 파일 경로.
            """
            from .extraction import extract
            try:
                doc = extract(file_path, client=agent.client, model=agent.model)
            except Exception as exc:
                return f"추출 실패: {type(exc).__name__}: {exc}"
            vid = agent.register(doc)
            warn = ("\n경고: " + "; ".join(doc.extraction_warnings)
                    if doc.extraction_warnings else "")
            return (
                f"voucher_id={vid}\n"
                f"유형: {KR_NAME[doc.doc_type]} ({doc.doc_type.value}, "
                f"신뢰도 {doc.doc_type_confidence:.2f})\n"
                f"증빙번호: {doc.doc_number or '-'} / 일자: {doc.doc_date or '-'}\n"
                f"공급자: {doc.supplier.name if doc.supplier else '-'} "
                f"({doc.supplier.biz_reg_no if doc.supplier else '-'})\n"
                f"공급받는자: {doc.buyer.name if doc.buyer else '-'}\n"
                f"금액: 공급가액 {_money(doc.net_total)} / 세액 {_money(doc.tax_total)} "
                f"/ 합계 {_money(doc.gross_total)} {doc.currency}\n"
                f"명세 {len(doc.line_items)}행{warn}")

        @beta_tool
        def resolve_master(voucher_id: str) -> str:
            """증빙의 거래처를 SAP 공급업체/고객 코드에 매핑한다.

            Args:
                voucher_id: extract_voucher 가 반환한 증빙 ID.
            """
            try:
                doc = agent._voucher(voucher_id)
            except KeyError as exc:
                return str(exc)
            unresolved = enrich(doc, agent.lookup)
            parts = []
            if doc.supplier:
                parts.append(f"공급업체: {doc.supplier.name} → "
                             f"{doc.supplier.sap_vendor or '미등록'}")
            if doc.buyer:
                parts.append(f"고객: {doc.buyer.name} → "
                             f"{doc.buyer.sap_customer or '미등록'}")
            tail = ("\n미해결: " + "; ".join(unresolved)
                    + "\n→ 거래처 마스터 신규 등록(BAPI_BUPA_CREATE_FROM_DATA)이 "
                      "필요합니다. 사람 승인 대상입니다." if unresolved else "")
            return "\n".join(parts) + tail

        @beta_tool
        def explain_bapi_route(doc_type: str) -> str:
            """증빙 유형이 어떤 SAP BAPI 로 전기되는지 설명한다.

            Args:
                doc_type: 문서 유형 코드(예: tax_invoice_in). 'all' 이면 전체 요약.
            """
            if doc_type == "all":
                rows = [f"{KR_NAME[t]:28} {', '.join(r.all_bapis()[:2])}"
                        for t, r in ROUTES.items()]
                return "증빙 유형별 BAPI 매핑:\n" + "\n".join(rows)
            try:
                route = route_for(DocType(doc_type))
            except (ValueError, KeyError):
                return (f"알 수 없는 문서 유형: {doc_type}. "
                        f"사용 가능: {', '.join(t.value for t in list(DocType)[:10])} …")
            lines = [f"{route.kr_name} → 전기 성격 {route.posting_kind}"]
            for key, steps in route.variants.items():
                names = " → ".join(
                    f"{s.bapi}({BAPIS[s.bapi].tcode if s.bapi in BAPIS else '-'})"
                    for s in steps)
                lines.append(f"  [{key}] {names}")
            lines.append(f"원칙: {route.notes}")
            if route.caveat:
                lines.append(f"유의: {NO_STANDARD_BAPI[route.caveat]}")
            if route.always_approve:
                lines.append("이 유형은 항상 사람 승인이 필요하다.")
            return "\n".join(lines)

        @beta_tool
        def patch_voucher(voucher_id: str, field_path: str, value: str) -> str:
            """추출 결과의 특정 필드를 명시적으로 보정한다.

            Args:
                voucher_id: 증빙 ID.
                field_path: 필드 경로. 예: 'supplier.sap_vendor', 'posting_date',
                    'line_items.0.gl_account', 'line_items.1.tax_code',
                    'reference_docs.sap_po'.
                value: 설정할 값(문자열).
            """
            try:
                doc = agent._voucher(voucher_id)
            except KeyError as exc:
                return str(exc)
            parts = field_path.split(".")
            try:
                if parts[0] == "reference_docs" and len(parts) == 2:
                    doc.reference_docs[parts[1]] = value
                elif parts[0] == "line_items" and len(parts) == 3:
                    idx = int(parts[1])
                    setattr(doc.line_items[idx], parts[2],
                            _coerce(doc.line_items[idx], parts[2], value))
                elif len(parts) == 2:
                    obj = getattr(doc, parts[0])
                    if obj is None:
                        return f"{parts[0]} 이(가) 비어 있어 설정할 수 없습니다."
                    setattr(obj, parts[1], _coerce(obj, parts[1], value))
                elif len(parts) == 1:
                    setattr(doc, parts[0], _coerce(doc, parts[0], value))
                else:
                    return f"지원하지 않는 필드 경로: {field_path}"
            except Exception as exc:
                return f"설정 실패({field_path}={value}): {exc}"
            agent.session.plans.pop(voucher_id, None)
            agent.session.simulated.discard(voucher_id)
            return f"{voucher_id}.{field_path} = {value} 로 설정했습니다. 계획을 다시 세우십시오."

        @beta_tool
        def assess_kifrs(voucher_id: str) -> str:
            """증빙의 K-IFRS 회계판단(인식 시점·자본화·기간귀속·측정)을 확인한다.

            Args:
                voucher_id: 증빙 ID.
            """
            from .kifrs import assess
            try:
                doc = agent._voucher(voucher_id)
            except KeyError as exc:
                return str(exc)
            a = assess(doc.model_copy(deep=True), agent.ctx, agent.rules)
            tail = ""
            if a.blocking_judgments:
                tail = ("\n\n※ 위 판단 쟁점이 해소되기 전에는 자동 전기가 "
                        "차단된다. 사용자에게 확인한 뒤 patch_voucher 또는 "
                        "set_accounting_policy 로 반영하라.")
            return a.summary() + tail

        @beta_tool
        def set_accounting_policy(policy: str, value: str) -> str:
            """회사의 K-IFRS 회계정책 파라미터를 설정한다.

            Args:
                policy: 정책 이름. 'intangible_capitalization'(개발비 자본화 요건
                    충족 여부 true/false), 'capitalization_threshold'(자산 인식
                    최소금액), 'deferral_min_amount'(이연 최소금액),
                    'period_end'(보고기간 종료일 YYYY-MM-DD),
                    'lease_short_term_months', 'lease_low_value_threshold'.
                value: 설정할 값.
            """
            allowed = {"intangible_capitalization", "capitalization_threshold",
                       "deferral_min_amount", "period_end",
                       "lease_short_term_months", "lease_low_value_threshold"}
            if policy not in allowed:
                return f"설정할 수 없는 정책: {policy}. 가능: {', '.join(sorted(allowed))}"
            try:
                if policy == "intangible_capitalization":
                    parsed: object = value.strip().lower() in ("true", "1", "y", "yes", "예")
                elif policy == "period_end":
                    from .extraction import _date as parse_date
                    parsed = parse_date(value)
                    if parsed is None:
                        return f"날짜를 해석할 수 없습니다: {value}"
                elif policy == "lease_short_term_months":
                    parsed = int(value)
                else:
                    parsed = Decimal(value)
                setattr(agent.ctx, policy, parsed)
            except Exception as exc:
                return f"설정 실패({policy}={value}): {exc}"
            agent.session.plans.clear()
            agent.session.simulated.clear()
            return (f"회계정책 {policy} = {value} 로 설정했습니다. "
                    "기존 전기 계획은 무효화되었으니 다시 수립하십시오.")

        @beta_tool
        def plan_posting(voucher_id: str) -> str:
            """증빙의 SAP 전기 계획(BAPI 호출 순서와 파라미터)을 만든다.

            Args:
                voucher_id: 증빙 ID.
            """
            try:
                doc = agent._voucher(voucher_id)
            except KeyError as exc:
                return str(exc)
            p = build_plan(doc, agent.ctx, agent.rules)
            agent.session.plans[voucher_id] = p
            agent.session.simulated.discard(voucher_id)
            return explain(p)

        @beta_tool
        def inspect_bapi_params(voucher_id: str, call_index: int = 1) -> str:
            """생성된 BAPI 호출 파라미터를 확인한다(전기 전 점검용).

            Args:
                voucher_id: 증빙 ID.
                call_index: 확인할 호출 순번(1부터).
            """
            p = agent.session.plans.get(voucher_id)
            if p is None:
                return "먼저 plan_posting 을 실행하십시오."
            if not 1 <= call_index <= len(p.calls):
                return f"호출 순번 범위: 1~{len(p.calls)}"
            call = p.calls[call_index - 1]
            body = json.dumps(call.params, ensure_ascii=False, indent=2, default=str)
            if len(body) > 6000:
                body = body[:6000] + "\n… (생략)"
            return f"{call.bapi} 파라미터:\n{body}"

        @beta_tool
        def simulate_posting(voucher_id: str) -> str:
            """실제 전기 없이 SAP 검증 BAPI 로 DRY-RUN 검증한다.

            Args:
                voucher_id: 증빙 ID.
            """
            p = agent.session.plans.get(voucher_id)
            if p is None:
                return "먼저 plan_posting 을 실행하십시오."
            out = post(p, agent.sap, dry_run=True)
            if out.success:
                agent.session.simulated.add(voucher_id)
            return out.summary()

        @beta_tool
        def execute_posting(voucher_id: str, user_approved: bool = False) -> str:
            """DRY-RUN 을 통과한 계획을 SAP 에 실제로 전기하고 커밋한다.

            Args:
                voucher_id: 증빙 ID.
                user_approved: 사용자가 명시적으로 전기를 승인했으면 true.
            """
            p = agent.session.plans.get(voucher_id)
            if p is None:
                return "먼저 plan_posting 을 실행하십시오."
            if voucher_id not in agent.session.simulated:
                return ("DRY-RUN 검증을 통과하지 않았습니다. "
                        "simulate_posting 을 먼저 실행하십시오.")
            if p.requires_approval and not user_approved:
                return ("사람 승인이 필요한 전기입니다: "
                        + "; ".join(p.approval_reasons)
                        + " — 사용자 승인을 받은 뒤 user_approved=true 로 재호출하십시오.")
            if user_approved:
                agent.session.approved.add(voucher_id)
            out = post(p, agent.sap, dry_run=False,
                       auto_commit=agent.ctx.auto_commit,
                       allow_unapproved=user_approved)
            agent.session.outcomes[voucher_id] = out
            return out.summary()

        @beta_tool
        def posting_report() -> str:
            """이번 세션에서 처리한 증빙의 전기 결과를 표로 정리한다."""
            s = agent.session
            if not s.vouchers:
                return "처리한 증빙이 없습니다."
            rows = ["| ID | 유형 | 합계금액 | K-IFRS 인식 | BAPI | 결과 |",
                    "|---|---|---|---|---|---|"]
            for vid, doc in s.vouchers.items():
                out = s.outcomes.get(vid)
                p = s.plans.get(vid)
                bapis = ", ".join(c.bapi for c in p.calls) if p else "-"
                if out is None:
                    res = "미전기" + (" (DRY-RUN 통과)" if vid in s.simulated else "")
                elif out.success:
                    res = "전기완료 " + ", ".join(
                        f"{k.split('_')[-1]}={v}" for k, v in out.document_numbers.items())
                else:
                    res = "실패: " + (out.aborted_reason or "원인 불명")
                rows.append(f"| {vid} | {KR_NAME[doc.doc_type]} | "
                            f"{_money(doc.gross_total)} | "
                            f"{(p.kifrs_recognition if p else '-')} | "
                            f"{bapis} | {res} |")
            return "\n".join(rows)

        return [list_voucher_files, extract_voucher, resolve_master,
                explain_bapi_route, assess_kifrs, set_accounting_policy,
                patch_voucher, plan_posting, inspect_bapi_params,
                simulate_posting, execute_posting, posting_report]

    # ------------------------------------------------------------ 실행

    def run(self, instruction: str, *, max_iterations: int = 60,
            verbose: bool = True) -> str:
        """에이전트 루프를 실행하고 마지막 응답 텍스트를 반환한다."""
        runner = self.client.beta.messages.tool_runner(
            model=self.model,
            max_tokens=16000,
            system=[{"type": "text", "text": SYSTEM_PROMPT,
                     "cache_control": {"type": "ephemeral"}}],
            tools=self.tools,
            messages=[{"role": "user", "content": instruction}],
            thinking={"type": "adaptive"},
        )
        last_text = ""
        for i, message in enumerate(runner, 1):
            for block in message.content:
                if block.type == "text" and block.text.strip():
                    last_text = block.text
                    if verbose:
                        print(block.text)
                elif block.type == "tool_use" and verbose:
                    print(f"  ⟶ {block.name}({json.dumps(block.input, ensure_ascii=False)[:120]})")
            if i >= max_iterations:
                break
        return last_text


def _coerce(obj: Any, field_name: str, value: str) -> Any:
    """patch_voucher 값 타입 변환."""
    from datetime import date as _date
    current = getattr(obj, field_name, None)
    annotation = type(obj).model_fields.get(field_name) if hasattr(type(obj), "model_fields") else None
    if isinstance(current, Decimal):
        return Decimal(value)
    if isinstance(current, _date):
        from .extraction import _date as parse_date
        return parse_date(value)
    if annotation is not None:
        ann = str(annotation.annotation)
        if "Decimal" in ann:
            return Decimal(value)
        if "date" in ann:
            from .extraction import _date as parse_date
            return parse_date(value)
        if "float" in ann:
            return float(value)
        if "int" in ann and "Optional" not in ann:
            return int(value)
    return value
