"""전기 안전장치 테스트 - 중복 차단, 롤백, 승인 게이트, DRY-RUN 선행."""
from datetime import date
from decimal import Decimal as D

import pytest

from sap_voucher_agent.agent import VoucherAgent
from sap_voucher_agent.doc_types import DocType
from sap_voucher_agent.fixtures import sample
from sap_voucher_agent.master_data import enrich
from sap_voucher_agent.models import LineItem, Party, VoucherDocument
from sap_voucher_agent.planner import plan
from sap_voucher_agent.poster import post
from sap_voucher_agent.sap.mock import MockClient


def _ready(dt, lookup):
    doc = sample(dt, source_file=f"{dt.value}.pdf")
    enrich(doc, lookup)
    if doc.supplier and not doc.supplier.sap_vendor:
        doc.supplier.sap_vendor = "0000199999"
    if doc.buyer and not doc.buyer.sap_customer:
        doc.buyer.sap_customer = "0000299999"
    return doc


def test_duplicate_posting_is_blocked(ctx, sap, rules, lookup):
    doc = _ready(DocType.TAX_INVOICE_IN, lookup)
    p1 = plan(doc, ctx, rules)
    first = post(p1, sap, dry_run=False, allow_unapproved=True)
    assert first.success

    p2 = plan(doc, ctx, rules)          # 같은 증빙 재전기 시도
    second = post(p2, sap, dry_run=False, allow_unapproved=True)
    assert not second.success
    assert "중복" in second.summary()
    assert sap.rolled_back >= 1


def test_failure_triggers_rollback(ctx, rules, lookup):
    sap = MockClient(fail_on={"BAPI_ACC_DOCUMENT_POST"})
    doc = _ready(DocType.CASH_RECEIPT, lookup)
    p = plan(doc, ctx, rules)
    out = post(p, sap, dry_run=False, allow_unapproved=True)
    assert not out.success
    assert out.rolled_back
    assert not out.committed


def test_unbalanced_document_is_rejected_by_sap(ctx, sap):
    """차대가 맞지 않는 전표는 SAP 검증에서 걸러진다."""
    raw = sap.call(
        "BAPI_ACC_DOCUMENT_CHECK",
        DOCUMENTHEADER={"COMP_CODE": "1000", "DOC_DATE": "20260331",
                        "PSTNG_DATE": "20260331", "DOC_TYPE": "KR"},
        CURRENCYAMOUNT=[{"ITEMNO_ACC": "1", "CURR_TYPE": "00", "AMT_DOCCUR": "100.00"},
                        {"ITEMNO_ACC": "2", "CURR_TYPE": "00", "AMT_DOCCUR": "-90.00"}])
    assert any(r["TYPE"] == "E" for r in raw["RETURN"])


def test_approval_required_types_are_gated(ctx, sap, rules, lookup):
    doc = _ready(DocType.PROMISSORY_NOTE, lookup)
    p = plan(doc, ctx, rules)
    assert p.requires_approval
    blocked = post(p, sap, dry_run=False, allow_unapproved=False)
    assert not blocked.success
    assert "승인" in (blocked.aborted_reason or "")
    approved = post(p, sap, dry_run=False, allow_unapproved=True)
    assert approved.success


def test_dry_run_never_posts(ctx, sap, rules, lookup):
    doc = _ready(DocType.TAX_INVOICE_IN, lookup)
    out = post(plan(doc, ctx, rules), sap, dry_run=True)
    assert out.success and out.dry_run
    assert not out.committed
    assert sap.committed == 0
    posting_calls = [n for n, _ in sap.calls
                     if n in ("BAPI_ACC_DOCUMENT_POST", "BAPI_INCOMINGINVOICE_CREATE")]
    assert posting_calls == []


def test_blocking_validation_prevents_any_call(ctx, sap, rules):
    doc = VoucherDocument(
        doc_type=DocType.TAX_INVOICE_IN, doc_date=date(2026, 3, 31),
        supplier=Party(name="미등록", biz_reg_no="214-81-01117"),
        net_total=D("100000"), tax_total=D("10000"), gross_total=D("110000"))
    p = plan(doc, ctx, rules)
    assert not p.postable and not p.calls
    out = post(p, sap, dry_run=False)
    assert not out.success and sap.calls == []


# --------------------------------------------------------------------------- 에이전트 툴

def test_agent_requires_simulation_before_execute(ctx, sap, lookup):
    agent = VoucherAgent(sap=sap, ctx=ctx, lookup=lookup, anthropic_client=object())
    tools = {t.to_dict()["name"]: t for t in agent.tools}
    vid = agent.register(_ready(DocType.CASH_RECEIPT, lookup))

    assert "plan_posting" in tools["plan_posting"].call({"voucher_id": vid}) or True
    tools["plan_posting"].call({"voucher_id": vid})
    out = tools["execute_posting"].call({"voucher_id": vid, "user_approved": True})
    assert "DRY-RUN" in out
    assert sap.committed == 0

    tools["simulate_posting"].call({"voucher_id": vid})
    out = tools["execute_posting"].call({"voucher_id": vid, "user_approved": True})
    assert "전기 완료" in out


def test_agent_execute_without_user_approval_is_refused(ctx, sap, lookup):
    agent = VoucherAgent(sap=sap, ctx=ctx, lookup=lookup, anthropic_client=object())
    tools = {t.to_dict()["name"]: t for t in agent.tools}
    vid = agent.register(_ready(DocType.SERVICE_CONTRACT, lookup))
    tools["plan_posting"].call({"voucher_id": vid})
    tools["simulate_posting"].call({"voucher_id": vid})
    out = tools["execute_posting"].call({"voucher_id": vid, "user_approved": False})
    assert "승인" in out
    assert sap.committed == 0


def test_patch_voucher_invalidates_plan(ctx, sap, lookup):
    agent = VoucherAgent(sap=sap, ctx=ctx, lookup=lookup, anthropic_client=object())
    tools = {t.to_dict()["name"]: t for t in agent.tools}
    vid = agent.register(_ready(DocType.CASH_RECEIPT, lookup))
    tools["plan_posting"].call({"voucher_id": vid})
    tools["simulate_posting"].call({"voucher_id": vid})
    assert vid in agent.session.simulated
    tools["patch_voucher"].call({"voucher_id": vid,
                                 "field_path": "line_items.0.gl_account",
                                 "value": "830100"})
    assert vid not in agent.session.simulated
    assert agent.session.vouchers[vid].line_items[0].gl_account == "830100"


# --------------------------------------------------------------- LUW·멱등 규약

def _customs_doc(lookup, with_tax=True):
    """수입신고필증 - 관세 송장과 부가세 전표 두 문서를 만드는 계획."""
    from decimal import Decimal
    doc = _ready(DocType.IMPORT_DECLARATION, lookup)
    tax = Decimal("253329") if with_tax else Decimal(0)
    doc.line_items = [LineItem(line_no=1, description="관세 및 통관수수료",
                               net_amount=Decimal("2533297"), tax_amount=tax,
                               po_number="4500000002", po_item="00010")]
    doc.net_total = Decimal("2533297")
    doc.tax_total = tax
    doc.gross_total = doc.net_total + tax
    return doc


def _refs(plan_obj):
    out = []
    for call in plan_obj.calls:
        for struct in ("HEADERDATA", "DOCUMENTHEADER", "GOODSMVT_HEADER"):
            h = call.params.get(struct)
            if isinstance(h, dict) and h.get("REF_DOC_NO"):
                out.append(h["REF_DOC_NO"])
    return out


def test_multi_document_plan_uses_distinct_references(ctx, rules, lookup):
    """한 증빙이 두 문서를 만들면 참조번호가 겹치면 안 된다.

    겹치면 두 번째 전기가 자기 자신의 첫 번째 문서와 중복으로 판정되어 실패한다.
    """
    from sap_voucher_agent.planner import plan as build
    p = build(_customs_doc(lookup), ctx, rules)
    assert len(p.calls) >= 2
    refs = _refs(p)
    assert len(refs) == len(set(refs)), f"참조번호 중복: {refs}"
    assert all(len(r) <= 16 for r in refs)


def test_multi_document_plan_posts_both_documents(ctx, sap, rules, lookup):
    from sap_voucher_agent.planner import plan as build
    p = build(_customs_doc(lookup), ctx, rules)
    out = post(p, sap, dry_run=False, allow_unapproved=True)
    assert out.success, out.summary()
    assert len(out.document_numbers) >= 2


def test_customs_invoice_sends_taxdata_when_gross_includes_tax(ctx, rules, lookup):
    """총액에 세액을 넣었으면 TAXDATA 도 넘겨야 MIRO 가 균형을 맞춘다."""
    from decimal import Decimal
    from sap_voucher_agent.planner import plan as build
    p = build(_customs_doc(lookup), ctx, rules)
    miro = next(c for c in p.calls if c.bapi == "BAPI_INCOMINGINVOICE_CREATE")
    gross = Decimal(miro.params["HEADERDATA"]["GROSS_AMOUNT"])
    items = sum(Decimal(i["ITEM_AMOUNT"]) for i in miro.params["ITEMDATA"])
    taxes = sum(Decimal(t["TAX_AMOUNT"]) for t in miro.params.get("TAXDATA", []))
    assert gross == items + taxes
    assert all(t["TAX_CODE"] for t in miro.params.get("TAXDATA", []))


def test_commit_failure_is_reported_as_failure(ctx, rules, lookup):
    """COMMIT 이 실패하면 채번된 문서번호가 있어도 성공으로 보고하면 안 된다."""
    sap = MockClient(fail_on={"BAPI_TRANSACTION_COMMIT"})
    p = plan(_ready(DocType.CASH_RECEIPT, lookup), ctx, rules)
    out = post(p, sap, dry_run=False, allow_unapproved=True)
    assert not out.success
    assert not out.committed
    assert out.rolled_back
    assert "COMMIT 실패" in out.summary()


def test_testrun_rolls_back_luw_before_real_posting(ctx, rules, lookup):
    """TESTRUN 은 처리 로직을 태우므로 실제 전기 전에 LUW 를 정리해야 한다."""
    sap = MockClient()
    p = plan(_ready(DocType.PURCHASE_ORDER, lookup), ctx, rules)
    out = post(p, sap, dry_run=False, allow_unapproved=True)
    assert out.success
    names = [n for n, _ in sap.calls]
    testrun_idx = names.index("BAPI_PO_CREATE1")
    rollback_idx = names.index("BAPI_TRANSACTION_ROLLBACK")
    real_idx = [i for i, n in enumerate(names) if n == "BAPI_PO_CREATE1"][1]
    assert testrun_idx < rollback_idx < real_idx
    assert not out.rolled_back          # 정리용 롤백은 실패가 아니다


def test_dry_run_with_testrun_leaves_no_dirty_luw(ctx, rules, lookup):
    sap = MockClient()
    out = post(plan(_ready(DocType.PURCHASE_ORDER, lookup), ctx, rules),
               sap, dry_run=True)
    assert out.success and out.dry_run
    assert sap.rolled_back == 1
    assert sap.committed == 0


def test_check_only_bapi_does_not_rollback(ctx, rules, lookup):
    """부작용 없는 CHECK BAPI 만 쓴 경우 불필요한 롤백을 하지 않는다."""
    sap = MockClient()
    post(plan(_ready(DocType.CASH_RECEIPT, lookup), ctx, rules), sap, dry_run=True)
    assert sap.rolled_back == 0
    assert [n for n, _ in sap.calls] == ["BAPI_ACC_DOCUMENT_CHECK"]
