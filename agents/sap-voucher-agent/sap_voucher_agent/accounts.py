# -*- coding: utf-8 -*-
"""계정과목·세금코드 결정 규칙.

증빙에서 읽은 한글 적요/계정과목을 SAP G/L 계정과 세금코드로 변환한다.
회사마다 계정체계가 다르므로 `AccountRules` 를 JSON 으로 오버라이드할 수 있다.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Optional

from .doc_types import DocType

# --------------------------------------------------------------------------- 세금코드

#: 한국 부가세 표준 세금코드(예시 - 실제 값은 회사 커스터마이징에 맞춰야 한다)
TAX_CODE_INPUT_10 = "V1"      # 매입 과세 10% (공제)
TAX_CODE_INPUT_NON = "V2"     # 매입 과세 10% (불공제 - 접대비 등)
TAX_CODE_INPUT_EXEMPT = "V0"  # 매입 면세/영세
TAX_CODE_OUTPUT_10 = "A1"     # 매출 과세 10%
TAX_CODE_OUTPUT_ZERO = "A0"   # 매출 영세율

#: 매입세액 공제가 불가능한 계정 카테고리
NON_DEDUCTIBLE_CATEGORIES = {"entertainment", "congratulatory", "donation"}

#: 부가가치세 면세 대상 카테고리
EXEMPT_CATEGORIES = {"passenger_transport", "education", "books", "insurance", "finance"}


# --------------------------------------------------------------------------- 계정 결정

@dataclass(frozen=True)
class AccountRule:
    """적요 키워드 → 계정 매핑 규칙 한 줄."""

    category: str
    gl_account: str
    kr_name: str
    keywords: tuple[str, ...]
    deductible: bool = True
    exempt: bool = False
    #: 손금 한도(원). 초과 시 경고 - 예: 경조사비 20만원
    limit_per_case: Optional[Decimal] = None


#: 기본 규칙표. 계정번호는 한국 기업 일반 계정체계를 따른 예시값이다.
DEFAULT_RULES: tuple[AccountRule, ...] = (
    AccountRule("supplies", "830100", "소모품비",
                ("사무용품", "소모품", "복사용지", "문구", "청소용품", "생수")),
    AccountRule("entertainment", "813100", "접대비",
                ("접대", "거래처 중식", "거래처 식사", "회식(거래처)"),
                deductible=False),
    AccountRule("congratulatory", "813200", "접대비(경조사비)",
                ("경조사", "축의금", "조의금", "화환", "청첩", "부고"),
                deductible=False, limit_per_case=Decimal("200000")),
    AccountRule("welfare", "811100", "복리후생비",
                ("복리후생", "직원 식대", "다과", "간식", "사내 회의")),
    AccountRule("travel", "812100", "여비교통비",
                ("여비", "교통비", "출장", "택시", "항공", "KTX", "승차권",
                 "숙박", "통행료", "주차")),
    AccountRule("passenger_transport", "812100", "여비교통비(면세)",
                ("택시", "시외버스", "고속버스", "지하철"), exempt=True),
    AccountRule("communication", "814100", "통신비",
                ("통신", "전화", "인터넷", "우편", "등기")),
    AccountRule("utilities", "815100", "수도광열비",
                ("전기요금", "수도", "가스", "광열")),
    AccountRule("tax_public", "817100", "세금과공과",
                ("재산세", "주민세", "지방세", "면허세", "인지세", "공과금",
                 "지역자원시설세", "지방교육세")),
    AccountRule("rent", "819100", "지급임차료",
                ("임차료", "월세", "리스료", "정수기 임차")),
    AccountRule("maintenance", "820100", "수선비", ("수선", "유지보수", "정비")),
    AccountRule("insurance_expense", "821100", "보험료",
                ("보험료", "산재보험", "고용보험"), exempt=True),
    AccountRule("vehicle", "822100", "차량유지비",
                ("주유", "차량", "유류", "정비", "하이패스")),
    AccountRule("education", "825100", "교육훈련비",
                ("교육", "연수", "세미나", "수강료", "위탁교육"), exempt=True),
    AccountRule("books", "826100", "도서인쇄비",
                ("도서", "서적", "인쇄", "명함", "매뉴얼"), exempt=True),
    AccountRule("transport_freight", "824100", "운반비",
                ("운반", "택배", "퀵서비스", "화물", "배송")),
    AccountRule("fee", "831100", "지급수수료",
                ("수수료", "송금수수료", "발급 수수료", "용역", "컨설팅",
                 "클라우드", "서버 사용료", "라이선스")),
    AccountRule("advertising", "833100", "광고선전비", ("광고", "선전", "홍보", "판촉")),
    AccountRule("donation", "834100", "기부금", ("기부", "후원"), deductible=False),
    AccountRule("outsourcing", "835100", "외주용역비",
                ("외주", "프리랜서", "용역비", "개발 용역", "디자인")),
    AccountRule("labor_daily", "836100", "잡급(일용노무비)",
                ("일용", "노무비", "상하차", "일당")),
    AccountRule("salary", "801100", "급여", ("급여", "상여", "임금")),
    # 소프트웨어 개발 지출의 자본화 여부는 K-IFRS 1038 개발단계 요건 판단 사항이다.
    # 여기서는 기본값인 비용 계정으로 두고, 자본화는 kifrs.py 가 결정한다.
    AccountRule("software_dev", "835200", "외주용역비(소프트웨어 개발)",
                ("소프트웨어 개발", "ERP", "시스템 구축", "모듈 개발",
                 "데이터 마이그레이션")),
)


#: 대차 상대계정(재무상태표 계정)
BALANCE_ACCOUNTS: dict[str, str] = {
    "ap_trade": "251100",          # 외상매입금
    "ap_other": "253100",          # 미지급금
    "ap_card": "253200",           # 미지급금(법인카드)
    "ar_trade": "108100",          # 외상매출금
    "cash": "101100",              # 현금
    "petty_cash": "101200",        # 소액현금(전도금)
    "bank": "103100",              # 보통예금
    "vat_input": "135100",         # 부가세대급금
    "vat_output": "255100",        # 부가세예수금
    "wht_payable": "254100",       # 예수금(원천세)
    "si_payable": "254200",        # 예수금(4대보험)
    "salary_payable": "254300",    # 미지급급여
    "notes_receivable": "110100",  # 받을어음
    "notes_payable": "252100",     # 지급어음
    "advance_paid": "134100",      # 선급금/가지급금
    "gr_ir": "259100",             # 미착품/GR-IR 계정
    "fx_gain": "907100",           # 외환차익
    "fx_loss": "937100",           # 외환차손
    "bank_clearing": "103900",     # 은행미결계정
    "prepaid_tax": "136100",       # 선납세금
    # ── K-IFRS 기간귀속·측정 관련 ──────────────────────────────────────────
    "prepaid_expense": "133100",   # 선급비용 (K-IFRS 발생주의 이연)
    "accrued_expense": "253300",   # 미지급비용 (기간 경과분)
    "contract_liability": "255300",  # 계약부채(선수금) - K-IFRS 1115
    "contract_asset": "109100",    # 계약자산 - K-IFRS 1115
    "unearned_revenue": "255300",  # 선수수익 (계약부채와 동일 계정)
    "rou_asset": "178100",         # 사용권자산 - K-IFRS 1116
    "lease_liability": "258100",   # 리스부채 - K-IFRS 1116
    "intangible_asset": "178200",  # 무형자산(소프트웨어) - K-IFRS 1038
    "tangible_asset": "202100",    # 유형자산(비품) - K-IFRS 1016
    "inventory": "146100",         # 재고자산 - K-IFRS 1002
    "cip": "179100",               # 건설중인자산/개발중인자산
    "annual_leave_provision": "295100",  # 연차수당충당부채 - K-IFRS 1019
    "allowance_ecl": "109900",     # 대손충당금(기대신용손실) - K-IFRS 1109
    "depreciation": "845100",      # 감가상각비
    "amortization": "846100",      # 무형자산상각비
    "interest_expense": "931100",  # 이자비용
    "present_value_discount": "110900",  # 현재가치할인차금
}


@dataclass
class AccountRules:
    """계정 결정 엔진. JSON 으로 회사별 계정체계를 오버라이드할 수 있다."""

    rules: tuple[AccountRule, ...] = DEFAULT_RULES
    balance: dict[str, str] = field(default_factory=lambda: dict(BALANCE_ACCOUNTS))
    fallback_expense: str = "839100"   # 잡비
    fallback_kr: str = "잡비"

    @classmethod
    def from_json(cls, path: str | Path) -> "AccountRules":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        rules = tuple(
            AccountRule(
                category=r["category"], gl_account=r["gl_account"],
                kr_name=r.get("kr_name", r["category"]),
                keywords=tuple(r.get("keywords", ())),
                deductible=r.get("deductible", True),
                exempt=r.get("exempt", False),
                limit_per_case=(Decimal(str(r["limit_per_case"]))
                                if r.get("limit_per_case") is not None else None),
            )
            for r in data.get("rules", [])
        ) or DEFAULT_RULES
        balance = {**BALANCE_ACCOUNTS, **data.get("balance", {})}
        return cls(rules=rules, balance=balance,
                   fallback_expense=data.get("fallback_expense", "839100"),
                   fallback_kr=data.get("fallback_kr", "잡비"))

    # ---------------------------------------------------------------- 결정 로직

    def match(self, text: str, hint: str | None = None) -> AccountRule:
        """적요/계정과목 텍스트로 규칙을 찾는다. 우선순위: hint > 키워드 > 폴백."""
        haystack = f"{hint or ''} {text or ''}"
        best: Optional[AccountRule] = None
        best_len = 0
        for rule in self.rules:
            if hint and hint.strip() == rule.kr_name:
                return rule
            for kw in rule.keywords:
                if kw and kw in haystack and len(kw) > best_len:
                    best, best_len = rule, len(kw)
        return best or AccountRule("other", self.fallback_expense, self.fallback_kr, ())

    def tax_code(self, rule: AccountRule, *, direction: str = "input",
                 has_tax: bool = True) -> str:
        """세금코드 결정. direction: 'input'(매입) / 'output'(매출)."""
        if direction == "output":
            return TAX_CODE_OUTPUT_10 if has_tax else TAX_CODE_OUTPUT_ZERO
        if not has_tax or rule.exempt or rule.category in EXEMPT_CATEGORIES:
            return TAX_CODE_INPUT_EXEMPT
        if not rule.deductible or rule.category in NON_DEDUCTIBLE_CATEGORIES:
            return TAX_CODE_INPUT_NON
        return TAX_CODE_INPUT_10

    def gl(self, key: str) -> str:
        """상대계정(재무상태표) 조회."""
        if key not in self.balance:
            raise KeyError(f"정의되지 않은 상대계정 키: {key}")
        return self.balance[key]


#: 증빙 유형별 기본 상대계정(대변) 키
CREDIT_ACCOUNT_BY_DOCTYPE: dict[DocType, str] = {
    DocType.TAX_INVOICE_IN: "ap_trade",
    DocType.E_TAX_INVOICE: "ap_trade",
    DocType.INVOICE_EXEMPT: "ap_trade",
    DocType.IMPORT_TAX_INVOICE: "ap_other",
    DocType.UTILITY_BILL: "ap_other",
    DocType.CARD_SALES_SLIP: "ap_card",
    DocType.CORPORATE_CARD_STMT: "ap_card",
    DocType.CASH_RECEIPT: "cash",
    DocType.SIMPLE_RECEIPT: "cash",
    DocType.PETTY_CASH_SETTLEMENT: "petty_cash",
    DocType.TAXI_RECEIPT: "cash",
    DocType.TOLL_RECEIPT: "ap_card",
    DocType.PARKING_RECEIPT: "cash",
    DocType.RESTAURANT_RECEIPT: "ap_card",
    DocType.LODGING_RECEIPT: "ap_card",
    DocType.AIR_TICKET_RECEIPT: "ap_card",
    DocType.RAIL_TICKET_RECEIPT: "ap_card",
    DocType.CONGRATULATORY_EXPENSE: "cash",
    DocType.DONATION_RECEIPT: "bank",
    DocType.NATIONAL_TAX_RECEIPT: "bank",
    DocType.LOCAL_TAX_RECEIPT: "bank",
    DocType.SOCIAL_INSURANCE_BILL: "bank",
    DocType.WHT_BUSINESS: "ap_other",
    DocType.DAILY_WORKER_PAYMENT: "ap_other",
    DocType.COMMERCIAL_INVOICE: "ap_trade",
    DocType.IMPORT_DECLARATION: "ap_other",
    DocType.FX_REMITTANCE: "bank",
    DocType.WIRE_TRANSFER_SLIP: "bank",
    DocType.PAYMENT_RECEIPT: "bank",
    DocType.BANK_STATEMENT: "bank",
    DocType.PROMISSORY_NOTE: "notes_payable",
    DocType.EXPENSE_RESOLUTION: "ap_other",
}


def credit_account_key(doc_type: DocType, payment_method: str | None = None) -> str:
    """증빙 유형과 결제수단으로 대변 상대계정 키를 고른다."""
    pm = (payment_method or "").strip()
    if pm:
        if any(k in pm for k in ("카드", "CARD", "card")):
            return "ap_card"
        if any(k in pm for k in ("현금", "CASH", "cash")):
            return "cash"
        if any(k in pm for k in ("이체", "계좌", "자동이체", "송금")):
            return "bank"
        if "어음" in pm:
            return "notes_payable"
    return CREDIT_ACCOUNT_BY_DOCTYPE.get(doc_type, "ap_other")
