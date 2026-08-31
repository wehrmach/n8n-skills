import sys
from decimal import Decimal
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sap_voucher_agent.accounts import AccountRules          # noqa: E402
from sap_voucher_agent.master_data import MasterLookup       # noqa: E402
from sap_voucher_agent.models import PostingContext          # noqa: E402
from sap_voucher_agent.sap.mock import MockClient            # noqa: E402


@pytest.fixture
def ctx() -> PostingContext:
    return PostingContext(
        company_code="1000", fiscal_year=2026, username="AI_AGENT",
        purchasing_org="1000", purchasing_group="001", plant="1000",
        storage_location="0001", sales_org="1000", distribution_channel="10",
        division="00", default_cost_center="1000-ADM",
        approval_threshold=Decimal("50000000"))


@pytest.fixture
def sap() -> MockClient:
    return MockClient()


@pytest.fixture
def rules() -> AccountRules:
    return AccountRules()


@pytest.fixture
def lookup(sap) -> MasterLookup:
    return MasterLookup(client=sap)


@pytest.fixture
def resolved_samples(lookup):
    """마스터가 해석된 50종 샘플."""
    from sap_voucher_agent.fixtures import all_samples
    from sap_voucher_agent.master_data import enrich
    out = {}
    for dt, doc in all_samples().items():
        doc.source_file = f"{dt.value}.pdf"
        enrich(doc, lookup)
        if doc.supplier and not doc.supplier.sap_vendor:
            doc.supplier.sap_vendor = "0000199999"
        if doc.buyer and not doc.buyer.sap_customer:
            doc.buyer.sap_customer = "0000299999"
        out[dt] = doc
    return out
