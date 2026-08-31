# -*- coding: utf-8 -*-
"""증빙 유형 → SAP 표준 BAPI 전기 경로 레지스트리.

이 모듈이 에이전트의 핵심 지식이다. 50종 증빙 각각에 대해
 * 어떤 SAP 모듈의 어떤 표준 BAPI 를 호출할지
 * 여러 단계가 필요한 경우 그 순서
 * PO 참조 유무처럼 상황에 따라 갈리는 분기(variant)
 * 표준 BAPI 가 없는 경우의 대안 경로
를 선언적으로 정의한다.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional

from .doc_types import KR_NAME, DocType
from .models import VoucherDocument

#: 전기 성격 - 감사 추적과 승인 정책에 사용
PostingKind = str
AP_INVOICE = "AP_INVOICE"        # 매입채무 발생
AR_INVOICE = "AR_INVOICE"        # 매출채권 발생
GL_POSTING = "GL_POSTING"        # 순수 G/L 전표
PAYMENT_IN = "PAYMENT_IN"        # 입금
PAYMENT_OUT = "PAYMENT_OUT"      # 지급/출금
REVERSAL = "REVERSAL"            # 역분개
PROCUREMENT = "PROCUREMENT"      # 구매 프로세스 문서(PR/PO/계약)
LOGISTICS = "LOGISTICS"          # 입출고/납품/검수
SALES = "SALES"                  # 영업 프로세스 문서
TRAVEL = "TRAVEL"                # 출장경비
MASTER_DATA = "MASTER_DATA"      # 마스터 등록
ATTACHMENT = "ATTACHMENT"        # 첨부/아카이빙만


@dataclass(frozen=True)
class RouteStep:
    """전기 경로의 한 단계."""

    bapi: str
    builder: str                     # builders.BUILDERS 의 키
    purpose: str
    optional: bool = False           # 데이터가 없으면 건너뛴다
    commit: bool = True


@dataclass(frozen=True)
class PostingRoute:
    """증빙 유형 1건의 전기 경로."""

    doc_type: DocType
    posting_kind: PostingKind
    variants: dict[str, tuple[RouteStep, ...]]
    #: 문서 내용에 따라 variant 키를 고르는 함수
    selector: Optional[Callable[[VoucherDocument], str]] = None
    default_variant: str = "default"
    notes: str = ""
    #: 항상 사람 승인이 필요한가(금액 무관)
    always_approve: bool = False
    #: 표준 BAPI 부재 등 실무 유의사항 키(bapi_defs.NO_STANDARD_BAPI)
    caveat: Optional[str] = None

    @property
    def kr_name(self) -> str:
        return KR_NAME[self.doc_type]

    def steps_for(self, doc: VoucherDocument) -> tuple[RouteStep, ...]:
        key = self.default_variant
        if self.selector is not None:
            try:
                key = self.selector(doc) or self.default_variant
            except Exception:                     # 분기 판단 실패 시 기본 경로
                key = self.default_variant
        return self.variants.get(key, self.variants[self.default_variant])

    def all_bapis(self) -> list[str]:
        seen: list[str] = []
        for steps in self.variants.values():
            for s in steps:
                if s.bapi not in seen:
                    seen.append(s.bapi)
        return seen


# --------------------------------------------------------------------------- 분기 판단

def _has_po(doc: VoucherDocument) -> bool:
    if doc.reference_docs.get("po_number") or doc.reference_docs.get("sap_po"):
        return True
    return any(li.po_number for li in doc.line_items)


def _po_or_fi(doc: VoucherDocument) -> str:
    """PO 참조가 있으면 MIRO(송장검증), 없으면 FI 직접전표."""
    return "with_po" if _has_po(doc) else "fi_direct"


def _credit_or_debit(doc: VoucherDocument) -> str:
    """수정세금계산서: 음(-)금액이면 역분개, 아니면 증액 전표."""
    return "reversal" if doc.gross_total < 0 else "additional"


def _fx_or_krw(doc: VoucherDocument) -> str:
    return "foreign" if (doc.currency or "KRW").upper() != "KRW" else "default"


# --------------------------------------------------------------------------- 공통 스텝 조각

_S_ACC_AP = RouteStep("BAPI_ACC_DOCUMENT_POST", "acc_ap_invoice",
                      "매입채무(공급업체) 회계전표 전기")
_S_ACC_AR = RouteStep("BAPI_ACC_DOCUMENT_POST", "acc_ar_invoice",
                      "매출채권(고객) 회계전표 전기")
_S_ACC_GL = RouteStep("BAPI_ACC_DOCUMENT_POST", "acc_gl",
                      "G/L 계정 간 회계전표 전기")
_S_ACC_PAY_OUT = RouteStep("BAPI_ACC_DOCUMENT_POST", "acc_payment_out",
                           "출금(지급) 전표 전기")
_S_ACC_PAY_IN = RouteStep("BAPI_ACC_DOCUMENT_POST", "acc_payment_in",
                          "입금 전표 전기")
_S_MIRO = RouteStep("BAPI_INCOMINGINVOICE_CREATE", "mm_invoice",
                    "구매송장 검증 전기(PO 3-way matching)")
_S_ATTACH = RouteStep("ARCHIVOBJECT_CREATE_TABLE", "doc_attach",
                      "원본 증빙 PDF 아카이빙 및 전표 연결", optional=True, commit=False)


def _with_attach(*steps: RouteStep) -> tuple[RouteStep, ...]:
    """모든 전기 경로 끝에 원본 증빙 아카이빙 단계를 붙인다."""
    return (*steps, _S_ATTACH)


# --------------------------------------------------------------------------- 레지스트리

ROUTES: dict[DocType, PostingRoute] = {}


def _reg(route: PostingRoute) -> None:
    ROUTES[route.doc_type] = route


# ── ① 적격증빙 ─────────────────────────────────────────────────────────────
_reg(PostingRoute(
    DocType.TAX_INVOICE_IN, AP_INVOICE,
    variants={
        "with_po": _with_attach(_S_MIRO),
        "fi_direct": _with_attach(_S_ACC_AP),
        "default": _with_attach(_S_ACC_AP),
    },
    selector=_po_or_fi,
    notes=("매입 세금계산서. 구매오더 참조가 있으면 MIRO(BAPI_INCOMINGINVOICE_CREATE)로 "
           "송장검증 전기하고, 없으면 FI 직접전표(BAPI_ACC_DOCUMENT_POST, FB60 상당)로 "
           "처리한다. 부가세는 ACCOUNTTAX/TAXDATA 에 세금코드와 함께 넘긴다.")))

_reg(PostingRoute(
    DocType.TAX_INVOICE_OUT, AR_INVOICE,
    variants={
        "default": _with_attach(_S_ACC_AR),
        "sd_billing": _with_attach(
            RouteStep("BAPI_BILLINGDOC_CREATEMULTIPLE", "sd_billing",
                      "SD 청구문서 생성(회계전표 자동 생성)")),
    },
    notes=("매출 세금계산서. SD 수주-납품 프로세스를 타는 경우 VF01 상당의 "
           "BAPI_BILLINGDOC_CREATEMULTIPLE 로 청구문서를 만들면 FI 전표가 자동 생성된다. "
           "단건 매출은 FI 직접전표(FB70 상당)로 전기한다.")))

_reg(PostingRoute(
    DocType.E_TAX_INVOICE, AP_INVOICE,
    variants={
        "with_po": _with_attach(_S_MIRO),
        "fi_direct": _with_attach(_S_ACC_AP),
        "default": _with_attach(_S_ACC_AP),
    },
    selector=_po_or_fi,
    notes=("전자세금계산서. 국세청 승인번호를 참조번호(XBLNR)와 멱등키로 사용하여 "
           "중복 전기를 차단한다. 전기 로직 자체는 종이 세금계산서와 동일하다.")))

_reg(PostingRoute(
    DocType.TAX_INVOICE_AMENDED, REVERSAL,
    variants={
        "reversal": _with_attach(
            RouteStep("BAPI_ACC_DOCUMENT_REV_POST", "acc_reversal",
                      "당초 전표 역분개(FB08 상당)")),
        "additional": _with_attach(_S_ACC_AP),
        "default": _with_attach(
            RouteStep("BAPI_ACC_DOCUMENT_REV_POST", "acc_reversal",
                      "당초 전표 역분개(FB08 상당)")),
    },
    selector=_credit_or_debit,
    always_approve=True,
    notes=("수정세금계산서. 음(-)금액이면 당초 전표를 BAPI_ACC_DOCUMENT_REV_POST 로 "
           "역분개하고, 정정분을 별도 전기한다. 취소·정정은 감사 대상이므로 "
           "금액과 무관하게 사람 승인을 요구한다. MM 송장이면 "
           "BAPI_INCOMINGINVOICE_CANCEL(MR8M)을 사용한다.")))

_reg(PostingRoute(
    DocType.INVOICE_EXEMPT, AP_INVOICE,
    variants={
        "with_po": _with_attach(_S_MIRO),
        "fi_direct": _with_attach(_S_ACC_AP),
        "default": _with_attach(_S_ACC_AP),
    },
    selector=_po_or_fi,
    notes=("면세 계산서. 세액이 없으므로 면세용 세금코드(예: V0)를 적용하고 "
           "ACCOUNTTAX 라인을 생성하지 않는다.")))

_reg(PostingRoute(
    DocType.IMPORT_TAX_INVOICE, AP_INVOICE,
    variants={
        "default": _with_attach(
            RouteStep("BAPI_INCOMINGINVOICE_CREATE", "mm_invoice_tax_only",
                      "수입 부가세만 전기(Tax-only invoice, 세관장 발행분)")),
        "fi_direct": _with_attach(
            RouteStep("BAPI_ACC_DOCUMENT_POST", "acc_import_vat",
                      "수입 부가세 FI 직접전표")),
    },
    notes=("수입세금계산서. 공급가액 없이 부가세만 있는 tax-only 송장으로, "
           "MIRO 의 '세금만' 송장 유형 또는 FI 직접전표로 매입세액을 인식한다. "
           "관세·통관수수료는 수입신고필증 경로에서 별도 처리한다.")))

_reg(PostingRoute(
    DocType.CARD_SALES_SLIP, GL_POSTING,
    variants={
        "default": _with_attach(
            RouteStep("BAPI_ACC_DOCUMENT_POST", "acc_card_expense",
                      "법인카드 사용액 비용/미지급금 전기")),
        "travel": _with_attach(
            RouteStep("BAPI_TRIP_CREATE_FROM_DATA", "tv_trip",
                      "출장경비 항목으로 등록")),
    },
    notes=("신용카드 매출전표. 비용계정 차변 / 카드미지급금(공급업체=카드사) 대변으로 "
           "전기한다. 접대비는 매입세액 불공제 세금코드를 적용해야 한다.")))

_reg(PostingRoute(
    DocType.CASH_RECEIPT, GL_POSTING,
    variants={"default": _with_attach(
        RouteStep("BAPI_ACC_DOCUMENT_POST", "acc_cash_expense",
                  "현금 지출 비용전표 전기"))},
    notes=("지출증빙용 현금영수증. 비용 차변 / 현금(또는 소액현금) 대변. "
           "식별번호가 자사 사업자번호인지 검증해야 매입세액 공제가 가능하다.")))

# ── ② 상거래 증빙 ──────────────────────────────────────────────────────────
_reg(PostingRoute(
    DocType.QUOTATION, SALES,
    variants={"default": (RouteStep("BAPI_QUOTATION_CREATEFROMDATA2", "sd_quotation",
                                    "SD 견적 문서 생성(VA21 상당)"), _S_ATTACH)},
    notes=("받은 견적서는 회계 전기 대상이 아니다. 자사가 발행한 견적이면 SD 견적문서로 "
           "등록하고, 매입 견적이면 구매요청(PR)의 첨부 근거로만 사용한다.")))

_reg(PostingRoute(
    DocType.PURCHASE_ORDER, PROCUREMENT,
    variants={"default": (RouteStep("BAPI_PO_CREATE1", "mm_po",
                                    "구매오더 생성(ME21N 상당)"), _S_ATTACH)},
    notes=("발주서. 구매오더를 생성하고 오더번호를 후속 입고(GR)·송장(IR)의 참조로 "
           "사용한다. 계정지정범주(K: 코스트센터, F: 오더)를 반드시 지정한다.")))

_reg(PostingRoute(
    DocType.DELIVERY_STATEMENT, LOGISTICS,
    variants={
        "with_po": (RouteStep("BAPI_GOODSMVT_CREATE", "mm_gr",
                              "구매오더 참조 입고(이동유형 101)"), _S_ATTACH),
        "fi_direct": _with_attach(_S_ACC_AP),
        "default": (RouteStep("BAPI_GOODSMVT_CREATE", "mm_gr",
                              "구매오더 참조 입고(이동유형 101)"), _S_ATTACH),
    },
    selector=_po_or_fi,
    notes=("거래명세서. PO 가 있으면 입고(GR) 자재문서를 생성해 GR/IR 계정을 통해 "
           "송장과 대사한다. PO 없는 용역이면 FI 직접전표로 처리한다.")))

_reg(PostingRoute(
    DocType.BILLING_REQUEST, AR_INVOICE,
    variants={"default": _with_attach(_S_ACC_AR)},
    notes=("청구서. 자사가 발행한 청구는 매출채권 전표, 수취한 청구는 세금계산서 수취 "
           "전까지 전기하지 않고 대기(파킹)하는 것이 원칙이다.")))

_reg(PostingRoute(
    DocType.PAYMENT_RECEIPT, PAYMENT_IN,
    variants={"default": _with_attach(_S_ACC_PAY_IN)},
    notes=("입금표. 은행계정 차변 / 매출채권 대변으로 전기하고, 해당 고객의 "
           "미결항목(open item)을 소거(clearing)한다.")))

_reg(PostingRoute(
    DocType.GOODS_ACCEPTANCE, LOGISTICS,
    variants={
        "service": (RouteStep("BAPI_ENTRYSHEET_CREATE", "mm_service_entry",
                              "서비스 확인서 생성(ML81N 상당)"), _S_ATTACH),
        "default": (RouteStep("BAPI_GOODSMVT_CREATE", "mm_gr",
                              "입고 자재문서 생성(이동유형 101)"), _S_ATTACH),
    },
    selector=lambda d: "service" if not any(li.material for li in d.line_items) else "default",
    notes=("검수확인서. 자재는 입고(GR), 용역은 서비스 확인서(SES)로 검수를 인식한다. "
           "이 단계가 있어야 송장검증(MIRO)에서 3-way matching 이 성립한다.")))

_reg(PostingRoute(
    DocType.DELIVERY_NOTE, LOGISTICS,
    variants={"default": (RouteStep("BAPI_INB_DELIVERY_CREATE", "mm_inb_delivery",
                                    "입고예정 납품문서 생성(VL31N 상당)"), _S_ATTACH)},
    notes=("물품인수증·운송장. 입고예정 납품(Inbound Delivery)을 생성한 뒤 "
           "입고전기(GR)로 이어진다. 운송장번호는 납품문서 참조필드에 보관한다.")))

_reg(PostingRoute(
    DocType.SERVICE_CONTRACT, PROCUREMENT,
    variants={"default": (RouteStep("BAPI_CONTRACT_CREATE", "mm_contract",
                                    "구매계약(Outline Agreement) 생성"), _S_ATTACH)},
    always_approve=True,
    notes=("용역계약서. 기간계약을 구매계약으로 등록하면 후속 PO 가 계약을 참조한다. "
           "계약 등록은 금액과 무관하게 사람 승인을 요구한다.")))

# ── ③ 내부 회계 증빙 ───────────────────────────────────────────────────────
_reg(PostingRoute(
    DocType.EXPENSE_RESOLUTION, GL_POSTING,
    variants={"default": _with_attach(
        RouteStep("BAPI_ACC_DOCUMENT_POST", "acc_multi_expense",
                  "지출결의 명세를 복합 회계전표로 전기"))},
    notes=("지출결의서. 명세 각 줄을 비용 차변 라인으로, 결제수단별 합계를 대변 라인으로 "
           "묶어 하나의 복합전표(one document, many line items)로 전기한다.")))

_reg(PostingRoute(
    DocType.PURCHASE_APPROVAL, PROCUREMENT,
    variants={"default": (RouteStep("BAPI_PR_CREATE", "mm_pr",
                                    "구매요청(PR) 생성(ME51N 상당)"), _S_ATTACH)},
    notes=("구매품의서. 사내 결재가 끝난 품의를 구매요청으로 전환하고, "
           "릴리즈 전략 통과 후 PO 로 전환한다.")))

_reg(PostingRoute(
    DocType.TRAVEL_SETTLEMENT, TRAVEL,
    variants={"default": (RouteStep("BAPI_TRIP_CREATE_FROM_DATA", "tv_trip",
                                    "출장 및 경비 정산 등록(PR05 상당)"), _S_ATTACH)},
    caveat=None,
    notes=("출장여비 정산서. FI-TV 출장 데이터로 등록한 뒤 정산 전기 프로그램에서 "
           "FI 전표가 생성된다. 가지급금(선지급)이 있으면 정산 시 상계된다.")))

_reg(PostingRoute(
    DocType.CORPORATE_CARD_STMT, AP_INVOICE,
    variants={"default": _with_attach(
        RouteStep("BAPI_ACC_DOCUMENT_POST", "acc_card_statement",
                  "카드 명세 전체를 비용/카드미지급금 복합전표로 전기"))},
    notes=("법인카드 월별 사용내역서. 건별 비용 차변 라인과 카드사 미지급금 대변 1라인으로 "
           "전기한다. 접대비·해외사용분은 매입세액 불공제 세금코드를 적용한다.")))

_reg(PostingRoute(
    DocType.CONGRATULATORY_EXPENSE, GL_POSTING,
    variants={"default": _with_attach(
        RouteStep("BAPI_ACC_DOCUMENT_POST", "acc_gl",
                  "경조사비 비용전표 전기"))},
    notes=("경조사비. 접대비(경조사비) 계정으로 전기하며 건당 20만원 한도를 검증한다. "
           "한도 초과분은 손금불산입 대상이므로 별도 계정으로 분리한다.")))

_reg(PostingRoute(
    DocType.PETTY_CASH_SETTLEMENT, GL_POSTING,
    variants={"default": _with_attach(
        RouteStep("BAPI_ACC_DOCUMENT_POST", "acc_multi_expense",
                  "소액현금 사용액 복합전표 전기"))},
    caveat="cash_journal",
    notes=("소액현금(전도금) 정산서. 현금출납장(FBCJ)에는 공개 표준 BAPI 가 없으므로 "
           "FI 전표로 비용 차변 / 소액현금 대변 전기한다.")))

# ── ④ 인사·급여 증빙 ───────────────────────────────────────────────────────
_reg(PostingRoute(
    DocType.PAYSLIP, GL_POSTING,
    variants={"default": _with_attach(
        RouteStep("BAPI_ACC_DOCUMENT_POST", "acc_payroll",
                  "급여비용/예수금/미지급급여 복합전표 전기"))},
    caveat="payroll_posting",
    always_approve=True,
    notes=("급여명세서. 급여비용 차변, 4대보험·소득세 예수금 대변, 실지급액 미지급급여 "
           "대변으로 전기한다. 정식 경로는 PC00_M99_CIPE 급여결과 전기이므로 "
           "반드시 PY 전기문서와 대사해야 한다.")))

_reg(PostingRoute(
    DocType.WHT_EMPLOYMENT, GL_POSTING,
    variants={"default": _with_attach(
        RouteStep("BAPI_ACC_DOCUMENT_POST", "acc_wht_settlement",
                  "연말정산 결정세액 정산 전표 전기"))},
    notes=("근로소득 원천징수영수증. 연말정산 결과 차감징수(환급)액을 "
           "예수금과 미지급/미수 계정으로 정산 전기한다.")))

_reg(PostingRoute(
    DocType.WHT_BUSINESS, AP_INVOICE,
    variants={"default": _with_attach(
        RouteStep("BAPI_ACC_DOCUMENT_POST", "acc_ap_withholding",
                  "사업소득 지급 + 원천징수(ACCOUNTWT) 전표 전기"))},
    notes=("사업소득 원천징수영수증(3.3%). BAPI_ACC_DOCUMENT_POST 의 ACCOUNTWT "
           "테이블에 원천세 유형(WITHT)·코드(WT_WITHCD)·과세표준을 넘겨 "
           "지급액에서 3.3% 를 예수금으로 분리한다.")))

_reg(PostingRoute(
    DocType.DAILY_WORKER_PAYMENT, GL_POSTING,
    variants={"default": _with_attach(
        RouteStep("BAPI_ACC_DOCUMENT_POST", "acc_multi_expense",
                  "일용노무비 및 원천세 예수금 전표 전기"))},
    notes=("일용근로소득 지급명세서. 노무비 차변 / 예수금·미지급금 대변으로 전기하며, "
           "소액부징수(1,000원 미만) 대상은 원천세 라인을 생성하지 않는다.")))

_reg(PostingRoute(
    DocType.SOCIAL_INSURANCE_BILL, AP_INVOICE,
    variants={"default": _with_attach(
        RouteStep("BAPI_ACC_DOCUMENT_POST", "acc_social_insurance",
                  "4대보험 사업주부담분 비용 / 근로자부담분 예수금 상계 전기"))},
    notes=("4대 사회보험료 고지서. 사업주부담분은 복리후생비(법정), 근로자부담분은 "
           "급여에서 공제한 예수금과 상계한다. 산재보험은 전액 사업주 부담이다.")))

# ── ⑤ 세금·공과금 증빙 ─────────────────────────────────────────────────────
_reg(PostingRoute(
    DocType.NATIONAL_TAX_RECEIPT, PAYMENT_OUT,
    variants={"default": _with_attach(
        RouteStep("BAPI_ACC_DOCUMENT_POST", "acc_tax_payment",
                  "국세 납부 전표 전기(부가세예수금 상계 또는 세금과공과)"))},
    notes=("국세 납부영수증. 부가가치세는 부가세예수금/대급금을 상계하고 잔액을 "
           "은행 대변으로, 법인세 등은 세금과공과 또는 선급법인세로 전기한다.")))

_reg(PostingRoute(
    DocType.LOCAL_TAX_RECEIPT, PAYMENT_OUT,
    variants={"default": _with_attach(
        RouteStep("BAPI_ACC_DOCUMENT_POST", "acc_tax_payment",
                  "지방세 납부 전표 전기(세금과공과)"))},
    notes=("지방세 납부확인서. 재산세·주민세 등은 세금과공과 차변 / 은행 대변. "
           "취득세는 자산 취득원가에 가산해야 하므로 계정 결정 시 주의한다.")))

_reg(PostingRoute(
    DocType.UTILITY_BILL, AP_INVOICE,
    variants={"default": _with_attach(_S_ACC_AP)},
    notes=("공과금 청구서. 세금계산서를 갈음하는 서류이므로 매입세액 공제가 가능하다. "
           "전력산업기반기금 등 비과세 항목은 세금코드 없이 별도 라인으로 분리한다.")))

_reg(PostingRoute(
    DocType.DONATION_RECEIPT, GL_POSTING,
    variants={"default": _with_attach(
        RouteStep("BAPI_ACC_DOCUMENT_POST", "acc_gl", "기부금 비용전표 전기"))},
    notes=("기부금영수증. 법정/지정 기부금 구분에 따라 계정을 분리해야 손금한도 "
           "계산이 가능하다. 현물기부는 자산 감소와 함께 전기한다.")))

# ── ⑥ 금융 증빙 ────────────────────────────────────────────────────────────
_reg(PostingRoute(
    DocType.BANK_STATEMENT, GL_POSTING,
    variants={"default": _with_attach(
        RouteStep("BAPI_ACC_DOCUMENT_POST", "acc_bank_statement",
                  "은행 거래 라인별 전표 전기"))},
    caveat="bank_statement",
    notes=("예금 거래내역서. 정식 경로는 MT940/FINSTA 전자명세서 업로드(RFEBKA00)다. "
           "본 에이전트는 라인별로 FI 전표를 생성하며, 미매칭 라인은 "
           "은행미결계정에 남겨 사람이 처리하도록 한다.")))

_reg(PostingRoute(
    DocType.WIRE_TRANSFER_SLIP, PAYMENT_OUT,
    variants={
        "default": _with_attach(_S_ACC_PAY_OUT),
        "incoming": _with_attach(_S_ACC_PAY_IN),
    },
    notes=("무통장입금증·이체확인증. 자사 출금이면 매입채무 소거, 자사 입금이면 "
           "매출채권 소거로 전기한다.")))

_reg(PostingRoute(
    DocType.PROMISSORY_NOTE, GL_POSTING,
    variants={"default": _with_attach(
        RouteStep("BAPI_ACC_DOCUMENT_POST", "acc_bill_of_exchange",
                  "어음 특별원장(Special G/L) 전표 전기"))},
    always_approve=True,
    notes=("약속어음. 수취어음은 특별원장 지시자 'W'(받을어음), 발행어음은 지급어음으로 "
           "전기한다. 만기 관리가 필요하므로 사람 승인을 요구한다.")))

_reg(PostingRoute(
    DocType.FX_REMITTANCE, PAYMENT_OUT,
    variants={
        "foreign": _with_attach(
            RouteStep("BAPI_ACC_DOCUMENT_POST", "acc_fx_payment",
                      "외화 송금 전표 전기(환율/환차손익 포함)")),
        "default": _with_attach(_S_ACC_PAY_OUT),
    },
    selector=_fx_or_krw,
    notes=("해외송금 영수증. CURRENCYAMOUNT 에 거래통화(CURR_TYPE '00')와 "
           "현지통화(CURR_TYPE '10') 금액을 함께 넘겨 환차손익을 인식한다. "
           "송금수수료는 지급수수료 계정으로 분리한다.")))

# ── ⑦ 여비교통·소액 실물 영수증 ────────────────────────────────────────────
_RECEIPT_NOTE_TAX = ("여객운송(택시·시외버스)은 부가세 면세이므로 매입세액 공제 대상이 "
                     "아니다. 세금코드 결정 시 면세코드를 적용한다.")

for _dt, _note in [
    (DocType.SIMPLE_RECEIPT,
     "간이영수증. 3만원 초과 시 적격증빙 미수취로 증빙불비가산세 대상임을 경고한다."),
    (DocType.TAXI_RECEIPT, _RECEIPT_NOTE_TAX),
    (DocType.TOLL_RECEIPT,
     "고속도로 통행료는 과세대상이므로 매입세액 공제가 가능하다."),
    (DocType.PARKING_RECEIPT,
     "주차요금은 과세대상. 업무용 차량 관련 비용은 차량유지비로 계정 결정한다."),
    (DocType.RESTAURANT_RECEIPT,
     "음식점 영수증. 접대 목적이면 접대비 계정 + 매입세액 불공제 세금코드를 적용하고, "
     "복리후생 목적이면 공제 가능하다. 목적 판단이 어려우면 사람 확인을 요청한다."),
    (DocType.LODGING_RECEIPT, "숙박용역은 과세대상으로 매입세액 공제가 가능하다."),
    (DocType.AIR_TICKET_RECEIPT,
     "국내선 항공운임은 과세, 국제선은 영세율이다. 공항시설사용료는 과세대상이 아니므로 "
     "별도 라인으로 분리한다."),
    (DocType.RAIL_TICKET_RECEIPT, "철도 여객운송은 과세대상으로 매입세액 공제가 가능하다."),
]:
    _reg(PostingRoute(
        _dt, TRAVEL,
        variants={
            "travel": (RouteStep("BAPI_TRIP_CREATE_FROM_DATA", "tv_trip_receipt",
                                 "출장 경비 항목으로 등록"), _S_ATTACH),
            "default": _with_attach(
                RouteStep("BAPI_ACC_DOCUMENT_POST", "acc_small_expense",
                          "여비교통비 등 소액 비용전표 전기")),
        },
        selector=lambda d: "travel" if d.reference_docs.get("trip_number") else "default",
        notes=_note))

# ── ⑧ 무역 증빙 ────────────────────────────────────────────────────────────
_reg(PostingRoute(
    DocType.COMMERCIAL_INVOICE, AP_INVOICE,
    variants={
        "with_po": _with_attach(
            RouteStep("BAPI_INCOMINGINVOICE_CREATE", "mm_invoice_import",
                      "수입 구매송장 검증 전기(외화)")),
        "fi_direct": _with_attach(
            RouteStep("BAPI_ACC_DOCUMENT_POST", "acc_fx_payment",
                      "수입 매입채무 외화전표 전기")),
        "default": _with_attach(
            RouteStep("BAPI_INCOMINGINVOICE_CREATE", "mm_invoice_import",
                      "수입 구매송장 검증 전기(외화)")),
    },
    selector=_po_or_fi,
    notes=("Commercial Invoice. 외화 송장이므로 통화·환율을 함께 전기하고, "
           "국내 매입세액은 수입세금계산서로 별도 인식한다(이 문서로 공제받지 않는다).")))

_reg(PostingRoute(
    DocType.PACKING_LIST, LOGISTICS,
    variants={"default": (RouteStep("BAPI_INB_DELIVERY_CREATE", "mm_inb_delivery",
                                    "입고예정 납품 생성(수량·중량 기준)"), _S_ATTACH)},
    notes=("Packing List. 회계 전기 대상이 아니며 입고 수량 검증용 물류 문서로 등록한다.")))

_reg(PostingRoute(
    DocType.IMPORT_DECLARATION, AP_INVOICE,
    variants={"default": _with_attach(
        RouteStep("BAPI_INCOMINGINVOICE_CREATE", "mm_invoice_customs",
                  "관세·통관수수료를 계획외 부대비용 송장으로 전기"),
        RouteStep("BAPI_ACC_DOCUMENT_POST", "acc_import_vat",
                  "수입 부가세 매입세액 전기", optional=True))},
    notes=("수입신고필증. 관세는 재고 취득원가에 가산(계획 배송비용)하고, "
           "수입 부가세는 세관장 발행 수입세금계산서 기준으로 매입세액을 인식한다.")))

_reg(PostingRoute(
    DocType.BILL_OF_LADING, LOGISTICS,
    variants={"default": (RouteStep("BAPI_INB_DELIVERY_CREATE", "mm_inb_delivery",
                                    "입고예정 납품 생성(B/L 참조)"), _S_ATTACH)},
    notes=("선하증권. 유가증권이지만 회계 전기 대상은 아니며, 입고예정 납품과 "
           "수입원가 배부의 근거 문서로 첨부한다.")))

# ── ⑨ 첨부·보조 서류 ───────────────────────────────────────────────────────
_reg(PostingRoute(
    DocType.BUSINESS_REGISTRATION, MASTER_DATA,
    variants={"default": (
        RouteStep("BAPI_BUPA_CREATE_FROM_DATA", "md_bp_create",
                  "비즈니스파트너 생성(BP)"),
        RouteStep("BAPI_BUPA_ROLE_ADD_2", "md_bp_role",
                  "공급업체 역할(FLVN00) 부여"),
        _S_ATTACH)},
    always_approve=True,
    notes=("사업자등록증 사본. 거래처 마스터를 신규 등록/변경하는 근거 서류다. "
           "마스터 데이터 변경은 내부통제상 항상 사람 승인을 요구한다. "
           "ECC 환경이면 BAPI_VENDOR_CREATE 를 사용한다.")))

_reg(PostingRoute(
    DocType.BANKBOOK_COPY, MASTER_DATA,
    variants={"default": (
        RouteStep("BAPI_BUPA_BANKDETAIL_ADD", "md_bp_bank",
                  "거래처 은행계좌 등록"),
        _S_ATTACH)},
    always_approve=True,
    notes=("통장 사본. 지급계좌 등록/변경 근거. 계좌 변경은 사기 위험이 높아 "
           "예외 없이 사람 승인과 콜백 검증을 요구한다.")))

_reg(PostingRoute(
    DocType.EVIDENCE_COVER_SHEET, ATTACHMENT,
    variants={"default": (_S_ATTACH,)},
    notes=("지출증빙 부착대지. 그 자체로는 전기 대상이 아니며, 부착된 개별 증빙을 "
           "각각 처리한 뒤 대지를 전표 첨부로 아카이빙한다.")))


# --------------------------------------------------------------------------- 조회 API

def route_for(doc_type: DocType) -> PostingRoute:
    """문서 유형의 전기 경로를 반환한다."""
    if doc_type not in ROUTES:
        raise KeyError(f"전기 경로가 정의되지 않은 문서 유형: {doc_type}")
    return ROUTES[doc_type]


def coverage() -> dict[str, object]:
    """레지스트리 커버리지 요약(테스트/문서화용)."""
    kinds: dict[str, int] = {}
    bapis: set[str] = set()
    for r in ROUTES.values():
        kinds[r.posting_kind] = kinds.get(r.posting_kind, 0) + 1
        bapis.update(r.all_bapis())
    return {
        "doc_types": len(ROUTES),
        "posting_kinds": dict(sorted(kinds.items())),
        "distinct_bapis": sorted(bapis),
        "always_approve": sorted(r.doc_type.value for r in ROUTES.values() if r.always_approve),
    }
