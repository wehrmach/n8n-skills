# -*- coding: utf-8 -*-
"""증빙 → SAP 전기(posting)에 쓰이는 도메인 모델.

Pydantic 모델은 두 곳에서 함께 쓰인다.
1. Claude 구조화 출력(`client.messages.parse`)의 스키마 - 증빙 PDF에서 추출
2. BAPI 파라미터 빌더의 입력 - SAP RFC 호출 구조 생성
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

from .doc_types import DocType


# --------------------------------------------------------------------------- 거래 당사자

class Party(BaseModel):
    """거래 당사자(공급자/공급받는자/지급처)."""

    name: str = Field(description="상호 또는 법인명")
    biz_reg_no: Optional[str] = Field(
        None, description="사업자등록번호 000-00-00000 형식. 없으면 null")
    ceo: Optional[str] = Field(None, description="대표자 성명")
    address: Optional[str] = None
    biz_type: Optional[str] = Field(None, description="업태")
    biz_item: Optional[str] = Field(None, description="종목")
    tel: Optional[str] = None
    email: Optional[str] = None
    #: SAP 마스터 키 - 조회/매핑 후 채워진다
    sap_vendor: Optional[str] = Field(None, description="SAP 공급업체(LIFNR)")
    sap_customer: Optional[str] = Field(None, description="SAP 고객(KUNNR)")


class BankAccount(BaseModel):
    bank_name: Optional[str] = None
    account_no: Optional[str] = None
    holder: Optional[str] = None
    swift: Optional[str] = None


# --------------------------------------------------------------------------- 명세 라인

class LineItem(BaseModel):
    """증빙의 품목/명세 한 줄."""

    line_no: int = Field(description="1부터 시작하는 순번")
    description: str = Field(description="품목명 또는 적요")
    spec: Optional[str] = Field(None, description="규격")
    quantity: Optional[Decimal] = None
    unit: Optional[str] = Field(None, description="단위(EA, 식, 회 등)")
    unit_price: Optional[Decimal] = None
    net_amount: Decimal = Field(description="공급가액(부가세 제외)")
    tax_amount: Decimal = Field(default=Decimal(0), description="부가세액")
    #: 회계 정보 - 추출 단계에서 비어 있으면 계정 결정 단계에서 채운다
    gl_account: Optional[str] = Field(None, description="SAP 총계정원장 계정(HKONT)")
    cost_center: Optional[str] = Field(None, description="코스트센터(KOSTL)")
    wbs_element: Optional[str] = None
    internal_order: Optional[str] = None
    tax_code: Optional[str] = Field(None, description="SAP 세금코드(MWSKZ)")
    material: Optional[str] = Field(None, description="자재번호(MATNR)")
    plant: Optional[str] = Field(None, description="플랜트(WERKS)")
    po_number: Optional[str] = Field(None, description="참조 구매오더(EBELN)")
    po_item: Optional[str] = Field(None, description="구매오더 품목(EBELP)")

    @property
    def gross_amount(self) -> Decimal:
        return self.net_amount + self.tax_amount


# --------------------------------------------------------------------------- 원천징수

class WithholdingTax(BaseModel):
    """원천징수 정보(사업소득 3.3%, 근로소득 등)."""

    wt_type: str = Field(description="원천징수 유형 코드(SAP WITHT)")
    wt_code: str = Field(description="원천징수 세금코드(SAP WT_WITHCD)")
    base_amount: Decimal
    income_tax: Decimal = Field(description="소득세")
    local_income_tax: Decimal = Field(default=Decimal(0), description="지방소득세")

    @property
    def total(self) -> Decimal:
        return self.income_tax + self.local_income_tax


# --------------------------------------------------------------------------- 증빙 문서

class VoucherDocument(BaseModel):
    """증빙 1건에서 추출한 정규화 데이터."""

    doc_type: DocType = Field(description="증빙 문서 유형")
    doc_type_confidence: float = Field(
        default=1.0, ge=0.0, le=1.0, description="유형 분류 신뢰도 0~1")

    doc_number: Optional[str] = Field(
        None, description="증빙 고유번호(승인번호/영수증번호/발주번호 등)")
    doc_date: Optional[date] = Field(None, description="증빙 작성일자")
    posting_date: Optional[date] = Field(None, description="전기일자. 없으면 doc_date 사용")
    due_date: Optional[date] = Field(None, description="지급기일/결제기한")

    supplier: Optional[Party] = Field(None, description="공급자(매입 시 거래처)")
    buyer: Optional[Party] = Field(None, description="공급받는자(자사 또는 고객)")

    currency: str = Field(default="KRW", description="ISO 통화코드")
    exchange_rate: Optional[Decimal] = Field(None, description="외화 시 적용환율")
    net_total: Decimal = Field(default=Decimal(0), description="공급가액 합계")
    tax_total: Decimal = Field(default=Decimal(0), description="부가세 합계")
    gross_total: Decimal = Field(default=Decimal(0), description="합계금액(총액)")

    line_items: list[LineItem] = Field(default_factory=list)
    withholding: Optional[WithholdingTax] = None
    bank_account: Optional[BankAccount] = None

    payment_method: Optional[str] = Field(
        None, description="현금/카드/계좌이체/어음 등")
    reference_docs: dict[str, str] = Field(
        default_factory=dict,
        description="연관 문서 번호 (예: {'po_number': 'PO-2026-0198'})")
    notes: Optional[str] = None

    #: 원본 추적
    source_file: Optional[str] = None
    extraction_warnings: list[str] = Field(default_factory=list)

    @property
    def effective_posting_date(self) -> Optional[date]:
        return self.posting_date or self.doc_date

    def totals_consistent(self, tolerance: Decimal = Decimal("1")) -> bool:
        """합계금액 = 공급가액 + 세액 인지 검사(원 단위 절사 허용)."""
        return abs(self.net_total + self.tax_total - self.gross_total) <= tolerance


# --------------------------------------------------------------------------- 전기 컨텍스트

class PostingContext(BaseModel):
    """전기 시 필요한 조직 구조·기본값. 회사별 커스터마이징 지점."""

    company_code: str = Field(description="회사코드(BUKRS)")
    fiscal_year: Optional[int] = None
    currency: str = "KRW"
    username: str = Field(default="AI_AGENT", description="SAP 사용자 ID")

    # MM
    purchasing_org: Optional[str] = Field(None, description="구매조직(EKORG)")
    purchasing_group: Optional[str] = Field(None, description="구매그룹(EKGRP)")
    plant: Optional[str] = Field(None, description="플랜트(WERKS)")
    storage_location: Optional[str] = Field(None, description="저장위치(LGORT)")
    # SD
    sales_org: Optional[str] = Field(None, description="영업조직(VKORG)")
    distribution_channel: Optional[str] = None
    division: Optional[str] = None
    # FI 기본값
    default_cost_center: Optional[str] = None
    house_bank: Optional[str] = None

    dry_run: bool = Field(
        default=True,
        description="True면 BAPI_*_CHECK 만 호출하고 실제 전기는 하지 않는다")
    auto_commit: bool = Field(
        default=True, description="성공 시 BAPI_TRANSACTION_COMMIT 자동 호출")
    approval_threshold: Decimal = Field(
        default=Decimal("10000000"),
        description="이 금액을 초과하면 사람 승인 없이 전기하지 않는다")


# --------------------------------------------------------------------------- BAPI 호출/결과

class BapiCall(BaseModel):
    """단일 BAPI 호출 명세."""

    bapi: str = Field(description="BAPI 함수명, 예: BAPI_ACC_DOCUMENT_POST")
    params: dict[str, Any] = Field(default_factory=dict, description="RFC 임포트/테이블 파라미터")
    purpose: str = Field(default="", description="이 호출이 무엇을 하는지")
    commit: bool = Field(default=True, description="성공 후 COMMIT 필요 여부")
    check_bapi: Optional[str] = Field(
        None, description="사전 검증용 BAPI (예: BAPI_ACC_DOCUMENT_CHECK)")


class BapiMessage(BaseModel):
    """BAPIRET2 한 줄."""

    type: Literal["S", "I", "W", "E", "A", ""] = ""
    id: str = ""
    number: str = ""
    message: str = ""
    field: str = ""

    @property
    def is_error(self) -> bool:
        return self.type in ("E", "A")


class PostingResult(BaseModel):
    """BAPI 호출 결과."""

    bapi: str
    success: bool
    document_number: Optional[str] = Field(None, description="생성된 SAP 문서번호")
    fiscal_year: Optional[str] = None
    messages: list[BapiMessage] = Field(default_factory=list)
    committed: bool = False
    dry_run: bool = False
    elapsed_ms: Optional[int] = None
    raw: dict[str, Any] = Field(default_factory=dict)

    @property
    def errors(self) -> list[BapiMessage]:
        return [m for m in self.messages if m.is_error]

    def summary(self) -> str:
        if self.success:
            doc = self.document_number or "-"
            mode = "DRY-RUN 검증 통과" if self.dry_run else f"전기 완료 문서번호 {doc}"
            return f"{self.bapi}: {mode}"
        errs = "; ".join(f"[{m.id}{m.number}] {m.message}" for m in self.errors) or "원인 불명"
        return f"{self.bapi}: 실패 - {errs}"


class PostingPlan(BaseModel):
    """증빙 1건에 대한 전체 전기 계획(여러 BAPI 스텝)."""

    doc_type: DocType
    kr_name: str
    posting_kind: str
    calls: list[BapiCall] = Field(default_factory=list)
    requires_approval: bool = False
    approval_reasons: list[str] = Field(default_factory=list)
    validation_errors: list[str] = Field(default_factory=list)
    validation_warnings: list[str] = Field(default_factory=list)
    notes: str = ""
    idempotency_key: Optional[str] = Field(
        None, description="중복 전기 방지 키(참조번호 XBLNR 로 사용)")

    @property
    def postable(self) -> bool:
        return not self.validation_errors and bool(self.calls)
