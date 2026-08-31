# -*- coding: utf-8 -*-
"""50종 증빙 전체를 Mock SAP 에 전기해 커버리지를 검증한다.

실행: python3 examples/run_all_types.py [--rfc]
"""
from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sap_voucher_agent.accounts import AccountRules            # noqa: E402
from sap_voucher_agent.doc_types import KR_NAME, DocType       # noqa: E402
from sap_voucher_agent.fixtures import all_samples             # noqa: E402
from sap_voucher_agent.master_data import MasterLookup, enrich  # noqa: E402
from sap_voucher_agent.models import PostingContext            # noqa: E402
from sap_voucher_agent.planner import plan                     # noqa: E402
from sap_voucher_agent.poster import post                      # noqa: E402
from sap_voucher_agent.sap.mock import MockClient              # noqa: E402

CTX = PostingContext(
    company_code="1000", fiscal_year=2026, username="AI_AGENT",
    purchasing_org="1000", purchasing_group="001", plant="1000",
    storage_location="0001", sales_org="1000", distribution_channel="10",
    division="00", default_cost_center="1000-ADM",
    approval_threshold=Decimal("50000000"),
)


def main() -> int:
    sap = MockClient()
    rules = AccountRules()
    lookup = MasterLookup(client=sap)
    samples = all_samples()

    ok = warn = blocked = failed = 0
    rows = []
    for dt, doc in samples.items():
        doc.source_file = f"{dt.value}.pdf"
        enrich(doc, lookup)
        # 마스터 미등록 거래처는 신규 채번했다고 가정(에이전트라면 사람에게 확인)
        if doc.supplier is not None and not doc.supplier.sap_vendor:
            doc.supplier.sap_vendor = "0000199999"
        if doc.buyer is not None and not doc.buyer.sap_customer:
            doc.buyer.sap_customer = "0000299999"

        p = plan(doc, CTX, rules)
        bapis = " → ".join(c.bapi.replace("BAPI_", "") for c in p.calls) or "-"
        if not p.postable:
            blocked += 1
            rows.append((dt, "차단", bapis, p.validation_errors[0][:60]))
            continue
        dry = post(p, sap, dry_run=True)
        if not dry.success:
            failed += 1
            rows.append((dt, "DRY실패", bapis, (dry.aborted_reason or "")[:60]))
            continue
        out = post(p, sap, dry_run=False, allow_unapproved=True)
        if out.success:
            ok += 1
            docs = ", ".join(f"{v}" for v in out.document_numbers.values())
            status = "전기완료" if not p.requires_approval else "전기완료(승인후)"
            if p.validation_warnings:
                warn += 1
            rows.append((dt, status, bapis, docs[:60]))
        else:
            failed += 1
            rows.append((dt, "전기실패", bapis, (out.aborted_reason or "")[:60]))

    w = max(len(KR_NAME[dt]) for dt, *_ in rows)
    print(f"{'증빙 유형':<{w}}  {'상태':<12} {'BAPI':<44} 결과")
    print("-" * (w + 110))
    for dt, status, bapis, detail in rows:
        print(f"{KR_NAME[dt]:<{w}}  {status:<12} {bapis:<44} {detail}")
    print("-" * (w + 110))
    print(f"총 {len(rows)}종 | 전기완료 {ok} | 경고동반 {warn} | "
          f"검증차단 {blocked} | 실패 {failed}")
    print(f"MockSAP: 호출 {len(sap.calls)}건 / COMMIT {sap.committed} / "
          f"ROLLBACK {sap.rolled_back}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
