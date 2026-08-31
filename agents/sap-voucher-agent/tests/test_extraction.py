"""판독(추출) 계층 테스트.

실제 Claude 호출 없이 두 가지를 검증한다.
 1. 요청 구성 - document 블록, 구조화 출력 스키마, 시스템 프롬프트 캐시
 2. 응답 변환 - 문자열 금액/날짜 → Decimal/date, 결측치 보정, 경고 전파
"""
from datetime import date
from decimal import Decimal as D

import pytest

from sap_voucher_agent import extraction as ex
from sap_voucher_agent.doc_types import DocType
from sap_voucher_agent.extraction import (ExtractedLine, ExtractedParty,
                                          ExtractedVoucher, to_voucher)


def _party(**kw):
    base = dict(name="", biz_reg_no="", ceo="", address="", biz_type="", biz_item="")
    base.update(kw)
    return ExtractedParty(**base)


def _extracted(**kw) -> ExtractedVoucher:
    base = dict(
        doc_type=DocType.TAX_INVOICE_IN, doc_type_reason="세금계산서 표제",
        confidence=0.96, doc_number="20260331-41000012-88776655",
        doc_date="2026-03-31", due_date="",
        supplier=_party(name="(주)한빛테크놀로지", biz_reg_no="214-81-01117"),
        buyer=_party(name="(주)미래유통", biz_reg_no="137-81-23454"),
        currency="KRW", exchange_rate="",
        net_total="12500000", tax_total="1250000", gross_total="13750000",
        line_items=[ExtractedLine(
            line_no=1, description="ERP 연동 모듈 개발", spec="1식", quantity="1",
            unit="식", unit_price="8000000", net_amount="8000000",
            tax_amount="800000", account_hint="", service_start="",
            service_end="")],
        payment_method="계좌이체", service_start="", service_end="",
        performance_date="", withholding_income_tax="",
        withholding_local_tax="", bank_name="", bank_account_no="",
        reference_po="", reference_original_doc="", notes="", warnings=[])
    base.update(kw)
    return ExtractedVoucher(**base)


# --------------------------------------------------------------------------- 변환

@pytest.mark.parametrize("raw,expected", [
    ("13,750,000", D("13750000")), ("￦13,750,000", D("13750000")),
    ("-1,250,000", D("-1250000")), ("", D(0)), ("△0", D(0)),
])
def test_amount_parsing(raw, expected):
    assert ex._dec(raw) == expected


@pytest.mark.parametrize("raw,expected", [
    ("2026-03-31", date(2026, 3, 31)), ("2026.03.31", date(2026, 3, 31)),
    ("20260331", date(2026, 3, 31)), ("2026년 03월 31일", date(2026, 3, 31)),
    ("", None), ("날짜없음", None),
])
def test_date_parsing(raw, expected):
    assert ex._date(raw) == expected


def test_to_voucher_maps_core_fields():
    doc = to_voucher(_extracted(), source_file="01.pdf")
    assert doc.doc_type is DocType.TAX_INVOICE_IN
    assert doc.doc_date == date(2026, 3, 31)
    assert doc.net_total == D("12500000") and doc.tax_total == D("1250000")
    assert doc.totals_consistent()
    assert doc.supplier.biz_reg_no == "214-81-01117"
    assert doc.line_items[0].quantity == D(1)
    assert doc.source_file == "01.pdf"


def test_missing_gross_is_derived_with_warning():
    doc = to_voucher(_extracted(gross_total=""))
    assert doc.gross_total == D("13750000")
    assert any("합계금액" in w for w in doc.extraction_warnings)


def test_empty_party_becomes_none():
    doc = to_voucher(_extracted(buyer=_party()))
    assert doc.buyer is None


def test_withholding_is_built():
    doc = to_voucher(_extracted(
        doc_type=DocType.WHT_BUSINESS, net_total="3000000", tax_total="0",
        gross_total="3000000", withholding_income_tax="90000",
        withholding_local_tax="9000"))
    assert doc.withholding is not None
    assert doc.withholding.total == D("99000")


def test_negative_amounts_survive_for_amended_invoice():
    doc = to_voucher(_extracted(
        doc_type=DocType.TAX_INVOICE_AMENDED, net_total="-12500000",
        tax_total="-1250000", gross_total="-13750000"))
    assert doc.gross_total == D("-13750000")
    assert doc.totals_consistent()


def test_service_period_and_performance_date_are_parsed():
    """K-IFRS 기간귀속 판단에 쓰이는 날짜가 도메인 모델로 넘어와야 한다."""
    doc = to_voucher(_extracted(
        service_start="2026-01-01", service_end="2026-12-31",
        performance_date="2026-03-25",
        line_items=[ExtractedLine(
            line_no=1, description="연간 유지보수", spec="", quantity="1",
            unit="식", unit_price="12000000", net_amount="12000000",
            tax_amount="1200000", account_hint="",
            service_start="2026-01-01", service_end="2026-12-31")]))
    assert doc.service_start == date(2026, 1, 1)
    assert doc.service_end == date(2026, 12, 31)
    assert doc.performance_date == date(2026, 3, 25)
    assert doc.line_items[0].service_end == date(2026, 12, 31)


def test_performance_date_is_not_guessed_from_doc_date():
    """문서에 없으면 작성일로 대체하지 않는다(K-IFRS 1115 인식일 오류 방지)."""
    doc = to_voucher(_extracted(performance_date=""))
    assert doc.performance_date is None


def test_system_prompt_demands_period_extraction():
    assert "service_start" in ex.SYSTEM_PROMPT
    assert "performance_date" in ex.SYSTEM_PROMPT
    assert "추측하지 않는다" in ex.SYSTEM_PROMPT


def test_reference_docs_are_carried():
    doc = to_voucher(_extracted(reference_po="PO-2026-0198",
                                reference_original_doc="20260331-000001"))
    assert doc.reference_docs["po_number"] == "PO-2026-0198"
    assert doc.reference_docs["original_document"] == "20260331-000001"


# --------------------------------------------------------------------------- 요청 구성

class _FakeMessages:
    def __init__(self):
        self.kwargs = None

    def parse(self, **kwargs):
        self.kwargs = kwargs

        class R:
            parsed_output = _extracted()
        return R()


class _FakeClient:
    def __init__(self):
        self.messages = _FakeMessages()


def test_extract_builds_pdf_request(tmp_path):
    pdf = tmp_path / "sample.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake")
    client = _FakeClient()

    doc = ex.extract(pdf, client=client)

    kw = client.messages.kwargs
    assert kw["model"] == "claude-opus-5"
    assert kw["output_format"] is ExtractedVoucher
    assert kw["thinking"] == {"type": "adaptive"}
    # 시스템 프롬프트는 캐시되어야 반복 판독 비용이 줄어든다
    assert kw["system"][0]["cache_control"] == {"type": "ephemeral"}
    # 문서 블록이 텍스트 지시문보다 앞에 와야 한다
    content = kw["messages"][0]["content"]
    assert content[0]["type"] == "document"
    assert content[0]["source"]["media_type"] == "application/pdf"
    assert content[1]["type"] == "text"
    assert doc.doc_type is DocType.TAX_INVOICE_IN


def test_extract_rejects_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        ex.extract(tmp_path / "없는파일.pdf", client=_FakeClient())


def test_system_prompt_lists_all_50_types():
    for dt in DocType:
        if dt is DocType.UNKNOWN:
            continue
        assert dt.value in ex.SYSTEM_PROMPT, f"{dt.value} 가 분류표에 없다"
