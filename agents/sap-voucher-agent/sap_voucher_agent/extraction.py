# -*- coding: utf-8 -*-
"""증빙 PDF → 구조화 데이터 추출 (Claude 구조화 출력).

PDF 를 document 블록으로 전달하고 `client.messages.parse` 의 구조화 출력으로
문서 유형 분류와 필드 추출을 한 번에 수행한다.

금액·날짜는 문자열로 받아 Decimal/date 로 변환한다. 부동소수 오차와
JSON Schema 호환성 문제를 동시에 피하기 위해서다.
"""
from __future__ import annotations

import base64
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, Field

from .doc_types import KR_NAME, DocType
from .models import (BankAccount, LineItem, Party, VoucherDocument,
                     WithholdingTax)

MODEL = "claude-opus-5"
MAX_TOKENS = 16000


# --------------------------------------------------------------------------- 추출 스키마

class ExtractedParty(BaseModel):
    name: str = Field(description="상호 또는 법인명. 없으면 빈 문자열")
    biz_reg_no: str = Field(description="사업자등록번호 000-00-00000. 없으면 빈 문자열")
    ceo: str = Field(description="대표자 성명. 없으면 빈 문자열")
    address: str = Field(description="주소. 없으면 빈 문자열")
    biz_type: str = Field(description="업태. 없으면 빈 문자열")
    biz_item: str = Field(description="종목. 없으면 빈 문자열")


class ExtractedLine(BaseModel):
    line_no: int = Field(description="1부터 시작하는 순번")
    description: str = Field(description="품목명 또는 적요")
    spec: str = Field(description="규격. 없으면 빈 문자열")
    quantity: str = Field(description="수량. 숫자만, 없으면 빈 문자열")
    unit: str = Field(description="단위. 없으면 빈 문자열")
    unit_price: str = Field(description="단가. 콤마 없는 숫자, 없으면 빈 문자열")
    net_amount: str = Field(description="공급가액. 콤마 없는 숫자")
    tax_amount: str = Field(description="부가세액. 콤마 없는 숫자, 없으면 0")
    account_hint: str = Field(
        description="증빙에 계정과목이 명시되어 있으면 그 한글 계정명, 없으면 빈 문자열")
    service_start: str = Field(
        description="이 품목의 용역·급부 제공 개시일 YYYY-MM-DD. "
                    "기간이 명시되지 않았거나 일시 제공이면 빈 문자열")
    service_end: str = Field(
        description="이 품목의 용역·급부 제공 종료일 YYYY-MM-DD. 없으면 빈 문자열")


class ExtractedVoucher(BaseModel):
    """증빙 1건에서 추출할 항목."""

    doc_type: DocType = Field(description="증빙 문서 유형 코드")
    doc_type_reason: str = Field(description="그 유형으로 판단한 근거를 한 문장으로")
    confidence: float = Field(ge=0.0, le=1.0, description="분류 신뢰도 0~1")

    doc_number: str = Field(
        description="증빙 고유번호(승인번호/영수증번호/발주번호 등). 없으면 빈 문자열")
    doc_date: str = Field(description="작성일자 YYYY-MM-DD. 없으면 빈 문자열")
    due_date: str = Field(description="지급기일/결제기한 YYYY-MM-DD. 없으면 빈 문자열")

    supplier: ExtractedParty = Field(description="공급자(판매자/발행자)")
    buyer: ExtractedParty = Field(description="공급받는자(구매자/수취인)")

    currency: str = Field(description="통화 ISO 코드. 기본 KRW")
    exchange_rate: str = Field(description="외화인 경우 적용환율. 없으면 빈 문자열")
    net_total: str = Field(description="공급가액 합계. 콤마 없는 숫자")
    tax_total: str = Field(description="부가세 합계. 콤마 없는 숫자, 없으면 0")
    gross_total: str = Field(description="합계금액(총액). 콤마 없는 숫자")

    line_items: list[ExtractedLine] = Field(description="명세 라인 목록")

    payment_method: str = Field(
        description="현금/신용카드/계좌이체/어음 등. 없으면 빈 문자열")
    withholding_income_tax: str = Field(
        description="원천징수 소득세. 없으면 빈 문자열")
    withholding_local_tax: str = Field(
        description="원천징수 지방소득세. 없으면 빈 문자열")
    bank_name: str = Field(description="계좌 은행명. 없으면 빈 문자열")
    bank_account_no: str = Field(description="계좌번호. 없으면 빈 문자열")

    service_start: str = Field(
        description="문서 전체의 계약·용역 제공 개시일 YYYY-MM-DD. 없으면 빈 문자열")
    service_end: str = Field(
        description="문서 전체의 계약·용역 제공 종료일 YYYY-MM-DD. 없으면 빈 문자열")
    performance_date: str = Field(
        description="수행의무 이행일 - 재화 인도일 또는 용역 검수 완료일 "
                    "YYYY-MM-DD. 문서에 없으면 빈 문자열(작성일로 추정하지 말 것)")
    reference_po: str = Field(description="참조 발주/구매오더 번호. 없으면 빈 문자열")
    reference_original_doc: str = Field(
        description="수정세금계산서의 당초 승인번호 등. 없으면 빈 문자열")
    notes: str = Field(description="적요·특기사항 요약. 없으면 빈 문자열")
    warnings: list[str] = Field(
        description="판독이 불확실하거나 항목이 누락된 부분에 대한 경고 목록")


# --------------------------------------------------------------------------- 변환

def _dec(value: str | None) -> Decimal:
    if not value:
        return Decimal(0)
    cleaned = re.sub(r"[^\d\-.]", "", str(value))
    if cleaned in ("", "-", "."):
        return Decimal(0)
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return Decimal(0)


def _dec_opt(value: str | None) -> Optional[Decimal]:
    if not value or not re.search(r"\d", str(value)):
        return None
    return _dec(value)


def _date(value: str | None) -> Optional[date]:
    if not value:
        return None
    v = str(value).strip()
    for fmt in ("%Y-%m-%d", "%Y.%m.%d", "%Y/%m/%d", "%Y%m%d", "%Y년 %m월 %d일"):
        try:
            return datetime.strptime(v, fmt).date()
        except ValueError:
            continue
    m = re.search(r"(\d{4})\D+(\d{1,2})\D+(\d{1,2})", v)
    if m:
        try:
            return date(int(m[1]), int(m[2]), int(m[3]))
        except ValueError:
            return None
    return None


def _party(p: ExtractedParty) -> Optional[Party]:
    if not (p.name or p.biz_reg_no):
        return None
    return Party(
        name=p.name or "(미상)",
        biz_reg_no=p.biz_reg_no or None, ceo=p.ceo or None,
        address=p.address or None, biz_type=p.biz_type or None,
        biz_item=p.biz_item or None)


def to_voucher(x: ExtractedVoucher, source_file: str | None = None) -> VoucherDocument:
    """추출 결과를 도메인 모델로 변환한다."""
    lines = [
        LineItem(
            line_no=li.line_no or i,
            description=li.description or "(적요 없음)",
            spec=li.spec or None,
            quantity=_dec_opt(li.quantity),
            unit=li.unit or None,
            unit_price=_dec_opt(li.unit_price),
            net_amount=_dec(li.net_amount),
            tax_amount=_dec(li.tax_amount),
            service_start=_date(li.service_start),
            service_end=_date(li.service_end),
        )
        for i, li in enumerate(x.line_items, 1)
    ]
    wht = None
    it, lt = _dec_opt(x.withholding_income_tax), _dec_opt(x.withholding_local_tax)
    if it:
        wht = WithholdingTax(
            wt_type="K1", wt_code="03", base_amount=_dec(x.net_total),
            income_tax=it, local_income_tax=lt or Decimal(0))
    bank = (BankAccount(bank_name=x.bank_name or None,
                        account_no=x.bank_account_no or None)
            if (x.bank_name or x.bank_account_no) else None)

    refs: dict[str, str] = {}
    if x.reference_po:
        refs["po_number"] = x.reference_po
    if x.reference_original_doc:
        refs["original_document"] = x.reference_original_doc

    net, tax, gross = _dec(x.net_total), _dec(x.tax_total), _dec(x.gross_total)
    warnings = list(x.warnings)
    if gross == 0 and (net or tax):
        gross = net + tax
        warnings.append("합계금액이 판독되지 않아 공급가액+세액으로 계산했습니다.")
    if net == 0 and gross and lines:
        net = sum(li.net_amount for li in lines)

    return VoucherDocument(
        doc_type=x.doc_type, doc_type_confidence=x.confidence,
        doc_number=x.doc_number or None,
        doc_date=_date(x.doc_date), due_date=_date(x.due_date),
        supplier=_party(x.supplier), buyer=_party(x.buyer),
        currency=(x.currency or "KRW").upper(),
        exchange_rate=_dec_opt(x.exchange_rate),
        net_total=net, tax_total=tax, gross_total=gross,
        line_items=lines, withholding=wht, bank_account=bank,
        payment_method=x.payment_method or None,
        service_start=_date(x.service_start), service_end=_date(x.service_end),
        performance_date=_date(x.performance_date),
        reference_docs=refs, notes=x.notes or None,
        source_file=source_file, extraction_warnings=warnings,
    )


# --------------------------------------------------------------------------- 프롬프트

def _taxonomy() -> str:
    return "\n".join(
        f"  {t.value:24} = {KR_NAME[t]}" for t in DocType if t is not DocType.UNKNOWN)


SYSTEM_PROMPT = f"""\
당신은 한국 기업의 회계 증빙을 판독하는 전문가다. 스캔된 증빙 이미지·PDF 에서
SAP ERP 전기에 필요한 데이터를 정확히 추출한다.

[문서 유형 분류표]
{_taxonomy()}

[추출 규칙]
1. 금액은 콤마·원화기호를 제거한 숫자 문자열로만 적는다. 음수는 앞에 '-' 를 붙인다.
   수정세금계산서의 취소분(△ 또는 괄호 표기)은 반드시 음수로 적는다.
2. 날짜는 YYYY-MM-DD 로 정규화한다. 판독 불가면 빈 문자열.
3. 공급자는 재화·용역을 제공한 쪽, 공급받는자는 대금을 지급하는 쪽이다.
   영수증류는 가맹점이 공급자, 사업자번호가 기재된 구매자가 공급받는자다.
4. 사업자등록번호는 000-00-00000 형식으로 적는다. 숫자를 임의로 보정하지 않는다.
5. 명세가 표로 되어 있으면 모든 행을 line_items 로 옮긴다. 빈 행은 제외한다.
6. 값이 문서에 없으면 추측하지 말고 빈 문자열을 넣고 warnings 에 사유를 남긴다.
7. 부가세가 면세인 문서(계산서, 택시영수증 등)는 tax_total 을 0 으로 둔다.
8. 워터마크('샘플', 'SAMPLE')와 안내문구는 데이터가 아니므로 무시한다.
9. confidence 는 유형 분류에 대한 확신도다. 표지가 명확하면 0.9 이상,
   유사 서식과 혼동 가능하면 0.6~0.8, 근거가 약하면 0.5 미만으로 준다.

[K-IFRS 기간귀속을 위한 추가 판독 - 매우 중요]
10. service_start / service_end : 용역·급부가 제공되는 기간을 찾아 적는다.
    "계약기간 2026-01-01 ~ 2026-12-31", "3월분", "연간", "1년 사용료",
    "2026년 3월 사용분" 같은 표현이 근거다. 이 기간이 있어야 선급비용 이연
    여부를 판단할 수 있다. 문서에 없으면 빈 문자열로 두고 추측하지 않는다.
11. performance_date : 재화를 인도했거나 용역 검수가 완료된 날이다.
    검수확인서·인수증·납품일 표기에서 찾는다. K-IFRS 상 수익·비용 인식일은
    세금계산서 작성일이 아니라 이 날짜다. 문서에 없으면 반드시 빈 문자열로
    두어라 - 작성일로 대체하면 안 된다.

정확성이 속도보다 중요하다. 판독이 불확실하면 warnings 에 반드시 남긴다."""

USER_INSTRUCTION = ("이 증빙을 판독하여 지정된 스키마로 추출하라. "
                    "문서 유형을 먼저 판단한 뒤 해당 유형의 필드를 채운다.")


# --------------------------------------------------------------------------- 추출 실행

def _pdf_block(path: Path) -> dict[str, Any]:
    data = base64.standard_b64encode(path.read_bytes()).decode("ascii")
    return {"type": "document",
            "source": {"type": "base64", "media_type": "application/pdf",
                       "data": data}}


def _image_block(path: Path) -> dict[str, Any]:
    media = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg",
             "gif": "image/gif", "webp": "image/webp"}[path.suffix.lower().lstrip(".")]
    data = base64.standard_b64encode(path.read_bytes()).decode("ascii")
    return {"type": "image",
            "source": {"type": "base64", "media_type": media, "data": data}}


def content_block(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    if p.suffix.lower() == ".pdf":
        return _pdf_block(p)
    return _image_block(p)


def extract(path: str | Path, *, client: Any = None, model: str = MODEL,
            thinking: bool = True) -> VoucherDocument:
    """증빙 파일 1건을 추출한다."""
    import anthropic

    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"증빙 파일을 찾을 수 없습니다: {p}")
    client = client or anthropic.Anthropic()

    kwargs: dict[str, Any] = {}
    if thinking:
        kwargs["thinking"] = {"type": "adaptive"}

    response = client.messages.parse(
        model=model,
        max_tokens=MAX_TOKENS,
        system=[{"type": "text", "text": SYSTEM_PROMPT,
                 "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user",
                   "content": [content_block(p),
                               {"type": "text", "text": USER_INSTRUCTION}]}],
        output_format=ExtractedVoucher,
        **kwargs,
    )
    return to_voucher(response.parsed_output, source_file=str(p))


def extract_many(paths: list[str | Path], *, client: Any = None,
                 model: str = MODEL) -> list[VoucherDocument]:
    """여러 증빙을 순차 추출한다(배치 API 사용 시 batches.md 참고)."""
    import anthropic
    client = client or anthropic.Anthropic()
    return [extract(p, client=client, model=model) for p in paths]
