"""K-IFRS 회계판단 테스트.

세법상 증빙 형식이 아니라 거래의 경제적 실질에 따라 인식·측정하는지 검증한다.
"""
from datetime import date
from decimal import Decimal as D

import pytest

from sap_voucher_agent.accounts import AccountRules
from sap_voucher_agent.doc_types import DocType
from sap_voucher_agent.fixtures import sample
from sap_voucher_agent.kifrs import (Recognition, apply_to_document, assess,
                                     build_deferral)
from sap_voucher_agent.models import (LineItem, Party, PostingContext,
                                      VoucherDocument)
from sap_voucher_agent.planner import plan


@pytest.fixture
def kctx() -> PostingContext:
    return PostingContext(
        company_code="1000", fiscal_year=2026, default_cost_center="1000-ADM",
        period_end=date(2026, 3, 31), approval_threshold=D("50000000"))


def _ap(desc, net, tax=D(0), **kw):
    lines = kw.pop("lines", None) or [
        LineItem(line_no=1, description=desc, net_amount=net, tax_amount=tax,
                 **{k: kw.pop(k) for k in ("service_start", "service_end")
                    if k in kw})]
    return VoucherDocument(
        doc_type=kw.pop("doc_type", DocType.TAX_INVOICE_IN),
        doc_date=kw.pop("doc_date", date(2026, 3, 31)),
        supplier=Party(name="공급자", biz_reg_no="214-81-01117",
                       sap_vendor="0000100234"),
        net_total=sum(li.net_amount for li in lines),
        tax_total=sum(li.tax_amount for li in lines),
        gross_total=sum(li.gross_amount for li in lines),
        line_items=lines, **kw)


# --------------------------------------------------------------- 발생주의·실질우선

def test_cash_receipt_voucher_is_settlement_not_expense(kctx):
    """입금표는 현금 이동일 뿐 수익 인식 사건이 아니다."""
    a = assess(sample(DocType.PAYMENT_RECEIPT), kctx)
    assert a.recognition is Recognition.SETTLEMENT
    assert "채권·채무 소거" in a.substance


def test_contract_alone_creates_no_accounting_entry(kctx):
    """계약 체결만으로는 자산·부채를 인식하지 않는다(미이행계약)."""
    a = assess(sample(DocType.SERVICE_CONTRACT), kctx)
    assert a.recognition is Recognition.NO_ENTRY
    assert "미이행계약" in a.substance


def test_purchase_order_creates_no_accounting_entry(kctx):
    assert assess(sample(DocType.PURCHASE_ORDER), kctx).recognition is Recognition.NO_ENTRY


def test_goods_acceptance_is_the_recognition_event(kctx):
    """검수·입고 시점에 통제가 이전되어 자산·비용을 인식한다."""
    a = assess(sample(DocType.GOODS_ACCEPTANCE), kctx)
    assert a.recognition in (Recognition.CAPITALIZE, Recognition.EXPENSE_NOW)
    assert "1115" in a.standards
    assert "통제 이전" in a.substance


# --------------------------------------------------------------- 기간귀속(cut-off)

def test_annual_service_is_deferred_by_accrual_basis(kctx):
    doc = _ap("사무실 화재보험료 연간", D("12000000"), D("1200000"),
              doc_date=date(2026, 3, 1),
              service_start=date(2026, 3, 1), service_end=date(2027, 2, 28))
    a = assess(doc, kctx)
    assert a.recognition is Recognition.DEFER
    d = a.deferrals[0]
    assert d.current_portion == D("1000000")       # 1개월 경과
    assert d.deferred_portion == D("11000000")
    assert len(d.schedule) == 11


def test_deferral_split_preserves_total_and_adds_prepaid_line(kctx):
    doc = _ap("연간 유지보수료", D("12000000"), D("1200000"),
              service_start=date(2026, 1, 1), service_end=date(2026, 12, 31))
    before = doc.net_total
    a = assess(doc, kctx)
    apply_to_document(doc, a, AccountRules())
    assert sum(li.net_amount for li in doc.line_items) == before
    prepaid = [li for li in doc.line_items if li.gl_account == "133100"]
    assert prepaid and prepaid[0].net_amount > 0
    # 부가세는 세금계산서 작성일 과세기간에 전액 공제되므로 이연 라인에 붙지 않는다
    assert prepaid[0].tax_amount == D(0)


def test_service_fully_in_period_is_not_deferred(kctx):
    doc = _ap("3월분 유지보수료", D("1000000"),
              service_start=date(2026, 3, 1), service_end=date(2026, 3, 31))
    assert assess(doc, kctx).deferrals == []


def test_immaterial_amount_is_not_deferred(kctx):
    doc = _ap("소액 구독료", D("50000"),
              service_start=date(2026, 3, 1), service_end=date(2027, 2, 28))
    assert assess(doc, kctx).deferrals == []


def test_periodic_expense_without_period_raises_judgment(kctx):
    a = assess(_ap("사무실 임차료", D("3000000")), kctx)
    assert any("기간 계약형" in j.question for j in a.judgments)


# --------------------------------------------------------------- 자본화

def test_software_development_requires_1038_judgment(kctx):
    a = assess(_ap("ERP 연동 모듈 개발", D("8000000")), kctx)
    j = [x for x in a.judgments if x.standard == "1038"]
    assert j and j[0].blocking
    assert "개발단계" in j[0].question


def test_software_capitalized_when_policy_confirmed(kctx):
    kctx.intangible_capitalization = True
    doc = _ap("ERP 연동 모듈 개발", D("8000000"))
    a = assess(doc, kctx)
    assert a.recognition is Recognition.CAPITALIZE
    apply_to_document(doc, a, AccountRules())
    assert doc.line_items[0].gl_account == "178200"


def test_below_threshold_is_expensed_not_capitalized(kctx):
    a = assess(_ap("노트북 구입", D("900000")), kctx)
    assert a.recognition is Recognition.EXPENSE_NOW
    assert not a.account_overrides
    assert any("기준금액" in r for r in a.rationale)


def test_equipment_above_threshold_is_capitalized(kctx):
    doc = _ap("서버 장비 구입", D("15000000"))
    a = assess(doc, kctx)
    assert a.recognition is Recognition.CAPITALIZE
    assert "1016" in a.standards
    apply_to_document(doc, a, AccountRules())
    assert doc.line_items[0].gl_account == "202100"


# --------------------------------------------------------------- 수익인식 1115

def test_revenue_needs_performance_date(kctx):
    a = assess(sample(DocType.TAX_INVOICE_OUT), kctx)
    assert "1115" in a.standards
    assert any("수행의무 이행일" in j.question for j in a.judgments)


def test_billing_before_performance_is_contract_liability(kctx):
    doc = sample(DocType.BILLING_REQUEST)
    doc.performance_date = date(2026, 6, 30)       # 전기일 이후 이행
    a = assess(doc, kctx)
    assert a.recognition is Recognition.CONTRACT_LIABILITY
    apply_to_document(doc, a, AccountRules())
    assert all(li.gl_account == "255300" for li in doc.line_items)


def test_revenue_recognized_when_performance_complete(kctx):
    doc = sample(DocType.TAX_INVOICE_OUT)
    doc.performance_date = date(2026, 3, 25)
    a = assess(doc, kctx)
    assert a.recognition is Recognition.REVENUE_NOW
    assert not a.account_overrides


# --------------------------------------------------------------- 리스 1116

def test_long_term_lease_requires_1116_judgment(kctx):
    doc = _ap("본사 사옥 임차료", D("120000000"),
              service_start=date(2026, 1, 1), service_end=date(2028, 12, 31))
    a = assess(doc, kctx)
    j = [x for x in a.judgments if x.standard == "1116"]
    assert j and j[0].blocking


def test_short_term_lease_is_exempt(kctx):
    doc = _ap("단기 사무실 임차료", D("6000000"),
              service_start=date(2026, 1, 1), service_end=date(2026, 6, 30))
    a = assess(doc, kctx)
    assert not [x for x in a.judgments if x.standard == "1116"]
    assert any("면제" in r for r in a.rationale)


# --------------------------------------------------------------- 외화 1021

def test_fx_without_rate_is_blocking(kctx):
    doc = sample(DocType.COMMERCIAL_INVOICE)
    doc.exchange_rate = None
    a = assess(doc, kctx)
    assert any(j.standard == "1021" and j.blocking for j in a.judgments)


def test_fx_with_rate_records_translation_basis(kctx):
    a = assess(sample(DocType.FX_REMITTANCE), kctx)
    assert "1021" in a.standards
    assert any("거래일 환율" in r for r in a.rationale)
    assert any("마감환율" in j.question for j in a.judgments)


# --------------------------------------------------------------- 기타 기준서

def test_promissory_note_long_term_requires_present_value(kctx):
    doc = sample(DocType.PROMISSORY_NOTE)
    doc.due_date = date(2028, 3, 31)
    a = assess(doc, kctx)
    assert any(j.standard == "1109" and j.blocking for j in a.judgments)


def test_payslip_flags_annual_leave_provision(kctx):
    a = assess(sample(DocType.PAYSLIP), kctx)
    assert "1019" in a.standards
    assert any("연차" in j.question for j in a.judgments)


def test_social_insurance_must_not_be_offset(kctx):
    a = assess(sample(DocType.SOCIAL_INSURANCE_BILL), kctx)
    assert "1001" in a.standards
    assert any("상계하지 않고" in r for r in a.rationale)


def test_import_costs_go_to_inventory_cost(kctx):
    a = assess(sample(DocType.IMPORT_DECLARATION), kctx)
    assert "1002" in a.standards
    assert any("취득원가에 포함" in r for r in a.rationale)


# --------------------------------------------------------------- 계획 통합

def test_plan_carries_kifrs_conclusion(kctx, lookup):
    from sap_voucher_agent.master_data import enrich
    doc = sample(DocType.CASH_RECEIPT)
    enrich(doc, lookup)
    p = plan(doc, kctx)
    assert p.kifrs_recognition
    assert p.kifrs_standards
    assert p.kifrs_rationale


def test_plan_does_not_mutate_input_document(kctx, lookup):
    """같은 문서로 두 번 계획해도 결과가 같아야 한다(이연 라인 중복 분할 방지)."""
    from sap_voucher_agent.master_data import enrich
    doc = _ap("연간 유지보수료", D("12000000"), D("1200000"),
              service_start=date(2026, 1, 1), service_end=date(2026, 12, 31))
    doc.supplier.sap_vendor = "0000100234"
    before = len(doc.line_items)
    p1 = plan(doc, kctx)
    p2 = plan(doc, kctx)
    assert len(doc.line_items) == before
    assert len(p1.calls) == len(p2.calls)
    assert p1.amortization_schedule == p2.amortization_schedule


def test_blocking_judgment_gates_posting(kctx, lookup, sap):
    from sap_voucher_agent.master_data import enrich
    from sap_voucher_agent.poster import post
    doc = sample(DocType.TAX_INVOICE_IN)     # ERP 개발 → 1038 판단 필요
    enrich(doc, lookup)
    p = plan(doc, kctx)
    assert p.requires_approval
    assert any("1038" in r for r in p.approval_reasons)
    blocked = post(p, sap, dry_run=False, allow_unapproved=False)
    assert not blocked.success


def test_deferred_plan_produces_balanced_document(kctx, lookup):
    doc = _ap("연간 유지보수료", D("12000000"), D("1200000"),
              service_start=date(2026, 1, 1), service_end=date(2026, 12, 31))
    doc.supplier.sap_vendor = "0000100234"
    p = plan(doc, kctx)
    assert p.postable
    amounts = p.calls[0].params["CURRENCYAMOUNT"]
    total = sum(D(a["AMT_DOCCUR"]) for a in amounts if a.get("CURR_TYPE") == "00")
    assert abs(total) < D("0.01")
    assert p.amortization_schedule
    # 선급비용 라인이 실제 전표에 포함되어야 한다
    assert any(g["GL_ACCOUNT"] == "0000133100" for g in p.calls[0].params["ACCOUNTGL"])


# --------------------------------------------------------------- 조세·수입·정정

def test_import_tax_invoice_is_recoverable_asset_not_cost(kctx):
    """환급 가능한 매입세액은 취득원가가 아니라 자산이다(1002 문단 11)."""
    a = assess(sample(DocType.IMPORT_TAX_INVOICE), kctx)
    assert a.recognition is Recognition.TAX_RECOVERABLE
    assert not a.account_overrides            # 자산 취득으로 오분류하지 않는다
    assert any("취득원가에서 제외" in r for r in a.rationale)


def test_amended_invoice_is_a_correction_requiring_1008_judgment(kctx):
    a = assess(sample(DocType.TAX_INVOICE_AMENDED), kctx)
    assert a.recognition is Recognition.CORRECTION
    j = [x for x in a.judgments if x.standard == "1008"]
    assert j and j[0].blocking
    assert "소급재작성" in j[0].question


def test_vat_payment_is_settlement_not_expense(kctx):
    """부가세는 대리 징수·납부액이므로 손익에 영향을 주지 않는다."""
    a = assess(sample(DocType.NATIONAL_TAX_RECEIPT), kctx)
    assert a.recognition is Recognition.SETTLEMENT
    assert any("수익·비용이 아니다" in r for r in a.rationale)


def test_property_tax_is_expense(kctx):
    a = assess(sample(DocType.LOCAL_TAX_RECEIPT), kctx)
    assert a.recognition is Recognition.EXPENSE_NOW


def test_acquisition_tax_must_be_capitalized(kctx):
    doc = _ap("건물 취득세 납부", D("30000000"), doc_type=DocType.LOCAL_TAX_RECEIPT)
    a = assess(doc, kctx)
    j = [x for x in a.judgments if x.standard == "1016"]
    assert j and j[0].blocking
    assert "취득원가에 가산" in j[0].question


def test_imported_goods_are_inventory(kctx):
    a = assess(sample(DocType.COMMERCIAL_INVOICE), kctx)
    assert a.recognition is Recognition.CAPITALIZE
    assert "1002" in a.standards
    # MIRO 자동계정결정에 맡기므로 계정을 직접 지정하지 않는다
    assert not a.account_overrides


def test_customs_declaration_allocates_duty_to_inventory(kctx):
    a = assess(sample(DocType.IMPORT_DECLARATION), kctx)
    assert a.recognition is Recognition.CAPITALIZE
    assert any("배부기준" in j.question for j in a.judgments)


def test_no_entry_documents_get_no_fx_noise(kctx):
    """인식 대상이 아닌 문서에 외화 판단을 붙이지 않는다."""
    a = assess(sample(DocType.BILL_OF_LADING), kctx)
    assert a.recognition is Recognition.NO_ENTRY
    assert "1021" not in a.standards


def test_materials_purchase_is_inventory(kctx):
    doc = _ap("원재료 입고", D("5000000"), lines=[
        LineItem(line_no=1, description="원재료 A", net_amount=D("5000000"),
                 material="MAT-0001", plant="1000")])
    a = assess(doc, kctx)
    assert a.recognition is Recognition.CAPITALIZE
    assert "1002" in a.standards


def test_fx_remittance_is_settlement(kctx):
    a = assess(sample(DocType.FX_REMITTANCE), kctx)
    assert a.recognition is Recognition.SETTLEMENT
    assert "1021" in a.standards


def test_every_doc_type_has_a_kifrs_conclusion(kctx):
    """50종 전부가 근거 있는 K-IFRS 인식 결론을 갖는다."""
    from sap_voucher_agent.fixtures import FACTORIES
    for dt, factory in FACTORIES.items():
        a = assess(factory(), kctx)
        assert a.recognition, f"{dt} 인식 결론 없음"
        assert a.substance, f"{dt} 거래 실질 설명 없음"
        assert a.standards, f"{dt} 적용 기준서 없음"
        assert a.rationale or a.recognition is Recognition.NO_ENTRY, \
            f"{dt} 판단 근거 없음"


# --------------------------------------------------------------- 기간배분 경계

def _defer_line(desc, amount, start, end, kctx):
    from sap_voucher_agent.kifrs import build_deferral
    doc = VoucherDocument(doc_type=DocType.TAX_INVOICE_IN, doc_date=date(2026, 3, 1))
    li = LineItem(line_no=1, description=desc, net_amount=D(amount),
                  service_start=start, service_end=end)
    return build_deferral(li, doc, kctx)


def test_amortization_never_starts_before_service_begins(kctx):
    """급부를 받기 전에 비용을 인식하면 발생주의에 어긋난다."""
    d = _defer_line("차기 연간 라이선스", "12000000",
                    date(2026, 7, 1), date(2027, 6, 30), kctx)
    assert d is not None
    assert d.current_portion == D(0)
    assert d.schedule[0].posting_date >= date(2026, 7, 1)
    assert len(d.schedule) == 12


def test_amortization_schedule_sums_to_deferred_amount(kctx):
    """나누어떨어지지 않는 금액도 스케줄 합계가 이연액과 정확히 일치해야 한다."""
    for amount, start, end in [
        ("12000000", date(2026, 3, 1), date(2027, 2, 28)),
        ("10000000", date(2026, 3, 1), date(2026, 9, 30)),
        ("7777777", date(2026, 2, 1), date(2027, 1, 31)),
        ("12000000", date(2026, 7, 1), date(2027, 6, 30)),
    ]:
        d = _defer_line("기간계약", amount, start, end, kctx)
        assert d is not None
        assert sum(e.amount for e in d.schedule) == d.deferred_portion
        assert d.current_portion + d.deferred_portion == D(amount)


def test_mostly_elapsed_service_defers_only_remainder(kctx):
    d = _defer_line("전기 개시 연간계약", "12000000",
                    date(2025, 7, 1), date(2026, 6, 30), kctx)
    assert d.current_portion == D("9000000")     # 2025-07 ~ 2026-03 = 9개월
    assert len(d.schedule) == 3


def test_mixed_treatment_document_is_flagged(kctx):
    """자본화와 이연이 섞인 문서는 문서 단위 결론만으로 판단하면 안 된다."""
    doc = _ap("혼합", D(0), lines=[
        LineItem(line_no=1, description="서버 장비 구입", net_amount=D("15000000")),
        LineItem(line_no=2, description="연간 유지보수료", net_amount=D("12000000"),
                 service_start=date(2026, 1, 1), service_end=date(2026, 12, 31))])
    a = assess(doc, kctx)
    assert a.account_overrides and a.deferrals
    assert any("섞여 있다" in r for r in a.rationale)
