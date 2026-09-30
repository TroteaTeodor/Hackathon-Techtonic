"""The shared mock fixtures (frontend/src/mocks) must match the backend contract."""

import json
from pathlib import Path

import pytest
from pydantic import TypeAdapter

from app import schemas

FIXTURES = Path("/contract-fixtures")
MODELS = {
    "me-customer.json": schemas.Me,
    "me-advisor.json": schemas.Me,
    "overview-sara.json": schemas.CustomerOverview,
    "customers.json": list[schemas.CustomerSummary],
    "customer-detail-sara.json": schemas.CustomerDetail,
    "customer-detail-jan.json": schemas.CustomerDetail,
    "customer-detail-after-inject.json": schemas.CustomerDetail,
    "scale.json": schemas.ScaleStats,
}


@pytest.mark.parametrize("name", sorted(MODELS))
def test_fixture_matches_contract(name):
    path = FIXTURES / name
    if not FIXTURES.exists():
        pytest.skip("contract fixtures are not mounted")
    TypeAdapter(MODELS[name]).validate_python(json.loads(path.read_text()))


def test_every_fixture_is_covered():
    if not FIXTURES.exists():
        pytest.skip("contract fixtures are not mounted")
    assert {p.name for p in FIXTURES.glob("*.json")} == set(MODELS)
