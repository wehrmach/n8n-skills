# -*- coding: utf-8 -*-
"""K-IFRS 회계판단 시연.

같은 증빙이라도 세법상 형식과 K-IFRS 회계 실질이 갈리는 지점을 보여준다.
실행: python3 examples/kifrs_walkthrough.py
"""
from __future__ import annotations

import sys
from datetime import date
from decimal import Decimal as D
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sap_voucher_agent.doc_types import DocType                # noqa: E402
from sap_voucher_agent.fixtures import sample                  # noqa: E402
from sap_voucher_agent.kifrs import assess                     # noqa: E402
from sap_voucher_agent.master_data import MasterLookup, enrich  # noqa: E402
from sap_voucher_agent.models import (LineItem, Party,          # noqa: E402
                                      PostingContext, VoucherDocument)
from sap_voucher_agent.planner import plan                     # noqa: E402
from sap_voucher_agent.poster import post                      # noqa: E402
from sap_voucher_agent.sap.mock import MockClient              # noqa: E402

CTX = PostingContext(
    company_code="1000", fiscal_year=2026, default_cost_center="1000-ADM",
    period_end=date(2026, 3, 31), approval_threshold=D("50000000"))
LOOKUP = MasterLookup()


def _vendor_doc(desc: str, net: str, tax: str = "0", **kw) -> VoucherDocument:
    lines = kw.pop("lines", None) or [LineItem(
        line_no=1, description=desc, net_amount=D(net), tax_amount=D(tax),
        service_start=kw.pop("service_start", None),
        service_end=kw.pop("service_end", None))]
    doc = VoucherDocument(
        doc_type=kw.pop("doc_type", DocType.TAX_INVOICE_IN),
        doc_number=kw.pop("doc_number", "DEMO-0001"),
        doc_date=kw.pop("doc_date", date(2026, 3, 1)),
        supplier=Party(name="(주)한빛테크놀로지", biz_reg_no="214-81-01117"),
        buyer=Party(name="(주)미래유통", biz_reg_no="137-81-23454"),
        net_total=sum(li.net_amount for li in lines),
        tax_total=sum(li.tax_amount for li in lines),
        gross_total=sum(li.gross_amount for li in lines),
        line_items=lines, **kw)
    enrich(doc, LOOKUP)
    return doc


def show(title: str, tax_view: str, doc: VoucherDocument,
         ctx: PostingContext | None = None) -> None:
    ctx = ctx or CTX
    enrich(doc, LOOKUP)
    print("=" * 96)
    print(f"■ {title}")
    print(f"  세법상 시각 : {tax_view}")
    a = assess(doc.model_copy(deep=True), ctx)
    print(f"  K-IFRS 실질 : {a.substance}")
    print(f"  인식 결론   : {a.recognition.kr}")
    for r in a.rationale:
        print(f"    · {r}")
    for j in a.judgments:
        print(f"    ! {j}")
    p = plan(doc, ctx)
    if p.calls:
        gl = p.calls[0].params.get("ACCOUNTGL") or []
        amounts = {x["ITEMNO_ACC"]: x["AMT_DOCCUR"]
                   for x in p.calls[0].params.get("CURRENCYAMOUNT", [])}
        if amounts:
            print("  생성 분개(차변/대변)")
            for row in gl:
                amt = D(amounts.get(row["ITEMNO_ACC"], "0"))
                side = "차변" if amt > 0 else "대변"
                print(f"    {side} {row['GL_ACCOUNT']} {abs(amt):>14,.0f}  "
                      f"{row.get('ITEM_TEXT','')[:40]}")
        for row in p.calls[0].params.get("ACCOUNTPAYABLE", []):
            amt = D(amounts.get(row["ITEMNO_ACC"], "0"))
            side = "차변" if amt > 0 else "대변"
            print(f"    {side} 공급업체 {row['VENDOR_NO']} {abs(amt):>10,.0f}  "
                  f"{row.get('ITEM_TEXT','')[:34]}")
        for row in p.calls[0].params.get("ACCOUNTRECEIVABLE", []):
            amt = D(amounts.get(row["ITEMNO_ACC"], "0"))
            side = "차변" if amt > 0 else "대변"
            print(f"    {side} 고객 {row['CUSTOMER']} {abs(amt):>13,.0f}  "
                  f"{row.get('ITEM_TEXT','')[:34]}")
    elif p.validation_errors:
        print(f"  전표 생성 불가: {p.validation_errors[0][:90]}")
    if p.amortization_schedule:
        print(f"  기간배분 스케줄 {len(p.amortization_schedule)}건 "
              f"(첫 회 {p.amortization_schedule[0]['period']} "
              f"{float(p.amortization_schedule[0]['amount']):,.0f}원)")
    if p.requires_approval:
        print(f"  → 자동 전기 차단: {p.approval_reasons[0][:90]}")
    print()


def main() -> int:
    print("K-IFRS 회계판단 시연 - 세법상 증빙 형식 vs 회계상 거래 실질\n")

    show("① 입금표 - 대금 13,750,000원 수령",
         "현금영수 사실을 증명하는 서류",
         sample(DocType.PAYMENT_RECEIPT))

    show("② 용역계약서 - 계약금액 13,750,000원",
         "인지세 과세문서, 거래 성립의 증거",
         sample(DocType.SERVICE_CONTRACT))

    show("③ 연간 화재보험료 세금계산서 (2026-03 ~ 2027-02)",
         "2026년 1기 매입세액 공제 대상, 작성일에 전액 매입 계상",
         _vendor_doc("사무실 화재보험료 연간", "12000000", "1200000",
                     service_start=date(2026, 3, 1), service_end=date(2027, 2, 28)))

    show("④ ERP 개발용역 세금계산서 8,000,000원 - 자본화 판단 전",
         "용역 매입, 전액 손금",
         _vendor_doc("ERP 연동 모듈 개발", "8000000", "800000"))

    capex_ctx = CTX.model_copy(update={"intangible_capitalization": True})
    show("⑤ 같은 증빙 - 개발비 자본화 요건 충족으로 회사가 판정한 경우",
         "동일 (세법상 차이 없음)",
         _vendor_doc("ERP 연동 모듈 개발", "8000000", "800000"), capex_ctx)

    prebill = sample(DocType.BILLING_REQUEST)
    prebill.performance_date = date(2026, 6, 30)
    show("⑥ 선청구 - 용역 제공 전 청구서 발행",
         "공급시기 도래로 세금계산서 발행 의무",
         prebill)

    show("⑦ 수입세금계산서 - 세관장 발행 부가세 2,100,000원",
         "수입 매입세액 공제 증빙",
         sample(DocType.IMPORT_TAX_INVOICE))

    show("⑧ 수정세금계산서 - 당초분 △13,750,000원 취소",
         "당초 세금계산서 취소 후 재발행",
         sample(DocType.TAX_INVOICE_AMENDED))

    # 실제 전기까지 이어지는지 확인
    sap = MockClient()
    doc = _vendor_doc("사무실 화재보험료 연간", "12000000", "1200000",
                      service_start=date(2026, 3, 1), service_end=date(2027, 2, 28))
    p = plan(doc, CTX)
    dry = post(p, sap, dry_run=True)
    out = post(p, sap, dry_run=False, allow_unapproved=True)
    print("=" * 96)
    print("■ ③번 증빙 실제 전기 결과")
    print(f"  DRY-RUN : {dry.summary()}")
    print(f"  전기     : {out.summary()}")
    print(f"  이후 매월 상각 전기 {len(p.amortization_schedule)}건이 남는다 "
          "(SAP 발생/이연 엔진 ACACTREE01 또는 반복전표 FBD1).")
    return 0 if out.success else 1


if __name__ == "__main__":
    raise SystemExit(main())
