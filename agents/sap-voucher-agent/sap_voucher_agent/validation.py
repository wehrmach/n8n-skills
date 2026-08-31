# -*- coding: utf-8 -*-
"""전기 전 검증 규칙.

두 층위를 검사한다.
 1. 한국 세무·증빙 규칙 - 적격증빙 요건, 손금 한도, 면세/불공제
 2. SAP 전기 요건 - 필수 마스터 매핑, 차대 균형, 기간, 금액 일관성

`ValidationIssue.blocking=True` 면 전기를 중단한다.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import Iterable

from .accounts import AccountRules
from .doc_types import KR_NAME, DocType
from .models import PostingContext, VoucherDocument

# --------------------------------------------------------------------------- 상수

#: 적격증빙(법정지출증빙) 수취 의무 기준금액
QUALIFIED_EVIDENCE_THRESHOLD = Decimal("30000")
#: 경조사비 손금 한도(건당)
CONDOLENCE_LIMIT = Decimal("200000")
#: 증빙불비가산세율
EVIDENCE_PENALTY_RATE = Decimal("0.02")

#: 적격증빙에 해당하는 문서 유형
QUALIFIED_EVIDENCE: frozenset[DocType] = frozenset({
    DocType.TAX_INVOICE_IN, DocType.TAX_INVOICE_OUT, DocType.E_TAX_INVOICE,
    DocType.TAX_INVOICE_AMENDED, DocType.INVOICE_EXEMPT, DocType.IMPORT_TAX_INVOICE,
    DocType.CARD_SALES_SLIP, DocType.CASH_RECEIPT, DocType.UTILITY_BILL,
    DocType.TOLL_RECEIPT, DocType.PARKING_RECEIPT, DocType.RESTAURANT_RECEIPT,
    DocType.LODGING_RECEIPT, DocType.AIR_TICKET_RECEIPT, DocType.RAIL_TICKET_RECEIPT,
})

#: 부가가치세 면세 대상 증빙(세액이 있으면 이상 데이터)
VAT_EXEMPT_DOCS: frozenset[DocType] = frozenset({
    DocType.INVOICE_EXEMPT, DocType.TAXI_RECEIPT,
})

#: 금액이 0원이어도 정상인 문서(물류·첨부 문서)
ZERO_AMOUNT_OK: frozenset[DocType] = frozenset({
    DocType.DELIVERY_NOTE, DocType.PACKING_LIST, DocType.BILL_OF_LADING,
    DocType.BUSINESS_REGISTRATION, DocType.BANKBOOK_COPY,
})

#: 공급가액이 아니라 세액만 기재되는 문서(세금만 있는 송장)
TAX_ONLY_DOCS: frozenset[DocType] = frozenset({DocType.IMPORT_TAX_INVOICE})

#: 명세 합계와 공급가액 합계가 구조적으로 다른 문서
#: (급여: 지급-공제 혼재 / 4대보험: 사업주·근로자 부담 분리)
LINE_SUM_EXEMPT: frozenset[DocType] = frozenset({
    DocType.PAYSLIP, DocType.SOCIAL_INSURANCE_BILL, DocType.BANK_STATEMENT,
})

#: 회계 전기 대상이 아닌 문서(마스터/첨부)
NON_POSTING_DOCS: frozenset[DocType] = frozenset({
    DocType.BUSINESS_REGISTRATION, DocType.BANKBOOK_COPY,
    DocType.EVIDENCE_COVER_SHEET, DocType.PACKING_LIST, DocType.BILL_OF_LADING,
    DocType.QUOTATION,
})


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    message: str
    blocking: bool = False
    field: str = ""

    def __str__(self) -> str:
        mark = "오류" if self.blocking else "경고"
        return f"[{mark}:{self.code}] {self.message}"


# --------------------------------------------------------------------------- 사업자번호

def valid_biz_reg_no(value: str | None) -> bool:
    """사업자등록번호 체크디지트 검증(가중치 1,3,7,1,3,7,1,3,5)."""
    if not value:
        return False
    digits = "".join(ch for ch in value if ch.isdigit())
    if len(digits) != 10:
        return False
    weights = (1, 3, 7, 1, 3, 7, 1, 3, 5)
    total = sum(int(d) * w for d, w in zip(digits[:9], weights))
    total += (int(digits[8]) * 5) // 10
    return (10 - total % 10) % 10 == int(digits[9])


# --------------------------------------------------------------------------- 규칙

def _check_totals(doc: VoucherDocument) -> Iterable[ValidationIssue]:
    if doc.gross_total == 0 and doc.net_total == 0:
        if doc.doc_type not in ZERO_AMOUNT_OK:
            yield ValidationIssue("AMT001", "금액이 0원입니다. 추출 결과를 확인하십시오.",
                                  blocking=True, field="gross_total")
        return
    if doc.doc_type in TAX_ONLY_DOCS:
        # 세관장 발행 수입세금계산서는 세액만 청구된다(공급가액은 과세표준일 뿐).
        if doc.gross_total != doc.tax_total:
            yield ValidationIssue(
                "AMT004",
                f"수입세금계산서의 청구액({doc.gross_total})은 부가세액"
                f"({doc.tax_total})과 같아야 합니다.", blocking=True,
                field="gross_total")
        return
    if not doc.totals_consistent():
        yield ValidationIssue(
            "AMT002",
            f"합계금액 불일치: 공급가액 {doc.net_total} + 세액 {doc.tax_total} "
            f"≠ 합계 {doc.gross_total}", blocking=True, field="gross_total")
    if doc.line_items and doc.doc_type not in LINE_SUM_EXEMPT:
        line_net = sum(li.net_amount for li in doc.line_items)
        if abs(line_net - doc.net_total) > Decimal("1"):
            yield ValidationIssue(
                "AMT003",
                f"명세 합계({line_net})와 공급가액 합계({doc.net_total})가 다릅니다.",
                blocking=True)


def _check_vat(doc: VoucherDocument) -> Iterable[ValidationIssue]:
    if doc.doc_type in VAT_EXEMPT_DOCS and doc.tax_total > 0:
        yield ValidationIssue(
            "VAT001",
            f"{KR_NAME[doc.doc_type]}은(는) 부가세 면세 대상인데 세액 "
            f"{doc.tax_total}원이 기재되어 있습니다.", blocking=True, field="tax_total")
    taxable = doc.doc_type in {
        DocType.TAX_INVOICE_IN, DocType.TAX_INVOICE_OUT, DocType.E_TAX_INVOICE}
    if taxable and doc.net_total > 0:
        expected = (doc.net_total * Decimal("0.1")).quantize(Decimal("1"))
        if abs(doc.tax_total - expected) > Decimal("1"):
            yield ValidationIssue(
                "VAT002",
                f"부가세액이 공급가액의 10%와 다릅니다(기재 {doc.tax_total} / "
                f"계산 {expected}). 영세율·면세 혼재 여부를 확인하십시오.")


def _check_evidence(doc: VoucherDocument) -> Iterable[ValidationIssue]:
    if doc.doc_type == DocType.SIMPLE_RECEIPT and doc.gross_total > QUALIFIED_EVIDENCE_THRESHOLD:
        penalty = (doc.gross_total * EVIDENCE_PENALTY_RATE).quantize(Decimal("1"))
        yield ValidationIssue(
            "EVD001",
            f"간이영수증 {doc.gross_total}원은 3만원 초과 거래로 적격증빙이 아닙니다. "
            f"증빙불비가산세 약 {penalty}원(2%)이 부과될 수 있습니다. "
            "세금계산서·카드전표·현금영수증 수취를 요청하십시오.")
    if doc.doc_type == DocType.CONGRATULATORY_EXPENSE and doc.gross_total > CONDOLENCE_LIMIT:
        yield ValidationIssue(
            "EVD002",
            f"경조사비 {doc.gross_total}원은 손금 한도 {CONDOLENCE_LIMIT}원을 "
            "초과하여 전액 손금불산입 대상입니다. 손금불산입 계정으로 분리하십시오.")
    if doc.doc_type == DocType.RESTAURANT_RECEIPT and doc.gross_total > QUALIFIED_EVIDENCE_THRESHOLD:
        yield ValidationIssue(
            "EVD003",
            "3만원 초과 접대성 지출입니다. 접대 목적이면 매입세액 불공제 세금코드와 "
            "접대 상대방·목적 기록이 필요합니다.")


def _check_parties(doc: VoucherDocument) -> Iterable[ValidationIssue]:
    for label, party in (("공급자", doc.supplier), ("공급받는자", doc.buyer)):
        if party is None or not party.biz_reg_no:
            continue
        if not valid_biz_reg_no(party.biz_reg_no):
            yield ValidationIssue(
                "PTY001",
                f"{label} 사업자등록번호 {party.biz_reg_no} 의 검증번호가 맞지 않습니다. "
                "OCR 오독 여부를 확인하십시오.", field="biz_reg_no")
    if doc.doc_type in QUALIFIED_EVIDENCE and doc.doc_type not in NON_POSTING_DOCS:
        if doc.supplier is None or not doc.supplier.biz_reg_no:
            yield ValidationIssue(
                "PTY002",
                "적격증빙인데 공급자 사업자등록번호가 없습니다. "
                "매입세액 공제가 부인될 수 있습니다.")


def _check_master(doc: VoucherDocument, ctx: PostingContext) -> Iterable[ValidationIssue]:
    from .mapping import AP_INVOICE, AR_INVOICE, route_for
    try:
        route = route_for(doc.doc_type)
    except KeyError:
        yield ValidationIssue("MAP001", f"전기 경로가 없는 문서 유형: {doc.doc_type}",
                              blocking=True)
        return
    if route.posting_kind == AP_INVOICE and not (doc.supplier and doc.supplier.sap_vendor):
        yield ValidationIssue(
            "MST001",
            f"매입 전기에는 SAP 공급업체 코드가 필요합니다. 사업자등록번호 "
            f"{doc.supplier.biz_reg_no if doc.supplier else '?'} 로 거래처 마스터를 "
            "조회하거나 신규 등록하십시오.", blocking=True, field="sap_vendor")
    if route.posting_kind == AR_INVOICE and not (doc.buyer and doc.buyer.sap_customer):
        yield ValidationIssue(
            "MST002", "매출 전기에는 SAP 고객 코드가 필요합니다.",
            blocking=True, field="sap_customer")


def _check_dates(doc: VoucherDocument, ctx: PostingContext,
                 today: date | None = None) -> Iterable[ValidationIssue]:
    today = today or date.today()
    if doc.doc_date is None:
        yield ValidationIssue("DAT001", "증빙 작성일자가 없습니다.", blocking=True,
                              field="doc_date")
        return
    pd = doc.effective_posting_date
    if pd and pd > today + timedelta(days=1):
        yield ValidationIssue(
            "DAT002", f"전기일자 {pd} 가 미래입니다. 전기기간이 열려 있지 않을 수 있습니다.",
            blocking=True, field="posting_date")
    if pd and (today - pd).days > 365:
        yield ValidationIssue(
            "DAT003", f"전기일자 {pd} 가 1년 이상 경과했습니다. 마감된 회계기간일 "
            "가능성이 높습니다.")
    if ctx.fiscal_year and pd and pd.year != ctx.fiscal_year:
        yield ValidationIssue(
            "DAT004",
            f"전기일자 연도({pd.year})와 회계연도({ctx.fiscal_year})가 다릅니다.")


def _check_approval(doc: VoucherDocument, ctx: PostingContext) -> Iterable[ValidationIssue]:
    from .mapping import route_for
    try:
        route = route_for(doc.doc_type)
    except KeyError:
        return
    if route.always_approve:
        yield ValidationIssue(
            "APR001",
            f"{KR_NAME[doc.doc_type]}은(는) 내부통제상 사람 승인이 필요한 문서입니다.")
    if abs(doc.gross_total) > ctx.approval_threshold:
        yield ValidationIssue(
            "APR002",
            f"금액 {doc.gross_total}원이 자동전기 한도 {ctx.approval_threshold}원을 "
            "초과합니다. 승인 후 전기하십시오.")


def _check_extraction(doc: VoucherDocument) -> Iterable[ValidationIssue]:
    if doc.doc_type == DocType.UNKNOWN:
        yield ValidationIssue("EXT001", "문서 유형을 분류하지 못했습니다.", blocking=True)
    if doc.doc_type_confidence < 0.7:
        yield ValidationIssue(
            "EXT002",
            f"문서 유형 분류 신뢰도가 낮습니다({doc.doc_type_confidence:.2f}). "
            "사람 확인을 권장합니다.")
    for w in doc.extraction_warnings:
        yield ValidationIssue("EXT003", f"추출 경고: {w}")


# --------------------------------------------------------------------------- 진입점

def validate(doc: VoucherDocument, ctx: PostingContext,
             rules: AccountRules | None = None,
             today: date | None = None) -> list[ValidationIssue]:
    """모든 검증 규칙을 실행한다."""
    issues: list[ValidationIssue] = []
    issues.extend(_check_extraction(doc))
    if doc.doc_type in NON_POSTING_DOCS:
        issues.append(ValidationIssue(
            "INF001",
            f"{KR_NAME.get(doc.doc_type, doc.doc_type)}은(는) 회계 전기 대상이 아닙니다. "
            "마스터 등록 또는 첨부 처리만 수행합니다."))
        issues.extend(_check_parties(doc))
        issues.extend(_check_approval(doc, ctx))
        return issues
    issues.extend(_check_totals(doc))
    issues.extend(_check_vat(doc))
    issues.extend(_check_evidence(doc))
    issues.extend(_check_parties(doc))
    issues.extend(_check_master(doc, ctx))
    issues.extend(_check_dates(doc, ctx, today))
    issues.extend(_check_approval(doc, ctx))
    return issues


def blocking(issues: list[ValidationIssue]) -> list[ValidationIssue]:
    return [i for i in issues if i.blocking]
