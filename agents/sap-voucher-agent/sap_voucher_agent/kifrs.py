# -*- coding: utf-8 -*-
"""K-IFRS(한국채택국제회계기준) 회계판단 엔진.

세금계산서·영수증은 **세법상 서류**일 뿐이며, K-IFRS 회계처리는 거래의
**경제적 실질**에 따라 결정된다(개념체계 - 실질우선). 이 모듈은 증빙에서
읽은 사실관계를 다음 축으로 판단한다.

  1. 회계사건 여부   - 미이행계약·현금이동은 그 자체로 손익 인식 사건이 아니다
  2. 인식 시점       - 발생주의, 수행의무 이행(1115), 기간귀속(cut-off)
  3. 자산 vs 비용    - 유형자산(1016)·무형자산(1038)·재고자산(1002) 자본화
  4. 측정            - 외화환산(1021), 현재가치(1109), 취득원가 구성요소
  5. 표시            - 상계금지(1001)

판단이 회사 정책·사실관계에 달린 경우 임의로 결정하지 않고 `judgments` 로
사람에게 넘긴다. 금액은 어떤 경우에도 자동으로 바꾸지 않는다.
"""
from __future__ import annotations

import calendar
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from enum import Enum
from typing import Iterable, Optional

from .accounts import AccountRules
from .doc_types import KR_NAME, DocType
from .models import LineItem, PostingContext, VoucherDocument

# --------------------------------------------------------------------------- 기준서

STANDARDS: dict[str, str] = {
    "CF": "재무보고를 위한 개념체계 - 발생주의·실질우선·중요성",
    "1001": "K-IFRS 제1001호 재무제표 표시 - 상계 금지",
    "1002": "K-IFRS 제1002호 재고자산 - 취득원가(매입부대비용 포함)",
    "1012": "K-IFRS 제1012호 법인세 - 당기법인세와 이연법인세",
    "1016": "K-IFRS 제1016호 유형자산 - 인식요건과 취득원가",
    "1019": "K-IFRS 제1019호 종업원급여 - 단기종업원급여",
    "1021": "K-IFRS 제1021호 환율변동효과 - 거래일환율·마감환율",
    "1037": "K-IFRS 제1037호 충당부채·우발부채·우발자산",
    "1038": "K-IFRS 제1038호 무형자산 - 개발비 자본화 요건",
    "1008": "K-IFRS 제1008호 회계정책, 회계추정치 변경과 오류 - 오류의 소급수정",
    "1109": "K-IFRS 제1109호 금융상품 - 상각후원가·기대신용손실",
    "1115": "K-IFRS 제1115호 고객과의 계약에서 생기는 수익 - 수행의무 이행",
    "1116": "K-IFRS 제1116호 리스 - 사용권자산·리스부채",
}


class Recognition(str, Enum):
    """K-IFRS 상 인식 결론."""

    EXPENSE_NOW = "expense_now"                  # 당기 비용
    DEFER = "defer"                              # 선급비용 계상 후 기간배분
    ACCRUE = "accrue"                            # 미지급비용 계상(기간 경과분)
    CAPITALIZE = "capitalize"                    # 자산 인식
    REVENUE_NOW = "revenue_now"                  # 수익 인식
    CONTRACT_LIABILITY = "contract_liability"    # 계약부채(선수금)
    SETTLEMENT = "settlement"                    # 채권·채무 소거(손익 없음)
    TAX_RECOVERABLE = "tax_recoverable"          # 환급 가능 매입세액(자산)
    CORRECTION = "correction"                    # 기인식분의 취소·정정
    NO_ENTRY = "no_entry"                        # 회계사건 아님

    @property
    def kr(self) -> str:
        return {
            Recognition.EXPENSE_NOW: "당기 비용 인식",
            Recognition.DEFER: "선급비용 계상 후 기간 배분",
            Recognition.ACCRUE: "미지급비용 계상",
            Recognition.CAPITALIZE: "자산 인식(자본화)",
            Recognition.REVENUE_NOW: "수익 인식",
            Recognition.CONTRACT_LIABILITY: "계약부채(선수금) 인식",
            Recognition.SETTLEMENT: "채권·채무 소거(손익 미발생)",
            Recognition.TAX_RECOVERABLE: "환급 가능 매입세액(자산) 인식",
            Recognition.CORRECTION: "기인식분의 취소·정정",
            Recognition.NO_ENTRY: "회계 인식 대상 아님",
        }[self]


@dataclass(frozen=True)
class Judgment:
    """사람이 판단해야 하는 회계 쟁점."""

    standard: str
    question: str
    default_treatment: str
    blocking: bool = False

    def __str__(self) -> str:
        mark = "판단필요(차단)" if self.blocking else "판단필요"
        return (f"[{mark}:K-IFRS {self.standard}] {self.question} "
                f"→ 기본처리: {self.default_treatment}")


@dataclass
class AmortizationEntry:
    """기간 배분 스케줄 1행."""

    period: str            # YYYY-MM
    posting_date: date
    amount: Decimal
    description: str


@dataclass
class Deferral:
    """이연(선급비용) 처리 계획."""

    total: Decimal
    current_portion: Decimal      # 당기 비용
    deferred_portion: Decimal     # 선급비용
    service_start: date
    service_end: date
    schedule: list[AmortizationEntry] = field(default_factory=list)
    line_no: int = 1
    description: str = ""


@dataclass
class KifrsAssessment:
    """증빙 1건에 대한 K-IFRS 회계판단 결과."""

    doc_type: DocType
    recognition: Recognition
    standards: list[str] = field(default_factory=list)
    rationale: list[str] = field(default_factory=list)
    judgments: list[Judgment] = field(default_factory=list)
    #: line_no → 대체할 G/L 계정
    account_overrides: dict[int, str] = field(default_factory=dict)
    deferrals: list[Deferral] = field(default_factory=list)
    #: 실질 판단 결과 요약(감사 추적용)
    substance: str = ""

    @property
    def blocking_judgments(self) -> list[Judgment]:
        return [j for j in self.judgments if j.blocking]

    def standard_texts(self) -> list[str]:
        return [f"K-IFRS {s} — {STANDARDS[s]}" if s in STANDARDS else s
                for s in self.standards]

    def summary(self) -> str:
        lines = [f"■ K-IFRS 인식 : {self.recognition.kr}",
                 f"■ 거래의 실질 : {self.substance}"]
        if self.standards:
            lines.append("■ 적용 기준서")
            lines += [f"   - {t}" for t in self.standard_texts()]
        if self.rationale:
            lines.append("■ 판단 근거")
            lines += [f"   - {r}" for r in self.rationale]
        if self.account_overrides:
            lines.append("■ 계정 재분류")
            lines += [f"   - 명세 {n}행 → {acc}" for n, acc in self.account_overrides.items()]
        for d in self.deferrals:
            lines.append(
                f"■ 기간 배분 ({d.service_start} ~ {d.service_end}) : "
                f"당기비용 {d.current_portion:,.0f} / 선급비용 {d.deferred_portion:,.0f}")
            for e in d.schedule[:3]:
                lines.append(f"   - {e.period} {e.amount:,.0f} ({e.description})")
            if len(d.schedule) > 3:
                lines.append(f"   - … 총 {len(d.schedule)}개월 배분")
        if self.judgments:
            lines.append("■ 회계 판단 필요")
            lines += [f"   - {j}" for j in self.judgments]
        return "\n".join(lines)


# --------------------------------------------------------------------------- 분류표

#: 미이행계약·물류문서 - 그 자체로는 회계사건이 아니다(개념체계)
NO_ENTRY_DOCS: frozenset[DocType] = frozenset({
    DocType.QUOTATION, DocType.PURCHASE_ORDER, DocType.PURCHASE_APPROVAL,
    DocType.SERVICE_CONTRACT, DocType.DELIVERY_NOTE, DocType.PACKING_LIST,
    DocType.BILL_OF_LADING, DocType.BUSINESS_REGISTRATION,
    DocType.BANKBOOK_COPY, DocType.EVIDENCE_COVER_SHEET,
})

#: 현금 수수 - 채권·채무 소거일 뿐 손익 인식 사건이 아니다(발생주의)
SETTLEMENT_DOCS: frozenset[DocType] = frozenset({
    DocType.PAYMENT_RECEIPT, DocType.WIRE_TRANSFER_SLIP,
    DocType.BANK_STATEMENT, DocType.PROMISSORY_NOTE,
    DocType.FX_REMITTANCE, DocType.WHT_EMPLOYMENT,
})

#: 수익 인식 검토 대상
REVENUE_DOCS: frozenset[DocType] = frozenset({
    DocType.TAX_INVOICE_OUT, DocType.BILLING_REQUEST,
})

#: 기간 계약형 비용 - 용역기간에 걸쳐 배분해야 한다
PERIODIC_KEYWORDS: tuple[str, ...] = (
    "임차료", "월세", "리스", "보험료", "유지보수", "구독", "라이선스",
    "회비", "수신료", "관리비", "위탁운영", "SLA", "연간",
)

#: 리스 판단 대상 키워드(K-IFRS 1116)
LEASE_KEYWORDS: tuple[str, ...] = ("임차", "리스", "렌탈", "렌트", "월세")

#: 자본화 검토 대상 키워드
CAPEX_KEYWORDS: dict[str, tuple[str, ...]] = {
    "intangible_asset": ("소프트웨어 개발", "시스템 구축", "모듈 개발", "ERP",
                         "라이선스 취득", "특허", "상표"),
    "tangible_asset": ("서버", "장비", "기계", "비품", "차량 취득", "설비",
                       "노트북", "컴퓨터"),
}


# --------------------------------------------------------------------------- 유틸

def _month_end(d: date) -> date:
    return d.replace(day=calendar.monthrange(d.year, d.month)[1])


def _months_between(start: date, end: date) -> int:
    """서비스 기간의 개월 수(부분 월 포함)."""
    return max(1, (end.year - start.year) * 12 + (end.month - start.month) + 1)


def _round(v: Decimal) -> Decimal:
    return v.quantize(Decimal("1"), rounding=ROUND_HALF_UP)


def _has(text: str, keywords: Iterable[str]) -> bool:
    t = text or ""
    return any(k in t for k in keywords)


def _line_texts(doc: VoucherDocument) -> str:
    return " ".join(li.description or "" for li in doc.line_items) + " " + (doc.notes or "")


# --------------------------------------------------------------------------- 기간 배분

def build_deferral(li: LineItem, doc: VoucherDocument,
                   ctx: PostingContext) -> Optional[Deferral]:
    """용역 제공기간이 전기 기간을 넘어서면 선급비용으로 이연한다."""
    start = li.service_start or doc.service_start
    end = li.service_end or doc.service_end
    if not (start and end) or end <= start:
        return None
    cutoff = ctx.period_end or doc.effective_posting_date or date.today()
    if end <= cutoff:
        return None                                  # 전액 당기 귀속
    if li.net_amount < ctx.deferral_min_amount:
        return None                                  # 중요성 기준 미만

    total_months = _months_between(start, end)
    if start > cutoff:
        elapsed = 0
    else:
        elapsed = _months_between(start, cutoff)
    elapsed = min(elapsed, total_months)

    monthly = _round(li.net_amount / total_months)
    current = _round(monthly * elapsed)
    deferred = li.net_amount - current
    if deferred <= 0:
        return None

    schedule: list[AmortizationEntry] = []
    cursor = _month_end(cutoff) + timedelta(days=1)
    remaining = deferred
    for i in range(total_months - elapsed):
        pd = _month_end(cursor)
        amount = monthly if i < (total_months - elapsed - 1) else remaining
        remaining -= amount
        schedule.append(AmortizationEntry(
            period=f"{pd.year}-{pd.month:02d}", posting_date=pd, amount=amount,
            description=f"{li.description} 기간배분 {i + 1}/{total_months - elapsed}"))
        cursor = pd + timedelta(days=1)
        if remaining <= 0:
            break

    return Deferral(total=li.net_amount, current_portion=current,
                    deferred_portion=deferred, service_start=start,
                    service_end=end, schedule=schedule, line_no=li.line_no,
                    description=li.description)


# --------------------------------------------------------------------------- 개별 규칙

def _assess_no_entry(doc: VoucherDocument, a: KifrsAssessment) -> None:
    a.recognition = Recognition.NO_ENTRY
    a.standards.append("CF")
    if doc.doc_type in (DocType.QUOTATION, DocType.PURCHASE_ORDER,
                        DocType.PURCHASE_APPROVAL, DocType.SERVICE_CONTRACT):
        a.substance = "미이행계약(executory contract) - 쌍방 미이행 상태"
        a.rationale.append(
            "계약 체결만으로는 자산·부채를 인식하지 않는다. 재화·용역이 실제로 "
            "제공되거나 대가를 지급할 현재의무가 생긴 시점에 인식한다.")
    else:
        a.substance = "물류·첨부 문서 - 회계 인식 대상 아님"


def _assess_control_transfer(doc: VoucherDocument, ctx: PostingContext,
                             a: KifrsAssessment, rules: AccountRules) -> None:
    """검수·입고 - 자산에 대한 통제가 이전되는 시점."""
    has_material = any(li.material for li in doc.line_items)
    a.standards.append("1115")
    a.substance = "재화·용역에 대한 통제 이전 - 자산 또는 비용의 인식 시점"
    a.rationale.append(
        "K-IFRS 1115 상 고객(당사)이 자산을 통제하게 되는 검수·입고 시점에 "
        "자산 또는 비용을 인식한다. 세금계산서 수취일이 아니라 이 날짜가 "
        "발생주의상 귀속 시점이다.")
    if has_material:
        a.recognition = Recognition.CAPITALIZE
        a.standards.append("1002")
        a.rationale.append(
            "입고된 재화는 재고자산으로 인식하며, 취득원가에는 매입부대비용을 "
            "포함한다(K-IFRS 1002 문단 11). SAP 상 GR/IR 계정을 통해 송장과 "
            "대사된다.")
    else:
        a.recognition = Recognition.EXPENSE_NOW
        a.rationale.append(
            "용역 검수는 용역을 제공받은 사실을 확정하므로 해당 기간의 비용으로 "
            "인식한다.")
        _assess_capitalization(doc, ctx, a, rules)


def _assess_recoverable_tax(doc: VoucherDocument, a: KifrsAssessment) -> None:
    """수입세금계산서 - 환급 가능한 매입세액은 자산이며 취득원가가 아니다."""
    a.recognition = Recognition.TAX_RECOVERABLE
    a.standards.extend(["1002", "CF"])
    a.substance = "과세당국으로부터 환급받을 매입세액 - 자산(부가세대급금)"
    a.rationale.append(
        "환급받을 수 있는 매입세액은 재고자산·유형자산의 취득원가에서 제외한다"
        "(K-IFRS 1002 문단 11, 1016 문단 16). 세관장이 발행한 수입세금계산서의 "
        "부가세는 비용이 아니라 과세당국에 대한 채권으로 인식한다.")
    a.rationale.append(
        "관세·통관수수료 등 환급되지 않는 제세공과금은 별도로 재고자산 "
        "취득원가에 가산한다(수입신고필증 경로에서 처리).")


def _assess_correction(doc: VoucherDocument, ctx: PostingContext,
                       a: KifrsAssessment) -> None:
    """수정세금계산서 - 기인식분의 취소·정정."""
    a.recognition = Recognition.CORRECTION
    a.standards.extend(["CF", "1008"])
    a.substance = "이미 인식한 거래의 취소 또는 금액 정정"
    a.rationale.append(
        "수정세금계산서는 새로운 거래가 아니라 기인식 거래의 정정이다. "
        "원 전표를 역분개하고 정정분을 다시 인식한다.")
    a.judgments.append(Judgment(
        "1008",
        "정정 사유를 확인하라. (a) 당기 중 거래조건 변경(환입·할인·계약해제)이면 "
        "당기 손익에 반영한다. (b) 전기(前期) 재무제표의 오류라면 중요성 판단 후 "
        "소급재작성(비교표시 재무제표 수정)이 필요하다.",
        "당기 거래조건 변경으로 보아 당기 손익에 반영", blocking=True))
    if doc.gross_total >= 0:
        a.judgments.append(Judgment(
            "1008",
            "수정세금계산서 금액이 음수가 아니다. 증액 정정인지 당초분 재발행인지 "
            "확인하라. 당초분을 취소하지 않고 증액분만 전기하면 이중계상된다.",
            "증액 정정으로 보아 차액만 추가 인식"))


def _assess_tax_payment(doc: VoucherDocument, a: KifrsAssessment) -> None:
    """조세 납부 - 부가세는 예수금 정산, 재산세 등은 당기 비용."""
    text = _line_texts(doc)
    if _has(text, ("부가가치세", "부가세")):
        a.recognition = Recognition.SETTLEMENT
        a.standards.append("CF")
        a.substance = "부가가치세 납부 - 이미 인식한 예수금·대급금의 정산"
        a.rationale.append(
            "부가가치세는 사업자가 과세당국을 대신해 징수·납부하는 금액으로 "
            "기업의 수익·비용이 아니다. 부가세예수금과 부가세대급금을 상계한 "
            "잔액을 납부하는 것이므로 손익에 영향을 주지 않는다.")
        return
    if _has(text, ("법인세", "소득세")):
        a.recognition = Recognition.EXPENSE_NOW
        a.standards.extend(["CF", "1012"])
        a.substance = "법인세 납부 - 당기법인세부채의 정산"
        a.rationale.append(
            "중간예납·확정신고 납부액은 당기법인세부채를 감소시키며, 결산 시 "
            "법인세비용과 이연법인세를 별도로 인식한다(K-IFRS 1012).")
        return
    a.recognition = Recognition.EXPENSE_NOW
    a.standards.append("CF")
    a.substance = "재산세·주민세 등 - 당기 세금과공과"
    a.rationale.append(
        "재산세·지역자원시설세 등은 발생 사실이 확정된 기간의 비용으로 인식한다. "
        "다만 취득세·등록세는 자산 취득원가에 가산한다(K-IFRS 1016 문단 16).")
    if _has(text, ("취득세", "등록세")):
        a.judgments.append(Judgment(
            "1016",
            "취득세·등록세는 비용이 아니라 관련 자산의 취득원가에 가산해야 한다. "
            "대상 자산을 확인하라.",
            "세금과공과로 비용 처리", blocking=True))


def _assess_import_acquisition(doc: VoucherDocument, ctx: PostingContext,
                               a: KifrsAssessment, rules: AccountRules) -> None:
    """수입 거래 - 재고자산 취득원가 구성."""
    a.standards.extend(["1002", "CF"])
    has_material = any(li.material for li in doc.line_items)
    if has_material or doc.doc_type is DocType.IMPORT_DECLARATION:
        a.recognition = Recognition.CAPITALIZE
        a.substance = "수입 재화의 취득 - 재고자산 취득원가 인식"
        a.rationale.append(
            "매입가액에 수입관세·운임·보험료 등 취득에 직접 관련된 원가를 가산해 "
            "재고자산 취득원가를 구성한다(K-IFRS 1002 문단 11). 환급 가능한 "
            "매입세액은 취득원가에서 제외한다.")
        a.rationale.append(
            "SAP MM 송장검증(MIRO) 경로에서는 자동계정결정이 재고계정과 GR/IR "
            "계정을 결정하므로 계정을 직접 지정하지 않는다.")
    else:
        a.recognition = Recognition.EXPENSE_NOW
        a.substance = "수입 용역의 수취 - 당기 비용"
    if doc.doc_type is DocType.IMPORT_DECLARATION:
        a.judgments.append(Judgment(
            "1002",
            "관세를 재고자산 취득원가에 배부할 대상 품목과 배부기준(금액·중량)을 "
            "확인하라. 이미 판매된 재고분은 매출원가로 직접 인식한다.",
            "SAP 계획외 부대비용(FRA1)으로 입고 품목에 금액 비례 배부"))


def _assess_settlement(doc: VoucherDocument, ctx: PostingContext,
                       a: KifrsAssessment) -> None:
    a.recognition = Recognition.SETTLEMENT
    a.standards.append("CF")
    a.substance = "현금·금융자산의 이동 - 채권·채무 소거"
    a.rationale.append(
        "발생주의에 따라 현금 수수는 그 자체로 수익·비용을 발생시키지 않는다. "
        "이미 인식된 채권·채무를 소거할 뿐이다.")
    if doc.doc_type == DocType.PROMISSORY_NOTE:
        a.standards.append("1109")
        a.substance = "어음 - 상각후원가 측정 금융자산/금융부채"
        months = 0
        if doc.due_date and doc.doc_date:
            months = _months_between(doc.doc_date, doc.due_date)
        if months > 12:
            a.judgments.append(Judgment(
                "1109",
                f"만기 {months}개월 어음은 장기금융상품이다. 현재가치 할인 "
                "(유효이자율법) 대상인지 확인이 필요하다.",
                "현재가치할인차금 계상 후 유효이자율로 상각", blocking=True))
        else:
            a.rationale.append(
                f"만기 {months or '?'}개월 단기어음으로 현재가치 할인의 효과가 "
                "중요하지 않다. 액면금액으로 측정한다.")
        a.judgments.append(Judgment(
            "1109",
            "받을어음이면 기대신용손실(ECL) 충당금 설정 대상이다. "
            "간편법(전체기간 기대신용손실) 적용 여부를 확인하라.",
            "매출채권 대손충당금 설정 정책에 따름"))
    if doc.doc_type == DocType.BANK_STATEMENT:
        a.judgments.append(Judgment(
            "CF",
            "은행 거래 라인마다 상대계정(채권 소거 / 비용 / 미결)이 다르다. "
            "미매칭 라인은 은행미결계정에 남긴다.",
            "미매칭분 은행미결계정 계상 후 사람이 정리"))


def _assess_revenue(doc: VoucherDocument, ctx: PostingContext,
                    a: KifrsAssessment, rules: AccountRules) -> None:
    a.standards.append("1115")
    perf = doc.performance_date
    posting = doc.effective_posting_date
    if perf is None:
        a.recognition = Recognition.REVENUE_NOW
        a.substance = "재화·용역 제공에 따른 수익 - 수행의무 이행일 확인 필요"
        a.judgments.append(Judgment(
            "1115",
            "세금계산서 발행일은 세법상 공급시기일 뿐 수익인식일이 아니다. "
            "수행의무 이행일(인도·검수 완료일)을 확인하라.",
            "세금계산서 작성일을 수행의무 이행일로 간주", blocking=False))
        a.rationale.append(
            "K-IFRS 1115 5단계 모형에 따라 고객이 재화·용역을 통제하는 시점에 "
            "수익을 인식한다.")
    elif posting and perf > posting:
        a.recognition = Recognition.CONTRACT_LIABILITY
        a.substance = "선청구(수행의무 미이행) - 계약부채"
        a.rationale.append(
            f"수행의무 이행일({perf})이 전기일({posting}) 이후이므로 대가를 받을 "
            "권리가 무조건적이지 않다. 수익 대신 계약부채로 인식한다.")
        a.account_overrides.update(
            {li.line_no: rules.gl("contract_liability") for li in doc.line_items})
    else:
        a.recognition = Recognition.REVENUE_NOW
        a.substance = "수행의무 이행 완료 - 수익 인식"
        a.rationale.append(f"수행의무 이행일 {perf} 에 고객이 통제를 획득했다.")


def _assess_capitalization(doc: VoucherDocument, ctx: PostingContext,
                           a: KifrsAssessment, rules: AccountRules) -> None:
    """유형·무형·재고 자본화 판단."""
    for li in doc.line_items:
        text = li.description or ""
        if _has(text, ("부가세", "매입세액", "관세", "세액")):
            continue          # 조세 항목은 자산 취득이 아니다
        for key, keywords in CAPEX_KEYWORDS.items():
            if not _has(text, keywords):
                continue
            if li.net_amount < ctx.capitalization_threshold:
                a.rationale.append(
                    f"'{text}' {li.net_amount:,.0f}원은 자본화 기준금액 "
                    f"{ctx.capitalization_threshold:,.0f}원 미만으로 중요성 관점에서 "
                    "당기 비용 처리한다.")
                continue
            std = "1038" if key == "intangible_asset" else "1016"
            a.standards.append(std)
            if key == "intangible_asset":
                if ctx.intangible_capitalization:
                    a.account_overrides[li.line_no] = rules.gl("intangible_asset")
                    a.recognition = Recognition.CAPITALIZE
                    a.rationale.append(
                        f"'{text}' 는 개발비 자본화 요건(K-IFRS 1038 문단 57) "
                        "충족으로 판정되어 무형자산으로 인식한다.")
                else:
                    a.judgments.append(Judgment(
                        "1038",
                        f"'{text}' {li.net_amount:,.0f}원 - 개발단계 6요건"
                        "(기술적 실현가능성·완성 의도·사용 능력·미래 경제적효익·"
                        "자원 확보·지출 측정 신뢰성) 충족 여부를 판단하라. "
                        "연구단계 지출은 전액 비용이다.",
                        "요건 미충족으로 보아 당기 비용 처리", blocking=True))
            else:
                a.account_overrides[li.line_no] = rules.gl("tangible_asset")
                a.recognition = Recognition.CAPITALIZE
                a.rationale.append(
                    f"'{text}' 는 미래 경제적효익이 유입될 가능성이 높고 원가를 "
                    "신뢰성 있게 측정할 수 있어 유형자산으로 인식한다"
                    "(K-IFRS 1016 문단 7).")
                a.judgments.append(Judgment(
                    "1016", f"'{text}' 의 내용연수와 감가상각방법을 지정하라.",
                    "내용연수 5년 정액법"))
            break


def _assess_lease(doc: VoucherDocument, ctx: PostingContext,
                  a: KifrsAssessment) -> None:
    if not _has(_line_texts(doc), LEASE_KEYWORDS):
        return
    a.standards.append("1116")
    months = 0
    if doc.service_start and doc.service_end:
        months = _months_between(doc.service_start, doc.service_end)
    short_term = 0 < months <= ctx.lease_short_term_months
    low_value = doc.gross_total <= ctx.lease_low_value_threshold
    if short_term or low_value:
        reason = ("단기리스" if short_term else "") + \
                 (" 및 " if short_term and low_value else "") + \
                 ("소액 기초자산 리스" if low_value else "")
        a.rationale.append(
            f"{reason} 면제 규정(K-IFRS 1116 문단 5~6)을 적용하여 "
            "사용권자산·리스부채를 인식하지 않고 리스료를 정액 비용으로 처리한다.")
    else:
        a.judgments.append(Judgment(
            "1116",
            "리스 거래로 보이며 단기·소액 면제 대상이 아니다. 사용권자산과 "
            "리스부채를 인식해야 하는지(식별되는 자산의 사용통제권 이전 여부) "
            "판단하라.",
            "사용권자산·리스부채 인식 후 감가상각비와 이자비용으로 분리",
            blocking=True))


def _assess_deferral(doc: VoucherDocument, ctx: PostingContext,
                     a: KifrsAssessment, rules: AccountRules) -> None:
    """발생주의에 따른 기간귀속(cut-off) 판단."""
    periodic = _has(_line_texts(doc), PERIODIC_KEYWORDS)
    for li in doc.line_items:
        d = build_deferral(li, doc, ctx)
        if d is None:
            continue
        a.deferrals.append(d)
        a.recognition = Recognition.DEFER
        a.standards.append("CF")
        a.rationale.append(
            f"'{li.description}' 은(는) {d.service_start}~{d.service_end} 기간에 "
            f"제공되는 급부다. 발생주의에 따라 경과분 {d.current_portion:,.0f}원만 "
            f"당기 비용으로 인식하고 {d.deferred_portion:,.0f}원은 선급비용으로 "
            "이연한다.")
    if periodic and not a.deferrals:
        missing = [li.line_no for li in doc.line_items
                   if not (li.service_start or doc.service_start)]
        if missing:
            a.judgments.append(Judgment(
                "CF",
                "기간 계약형 비용(임차료·보험료·유지보수·구독 등)으로 보이나 "
                "용역 제공기간이 확인되지 않는다. 기간을 확인해 선급비용 이연 "
                "여부를 판단하라.",
                "전액 당기 비용 처리"))


def _assess_fx(doc: VoucherDocument, a: KifrsAssessment) -> None:
    if (doc.currency or "KRW").upper() == "KRW":
        return
    a.standards.append("1021")
    if doc.exchange_rate is None:
        a.judgments.append(Judgment(
            "1021",
            f"{doc.currency} 외화거래인데 적용환율이 없다. 거래일의 현물환율로 "
            "기능통화(KRW)로 환산해야 한다.",
            "전기일 기준 매매기준율 적용", blocking=True))
    else:
        a.rationale.append(
            f"외화거래를 거래일 환율 {doc.exchange_rate}로 기능통화 환산한다"
            "(K-IFRS 1021 문단 21).")
    a.judgments.append(Judgment(
        "1021",
        "화폐성 외화항목(외화 매입채무)은 보고기간말 마감환율로 재환산하고 "
        "환산차이를 당기손익으로 인식해야 한다.",
        "결산 시 외화평가 프로그램(FAGL_FC_VAL)으로 일괄 처리"))


def _assess_employee_benefits(doc: VoucherDocument, a: KifrsAssessment) -> None:
    if doc.doc_type not in (DocType.PAYSLIP, DocType.DAILY_WORKER_PAYMENT,
                            DocType.WHT_EMPLOYMENT):
        return
    a.standards.append("1019")
    a.rationale.append(
        "단기종업원급여는 종업원이 근무용역을 제공한 회계기간에 비용으로 인식하고, "
        "미지급액은 부채로 인식한다(K-IFRS 1019 문단 11).")
    if doc.doc_type == DocType.PAYSLIP:
        a.judgments.append(Judgment(
            "1019",
            "미사용 연차유급휴가는 누적유급휴가로서 근무용역 제공 시점에 "
            "부채(연차수당충당부채)로 인식해야 한다. 급여 전기와 별도로 "
            "결산 시 계상 여부를 확인하라.",
            "결산 시 연차충당부채 별도 계상"))


def _assess_inventory_costs(doc: VoucherDocument, a: KifrsAssessment) -> None:
    if doc.doc_type not in (DocType.IMPORT_DECLARATION, DocType.COMMERCIAL_INVOICE):
        return
    a.standards.append("1002")
    a.rationale.append(
        "수입관세·운임·보험료 등 매입부대비용은 재고자산 취득원가에 포함한다"
        "(K-IFRS 1002 문단 11). 환급 예정인 부가세는 취득원가에서 제외한다.")


def _assess_offsetting(doc: VoucherDocument, a: KifrsAssessment) -> None:
    if doc.doc_type != DocType.SOCIAL_INSURANCE_BILL:
        return
    a.standards.append("1001")
    a.rationale.append(
        "사업주부담분(비용)과 근로자부담분(예수금 소거)은 성격이 다르므로 "
        "상계하지 않고 총액으로 표시한다(K-IFRS 1001 문단 32).")


def _assess_provision(doc: VoucherDocument, a: KifrsAssessment) -> None:
    if doc.doc_type != DocType.SERVICE_CONTRACT:
        return
    if _has(_line_texts(doc), ("하자보수", "하자보증", "품질보증")):
        a.standards.append("1037")
        a.judgments.append(Judgment(
            "1037",
            "하자보수 의무가 있는 계약이다. 과거 경험률에 근거한 하자보수충당부채 "
            "인식 대상인지 판단하라.",
            "매출 인식 시점에 충당부채 별도 계상"))


# --------------------------------------------------------------------------- 진입점

def assess(doc: VoucherDocument, ctx: PostingContext,
           rules: AccountRules | None = None) -> KifrsAssessment:
    """증빙 1건에 대한 K-IFRS 회계판단을 수행한다."""
    rules = rules or AccountRules()
    a = KifrsAssessment(doc_type=doc.doc_type, recognition=Recognition.EXPENSE_NOW)

    if doc.doc_type in NO_ENTRY_DOCS:
        _assess_no_entry(doc, a)
    elif doc.doc_type in (DocType.GOODS_ACCEPTANCE, DocType.DELIVERY_STATEMENT):
        _assess_control_transfer(doc, ctx, a, rules)
    elif doc.doc_type is DocType.IMPORT_TAX_INVOICE:
        _assess_recoverable_tax(doc, a)
    elif doc.doc_type is DocType.TAX_INVOICE_AMENDED:
        _assess_correction(doc, ctx, a)
    elif doc.doc_type in (DocType.NATIONAL_TAX_RECEIPT, DocType.LOCAL_TAX_RECEIPT):
        _assess_tax_payment(doc, a)
    elif doc.doc_type in (DocType.IMPORT_DECLARATION, DocType.COMMERCIAL_INVOICE):
        _assess_import_acquisition(doc, ctx, a, rules)
    elif doc.doc_type in SETTLEMENT_DOCS:
        _assess_settlement(doc, ctx, a)
    elif doc.doc_type in REVENUE_DOCS:
        _assess_revenue(doc, ctx, a, rules)
    else:
        a.recognition = Recognition.EXPENSE_NOW
        a.substance = f"{KR_NAME[doc.doc_type]} - 재화·용역 수취에 따른 비용·자산 인식"
        a.standards.append("CF")
        a.rationale.append(
            "발생주의에 따라 대금 지급 시점이 아니라 재화·용역을 제공받은 "
            "시점에 비용(또는 자산)을 인식한다.")
        if any(li.material for li in doc.line_items):
            a.recognition = Recognition.CAPITALIZE
            a.standards.append("1002")
            a.substance = "재화의 취득 - 재고자산 인식"
            a.rationale.append(
                "자재번호가 지정된 품목은 재고자산으로 인식하며, 계정은 SAP MM "
                "자동계정결정(평가클래스)에 따른다(K-IFRS 1002).")
        _assess_capitalization(doc, ctx, a, rules)
        _assess_deferral(doc, ctx, a, rules)
        _assess_lease(doc, ctx, a)

    if a.recognition is not Recognition.NO_ENTRY:
        _assess_fx(doc, a)
    _assess_employee_benefits(doc, a)
    _assess_inventory_costs(doc, a)
    _assess_offsetting(doc, a)
    _assess_provision(doc, a)

    # 중복 기준서 제거(선언 순서 유지)
    seen: list[str] = []
    for s in a.standards:
        if s not in seen:
            seen.append(s)
    a.standards = seen
    if not a.substance:
        a.substance = KR_NAME.get(doc.doc_type, doc.doc_type.value)
    return a


def apply_to_document(doc: VoucherDocument, a: KifrsAssessment,
                      rules: AccountRules | None = None) -> None:
    """판단 결과를 명세 라인에 반영한다.

    * 계정 재분류(자본화·계약부채)를 라인에 적용한다.
    * 이연분이 있으면 라인을 '당기 경과분' + '선급비용 이연분' 두 줄로 나눈다.
      총액은 바뀌지 않으므로 전표 차대와 합계 검증에 영향이 없다.
    * 부가세는 세금계산서 작성일이 속한 과세기간에 전액 공제되므로 원래 라인에
      그대로 남긴다(회계상 이연과 세법상 공제시기는 별개다).
    """
    rules = rules or AccountRules()
    for li in doc.line_items:
        if li.line_no in a.account_overrides:
            li.gl_account = a.account_overrides[li.line_no]

    if not a.deferrals:
        return
    by_line = {d.line_no: d for d in a.deferrals}
    new_items: list[LineItem] = []
    next_no = max((li.line_no for li in doc.line_items), default=0)
    for li in doc.line_items:
        d = by_line.get(li.line_no)
        if d is None:
            new_items.append(li)
            continue
        li.net_amount = d.current_portion
        li.description = f"{d.description} (당기 경과분)"
        new_items.append(li)
        next_no += 1
        new_items.append(LineItem(
            line_no=next_no,
            description=f"{d.description} (선급비용 이연분 "
                        f"{d.service_start}~{d.service_end})",
            net_amount=d.deferred_portion, tax_amount=Decimal(0),
            gl_account=rules.gl("prepaid_expense"),
            tax_code=li.tax_code, cost_center=li.cost_center,
            service_start=d.service_start, service_end=d.service_end))
    doc.line_items = new_items
