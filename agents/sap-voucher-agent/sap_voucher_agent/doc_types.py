# -*- coding: utf-8 -*-
"""한국 지류 증빙 50종의 문서 유형 정의.

`samples/korean-vouchers/` 에서 생성한 샘플 PDF 50종과 1:1로 대응한다.
"""
from __future__ import annotations

from enum import Enum


class DocType(str, Enum):
    """증빙 문서 유형. 값은 샘플 PDF 파일 접두 번호와 대응한다."""

    # ① 적격증빙(법정지출증빙)
    TAX_INVOICE_IN = "tax_invoice_in"                    # 01 세금계산서(공급받는자)
    TAX_INVOICE_OUT = "tax_invoice_out"                  # 02 세금계산서(공급자)
    E_TAX_INVOICE = "e_tax_invoice"                      # 03 전자세금계산서
    TAX_INVOICE_AMENDED = "tax_invoice_amended"          # 04 수정세금계산서
    INVOICE_EXEMPT = "invoice_exempt"                    # 05 계산서(면세)
    IMPORT_TAX_INVOICE = "import_tax_invoice"            # 06 수입세금계산서
    CARD_SALES_SLIP = "card_sales_slip"                  # 07 신용카드 매출전표
    CASH_RECEIPT = "cash_receipt"                        # 08 현금영수증

    # ② 상거래 증빙
    QUOTATION = "quotation"                              # 09 견적서
    PURCHASE_ORDER = "purchase_order"                    # 10 발주서
    DELIVERY_STATEMENT = "delivery_statement"            # 11 거래명세서
    BILLING_REQUEST = "billing_request"                  # 12 청구서
    PAYMENT_RECEIPT = "payment_receipt"                  # 13 입금표
    GOODS_ACCEPTANCE = "goods_acceptance"                # 14 납품·검수확인서
    DELIVERY_NOTE = "delivery_note"                      # 15 물품인수증(운송장)
    SERVICE_CONTRACT = "service_contract"                # 16 용역계약서

    # ③ 내부 회계 증빙
    EXPENSE_RESOLUTION = "expense_resolution"            # 17 지출결의서
    PURCHASE_APPROVAL = "purchase_approval"              # 18 구매품의서
    TRAVEL_SETTLEMENT = "travel_settlement"              # 19 출장여비 정산서
    CORPORATE_CARD_STMT = "corporate_card_stmt"          # 20 법인카드 사용내역서
    CONGRATULATORY_EXPENSE = "congratulatory_expense"    # 21 경조사비 지급 품의서
    PETTY_CASH_SETTLEMENT = "petty_cash_settlement"      # 22 소액현금(전도금) 정산서

    # ④ 인사·급여 증빙
    PAYSLIP = "payslip"                                  # 23 급여명세서
    WHT_EMPLOYMENT = "wht_employment"                    # 24 근로소득 원천징수영수증
    WHT_BUSINESS = "wht_business"                        # 25 사업소득 원천징수영수증(3.3%)
    DAILY_WORKER_PAYMENT = "daily_worker_payment"        # 26 일용근로소득 지급명세서
    SOCIAL_INSURANCE_BILL = "social_insurance_bill"      # 27 4대 사회보험료 고지서

    # ⑤ 세금·공과금 증빙
    NATIONAL_TAX_RECEIPT = "national_tax_receipt"        # 28 국세 납부영수증
    LOCAL_TAX_RECEIPT = "local_tax_receipt"              # 29 지방세 납부확인서
    UTILITY_BILL = "utility_bill"                        # 30 공과금 청구서(전기요금)
    DONATION_RECEIPT = "donation_receipt"                # 31 기부금영수증

    # ⑥ 금융 증빙
    BANK_STATEMENT = "bank_statement"                    # 32 예금 거래내역서
    WIRE_TRANSFER_SLIP = "wire_transfer_slip"            # 33 무통장입금증(이체확인증)
    PROMISSORY_NOTE = "promissory_note"                  # 34 약속어음
    FX_REMITTANCE = "fx_remittance"                      # 35 해외송금 영수증

    # ⑦ 여비교통·소액 실물 영수증
    SIMPLE_RECEIPT = "simple_receipt"                    # 36 간이영수증
    TAXI_RECEIPT = "taxi_receipt"                        # 37 택시 영수증
    TOLL_RECEIPT = "toll_receipt"                        # 38 고속도로 통행료 영수증
    PARKING_RECEIPT = "parking_receipt"                  # 39 주차요금 영수증
    RESTAURANT_RECEIPT = "restaurant_receipt"            # 40 음식점 POS 영수증
    LODGING_RECEIPT = "lodging_receipt"                  # 41 숙박 영수증
    AIR_TICKET_RECEIPT = "air_ticket_receipt"            # 42 항공권 e-티켓 영수증
    RAIL_TICKET_RECEIPT = "rail_ticket_receipt"          # 43 KTX 승차권 영수증

    # ⑧ 무역 증빙
    COMMERCIAL_INVOICE = "commercial_invoice"            # 44 Commercial Invoice
    PACKING_LIST = "packing_list"                        # 45 Packing List
    IMPORT_DECLARATION = "import_declaration"            # 46 수입신고필증
    BILL_OF_LADING = "bill_of_lading"                    # 47 선하증권(B/L)

    # ⑨ 첨부·보조 서류
    BUSINESS_REGISTRATION = "business_registration"      # 48 사업자등록증 사본
    BANKBOOK_COPY = "bankbook_copy"                      # 49 통장 사본
    EVIDENCE_COVER_SHEET = "evidence_cover_sheet"        # 50 지출증빙 부착대지

    UNKNOWN = "unknown"


#: 문서 유형 → 한글 명칭
KR_NAME: dict[DocType, str] = {
    DocType.TAX_INVOICE_IN: "세금계산서(공급받는자 보관용)",
    DocType.TAX_INVOICE_OUT: "세금계산서(공급자 보관용)",
    DocType.E_TAX_INVOICE: "전자세금계산서",
    DocType.TAX_INVOICE_AMENDED: "수정세금계산서",
    DocType.INVOICE_EXEMPT: "계산서(면세)",
    DocType.IMPORT_TAX_INVOICE: "수입세금계산서",
    DocType.CARD_SALES_SLIP: "신용카드 매출전표",
    DocType.CASH_RECEIPT: "현금영수증(지출증빙용)",
    DocType.QUOTATION: "견적서",
    DocType.PURCHASE_ORDER: "발주서(주문서)",
    DocType.DELIVERY_STATEMENT: "거래명세서",
    DocType.BILLING_REQUEST: "청구서(인보이스)",
    DocType.PAYMENT_RECEIPT: "입금표",
    DocType.GOODS_ACCEPTANCE: "납품·검수확인서",
    DocType.DELIVERY_NOTE: "물품인수증(운송장)",
    DocType.SERVICE_CONTRACT: "용역계약서",
    DocType.EXPENSE_RESOLUTION: "지출결의서",
    DocType.PURCHASE_APPROVAL: "구매품의서",
    DocType.TRAVEL_SETTLEMENT: "출장여비 정산서",
    DocType.CORPORATE_CARD_STMT: "법인카드 사용내역서",
    DocType.CONGRATULATORY_EXPENSE: "경조사비 지급 품의서",
    DocType.PETTY_CASH_SETTLEMENT: "소액현금(전도금) 정산서",
    DocType.PAYSLIP: "급여명세서",
    DocType.WHT_EMPLOYMENT: "근로소득 원천징수영수증",
    DocType.WHT_BUSINESS: "사업소득 원천징수영수증(3.3%)",
    DocType.DAILY_WORKER_PAYMENT: "일용근로소득 지급명세서",
    DocType.SOCIAL_INSURANCE_BILL: "4대 사회보험료 고지서",
    DocType.NATIONAL_TAX_RECEIPT: "국세 납부영수증",
    DocType.LOCAL_TAX_RECEIPT: "지방세 납부확인서",
    DocType.UTILITY_BILL: "공과금 청구서(전기요금)",
    DocType.DONATION_RECEIPT: "기부금영수증",
    DocType.BANK_STATEMENT: "예금 거래내역서",
    DocType.WIRE_TRANSFER_SLIP: "무통장입금증(이체확인증)",
    DocType.PROMISSORY_NOTE: "약속어음",
    DocType.FX_REMITTANCE: "해외송금 영수증",
    DocType.SIMPLE_RECEIPT: "간이영수증",
    DocType.TAXI_RECEIPT: "택시 영수증",
    DocType.TOLL_RECEIPT: "고속도로 통행료 영수증",
    DocType.PARKING_RECEIPT: "주차요금 영수증",
    DocType.RESTAURANT_RECEIPT: "음식점 POS 영수증",
    DocType.LODGING_RECEIPT: "숙박 영수증",
    DocType.AIR_TICKET_RECEIPT: "항공권 e-티켓 영수증",
    DocType.RAIL_TICKET_RECEIPT: "KTX 승차권 영수증",
    DocType.COMMERCIAL_INVOICE: "Commercial Invoice(상업송장)",
    DocType.PACKING_LIST: "Packing List(포장명세서)",
    DocType.IMPORT_DECLARATION: "수입신고필증",
    DocType.BILL_OF_LADING: "선하증권(B/L)",
    DocType.BUSINESS_REGISTRATION: "사업자등록증 사본",
    DocType.BANKBOOK_COPY: "통장 사본",
    DocType.EVIDENCE_COVER_SHEET: "지출증빙 부착대지",
    DocType.UNKNOWN: "미분류",
}

#: 샘플 PDF 파일 번호 → 문서 유형 (평가/회귀 테스트용)
SAMPLE_NO: dict[int, DocType] = {
    1: DocType.TAX_INVOICE_IN, 2: DocType.TAX_INVOICE_OUT, 3: DocType.E_TAX_INVOICE,
    4: DocType.TAX_INVOICE_AMENDED, 5: DocType.INVOICE_EXEMPT, 6: DocType.IMPORT_TAX_INVOICE,
    7: DocType.CARD_SALES_SLIP, 8: DocType.CASH_RECEIPT, 9: DocType.QUOTATION,
    10: DocType.PURCHASE_ORDER, 11: DocType.DELIVERY_STATEMENT, 12: DocType.BILLING_REQUEST,
    13: DocType.PAYMENT_RECEIPT, 14: DocType.GOODS_ACCEPTANCE, 15: DocType.DELIVERY_NOTE,
    16: DocType.SERVICE_CONTRACT, 17: DocType.EXPENSE_RESOLUTION, 18: DocType.PURCHASE_APPROVAL,
    19: DocType.TRAVEL_SETTLEMENT, 20: DocType.CORPORATE_CARD_STMT,
    21: DocType.CONGRATULATORY_EXPENSE, 22: DocType.PETTY_CASH_SETTLEMENT,
    23: DocType.PAYSLIP, 24: DocType.WHT_EMPLOYMENT, 25: DocType.WHT_BUSINESS,
    26: DocType.DAILY_WORKER_PAYMENT, 27: DocType.SOCIAL_INSURANCE_BILL,
    28: DocType.NATIONAL_TAX_RECEIPT, 29: DocType.LOCAL_TAX_RECEIPT, 30: DocType.UTILITY_BILL,
    31: DocType.DONATION_RECEIPT, 32: DocType.BANK_STATEMENT, 33: DocType.WIRE_TRANSFER_SLIP,
    34: DocType.PROMISSORY_NOTE, 35: DocType.FX_REMITTANCE, 36: DocType.SIMPLE_RECEIPT,
    37: DocType.TAXI_RECEIPT, 38: DocType.TOLL_RECEIPT, 39: DocType.PARKING_RECEIPT,
    40: DocType.RESTAURANT_RECEIPT, 41: DocType.LODGING_RECEIPT, 42: DocType.AIR_TICKET_RECEIPT,
    43: DocType.RAIL_TICKET_RECEIPT, 44: DocType.COMMERCIAL_INVOICE, 45: DocType.PACKING_LIST,
    46: DocType.IMPORT_DECLARATION, 47: DocType.BILL_OF_LADING,
    48: DocType.BUSINESS_REGISTRATION, 49: DocType.BANKBOOK_COPY,
    50: DocType.EVIDENCE_COVER_SHEET,
}
