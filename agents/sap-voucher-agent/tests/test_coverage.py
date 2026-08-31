"""50종 증빙 전 유형에 대한 커버리지 회귀 테스트."""
from decimal import Decimal

import pytest

from sap_voucher_agent.builders import BUILDERS, idempotency_key
from sap_voucher_agent.doc_types import KR_NAME, DocType
from sap_voucher_agent.fixtures import FACTORIES
from sap_voucher_agent.mapping import ROUTES
from sap_voucher_agent.planner import plan
from sap_voucher_agent.poster import post
from sap_voucher_agent.sap.bapi_defs import BAPIS

ALL_TYPES = [t for t in DocType if t is not DocType.UNKNOWN]


def test_50_doc_types_defined():
    assert len(ALL_TYPES) == 50
    assert all(t in KR_NAME for t in ALL_TYPES)


@pytest.mark.parametrize("dt", ALL_TYPES, ids=lambda t: t.value)
def test_every_type_has_route_fixture_and_builders(dt):
    assert dt in ROUTES, f"{dt} 에 전기 경로가 없다"
    assert dt in FACTORIES, f"{dt} 에 샘플 픽스처가 없다"
    route = ROUTES[dt]
    for steps in route.variants.values():
        assert steps, f"{dt} 의 variant 가 비어 있다"
        for step in steps:
            assert step.bapi in BAPIS, f"{step.bapi} 가 BAPI 카탈로그에 없다"
            assert step.builder in BUILDERS, f"{step.builder} 빌더가 없다"


@pytest.mark.parametrize("dt", ALL_TYPES, ids=lambda t: t.value)
def test_every_type_plans_and_posts(dt, resolved_samples, ctx, sap, rules):
    doc = resolved_samples[dt]
    p = plan(doc, ctx, rules)
    assert p.postable, f"{dt} 계획 실패: {p.validation_errors}"
    assert p.calls, f"{dt} 에 BAPI 호출이 없다"

    dry = post(p, sap, dry_run=True)
    assert dry.success, f"{dt} DRY-RUN 실패: {dry.summary()}"

    out = post(p, sap, dry_run=False, allow_unapproved=True)
    assert out.success, f"{dt} 전기 실패: {out.summary()}"
    assert out.committed or not any(c.commit for c in p.calls)


@pytest.mark.parametrize("dt", ALL_TYPES, ids=lambda t: t.value)
def test_idempotency_key_fits_xblnr(dt, resolved_samples):
    key = idempotency_key(resolved_samples[dt])
    assert 0 < len(key) <= 16, f"{dt} 멱등키 길이 위반: {key}"


def test_fi_documents_are_balanced(resolved_samples, ctx, rules):
    """FI 전표는 반드시 차대가 일치해야 한다."""
    for dt, doc in resolved_samples.items():
        p = plan(doc, ctx, rules)
        for call in p.calls:
            if call.bapi != "BAPI_ACC_DOCUMENT_POST":
                continue
            amounts = call.params.get("CURRENCYAMOUNT", [])
            total = sum(Decimal(a["AMT_DOCCUR"]) for a in amounts
                        if a.get("CURR_TYPE") == "00")
            assert abs(total) < Decimal("0.01"), (
                f"{dt} FI 전표 차대 불일치: {total}")
