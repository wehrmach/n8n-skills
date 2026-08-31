# -*- coding: utf-8 -*-
"""50종 증빙의 대표 샘플 데이터.

`samples/korean-vouchers/` 의 PDF 샘플과 같은 가상 데이터를 코드로 재현한다.
LLM 추출 없이 매핑·빌더·전기 경로를 회귀 테스트하는 데 쓴다.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal as D
from typing import Callable

from .doc_types import DocType
from .models import (BankAccount, LineItem, Party, VoucherDocument,
                     WithholdingTax)

SUPPLIER = dict(name="(주)한빛테크놀로지", biz_reg_no="214-81-01117", ceo="김한빛",
                address="서울특별시 강남구 테헤란로 123, 8층",
                biz_type="서비스", biz_item="소프트웨어 개발")
BUYER = dict(name="(주)미래유통", biz_reg_no="137-81-23454", ceo="박미래",
             address="경기도 성남시 분당구 판교로 45, 3층",
             biz_type="도소매", biz_item="전자제품")

DEAL_LINES = [
    LineItem(line_no=1, description="ERP 연동 모듈 개발(설계·구현)", unit="식",
             quantity=D(1), unit_price=D("8000000"),
             net_amount=D("8000000"), tax_amount=D("800000")),
    LineItem(line_no=2, description="데이터 마이그레이션 용역", unit="식",
             quantity=D(1), unit_price=D("3000000"),
             net_amount=D("3000000"), tax_amount=D("300000")),
    LineItem(line_no=3, description="사용자 교육 및 매뉴얼 제작", unit="회",
             quantity=D(3), unit_price=D("500000"),
             net_amount=D("1500000"), tax_amount=D("150000")),
]


def _doc(dt: DocType, **kw) -> VoucherDocument:
    base = dict(doc_type=dt, doc_date=date(2026, 3, 31), currency="KRW",
                doc_type_confidence=0.95)
    base.update(kw)
    return VoucherDocument(**base)


def _simple(dt: DocType, desc: str, net: str, tax: str, *,
            supplier: dict | None = None, pay: str | None = None,
            doc_no: str = "", **kw) -> VoucherDocument:
    n, t = D(net), D(tax)
    return _doc(dt, doc_number=doc_no or None,
                supplier=Party(**(supplier or SUPPLIER)),
                buyer=Party(**BUYER),
                net_total=n, tax_total=t, gross_total=n + t,
                payment_method=pay,
                line_items=[LineItem(line_no=1, description=desc,
                                     net_amount=n, tax_amount=t)], **kw)


VENDOR_MUNGU = dict(name="한빛문구 역삼점", biz_reg_no="220-15-09875")
VENDOR_OFFICE = dict(name="대한사무기기(주)", biz_reg_no="106-81-02227")
VENDOR_QUICK = dict(name="번개퀵서비스", biz_reg_no="118-22-04560")
VENDOR_FOOD = dict(name="고향식당", biz_reg_no="120-15-08881")
VENDOR_HOTEL = dict(name="대한호텔 부산", biz_reg_no="605-81-02229")
VENDOR_AIR = dict(name="코리아항공(주)", biz_reg_no="110-81-04447")
VENDOR_RAIL = dict(name="대한철도공사", biz_reg_no="314-82-05555")
VENDOR_TAXI = dict(name="대한교통(주)", biz_reg_no="220-81-07775")
VENDOR_FOUND = dict(name="사단법인 한빛나눔재단", biz_reg_no="102-82-03333")


FACTORIES: dict[DocType, Callable[[], VoucherDocument]] = {}


def _reg(dt: DocType):
    def deco(fn: Callable[[], VoucherDocument]):
        FACTORIES[dt] = fn
        return fn
    return deco


# ── 적격증빙 ───────────────────────────────────────────────────────────────
@_reg(DocType.TAX_INVOICE_IN)
def _f01():
    return _doc(DocType.TAX_INVOICE_IN,
                doc_number="20260331-41000012-88776655",
                supplier=Party(**SUPPLIER), buyer=Party(**BUYER),
                net_total=D("12500000"), tax_total=D("1250000"),
                gross_total=D("13750000"),
                line_items=[li.model_copy(deep=True) for li in DEAL_LINES],
                payment_method="계좌이체")


@_reg(DocType.TAX_INVOICE_OUT)
def _f02():
    """자사 발행 매출 세금계산서(공급자 보관용). 매입분과는 별개 거래다."""
    d = _f01()
    d.doc_type = DocType.TAX_INVOICE_OUT
    d.doc_number = "20260331-41000012-11223344"
    d.supplier, d.buyer = Party(**SUPPLIER), Party(**BUYER)
    return d


@_reg(DocType.E_TAX_INVOICE)
def _f03():
    d = _f01()
    d.doc_type = DocType.E_TAX_INVOICE
    d.doc_number = "20260401-41000012-99887766"
    d.reference_docs = {"po_number": "PO-2026-0198", "sap_po": "4500000001"}
    for i, li in enumerate(d.line_items, 1):
        li.po_number = "4500000001"
        li.po_item = f"{i*10:05d}"
    return d


@_reg(DocType.TAX_INVOICE_AMENDED)
def _f04():
    return _doc(DocType.TAX_INVOICE_AMENDED, doc_number="2026-000418",
                supplier=Party(**SUPPLIER), buyer=Party(**BUYER),
                net_total=D("-12500000"), tax_total=D("-1250000"),
                gross_total=D("-13750000"),
                line_items=[LineItem(line_no=1, description="ERP 연동 모듈 개발(당초분 취소)",
                                     net_amount=D("-12500000"), tax_amount=D("-1250000"))],
                reference_docs={"original_document": "000000012310002026",
                                "reversal_reason": "01"},
                notes="기재사항 착오·정정(코드 04)")


@_reg(DocType.INVOICE_EXEMPT)
def _f05():
    return _doc(DocType.INVOICE_EXEMPT, doc_number="2026-000031",
                supplier=Party(**SUPPLIER), buyer=Party(**BUYER),
                net_total=D("4000000"), tax_total=D(0), gross_total=D("4000000"),
                line_items=[
                    LineItem(line_no=1, description="직업능력개발 위탁교육(면세)",
                             net_amount=D("3000000")),
                    LineItem(line_no=2, description="도서 구입 (기술서적)",
                             net_amount=D("1000000"))])


@_reg(DocType.IMPORT_TAX_INVOICE)
def _f06():
    return _doc(DocType.IMPORT_TAX_INVOICE, doc_number="2026-IMP-0451",
                supplier=Party(name="인천세관장", biz_reg_no="121-83-00111"),
                buyer=Party(**SUPPLIER),
                net_total=D("21000000"), tax_total=D("2100000"),
                gross_total=D("2100000"),
                line_items=[LineItem(line_no=1, description="수입 부가세(노트북 50대)",
                                     net_amount=D("21000000"), tax_amount=D("2100000"))],
                notes="세관장 발행 수입세금계산서")


@_reg(DocType.CARD_SALES_SLIP)
def _f07():
    return _simple(DocType.CARD_SALES_SLIP, "사무용품 구입(A4 복사용지 외 3건)",
                   "345455", "34545", supplier=VENDOR_MUNGU, pay="신용카드",
                   doc_no="30117742", doc_date=date(2026, 3, 17))


@_reg(DocType.CASH_RECEIPT)
def _f08():
    return _simple(DocType.CASH_RECEIPT, "A4 복사용지 외 3건", "163636", "16364",
                   supplier=VENDOR_OFFICE, pay="현금", doc_no="848112390",
                   doc_date=date(2026, 3, 25))


# ── 상거래 ─────────────────────────────────────────────────────────────────
@_reg(DocType.QUOTATION)
def _f09():
    d = _f01()
    d.doc_type = DocType.QUOTATION
    d.doc_number = "QT-2026-0173"
    d.doc_date = date(2026, 2, 27)
    d.due_date = date(2026, 3, 29)
    return d


@_reg(DocType.PURCHASE_ORDER)
def _f10():
    d = _f01()
    d.doc_type = DocType.PURCHASE_ORDER
    d.doc_number = "PO-2026-0198"
    d.doc_date = date(2026, 3, 2)
    d.due_date = date(2026, 3, 31)
    return d


@_reg(DocType.DELIVERY_STATEMENT)
def _f11():
    d = _f01()
    d.doc_type = DocType.DELIVERY_STATEMENT
    d.doc_number = "TS-2026-0331-07"
    d.reference_docs = {"po_number": "PO-2026-0198", "sap_po": "4500000001"}
    for i, li in enumerate(d.line_items, 1):
        li.po_number = "4500000001"
        li.po_item = f"{i*10:05d}"
        li.material = f"MAT-{i:04d}"
        li.plant = "1000"
    return d


@_reg(DocType.BILLING_REQUEST)
def _f12():
    d = _f01()
    d.doc_type = DocType.BILLING_REQUEST
    d.doc_number = "IV-2026-0331-02"
    d.due_date = date(2026, 4, 25)
    return d


@_reg(DocType.PAYMENT_RECEIPT)
def _f13():
    return _doc(DocType.PAYMENT_RECEIPT, doc_number="RC-2026-0425-11",
                doc_date=date(2026, 4, 25),
                supplier=Party(**SUPPLIER), buyer=Party(**BUYER),
                net_total=D("13750000"), tax_total=D(0), gross_total=D("13750000"),
                payment_method="계좌이체",
                line_items=[LineItem(line_no=1, description="용역대금 입금",
                                     net_amount=D("13750000"))])


@_reg(DocType.GOODS_ACCEPTANCE)
def _f14():
    d = _f01()
    d.doc_type = DocType.GOODS_ACCEPTANCE
    d.doc_number = "IN-2026-0331-05"
    d.reference_docs = {"sap_po": "4500000001", "sap_po_item": "00010"}
    return d


@_reg(DocType.DELIVERY_NOTE)
def _f15():
    return _doc(DocType.DELIVERY_NOTE, doc_number="6412-8890-3371",
                supplier=Party(**SUPPLIER), buyer=Party(**BUYER),
                net_total=D(0), tax_total=D(0), gross_total=D(0),
                reference_docs={"sap_po": "4500000001"},
                line_items=[
                    LineItem(line_no=1, description="서버 장비 (구축용)", unit="대",
                             quantity=D(2), net_amount=D(0), material="MAT-0001",
                             plant="1000", po_number="4500000001", po_item="00010"),
                    LineItem(line_no=2, description="산출물 문서 일체", unit="권",
                             quantity=D(5), net_amount=D(0), material="MAT-0002",
                             plant="1000", po_number="4500000001", po_item="00020")])


@_reg(DocType.SERVICE_CONTRACT)
def _f16():
    d = _f01()
    d.doc_type = DocType.SERVICE_CONTRACT
    d.doc_number = "CT-2026-0032"
    d.doc_date = date(2026, 3, 2)
    d.due_date = date(2027, 3, 1)
    return d


# ── 내부 회계 ──────────────────────────────────────────────────────────────
@_reg(DocType.EXPENSE_RESOLUTION)
def _f17():
    lines = [
        ("사무용품 구입 (A4용지 외)", "345455", "34545"),
        ("거래처 접대 (중식)", "140000", "14000"),
        ("택배 발송비", "32000", "0"),
        ("직원 교육 수강료", "660000", "0"),
        ("사무실 정수기 임차료", "40000", "4000"),
    ]
    items = [LineItem(line_no=i, description=t, net_amount=D(n), tax_amount=D(x))
             for i, (t, n, x) in enumerate(lines, 1)]
    net = sum(li.net_amount for li in items)
    tax = sum(li.tax_amount for li in items)
    return _doc(DocType.EXPENSE_RESOLUTION, doc_number="경지-2026-0331-14",
                supplier=Party(**SUPPLIER), net_total=net, tax_total=tax,
                gross_total=net + tax, line_items=items, payment_method="계좌이체")


@_reg(DocType.PURCHASE_APPROVAL)
def _f18():
    d = _f01()
    d.doc_type = DocType.PURCHASE_APPROVAL
    d.doc_number = "구매-2026-0221-03"
    d.doc_date = date(2026, 2, 21)
    d.due_date = date(2026, 3, 31)
    return d


@_reg(DocType.TRAVEL_SETTLEMENT)
def _f19():
    lines = [("KTX 서울→부산 (왕복)", "119600"), ("부산 시내 택시 3회", "34800"),
             ("숙박 (부산 1박)", "88000"), ("식대 (3식)", "42000"),
             ("일비 (2일)", "40000"), ("거래처 미팅 다과", "23000")]
    items = [LineItem(line_no=i, description=t, net_amount=D(a))
             for i, (t, a) in enumerate(lines, 1)]
    net = sum(li.net_amount for li in items)
    return _doc(DocType.TRAVEL_SETTLEMENT, doc_number="TRV-2026-0311",
                doc_date=date(2026, 3, 11), due_date=date(2026, 3, 10),
                supplier=Party(**SUPPLIER), net_total=net, tax_total=D(0),
                gross_total=net, line_items=items,
                reference_docs={"employee_no": "00001042",
                                "advance_amount": "300000"},
                notes="부산 신규 거래처 방문")


@_reg(DocType.CORPORATE_CARD_STMT)
def _f20():
    lines = [("사무용품", "45000", "0"), ("A4용지 외", "345455", "34545"),
             ("거래처 중식 접대(4인)", "140000", "14000"),
             ("차량 주유(법인차량)", "83636", "8364"),
             ("국내선 항공권", "126000", "12600"),
             ("숙박 1박", "120000", "12000"),
             ("클라우드 서버 사용료(해외)", "217400", "0"),
             ("사내 회의 다과", "25909", "2591")]
    items = [LineItem(line_no=i, description=t, net_amount=D(n), tax_amount=D(x))
             for i, (t, n, x) in enumerate(lines, 1)]
    net = sum(li.net_amount for li in items)
    tax = sum(li.tax_amount for li in items)
    return _doc(DocType.CORPORATE_CARD_STMT, doc_number="CARD-2026-03",
                supplier=Party(name="대한카드(주)", biz_reg_no="202-81-48929"),
                buyer=Party(**SUPPLIER), due_date=date(2026, 4, 15),
                net_total=net, tax_total=tax, gross_total=net + tax,
                line_items=items, payment_method="법인카드")


@_reg(DocType.CONGRATULATORY_EXPENSE)
def _f21():
    return _simple(DocType.CONGRATULATORY_EXPENSE, "거래처 임직원 자녀 결혼 축의금",
                   "200000", "0", supplier=SUPPLIER, pay="현금",
                   doc_no="경지-2026-0314-08", doc_date=date(2026, 3, 20))


@_reg(DocType.PETTY_CASH_SETTLEMENT)
def _f22():
    lines = [("우편·등기 발송", "12800"), ("사무실 생수 구입", "24000"),
             ("퀵서비스(계약서 송부)", "18000"), ("명함 제작 (3인분)", "45000"),
             ("회의용 다과", "31500"), ("청소용품 구입", "16700"),
             ("등기부등본 발급 수수료", "3000")]
    items = [LineItem(line_no=i, description=t, net_amount=D(a))
             for i, (t, a) in enumerate(lines, 1)]
    net = sum(li.net_amount for li in items)
    return _doc(DocType.PETTY_CASH_SETTLEMENT, doc_number="PC-2026-03",
                supplier=Party(**SUPPLIER), net_total=net, tax_total=D(0),
                gross_total=net, line_items=items, payment_method="현금")


# ── 인사·급여 ──────────────────────────────────────────────────────────────
@_reg(DocType.PAYSLIP)
def _f23():
    items = [
        LineItem(line_no=1, description="기본급", net_amount=D("4200000")),
        LineItem(line_no=2, description="직책수당", net_amount=D("300000")),
        LineItem(line_no=3, description="식대(비과세)", net_amount=D("200000")),
        LineItem(line_no=4, description="자가운전보조금(비과세)", net_amount=D("200000")),
        LineItem(line_no=5, description="연장근로수당", net_amount=D("412500")),
        LineItem(line_no=6, description="국민연금", net_amount=D("-265500")),
        LineItem(line_no=7, description="건강보험", net_amount=D("-209130")),
        LineItem(line_no=8, description="장기요양보험", net_amount=D("-27070")),
        LineItem(line_no=9, description="고용보험", net_amount=D("-44325")),
        LineItem(line_no=10, description="소득세", net_amount=D("-253060")),
        LineItem(line_no=11, description="지방소득세", net_amount=D("-25300")),
    ]
    gross = sum(li.net_amount for li in items if li.net_amount > 0)
    return _doc(DocType.PAYSLIP, doc_number="PAY-2026-03",
                doc_date=date(2026, 3, 25), supplier=Party(**SUPPLIER),
                net_total=gross, tax_total=D(0), gross_total=gross,
                line_items=items,
                reference_docs={"employee_no": "00001042"})


@_reg(DocType.WHT_EMPLOYMENT)
def _f24():
    return _doc(DocType.WHT_EMPLOYMENT, doc_number="2026-KR-00142",
                doc_date=date(2026, 2, 28), supplier=Party(**SUPPLIER),
                net_total=D("-453420"), tax_total=D(0), gross_total=D("-453420"),
                line_items=[LineItem(line_no=1, description="연말정산 차감징수(환급)액",
                                     net_amount=D("-453420"))],
                notes="근로소득 연말정산 환급")


@_reg(DocType.WHT_BUSINESS)
def _f25():
    return _doc(DocType.WHT_BUSINESS, doc_number="2026-BS-0087",
                doc_date=date(2026, 3, 25),
                supplier=Party(name="최프리", biz_reg_no=None),
                buyer=Party(**SUPPLIER),
                net_total=D("3000000"), tax_total=D(0), gross_total=D("3000000"),
                line_items=[LineItem(line_no=1, description="UI/UX 디자인 외주 용역",
                                     net_amount=D("3000000"))],
                withholding=WithholdingTax(wt_type="K1", wt_code="03",
                                           base_amount=D("3000000"),
                                           income_tax=D("90000"),
                                           local_income_tax=D("9000")))


@_reg(DocType.DAILY_WORKER_PAYMENT)
def _f26():
    items = [LineItem(line_no=1, description="일용노무비(김일용 8일)", net_amount=D("1280000")),
             LineItem(line_no=2, description="일용노무비(박일용 6일)", net_amount=D("960000")),
             LineItem(line_no=3, description="일용노무비(최일용 10일)", net_amount=D("1700000"))]
    net = sum(li.net_amount for li in items)
    return _doc(DocType.DAILY_WORKER_PAYMENT, doc_number="DW-2026-03",
                supplier=Party(**SUPPLIER), net_total=net, tax_total=D(0),
                gross_total=net, line_items=items)


@_reg(DocType.SOCIAL_INSURANCE_BILL)
def _f27():
    items = [
        LineItem(line_no=1, description="국민연금", net_amount=D("1991250"),
                 unit_price=D("1991250")),
        LineItem(line_no=2, description="건강보험", net_amount=D("1568663"),
                 unit_price=D("1568662")),
        LineItem(line_no=3, description="장기요양보험", net_amount=D("203140"),
                 unit_price=D("203140")),
        LineItem(line_no=4, description="고용보험", net_amount=D("553125"),
                 unit_price=D("398250")),
        LineItem(line_no=5, description="산재보험", net_amount=D("323025"),
                 unit_price=D(0)),
    ]
    employer = sum(li.net_amount for li in items)
    employee = sum(li.unit_price or D(0) for li in items)
    return _doc(DocType.SOCIAL_INSURANCE_BILL, doc_number="26-03-0000-1142",
                doc_date=date(2026, 4, 10), supplier=Party(**SUPPLIER),
                net_total=employer + employee, tax_total=D(0),
                gross_total=employer + employee, line_items=items,
                payment_method="계좌이체")


# ── 세금·공과금 ────────────────────────────────────────────────────────────
@_reg(DocType.NATIONAL_TAX_RECEIPT)
def _f28():
    return _doc(DocType.NATIONAL_TAX_RECEIPT, doc_number="0126-1-14-26-0-4318000",
                doc_date=date(2026, 4, 27), supplier=Party(**SUPPLIER),
                net_total=D("4318000"), tax_total=D(0), gross_total=D("4318000"),
                line_items=[LineItem(line_no=1, description="부가가치세 자진납부",
                                     net_amount=D("4318000"))],
                payment_method="계좌이체", notes="2026년 제1기 예정 부가가치세")


@_reg(DocType.LOCAL_TAX_RECEIPT)
def _f29():
    return _doc(DocType.LOCAL_TAX_RECEIPT, doc_number="11680-1-26-09-0000142",
                doc_date=date(2026, 7, 28), supplier=Party(**SUPPLIER),
                net_total=D("1644000"), tax_total=D(0), gross_total=D("1644000"),
                line_items=[LineItem(line_no=1, description="재산세(건축물) 외",
                                     net_amount=D("1644000"))],
                payment_method="계좌이체", notes="재산세·지방교육세·지역자원시설세")


@_reg(DocType.UTILITY_BILL)
def _f30():
    return _simple(DocType.UTILITY_BILL, "전기요금 2026년 3월분", "435000", "43500",
                   supplier=dict(name="한빛에너지(주)", biz_reg_no="120-81-00190"),
                   pay="자동이체", doc_no="0142-8891-33")


@_reg(DocType.DONATION_RECEIPT)
def _f31():
    return _simple(DocType.DONATION_RECEIPT, "아동 교육환경 개선 사업 후원금",
                   "8000000", "0", supplier=VENDOR_FOUND, pay="계좌이체",
                   doc_no="2026-0000-0451")


# ── 금융 ───────────────────────────────────────────────────────────────────
@_reg(DocType.BANK_STATEMENT)
def _f32():
    items = [
        LineItem(line_no=1, description="㈜대한상사 매출대금 입금", net_amount=D("22000000")),
        LineItem(line_no=2, description="㈜세종물산 매출대금 입금", net_amount=D("18700000")),
        LineItem(line_no=3, description="예금이자", net_amount=D("42310")),
    ]
    net = sum(li.net_amount for li in items)
    return _doc(DocType.BANK_STATEMENT, doc_number="STMT-2026-03",
                supplier=Party(**SUPPLIER), net_total=net, tax_total=D(0),
                gross_total=net, line_items=items,
                bank_account=BankAccount(bank_name="대한은행",
                                         account_no="123-456789-01-001"))


@_reg(DocType.WIRE_TRANSFER_SLIP)
def _f33():
    return _doc(DocType.WIRE_TRANSFER_SLIP, doc_number="2026042509331100781",
                doc_date=date(2026, 4, 25),
                supplier=Party(**SUPPLIER), buyer=Party(**BUYER),
                net_total=D("13750000"), tax_total=D(0), gross_total=D("13750000"),
                payment_method="계좌이체",
                line_items=[LineItem(line_no=1, description="용역대금 이체",
                                     net_amount=D("13750000"))])


@_reg(DocType.PROMISSORY_NOTE)
def _f34():
    return _doc(DocType.PROMISSORY_NOTE, doc_number="자가 12345678",
                doc_date=date(2026, 3, 31), due_date=date(2026, 9, 30),
                supplier=Party(**BUYER), buyer=Party(**SUPPLIER),
                net_total=D("30000000"), tax_total=D(0), gross_total=D("30000000"),
                payment_method="어음", notes="발행어음(지급어음)",
                line_items=[LineItem(line_no=1, description="약속어음 발행",
                                     net_amount=D("30000000"))])


@_reg(DocType.FX_REMITTANCE)
def _f35():
    return _doc(DocType.FX_REMITTANCE, doc_number="DHB-2026-FT-0031882",
                doc_date=date(2026, 3, 18), currency="USD",
                exchange_rate=D("1342.50"),
                supplier=Party(name="GLOBAL SOFT SOLUTIONS PTE. LTD.",
                               biz_reg_no=None),
                buyer=Party(**SUPPLIER),
                net_total=D("12500.00"), tax_total=D(0), gross_total=D("12500.00"),
                line_items=[LineItem(line_no=1, description="해외 소프트웨어 라이선스 사용료",
                                     net_amount=D("12500.00"))],
                payment_method="계좌이체")


# ── 여비·소액 ──────────────────────────────────────────────────────────────
@_reg(DocType.SIMPLE_RECEIPT)
def _f36():
    return _simple(DocType.SIMPLE_RECEIPT, "퀵서비스 운송료 및 포장자재",
                   "28000", "0", supplier=VENDOR_QUICK, pay="현금", doc_no="0142",
                   doc_date=date(2026, 3, 17))


@_reg(DocType.TAXI_RECEIPT)
def _f37():
    return _simple(DocType.TAXI_RECEIPT, "택시 이용(강남역→서울역)", "12100", "0",
                   supplier=VENDOR_TAXI, pay="법인카드", doc_no="21883047",
                   doc_date=date(2026, 3, 9))


@_reg(DocType.TOLL_RECEIPT)
def _f38():
    return _simple(DocType.TOLL_RECEIPT, "고속도로 통행료(서울→부산)", "19182", "1918",
                   supplier=dict(name="한국도로공사", biz_reg_no="201-82-00026"),
                   pay="하이패스", doc_no="2026-0309-118842", doc_date=date(2026, 3, 9))


@_reg(DocType.PARKING_RECEIPT)
def _f39():
    return _simple(DocType.PARKING_RECEIPT, "주차요금(한빛빌딩)", "5000", "500",
                   supplier=dict(name="한빛빌딩 주차장", biz_reg_no="214-81-29997"),
                   pay="현금영수증", doc_no="771204558", doc_date=date(2026, 3, 11))


@_reg(DocType.RESTAURANT_RECEIPT)
def _f40():
    return _simple(DocType.RESTAURANT_RECEIPT, "거래처 접대 중식(4인)", "140000", "14000",
                   supplier=VENDOR_FOOD, pay="법인카드", doc_no="44120987",
                   doc_date=date(2026, 3, 11))


@_reg(DocType.LODGING_RECEIPT)
def _f41():
    return _simple(DocType.LODGING_RECEIPT, "출장 숙박(부산 1박)", "80000", "8000",
                   supplier=VENDOR_HOTEL, pay="법인카드",
                   doc_no="BS-2026-0309-1142", doc_date=date(2026, 3, 10))


@_reg(DocType.AIR_TICKET_RECEIPT)
def _f42():
    return _simple(DocType.AIR_TICKET_RECEIPT, "국내선 항공권(김포-제주 왕복)",
                   "126000", "12600", supplier=VENDOR_AIR, pay="법인카드",
                   doc_no="180-2411882910", doc_date=date(2026, 3, 14))


@_reg(DocType.RAIL_TICKET_RECEIPT)
def _f43():
    return _simple(DocType.RAIL_TICKET_RECEIPT, "KTX 승차권(서울-부산 왕복)",
                   "108727", "10873", supplier=VENDOR_RAIL, pay="법인카드",
                   doc_no="26030-9-0114-2288", doc_date=date(2026, 3, 7))


# ── 무역 ───────────────────────────────────────────────────────────────────
@_reg(DocType.COMMERCIAL_INVOICE)
def _f44():
    items = [
        LineItem(line_no=1, description="NOTEBOOK COMPUTER 14in i7/16GB", unit="EA",
                 quantity=D(50), unit_price=D("300.00"), net_amount=D("15000.00"),
                 po_number="4500000002", po_item="00010", material="NB-X14-I7",
                 plant="1000"),
        LineItem(line_no=2, description="DOCKING STATION USB-C", unit="EA",
                 quantity=D(50), unit_price=D("45.00"), net_amount=D("2250.00"),
                 po_number="4500000002", po_item="00020", material="DS-C90",
                 plant="1000"),
        LineItem(line_no=3, description="SPARE BATTERY PACK", unit="EA",
                 quantity=D(20), unit_price=D("32.50"), net_amount=D("650.00"),
                 po_number="4500000002", po_item="00030", material="BT-55W",
                 plant="1000"),
        LineItem(line_no=4, description="FREIGHT & INSURANCE", unit="EA",
                 quantity=D(1), unit_price=D("970.00"), net_amount=D("970.00"),
                 po_number="4500000002", po_item="00040", plant="1000"),
    ]
    net = sum(li.net_amount for li in items)
    return _doc(DocType.COMMERCIAL_INVOICE, doc_number="GS-2026-0442",
                doc_date=date(2026, 3, 5), currency="USD",
                exchange_rate=D("1342.50"),
                supplier=Party(name="GLOBAL SOFT SOLUTIONS PTE. LTD."),
                buyer=Party(**SUPPLIER),
                net_total=net, tax_total=D(0), gross_total=net,
                line_items=items,
                reference_docs={"po_number": "PO-IMP-0442", "sap_po": "4500000002"})


@_reg(DocType.PACKING_LIST)
def _f45():
    d = _f44()
    d.doc_type = DocType.PACKING_LIST
    d.net_total = d.tax_total = d.gross_total = D(0)
    for li in d.line_items:
        li.net_amount = D(0)
    return d


@_reg(DocType.IMPORT_DECLARATION)
def _f46():
    return _doc(DocType.IMPORT_DECLARATION, doc_number="41099-26-0123456M",
                doc_date=date(2026, 3, 18),
                supplier=Party(name="인천세관장", biz_reg_no="121-83-00111"),
                buyer=Party(**SUPPLIER),
                net_total=D("2533297"), tax_total=D(0), gross_total=D("2533297"),
                line_items=[LineItem(line_no=1, description="수입 부가세 및 통관 부대비용",
                                     net_amount=D("2533297"),
                                     po_number="4500000002", po_item="00010")],
                reference_docs={"sap_po": "4500000002"})


@_reg(DocType.BILL_OF_LADING)
def _f47():
    d = _f45()
    d.doc_type = DocType.BILL_OF_LADING
    d.doc_number = "OSLSGINC26030088"
    d.doc_date = date(2026, 3, 8)
    return d


# ── 첨부·보조 ──────────────────────────────────────────────────────────────
@_reg(DocType.BUSINESS_REGISTRATION)
def _f48():
    return _doc(DocType.BUSINESS_REGISTRATION, doc_number="214-81-01117",
                doc_date=date(2023, 3, 2),
                supplier=Party(**SUPPLIER),
                net_total=D(0), tax_total=D(0), gross_total=D(0))


@_reg(DocType.BANKBOOK_COPY)
def _f49():
    return _doc(DocType.BANKBOOK_COPY, doc_number="123-456789-01-001",
                supplier=Party(**SUPPLIER),
                net_total=D(0), tax_total=D(0), gross_total=D(0),
                bank_account=BankAccount(bank_name="대한은행",
                                         account_no="123-456789-01-001",
                                         holder="(주)한빛테크놀로지"),
                reference_docs={"sap_bp": "BP00100234"})


@_reg(DocType.EVIDENCE_COVER_SHEET)
def _f50():
    return _doc(DocType.EVIDENCE_COVER_SHEET, doc_number="경지-2026-0331-14",
                supplier=Party(**SUPPLIER),
                net_total=D("412000"), tax_total=D(0), gross_total=D("412000"),
                line_items=[
                    LineItem(line_no=1, description="택배·퀵서비스 운송료",
                             net_amount=D("28000")),
                    LineItem(line_no=2, description="사무용품 구입(A4용지 외)",
                             net_amount=D("384000"))])


def sample(doc_type: DocType, *, source_file: str | None = None) -> VoucherDocument:
    """문서 유형의 대표 샘플을 생성한다."""
    doc = FACTORIES[doc_type]()
    if source_file:
        doc.source_file = source_file
    return doc


def all_samples() -> dict[DocType, VoucherDocument]:
    return {dt: fn() for dt, fn in FACTORIES.items()}
