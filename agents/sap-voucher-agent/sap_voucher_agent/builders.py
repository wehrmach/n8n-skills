# -*- coding: utf-8 -*-
"""BAPI 파라미터 빌더.

`VoucherDocument` + `PostingContext` → SAP RFC 임포트/테이블 파라미터 dict.
빌더 이름은 `mapping.RouteStep.builder` 와 1:1로 대응한다.

금액 부호 규약(BAPI_ACC_DOCUMENT_POST):
  CURRENCYAMOUNT-AMT_DOCCUR 가 양수면 차변(Debit), 음수면 대변(Credit).
"""
from __future__ import annotations

import hashlib
from datetime import date
from decimal import Decimal
from typing import Any, Callable, Optional

from .accounts import (BALANCE_ACCOUNTS, AccountRule, AccountRules,
                       credit_account_key)
from .doc_types import KR_NAME, DocType
from .models import LineItem, PostingContext, VoucherDocument

BuilderFn = Callable[[VoucherDocument, PostingContext, AccountRules], dict[str, Any]]
BUILDERS: dict[str, BuilderFn] = {}


def builder(name: str) -> Callable[[BuilderFn], BuilderFn]:
    def deco(fn: BuilderFn) -> BuilderFn:
        BUILDERS[name] = fn
        return fn
    return deco


# --------------------------------------------------------------------------- 유틸

def d8(value: Optional[date]) -> str:
    """RFC 날짜 문자열 YYYYMMDD."""
    return value.strftime("%Y%m%d") if value else ""


def amt(value: Decimal | int | float | None) -> str:
    """RFC 금액은 문자열로 넘겨 부동소수 오차를 피한다."""
    if value is None:
        return "0.00"
    return f"{Decimal(str(value)):.2f}"


def itemno(n: int) -> str:
    return f"{n:010d}"


def _fiscal(doc: VoucherDocument, ctx: PostingContext) -> tuple[str, str]:
    pd = doc.effective_posting_date or date.today()
    year = str(ctx.fiscal_year or pd.year)
    return year, f"{pd.month:02d}"


def idempotency_key(doc: VoucherDocument) -> str:
    """중복 전기 방지용 참조번호(XBLNR, 최대 16자)."""
    raw = (doc.doc_number or "").strip()
    if not raw:
        parts = [doc.doc_type.value[:6], d8(doc.doc_date), amt(doc.gross_total)]
        raw = "-".join(p for p in parts if p)
    cleaned = "".join(ch for ch in raw if ch.isalnum() or ch in "-_")
    if len(cleaned) <= 16:
        return cleaned
    # XBLNR 은 16자 제한. 앞부분(식별성)과 전체 해시(유일성)를 결합한다.
    digest = hashlib.md5(cleaned.encode("utf-8")).hexdigest()[:6].upper()
    return f"{cleaned[:9]}-{digest}"


def _header_text(doc: VoucherDocument) -> str:
    return f"{KR_NAME.get(doc.doc_type, doc.doc_type.value)} 자동전기"[:25]


class AccDoc:
    """BAPI_ACC_DOCUMENT_POST 파라미터 누적기."""

    def __init__(self, doc: VoucherDocument, ctx: PostingContext,
                 sap_doc_type: str = "KR", bus_act: str = "RFBU") -> None:
        year, period = _fiscal(doc, ctx)
        self.currency = doc.currency or ctx.currency
        self.header = {
            "OBJ_TYPE": "BKPFF",
            "OBJ_KEY": "$",                 # 내부채번
            "OBJ_SYS": "",
            "BUS_ACT": bus_act,
            "USERNAME": ctx.username,
            "HEADER_TXT": _header_text(doc),
            "COMP_CODE": ctx.company_code,
            "DOC_DATE": d8(doc.doc_date),
            "PSTNG_DATE": d8(doc.effective_posting_date),
            "FISC_YEAR": year,
            "FIS_PERIOD": period,
            "DOC_TYPE": sap_doc_type,
            "REF_DOC_NO": idempotency_key(doc),
        }
        self.gl: list[dict[str, Any]] = []
        self.payable: list[dict[str, Any]] = []
        self.receivable: list[dict[str, Any]] = []
        self.tax: list[dict[str, Any]] = []
        self.wt: list[dict[str, Any]] = []
        self.amounts: list[dict[str, Any]] = []
        self._n = 0

    def _next(self) -> str:
        self._n += 1
        return itemno(self._n)

    def _amount(self, no: str, value: Decimal, *, base: Decimal | None = None,
                tax: Decimal | None = None, local: Decimal | None = None,
                rate: Decimal | None = None) -> None:
        row: dict[str, Any] = {
            "ITEMNO_ACC": no, "CURR_TYPE": "00",
            "CURRENCY": self.currency, "AMT_DOCCUR": amt(value),
        }
        if base is not None:
            row["AMT_BASE"] = amt(base)
        if tax is not None:
            row["TAX_AMT"] = amt(tax)
        if rate is not None:
            row["EXCH_RATE"] = amt(rate)
        self.amounts.append(row)
        if local is not None:
            self.amounts.append({
                "ITEMNO_ACC": no, "CURR_TYPE": "10",
                "CURRENCY": "KRW", "AMT_DOCCUR": amt(local),
            })

    # ------------------------------------------------------------ 라인 추가

    def add_gl(self, account: str, value: Decimal, text: str, *,
               tax_code: str | None = None, cost_center: str | None = None,
               wbs: str | None = None, order: str | None = None,
               base: Decimal | None = None, local: Decimal | None = None,
               rate: Decimal | None = None) -> str:
        no = self._next()
        row: dict[str, Any] = {
            "ITEMNO_ACC": no, "GL_ACCOUNT": account.rjust(10, "0"),
            "ITEM_TEXT": (text or "")[:50],
        }
        if tax_code:
            row["TAX_CODE"] = tax_code
        if cost_center:
            row["COSTCENTER"] = cost_center
        if wbs:
            row["WBS_ELEMENT"] = wbs
        if order:
            row["ORDERID"] = order
        self.gl.append(row)
        self._amount(no, value, base=base, local=local, rate=rate)
        return no

    def add_payable(self, vendor: str, value: Decimal, text: str, *,
                    terms: str | None = None, baseline: date | None = None,
                    sp_gl: str | None = None, local: Decimal | None = None,
                    rate: Decimal | None = None) -> str:
        no = self._next()
        row: dict[str, Any] = {
            "ITEMNO_ACC": no, "VENDOR_NO": vendor.rjust(10, "0"),
            "ITEM_TEXT": (text or "")[:50],
        }
        if terms:
            row["PMNTTRMS"] = terms
        if baseline:
            row["BLINE_DATE"] = d8(baseline)
        if sp_gl:
            row["SP_GL_IND"] = sp_gl
        self.payable.append(row)
        self._amount(no, value, local=local, rate=rate)
        return no

    def add_receivable(self, customer: str, value: Decimal, text: str, *,
                       baseline: date | None = None, sp_gl: str | None = None) -> str:
        no = self._next()
        row: dict[str, Any] = {
            "ITEMNO_ACC": no, "CUSTOMER": customer.rjust(10, "0"),
            "ITEM_TEXT": (text or "")[:50],
        }
        if baseline:
            row["BLINE_DATE"] = d8(baseline)
        if sp_gl:
            row["SP_GL_IND"] = sp_gl
        self.receivable.append(row)
        self._amount(no, value)
        return no

    def add_tax(self, account: str, tax_code: str, tax_value: Decimal,
                base_value: Decimal, *, acct_key: str = "VST") -> str:
        no = self._next()
        self.tax.append({
            "ITEMNO_ACC": no, "GL_ACCOUNT": account.rjust(10, "0"),
            "TAX_CODE": tax_code, "ACCT_KEY": acct_key, "COND_KEY": acct_key,
        })
        self._amount(no, tax_value, base=base_value)
        return no

    def add_withholding(self, item_no: str, wt: Any) -> None:
        """ACCOUNTWT - 원천징수. item_no 는 대상 AP 라인 번호."""
        self.wt.append({
            "ITEMNO_ACC": item_no,
            "WT_TYPE": wt.wt_type,
            "WT_CODE": wt.wt_code,
            "BAS_AMT_TC": amt(wt.base_amount),
            "MAN_AMT_TC": amt(wt.income_tax),
            "CURRENCY": self.currency,
        })

    # ------------------------------------------------------------ 산출

    def balanced(self) -> bool:
        total = sum(Decimal(a["AMT_DOCCUR"]) for a in self.amounts
                    if a.get("CURR_TYPE") == "00")
        return abs(total) < Decimal("0.01")

    def params(self) -> dict[str, Any]:
        p: dict[str, Any] = {
            "DOCUMENTHEADER": self.header,
            "CURRENCYAMOUNT": self.amounts,
        }
        if self.gl:
            p["ACCOUNTGL"] = self.gl
        if self.payable:
            p["ACCOUNTPAYABLE"] = self.payable
        if self.receivable:
            p["ACCOUNTRECEIVABLE"] = self.receivable
        if self.tax:
            p["ACCOUNTTAX"] = self.tax
        if self.wt:
            p["ACCOUNTWT"] = self.wt
        return p


def xflags(row: dict[str, Any], *key_fields: str) -> dict[str, Any]:
    """MM BAPI 의 변경 플래그(X-구조)를 만든다.

    SAP 규약상 X-구조는 (a) 키 필드는 값을 그대로 복사하고 `<키>X` 플래그를
    'X' 로 세우며, (b) 나머지는 실제로 값을 넘긴 필드만 'X' 로 표시한다.
    값이 빈 필드에 'X' 를 세우면 "그 필드를 공란으로 설정하라"는 뜻이 되어
    릴리스에 따라 오류가 나거나 의도치 않게 필드가 지워진다.
    """
    out: dict[str, Any] = {}
    for k in key_fields:
        if k in row:
            out[k] = row[k]
            out[f"{k}X"] = "X"
    for k, v in row.items():
        if k in key_fields:
            continue
        if v not in ("", None, []):
            out[k] = "X"
    return out


def _vendor(doc: VoucherDocument) -> str:
    p = doc.supplier
    return (p.sap_vendor if p and p.sap_vendor else "") or "UNMAPPED"


def _customer(doc: VoucherDocument) -> str:
    p = doc.buyer
    return (p.sap_customer if p and p.sap_customer else "") or "UNMAPPED"


def _expense_lines(acc: AccDoc, doc: VoucherDocument, ctx: PostingContext,
                   rules: AccountRules, *, direction: str = "input") -> Decimal:
    """명세 라인을 비용(차변) G/L 라인으로 전개하고 세액 합계를 반환한다."""
    tax_total = Decimal(0)
    items = doc.line_items or [LineItem(
        line_no=1, description=doc.notes or KR_NAME.get(doc.doc_type, ""),
        net_amount=doc.net_total, tax_amount=doc.tax_total)]
    for li in items:
        rule = rules.match(li.description, hint=None)
        account = li.gl_account or rule.gl_account
        tcode = li.tax_code or rules.tax_code(
            rule, direction=direction, has_tax=li.tax_amount > 0)
        acc.add_gl(account, li.net_amount, li.description,
                   tax_code=tcode,
                   cost_center=li.cost_center or ctx.default_cost_center,
                   wbs=li.wbs_element, order=li.internal_order)
        tax_total += li.tax_amount
    return tax_total


# =========================================================================== FI

@builder("acc_ap_invoice")
def acc_ap_invoice(doc: VoucherDocument, ctx: PostingContext,
                   rules: AccountRules) -> dict[str, Any]:
    """매입 세금계산서 → AP 전표 (FB60 상당)."""
    acc = AccDoc(doc, ctx, sap_doc_type="KR")
    tax_total = _expense_lines(acc, doc, ctx, rules)
    if tax_total > 0:
        acc.add_tax(rules.gl("vat_input"), "V1", tax_total, doc.net_total)
    acc.add_payable(_vendor(doc), -doc.gross_total,
                    f"{doc.doc_number or ''} {doc.supplier.name if doc.supplier else ''}",
                    baseline=doc.doc_date)
    return acc.params()


@builder("acc_ar_invoice")
def acc_ar_invoice(doc: VoucherDocument, ctx: PostingContext,
                   rules: AccountRules) -> dict[str, Any]:
    """매출 세금계산서 → AR 전표 (FB70 상당)."""
    acc = AccDoc(doc, ctx, sap_doc_type="DR")
    acc.add_receivable(_customer(doc), doc.gross_total,
                       f"{doc.doc_number or ''} 매출", baseline=doc.doc_date)
    for li in doc.line_items or [LineItem(line_no=1, description="매출",
                                          net_amount=doc.net_total,
                                          tax_amount=doc.tax_total)]:
        acc.add_gl(li.gl_account or "401100", -li.net_amount, li.description,
                   tax_code=li.tax_code or "A1")
    if doc.tax_total > 0:
        acc.add_tax(rules.gl("vat_output"), "A1", -doc.tax_total, -doc.net_total,
                    acct_key="MWS")
    return acc.params()


@builder("acc_gl")
def acc_gl(doc: VoucherDocument, ctx: PostingContext,
           rules: AccountRules) -> dict[str, Any]:
    """순수 G/L 전표 (비용 차변 / 상대계정 대변)."""
    acc = AccDoc(doc, ctx, sap_doc_type="SA")
    tax_total = _expense_lines(acc, doc, ctx, rules)
    if tax_total > 0:
        acc.add_tax(rules.gl("vat_input"), "V1", tax_total, doc.net_total)
    key = credit_account_key(doc.doc_type, doc.payment_method)
    acc.add_gl(rules.gl(key), -doc.gross_total,
               f"{KR_NAME.get(doc.doc_type,'')} 상대계정")
    return acc.params()


@builder("acc_multi_expense")
def acc_multi_expense(doc: VoucherDocument, ctx: PostingContext,
                      rules: AccountRules) -> dict[str, Any]:
    """지출결의·소액현금·일용노무비 - 명세 다건을 한 전표로 묶는다."""
    acc = AccDoc(doc, ctx, sap_doc_type="SA")
    by_credit: dict[str, Decimal] = {}
    for li in doc.line_items:
        rule = rules.match(li.description)
        acc.add_gl(li.gl_account or rule.gl_account, li.net_amount, li.description,
                   tax_code=li.tax_code or rules.tax_code(
                       rule, has_tax=li.tax_amount > 0),
                   cost_center=li.cost_center or ctx.default_cost_center)
        if li.tax_amount > 0:
            acc.add_tax(rules.gl("vat_input"), li.tax_code or "V1",
                        li.tax_amount, li.net_amount)
        key = credit_account_key(doc.doc_type, doc.payment_method)
        by_credit[key] = by_credit.get(key, Decimal(0)) + li.gross_amount
    for key, total in by_credit.items():
        acc.add_gl(rules.gl(key), -total, f"{KR_NAME.get(doc.doc_type,'')} 지급")
    return acc.params()


@builder("acc_card_expense")
def acc_card_expense(doc: VoucherDocument, ctx: PostingContext,
                     rules: AccountRules) -> dict[str, Any]:
    """법인카드 단건 - 비용 / 카드미지급금."""
    acc = AccDoc(doc, ctx, sap_doc_type="SA")
    tax_total = _expense_lines(acc, doc, ctx, rules)
    if tax_total > 0:
        acc.add_tax(rules.gl("vat_input"), "V1", tax_total, doc.net_total)
    acc.add_gl(rules.gl("ap_card"), -doc.gross_total,
               f"법인카드 {doc.doc_number or ''}")
    return acc.params()


@builder("acc_card_statement")
def acc_card_statement(doc: VoucherDocument, ctx: PostingContext,
                       rules: AccountRules) -> dict[str, Any]:
    """법인카드 월 명세 - 건별 비용 차변 + 카드사 미지급금 1라인 대변."""
    acc = AccDoc(doc, ctx, sap_doc_type="KR")
    total = Decimal(0)
    for li in doc.line_items:
        rule = rules.match(li.description)
        tcode = li.tax_code or rules.tax_code(rule, has_tax=li.tax_amount > 0)
        acc.add_gl(li.gl_account or rule.gl_account, li.net_amount, li.description,
                   tax_code=tcode, cost_center=li.cost_center or ctx.default_cost_center)
        if li.tax_amount > 0:
            acc.add_tax(rules.gl("vat_input"), tcode, li.tax_amount, li.net_amount)
        total += li.gross_amount
    acc.add_payable(_vendor(doc), -total, "법인카드 결제대금", baseline=doc.due_date)
    return acc.params()


@builder("acc_cash_expense")
@builder("acc_small_expense")
def acc_cash_expense(doc: VoucherDocument, ctx: PostingContext,
                     rules: AccountRules) -> dict[str, Any]:
    """현금영수증·소액 실물영수증 - 비용 / 현금(또는 카드미지급금)."""
    acc = AccDoc(doc, ctx, sap_doc_type="SA")
    tax_total = _expense_lines(acc, doc, ctx, rules)
    if tax_total > 0:
        acc.add_tax(rules.gl("vat_input"), "V1", tax_total, doc.net_total)
    key = credit_account_key(doc.doc_type, doc.payment_method)
    acc.add_gl(rules.gl(key), -doc.gross_total, f"{KR_NAME.get(doc.doc_type,'')} 지급")
    return acc.params()


@builder("acc_payment_out")
def acc_payment_out(doc: VoucherDocument, ctx: PostingContext,
                    rules: AccountRules) -> dict[str, Any]:
    """출금(지급) - 매입채무 차변 소거 / 은행 대변."""
    acc = AccDoc(doc, ctx, sap_doc_type="KZ")
    acc.add_payable(_vendor(doc), doc.gross_total, f"지급 {doc.doc_number or ''}")
    acc.add_gl(rules.gl("bank"), -doc.gross_total, "출금")
    return acc.params()


@builder("acc_payment_in")
def acc_payment_in(doc: VoucherDocument, ctx: PostingContext,
                   rules: AccountRules) -> dict[str, Any]:
    """입금 - 은행 차변 / 매출채권 대변 소거."""
    acc = AccDoc(doc, ctx, sap_doc_type="DZ")
    acc.add_gl(rules.gl("bank"), doc.gross_total, f"입금 {doc.doc_number or ''}")
    acc.add_receivable(_customer(doc), -doc.gross_total, "매출채권 회수")
    return acc.params()


@builder("acc_fx_payment")
def acc_fx_payment(doc: VoucherDocument, ctx: PostingContext,
                   rules: AccountRules) -> dict[str, Any]:
    """외화 송금 - 거래통화/현지통화 금액과 환율을 함께 전기."""
    acc = AccDoc(doc, ctx, sap_doc_type="KZ")
    acc.currency = doc.currency or "USD"
    rate = doc.exchange_rate
    local = (doc.gross_total * rate) if rate else None
    acc.add_payable(_vendor(doc), doc.gross_total, f"해외송금 {doc.doc_number or ''}",
                    local=local, rate=rate)
    acc.add_gl(rules.gl("bank"), -doc.gross_total, "외화 출금",
               local=(-local if local is not None else None), rate=rate)
    return acc.params()


@builder("acc_reversal")
def acc_reversal(doc: VoucherDocument, ctx: PostingContext,
                 rules: AccountRules) -> dict[str, Any]:
    """BAPI_ACC_DOCUMENT_REV_POST - 당초 전표 역분개."""
    orig = doc.reference_docs.get("original_document", "")
    year, _ = _fiscal(doc, ctx)
    return {
        "REVERSAL": {
            "OBJ_TYPE": "BKPFF",
            "OBJ_KEY": orig,
            "OBJ_KEY_R": "$",
            "OBJ_SYS": "",
            "COMP_CODE": ctx.company_code,
            "REASON_REV": doc.reference_docs.get("reversal_reason", "01"),
            "PSTNG_DATE": d8(doc.effective_posting_date),
            "FIS_PERIOD": _fiscal(doc, ctx)[1],
            "USERNAME": ctx.username,
        },
        "BUS_ACT": "RFBU",
    }


@builder("acc_ap_withholding")
def acc_ap_withholding(doc: VoucherDocument, ctx: PostingContext,
                       rules: AccountRules) -> dict[str, Any]:
    """사업소득 지급 + 원천징수 3.3% (ACCOUNTWT)."""
    acc = AccDoc(doc, ctx, sap_doc_type="KR")
    _expense_lines(acc, doc, ctx, rules)
    ap_no = acc.add_payable(_vendor(doc), -doc.gross_total,
                            f"사업소득 지급 {doc.doc_number or ''}",
                            baseline=doc.doc_date)
    if doc.withholding:
        acc.add_withholding(ap_no, doc.withholding)
    return acc.params()


@builder("acc_wht_settlement")
def acc_wht_settlement(doc: VoucherDocument, ctx: PostingContext,
                       rules: AccountRules) -> dict[str, Any]:
    """연말정산 차감징수(환급)액 정산."""
    acc = AccDoc(doc, ctx, sap_doc_type="SA")
    net = doc.gross_total
    if net < 0:   # 환급
        acc.add_gl(rules.gl("wht_payable"), -net, "연말정산 환급(예수금 감소)")
        acc.add_gl(rules.gl("salary_payable"), net, "환급액 지급의무")
    else:
        acc.add_gl(rules.gl("salary_payable"), -net, "추가징수액")
        acc.add_gl(rules.gl("wht_payable"), net, "연말정산 추가징수(예수금 증가)")
    return acc.params()


@builder("acc_payroll")
def acc_payroll(doc: VoucherDocument, ctx: PostingContext,
                rules: AccountRules) -> dict[str, Any]:
    """급여 전기 - 급여비용 / 예수금·미지급급여."""
    acc = AccDoc(doc, ctx, sap_doc_type="SA")
    gross = doc.gross_total
    deductions = Decimal(0)
    for li in doc.line_items:
        if li.net_amount < 0:                       # 공제 항목
            deductions += -li.net_amount
            key = "si_payable" if any(
                k in li.description for k in ("연금", "건강", "고용", "요양", "산재")
            ) else "wht_payable"
            acc.add_gl(rules.gl(key), li.net_amount, li.description)
        else:
            acc.add_gl(li.gl_account or rules.match(li.description).gl_account,
                       li.net_amount, li.description,
                       cost_center=li.cost_center or ctx.default_cost_center)
    acc.add_gl(rules.gl("salary_payable"), -(gross - deductions), "실지급액(미지급급여)")
    return acc.params()


@builder("acc_social_insurance")
def acc_social_insurance(doc: VoucherDocument, ctx: PostingContext,
                         rules: AccountRules) -> dict[str, Any]:
    """4대보험 고지 - 사업주부담(비용) + 근로자부담(예수금 상계) / 은행."""
    acc = AccDoc(doc, ctx, sap_doc_type="SA")
    employer = Decimal(0)
    employee = Decimal(0)
    for li in doc.line_items:
        # 관례: net_amount=사업주부담, unit_price=근로자부담
        employer += li.net_amount
        employee += (li.unit_price or Decimal(0))
    if employer:
        acc.add_gl(rules.match("보험료").gl_account, employer, "4대보험 사업주부담분")
    if employee:
        acc.add_gl(rules.gl("si_payable"), employee, "근로자부담분 예수금 상계")
    acc.add_gl(rules.gl("bank"), -(employer + employee), "4대보험료 납부")
    return acc.params()


@builder("acc_tax_payment")
def acc_tax_payment(doc: VoucherDocument, ctx: PostingContext,
                    rules: AccountRules) -> dict[str, Any]:
    """국세·지방세 납부."""
    acc = AccDoc(doc, ctx, sap_doc_type="SA")
    is_vat = any("부가" in (li.description or "") for li in doc.line_items) or \
        "부가" in (doc.notes or "")
    if is_vat:
        acc.add_gl(rules.gl("vat_output"), doc.gross_total, "부가세예수금 상계")
    else:
        acc.add_gl(rules.match("세금과공과").gl_account, doc.gross_total,
                   doc.notes or "조세 납부",
                   cost_center=ctx.default_cost_center)
    acc.add_gl(rules.gl("bank"), -doc.gross_total, "세금 납부")
    return acc.params()


@builder("acc_import_vat")
def acc_import_vat(doc: VoucherDocument, ctx: PostingContext,
                   rules: AccountRules) -> dict[str, Any]:
    """수입 부가세만 인식(세관장 발행분)."""
    acc = AccDoc(doc, ctx, sap_doc_type="KR")
    vat = doc.tax_total or doc.gross_total
    acc.add_gl(rules.gl("vat_input"), vat, "수입 부가세 매입세액", tax_code="V1")
    acc.add_payable(_vendor(doc), -vat, "세관 납부 부가세", baseline=doc.doc_date)
    return acc.params()


@builder("acc_bill_of_exchange")
def acc_bill_of_exchange(doc: VoucherDocument, ctx: PostingContext,
                         rules: AccountRules) -> dict[str, Any]:
    """어음 - 특별원장(Special G/L) 전기."""
    acc = AccDoc(doc, ctx, sap_doc_type="SA")
    issued = "발행" in (doc.notes or "") or doc.buyer is not None
    if issued:
        acc.add_payable(_vendor(doc), -doc.gross_total,
                        f"지급어음 {doc.doc_number or ''}", sp_gl="W",
                        baseline=doc.due_date)
        acc.add_gl(rules.gl("ap_trade"), doc.gross_total, "외상매입금 대체")
    else:
        acc.add_receivable(_customer(doc), doc.gross_total,
                           f"받을어음 {doc.doc_number or ''}", sp_gl="W",
                           baseline=doc.due_date)
        acc.add_gl(rules.gl("ar_trade"), -doc.gross_total, "외상매출금 대체")
    return acc.params()


@builder("acc_bank_statement")
def acc_bank_statement(doc: VoucherDocument, ctx: PostingContext,
                       rules: AccountRules) -> dict[str, Any]:
    """은행 명세 라인별 전표(미매칭분은 은행미결계정)."""
    acc = AccDoc(doc, ctx, sap_doc_type="SA")
    for li in doc.line_items:
        acc.add_gl(rules.gl("bank"), li.net_amount, li.description)
        acc.add_gl(li.gl_account or rules.gl("bank_clearing"), -li.net_amount,
                   f"{li.description} 상대계정")
    return acc.params()


# =========================================================================== MM

def _mm_header(doc: VoucherDocument, ctx: PostingContext, *,
               invoice_ind: str = "X", doc_type: str = "RE") -> dict[str, Any]:
    return {
        "INVOICE_IND": invoice_ind,
        "DOC_TYPE": doc_type,
        "DOC_DATE": d8(doc.doc_date),
        "PSTNG_DATE": d8(doc.effective_posting_date),
        "REF_DOC_NO": idempotency_key(doc),
        "COMP_CODE": ctx.company_code,
        "CURRENCY": doc.currency or ctx.currency,
        "GROSS_AMOUNT": amt(doc.gross_total),
        "CALC_TAX_IND": "",
        "HEADER_TXT": _header_text(doc),
        "DIFF_INV": _vendor(doc),
    }


@builder("mm_invoice")
def mm_invoice(doc: VoucherDocument, ctx: PostingContext,
               rules: AccountRules) -> dict[str, Any]:
    """BAPI_INCOMINGINVOICE_CREATE - PO 참조 송장검증(MIRO)."""
    items = []
    for i, li in enumerate(doc.line_items, 1):
        items.append({
            "INVOICE_DOC_ITEM": f"{i:06d}",
            "PO_NUMBER": (li.po_number or doc.reference_docs.get("sap_po", "")),
            "PO_ITEM": (li.po_item or f"{i:05d}"),
            "TAX_CODE": li.tax_code or "V1",
            "ITEM_AMOUNT": amt(li.net_amount),
            "QUANTITY": amt(li.quantity) if li.quantity is not None else "",
            "PO_UNIT": li.unit or "",
            "ITEM_TEXT": (li.description or "")[:50],
        })
    params: dict[str, Any] = {
        "HEADERDATA": _mm_header(doc, ctx),
        "ITEMDATA": items,
    }
    if doc.tax_total > 0:
        params["TAXDATA"] = [{
            "TAX_CODE": doc.line_items[0].tax_code if doc.line_items else "V1",
            "TAX_AMOUNT": amt(doc.tax_total),
            "TAX_BASE_AMOUNT": amt(doc.net_total),
        }]
    return params


@builder("mm_invoice_import")
def mm_invoice_import(doc: VoucherDocument, ctx: PostingContext,
                      rules: AccountRules) -> dict[str, Any]:
    """수입 송장(외화) - 환율 포함."""
    params = mm_invoice(doc, ctx, rules)
    if doc.exchange_rate:
        params["HEADERDATA"]["EXCH_RATE"] = amt(doc.exchange_rate)
    params["HEADERDATA"]["CALC_TAX_IND"] = ""
    return params


@builder("mm_invoice_tax_only")
def mm_invoice_tax_only(doc: VoucherDocument, ctx: PostingContext,
                        rules: AccountRules) -> dict[str, Any]:
    """수입세금계산서 - 부가세만 있는 tax-only 송장."""
    vat = doc.tax_total or doc.gross_total
    header = _mm_header(doc, ctx)
    header["GROSS_AMOUNT"] = amt(vat)
    return {
        "HEADERDATA": header,
        "ITEMDATA": [],
        "TAXDATA": [{"TAX_CODE": "V1", "TAX_AMOUNT": amt(vat),
                     "TAX_BASE_AMOUNT": amt(doc.net_total)}],
    }


@builder("mm_invoice_customs")
def mm_invoice_customs(doc: VoucherDocument, ctx: PostingContext,
                       rules: AccountRules) -> dict[str, Any]:
    """수입신고필증 - 관세/통관비를 계획외 부대비용 송장으로."""
    items = []
    for i, li in enumerate(doc.line_items, 1):
        items.append({
            "INVOICE_DOC_ITEM": f"{i:06d}",
            "PO_NUMBER": li.po_number or doc.reference_docs.get("sap_po", ""),
            "PO_ITEM": li.po_item or f"{i:05d}",
            "ITEM_AMOUNT": amt(li.net_amount),
            "TAX_CODE": li.tax_code or "V1",
            "COND_TYPE": "FRA1",        # 부대비용 조건유형(관세/운임)
            "ITEM_TEXT": (li.description or "관세·통관비")[:50],
        })
    return {"HEADERDATA": _mm_header(doc, ctx), "ITEMDATA": items}


@builder("mm_po")
def mm_po(doc: VoucherDocument, ctx: PostingContext,
          rules: AccountRules) -> dict[str, Any]:
    """BAPI_PO_CREATE1 - 구매오더 생성."""
    header = {
        "COMP_CODE": ctx.company_code,
        "DOC_TYPE": "NB",
        "VENDOR": _vendor(doc),
        "PURCH_ORG": ctx.purchasing_org or "",
        "PUR_GROUP": ctx.purchasing_group or "",
        "CURRENCY": doc.currency or ctx.currency,
        "DOC_DATE": d8(doc.doc_date),
        "REF_1": idempotency_key(doc),
    }
    headerx = xflags(header)          # 값이 있는 필드만 변경 대상으로 표시
    items, itemsx, accts, acctsx, sched, schedx = [], [], [], [], [], []
    for i, li in enumerate(doc.line_items, 1):
        no = f"{i * 10:05d}"
        rule = rules.match(li.description)
        is_service = not li.material
        items.append({
            "PO_ITEM": no,
            "MATERIAL": li.material or "",
            "SHORT_TEXT": (li.description or "")[:40],
            "PLANT": li.plant or ctx.plant or "",
            "QUANTITY": amt(li.quantity or 1),
            "PO_UNIT": li.unit or "EA",
            "NET_PRICE": amt(li.unit_price or li.net_amount),
            "PRICE_UNIT": "1",
            "TAX_CODE": li.tax_code or rules.tax_code(rule, has_tax=li.tax_amount > 0),
            "ACCTASSCAT": "K" if is_service else "",       # K=코스트센터
            "ITEM_CAT": "D" if is_service else "",          # D=서비스
        })
        itemsx.append(xflags(items[-1], "PO_ITEM"))
        if is_service:
            accts.append({
                "PO_ITEM": no, "SERIAL_NO": "01",
                "GL_ACCOUNT": (li.gl_account or rule.gl_account).rjust(10, "0"),
                "COSTCENTER": li.cost_center or ctx.default_cost_center or "",
                "QUANTITY": amt(li.quantity or 1),
            })
            acctsx.append(xflags(accts[-1], "PO_ITEM", "SERIAL_NO"))
        sched.append({"PO_ITEM": no, "SCHED_LINE": "0001",
                      "DELIVERY_DATE": d8(doc.due_date or doc.doc_date),
                      "QUANTITY": amt(li.quantity or 1)})
        schedx.append(xflags(sched[-1], "PO_ITEM", "SCHED_LINE"))
    params = {"POHEADER": header, "POHEADERX": headerx,
              "POITEM": items, "POITEMX": itemsx,
              "POSCHEDULE": sched, "POSCHEDULEX": schedx}
    if accts:
        params["POACCOUNT"] = accts
        params["POACCOUNTX"] = acctsx
    return params


@builder("mm_pr")
def mm_pr(doc: VoucherDocument, ctx: PostingContext,
          rules: AccountRules) -> dict[str, Any]:
    """BAPI_PR_CREATE - 구매요청 생성."""
    items, accts = [], []
    for i, li in enumerate(doc.line_items, 1):
        no = f"{i * 10:05d}"
        rule = rules.match(li.description)
        items.append({
            "PREQ_ITEM": no,
            "SHORT_TEXT": (li.description or "")[:40],
            "MATERIAL": li.material or "",
            "PLANT": li.plant or ctx.plant or "",
            "QUANTITY": amt(li.quantity or 1),
            "UNIT": li.unit or "EA",
            "PREQ_PRICE": amt(li.unit_price or li.net_amount),
            "PURCH_ORG": ctx.purchasing_org or "",
            "PUR_GROUP": ctx.purchasing_group or "",
            "DELIV_DATE": d8(doc.due_date or doc.doc_date),
            "ACCTASSCAT": "K",
            "C_ACC_ASS": "X",
        })
        accts.append({
            "PREQ_ITEM": no, "SERIAL_NO": "01",
            "G_L_ACCT": (li.gl_account or rule.gl_account).rjust(10, "0"),
            "COST_CTR": li.cost_center or ctx.default_cost_center or "",
        })
    return {"PRHEADER": {"PR_TYPE": "NB"},
            "PRHEADERX": {"PR_TYPE": "X"},
            "PRITEM": items,
            "PRITEMX": [xflags(it, "PREQ_ITEM") for it in items],
            "PRACCOUNT": accts,
            "PRACCOUNTX": [xflags(a, "PREQ_ITEM", "SERIAL_NO") for a in accts]}


@builder("mm_contract")
def mm_contract(doc: VoucherDocument, ctx: PostingContext,
                rules: AccountRules) -> dict[str, Any]:
    """BAPI_CONTRACT_CREATE - 구매계약(기간계약)."""
    header = {
        "COMP_CODE": ctx.company_code,
        "DOC_TYPE": "MK",
        "VENDOR": _vendor(doc),
        "PURCH_ORG": ctx.purchasing_org or "",
        "PUR_GROUP": ctx.purchasing_group or "",
        "DOC_DATE": d8(doc.doc_date),
        "VPER_START": d8(doc.doc_date),
        "VPER_END": d8(doc.due_date or doc.doc_date),
        "CURRENCY": doc.currency or ctx.currency,
        "TARGET_VAL": amt(doc.net_total),
        "REF_1": idempotency_key(doc),
    }
    items = [{
        "ITEM_NO": f"{i * 10:05d}",
        "SHORT_TEXT": (li.description or "")[:40],
        "PLANT": li.plant or ctx.plant or "",
        "TARGET_QTY": amt(li.quantity or 1),
        "PO_UNIT": li.unit or "EA",
        "NET_PRICE": amt(li.unit_price or li.net_amount),
        "TAX_CODE": li.tax_code or "V1",
        "ITEM_CAT": "D",
    } for i, li in enumerate(doc.line_items, 1)]
    return {"HEADER": header,
            "HEADERX": xflags(header),
            "ITEM": items,
            "ITEMX": [xflags(it, "ITEM_NO") for it in items]}


@builder("mm_gr")
def mm_gr(doc: VoucherDocument, ctx: PostingContext,
          rules: AccountRules) -> dict[str, Any]:
    """BAPI_GOODSMVT_CREATE - PO 참조 입고(이동유형 101)."""
    items = []
    for i, li in enumerate(doc.line_items, 1):
        items.append({
            "MATERIAL": li.material or "",
            "PLANT": li.plant or ctx.plant or "",
            "STGE_LOC": ctx.storage_location or "",
            "MOVE_TYPE": "101",
            "ENTRY_QNT": amt(li.quantity or 1),
            "ENTRY_UOM": li.unit or "EA",
            "PO_NUMBER": li.po_number or doc.reference_docs.get("sap_po", ""),
            "PO_ITEM": li.po_item or f"{i * 10:05d}",
            "MVT_IND": "B",             # B = PO 참조 입고
            "ITEM_TEXT": (li.description or "")[:50],
        })
    return {
        "GOODSMVT_HEADER": {
            "PSTNG_DATE": d8(doc.effective_posting_date),
            "DOC_DATE": d8(doc.doc_date),
            "REF_DOC_NO": idempotency_key(doc),
            "HEADER_TXT": _header_text(doc),
        },
        "GOODSMVT_CODE": {"GM_CODE": "01"},     # 01 = MB01 입고
        "GOODSMVT_ITEM": items,
    }


@builder("mm_service_entry")
def mm_service_entry(doc: VoucherDocument, ctx: PostingContext,
                     rules: AccountRules) -> dict[str, Any]:
    """BAPI_ENTRYSHEET_CREATE - 서비스 확인서(용역 검수)."""
    po = doc.reference_docs.get("sap_po", "")
    items = [{
        "PCKG_NO": f"{i:010d}",
        "LINE_NO": f"{i:010d}",
        "SHORT_TEXT": (li.description or "")[:40],
        "QUANTITY": amt(li.quantity or 1),
        "BASE_UOM": li.unit or "LE",
        "GR_PRICE": amt(li.unit_price or li.net_amount),
        "EXTERNAL_NUMBER": f"{i:04d}",
    } for i, li in enumerate(doc.line_items, 1)]
    return {
        "ENTRYSHEETHEADER": {
            "PO_NUMBER": po,
            "PO_ITEM": doc.reference_docs.get("sap_po_item", "00010"),
            "SHORT_TEXT": _header_text(doc),
            "DOC_DATE": d8(doc.doc_date),
            "POSTG_DATE": d8(doc.effective_posting_date),
            "ACCEPTANCE": "X",           # 검수 승인 동시 처리
            "REF_DOC_NO": idempotency_key(doc),
        },
        "ENTRYSHEETITEMS": items,
    }


@builder("mm_inb_delivery")
def mm_inb_delivery(doc: VoucherDocument, ctx: PostingContext,
                    rules: AccountRules) -> dict[str, Any]:
    """BAPI_INB_DELIVERY_CREATE - 입고예정 납품."""
    items = [{
        "REF_DOC": li.po_number or doc.reference_docs.get("sap_po", ""),
        "REF_ITEM": li.po_item or f"{i * 10:05d}",
        "DLV_QTY": amt(li.quantity or 1),
        "SALES_UNIT": li.unit or "EA",
        "MATERIAL": li.material or "",
        "PLANT": li.plant or ctx.plant or "",
    } for i, li in enumerate(doc.line_items, 1)]
    return {
        "SHIP_NOTIFICATION_HEADER": {
            "DELIV_NUMB_EXT": doc.doc_number or "",
            "DELIV_DATE": d8(doc.due_date or doc.doc_date),
            "VENDOR": _vendor(doc),
        },
        "SHIP_NOTIFICATION_ITEM": items,
    }


# =========================================================================== SD

@builder("sd_quotation")
def sd_quotation(doc: VoucherDocument, ctx: PostingContext,
                 rules: AccountRules) -> dict[str, Any]:
    """BAPI_QUOTATION_CREATEFROMDATA2 - SD 견적."""
    return {
        "QUOTATION_HEADER_IN": {
            "DOC_TYPE": "AG",
            "SALES_ORG": ctx.sales_org or "",
            "DISTR_CHAN": ctx.distribution_channel or "",
            "DIVISION": ctx.division or "",
            "QT_VALID_F": d8(doc.doc_date),
            "QT_VALID_T": d8(doc.due_date or doc.doc_date),
            "PURCH_NO_C": doc.doc_number or "",
            "CURRENCY": doc.currency or ctx.currency,
        },
        "QUOTATION_ITEMS_IN": [{
            "ITM_NUMBER": f"{i * 10:06d}",
            "MATERIAL": li.material or "",
            "SHORT_TEXT": (li.description or "")[:40],
            "TARGET_QTY": amt(li.quantity or 1),
            "TARGET_QU": li.unit or "EA",
        } for i, li in enumerate(doc.line_items, 1)],
        "QUOTATION_PARTNERS": [{
            "PARTN_ROLE": "AG",
            "PARTN_NUMB": _customer(doc),
        }],
    }


@builder("sd_billing")
def sd_billing(doc: VoucherDocument, ctx: PostingContext,
               rules: AccountRules) -> dict[str, Any]:
    """BAPI_BILLINGDOC_CREATEMULTIPLE - SD 청구문서."""
    return {
        "BILLINGDATAIN": [{
            "SALESORG": ctx.sales_org or "",
            "DISTR_CHAN": ctx.distribution_channel or "",
            "DIVISION": ctx.division or "",
            "DOC_TYPE": "F2",
            "REF_DOC": doc.reference_docs.get("sap_delivery",
                                              doc.reference_docs.get("sap_sales_order", "")),
            "REF_DOC_CA": "J",
            "BILL_DATE": d8(doc.doc_date),
            "SOLD_TO": _customer(doc),
            "PRICE_DATE": d8(doc.doc_date),
        }],
    }


# =========================================================================== FI-TV

def _trip_receipts(doc: VoucherDocument) -> list[dict[str, Any]]:
    out = []
    for i, li in enumerate(doc.line_items, 1):
        out.append({
            "REC_NUMBER": f"{i:04d}",
            "EXP_TYPE": (li.tax_code or "")[:4] or "MEAL",
            "REC_AMOUNT": amt(li.gross_amount),
            "REC_CURR": doc.currency or "KRW",
            "REC_DATE": d8(doc.doc_date),
            "REC_RECEIPT": "X",
            "COMMENT": (li.description or "")[:60],
        })
    return out


@builder("tv_trip")
@builder("tv_trip_receipt")
def tv_trip(doc: VoucherDocument, ctx: PostingContext,
            rules: AccountRules) -> dict[str, Any]:
    """BAPI_TRIP_CREATE_FROM_DATA - 출장/경비 등록."""
    pernr = doc.reference_docs.get("employee_no", "")
    return {
        "EMPLOYEENUMBER": pernr,
        "GENERALDATA": {
            "DATE_BEG": d8(doc.doc_date),
            "DATE_END": d8(doc.due_date or doc.doc_date),
            "COUNTRY": "KR",
            "REASON": (doc.notes or "국내출장")[:40],
            "COMP_CODE": ctx.company_code,
            "COSTCENTER": ctx.default_cost_center or "",
        },
        "RECEIPTS": _trip_receipts(doc),
        "ADVANCES": ([{"ADV_DATE": d8(doc.doc_date),
                       "ADV_AMOUNT": doc.reference_docs["advance_amount"],
                       "ADV_CURR": doc.currency or "KRW"}]
                     if doc.reference_docs.get("advance_amount") else []),
    }


# =========================================================================== 마스터

@builder("md_bp_create")
def md_bp_create(doc: VoucherDocument, ctx: PostingContext,
                 rules: AccountRules) -> dict[str, Any]:
    """BAPI_BUPA_CREATE_FROM_DATA - BP(거래처) 생성."""
    p = doc.supplier or doc.buyer
    name = p.name if p else ""
    return {
        "PARTNERCATEGORY": "2",           # 2 = 조직(법인)
        "PARTNERGROUP": "BP01",
        "CENTRALDATAORGANIZATION": {"NAME1": name[:40]},
        "CENTRALDATA": {"SEARCHTERM1": (p.biz_reg_no if p else "")[:20]},
        "ADDRESSDATA": {
            "STREET": ((p.address if p else "") or "")[:60],
            "COUNTRY": "KR", "LANGU": "KO",
            "TEL1_NUMBR": (p.tel if p else "") or "",
            "E_MAIL": (p.email if p else "") or "",
        },
    }


@builder("md_bp_role")
def md_bp_role(doc: VoucherDocument, ctx: PostingContext,
               rules: AccountRules) -> dict[str, Any]:
    """BAPI_BUPA_ROLE_ADD_2 - 공급업체 역할 부여."""
    return {
        "BUSINESSPARTNER": doc.reference_docs.get("sap_bp", ""),
        "BUSINESSPARTNERROLE": "FLVN00",
    }


@builder("md_bp_bank")
def md_bp_bank(doc: VoucherDocument, ctx: PostingContext,
               rules: AccountRules) -> dict[str, Any]:
    """BAPI_BUPA_BANKDETAIL_ADD - 거래처 은행계좌 등록."""
    b = doc.bank_account
    return {
        "BUSINESSPARTNER": doc.reference_docs.get("sap_bp", ""),
        "BANKDETAILID": "0001",
        "BANKDETAILDATA": {
            "BANKCOUNTRY": "KR",
            "BANKKEY": (b.bank_name if b else "") or "",
            "BANKACCOUNT": ((b.account_no if b else "") or "").replace("-", "")[:18],
            "ACCOUNTHOLDER": (b.holder if b else "") or "",
        },
    }


@builder("doc_attach")
def doc_attach(doc: VoucherDocument, ctx: PostingContext,
               rules: AccountRules) -> dict[str, Any]:
    """ARCHIVOBJECT_CREATE_TABLE - 원본 증빙 아카이빙."""
    return {
        "ARCHIV_ID": "Z1",
        "AR_OBJECT": "ZVOUCHER",
        "DOCUMENTTYPE": "PDF",
        "OBJECT_ID": idempotency_key(doc),
        "FILENAME": doc.source_file or "",
        "SAP_OBJECT": "BKPF",
    }


def build(builder_name: str, doc: VoucherDocument, ctx: PostingContext,
          rules: AccountRules) -> dict[str, Any]:
    if builder_name not in BUILDERS:
        raise KeyError(f"등록되지 않은 빌더: {builder_name}")
    return BUILDERS[builder_name](doc, ctx, rules)
