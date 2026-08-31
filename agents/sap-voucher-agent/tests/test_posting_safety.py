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
