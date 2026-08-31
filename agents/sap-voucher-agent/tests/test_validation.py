"""한국 세무·증빙 규칙 검증 테스트."""
from datetime import date
from decimal import Decimal as D

import pytest

from sap_voucher_agent.doc_types import DocType
from sap_voucher_agent.models import LineItem, Party, PostingContext, VoucherDocument
from sap_voucher_agent.validation import valid_biz_reg_no, validate


def _codes(issues):
    return {i.code for i in issues}


def _doc(dt, gross, **kw):
    net = kw.pop("net", gross)
    tax = kw.pop("tax", D(0))
    return VoucherDocument(
        doc_type=dt, doc_date=date(2026, 3, 31),
        supplier=Party(name="테스트상사", biz_reg_no="214-81-01117",
                       sap_vendor="0000100234"),
        net_total=net, tax_total=tax, gross_total=gross,
        line_items=[LineItem(line_no=1, description="테스트", net_amount=net,
                             tax_amount=tax)], **kw)


@pytest.mark.parametrize("value,expected", [
    ("214-81-01117", True), ("2148101117", True),
    ("214-81-01118", False), ("214-81-0111", False), ("", False), (None, False),
])
def test_biz_reg_no_checksum(value, expected):
    assert valid_biz_reg_no(value) is expected


def test_simple_receipt_over_30k_warns(ctx):
    issues = validate(_doc(DocType.SIMPLE_RECEIPT, D("50000")), ctx)
    assert "EVD001" in _codes(issues)
    assert not any(i.blocking for i in issues if i.code == "EVD001")


def test_simple_receipt_under_30k_clean(ctx):
    assert "EVD001" not in _codes(validate(_doc(DocType.SIMPLE_RECEIPT, D("28000")), ctx))


def test_condolence_over_limit_warns(ctx):
    issues = validate(_doc(DocType.CONGRATULATORY_EXPENSE, D("300000")), ctx)
    assert "EVD002" in _codes(issues)


def test_exempt_doc_with_tax_is_blocking(ctx):
    doc = _doc(DocType.TAXI_RECEIPT, D("11000"), net=D("10000"), tax=D("1000"))
    issues = validate(doc, ctx)
    assert any(i.code == "VAT001" and i.blocking for i in issues)


def test_tax_invoice_vat_rate_mismatch_warns(ctx):
    doc = _doc(DocType.TAX_INVOICE_IN, D("1050000"), net=D("1000000"), tax=D("50000"))
    assert "VAT002" in _codes(validate(doc, ctx))


def test_total_mismatch_blocks(ctx):
    doc = _doc(DocType.TAX_INVOICE_IN, D("999"), net=D("1000000"), tax=D("100000"))
    assert any(i.code == "AMT002" and i.blocking for i in validate(doc, ctx))


def test_import_tax_invoice_is_tax_only(ctx):
    doc = VoucherDocument(
        doc_type=DocType.IMPORT_TAX_INVOICE, doc_date=date(2026, 3, 18),
        supplier=Party(name="인천세관장", biz_reg_no="121-83-00111",
                       sap_vendor="0000100323"),
        net_total=D("21000000"), tax_total=D("2100000"), gross_total=D("2100000"))
    assert not any(i.blocking for i in validate(doc, ctx))


def test_ap_without_vendor_mapping_blocks(ctx):
    doc = VoucherDocument(
        doc_type=DocType.TAX_INVOICE_IN, doc_date=date(2026, 3, 31),
        supplier=Party(name="미등록상사", biz_reg_no="214-81-01117"),
        net_total=D("100000"), tax_total=D("10000"), gross_total=D("110000"))
    assert any(i.code == "MST001" and i.blocking for i in validate(doc, ctx))


def test_future_posting_date_blocks(ctx):
    doc = _doc(DocType.CASH_RECEIPT, D("11000"), net=D("10000"), tax=D("1000"),
               posting_date=date(2030, 1, 1))
    assert any(i.code == "DAT002" and i.blocking for i in validate(doc, ctx))


def test_low_confidence_warns(ctx):
    doc = _doc(DocType.CASH_RECEIPT, D("11000"), net=D("10000"), tax=D("1000"))
    doc.doc_type_confidence = 0.4
    assert "EXT002" in _codes(validate(doc, ctx))


def test_amount_threshold_requires_approval(ctx):
    small = PostingContext(company_code="1000", approval_threshold=D("1000"))
    doc = _doc(DocType.CASH_RECEIPT, D("11000"), net=D("10000"), tax=D("1000"))
    assert "APR002" in _codes(validate(doc, small))
