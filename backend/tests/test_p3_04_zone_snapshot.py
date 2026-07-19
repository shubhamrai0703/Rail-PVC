"""P3-04 regression: when both a generic steel series and a city-specific
variant are present, the city-specific value MUST win.

The reviewed implementation aliased the city-suffixed series to the engine
name only when the generic was absent. With both seeded, the generic won
and two contracts in different zones received identical snapshots.

KU-001 also depends on this service boundary: execute_pvc_run must request
the rolling quarter months derived from the persisted contract base month,
and pre-base bills must preserve the engine's structured blocking error.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from engine.types import BillPayload, IndexSnapshot
from services import pvc_service
from services.errors import EngineValidationProblem
from services.pvc_service import select_zone_series
from services.zone_mapping import city_for_zone


def _val(v: str) -> dict[str, Decimal]:
    return {"2025-01": Decimal(v)}


def test_city_specific_steel_overrides_generic_when_both_present():
    available = {
        "steel_tmt": _val("100"),                # generic — must NOT win
        "steel_tmt_kolkata": _val("200"),        # city-specific for ER → Kolkata
        "steel_angles_kolkata": _val("210"),
        "steel_plates_kolkata": _val("220"),
        "cement": _val("50"),
    }
    out = select_zone_series(available, "ER")
    assert out["steel_tmt"]["2025-01"] == Decimal("200"), (
        "city-specific Kolkata price must override the generic series for ER zone"
    )
    assert "steel_tmt_kolkata" not in out, "city-specific key should be consumed, not duplicated"
    assert out["cement"]["2025-01"] == Decimal("50"), "non-steel series passes through unchanged"


def test_two_zones_get_different_snapshots_when_city_data_seeded():
    available = {
        "steel_tmt": _val("100"),
        "steel_tmt_kolkata": _val("200"),
        "steel_tmt_delhi": _val("300"),
        "steel_angles_kolkata": _val("1"),
        "steel_plates_kolkata": _val("1"),
        "steel_angles_delhi": _val("1"),
        "steel_plates_delhi": _val("1"),
    }
    er = select_zone_series(available, "ER")    # → Kolkata
    nr = select_zone_series(available, "NR")    # → Delhi
    assert er["steel_tmt"]["2025-01"] == Decimal("200")
    assert nr["steel_tmt"]["2025-01"] == Decimal("300")


def test_generic_used_when_no_city_specific_available():
    available = {
        "steel_tmt": _val("100"),
        "steel_angles": _val("110"),
        "steel_plates": _val("120"),
    }
    out = select_zone_series(available, "NR")
    assert out["steel_tmt"]["2025-01"] == Decimal("100")


def test_zone_to_city_mapping_matches_gcc():
    # KU-006: spot-check each zone group to make sure the mapping table itself
    # didn't drift. If you change a mapping, this test should fail and force
    # you to re-read GCC 46A.9(2).
    assert city_for_zone("NR") == "Delhi"
    assert city_for_zone("ER") == "Kolkata"
    assert city_for_zone("CR") == "Mumbai"
    assert city_for_zone("SR") == "Chennai"
    with pytest.raises(ValueError):
        city_for_zone("INVALID-ZONE")


def _bill(measurement_date: date) -> BillPayload:
    return BillPayload(
        on_account_amount=Decimal("100000"),
        cement_amount=Decimal("0"),
        steel_angles_amount=Decimal("0"),
        steel_plates_amount=Decimal("0"),
        steel_tmt_amount=Decimal("0"),
        steel_other_amount=Decimal("0"),
        technical_withheld=Decimal("0"),
        recoveries_affecting_pvc=Decimal("0"),
        extra_item_decisions=[],
        carry_forwards=[],
        measurement_date=measurement_date,
    )


def _contract_session(base_month: date) -> AsyncMock:
    result = MagicMock()
    result.mappings.return_value.first.return_value = {
        "base_month": base_month,
        "railway_zone": "WR",
    }
    session = AsyncMock()
    session.execute = AsyncMock(return_value=result)
    return session


def _rule_set_row() -> dict[str, object]:
    return {
        "id": "rule-1",
        "quarter_mode": "measurement_date",
        "component_weights": {
            "labour": "0.2",
            "plant": "0.2",
            "fuel": "0.2",
            "materials": "0.2",
        },
        "adjustable_fraction": "0.85",
        "negative_pvc_policy": "allow",
        "quarter_avg_precision": "full",
        "rounding_mode": "round_2",
    }


@pytest.mark.asyncio
async def test_execute_pvc_run_loads_rolling_months_from_contract_base(monkeypatch):
    base_month = date(2023, 7, 1)
    session = _contract_session(base_month)
    captured: dict[str, object] = {}

    async def _build_bill_payload(_session, _bill_id, _contract_id):
        return _bill(date(2024, 4, 15))

    async def _build_index_snapshot(_session, base, months, zone):
        captured.update(base=base, months=months, zone=zone)
        return IndexSnapshot(base_month=base, series={})

    result = MagicMock(validation_errors=[])

    async def _persist_run_result(*_args, **_kwargs):
        return {"id": "run-1"}

    monkeypatch.setattr(pvc_service, "build_bill_payload", _build_bill_payload)
    monkeypatch.setattr(pvc_service, "build_index_snapshot", _build_index_snapshot)
    monkeypatch.setattr(pvc_service, "calculate_pvc", lambda *_args: result)
    monkeypatch.setattr(pvc_service, "persist_run_result", _persist_run_result)

    output = await pvc_service.execute_pvc_run(
        session,
        tenant_id="tenant-1",
        contract_id="contract-1",
        bill_id="bill-1",
        rule_set_row=_rule_set_row(),
        idempotency_key=None,
    )

    assert output == {"id": "run-1"}
    assert captured == {
        "base": base_month,
        "months": [date(2024, 2, 1), date(2024, 3, 1), date(2024, 4, 1)],
        "zone": "WR",
    }


@pytest.mark.asyncio
async def test_execute_pvc_run_surfaces_pre_base_engine_validation(monkeypatch):
    base_month = date(2024, 12, 1)
    session = _contract_session(base_month)
    persist = AsyncMock()

    async def _build_bill_payload(_session, _bill_id, _contract_id):
        return _bill(date(2024, 11, 30))

    async def _build_index_snapshot(_session, base, months, _zone):
        assert base == base_month
        assert months == []
        return IndexSnapshot(base_month=base, series={})

    monkeypatch.setattr(pvc_service, "build_bill_payload", _build_bill_payload)
    monkeypatch.setattr(pvc_service, "build_index_snapshot", _build_index_snapshot)
    monkeypatch.setattr(pvc_service, "persist_run_result", persist)

    with pytest.raises(EngineValidationProblem) as exc:
        await pvc_service.execute_pvc_run(
            session,
            tenant_id="tenant-1",
            contract_id="contract-1",
            bill_id="bill-1",
            rule_set_row=_rule_set_row(),
            idempotency_key=None,
        )

    assert exc.value.status_code == 422
    assert exc.value.extra["validation_errors"] == [
        "measurement_date 2024-11-30 falls in or before the contract base "
        "month 2024-12 — no PVC quarter exists yet"
    ]
    persist.assert_not_awaited()


def test_pre_base_bill_returns_422_engine_validation_over_http(monkeypatch):
    """KU-001-REVIEW: prove the pre-Q1 block reaches an HTTP caller as a
    structured 422 — POST route → execute_pvc_run → real resolver + engine →
    EngineValidationProblem → registered ApiProblem handler → JSON body.
    Only the DB session and payload builders are stubbed; the quarter
    resolver, calculator, and exception wiring are all real."""
    from fastapi.testclient import TestClient

    from main import app
    from services.auth import AuthUser, get_current_user
    from services.db import get_session

    base_month = date(2024, 12, 1)

    # The route + service issue three queries in order: rule-set lookup,
    # bill-ownership check, contract base_month/zone select.
    rule_set_result = MagicMock()
    rule_set_result.mappings.return_value.first.return_value = _rule_set_row()
    bill_result = MagicMock()
    bill_result.first.return_value = (1,)
    contract_result = MagicMock()
    contract_result.mappings.return_value.first.return_value = {
        "base_month": base_month,
        "railway_zone": "WR",
    }
    session = AsyncMock()
    session.execute = AsyncMock(
        side_effect=[rule_set_result, bill_result, contract_result]
    )

    async def _override_user() -> AuthUser:
        return AuthUser(
            user_id="u-1",
            tenant_id="tenant-1",
            auth_id="auth-1",
            email="t@example.com",
            display_name="t@example.com",
        )

    async def _override_session():
        return session

    async def _build_bill_payload(_session, _bill_id, _contract_id):
        return _bill(date(2024, 11, 30))

    async def _build_index_snapshot(_session, base, months, _zone):
        assert months == []
        return IndexSnapshot(base_month=base, series={})

    persist = AsyncMock()
    monkeypatch.setattr(pvc_service, "build_bill_payload", _build_bill_payload)
    monkeypatch.setattr(pvc_service, "build_index_snapshot", _build_index_snapshot)
    monkeypatch.setattr(pvc_service, "persist_run_result", persist)

    app.dependency_overrides[get_current_user] = _override_user
    app.dependency_overrides[get_session] = _override_session
    try:
        client = TestClient(app)
        resp = client.post(
            "/api/contracts/contract-1/pvc-runs",
            json={"bill_id": "bill-1"},
        )
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_session, None)

    assert resp.status_code == 422
    detail = resp.json()["detail"]
    assert detail["code"] == "engine_validation_error"
    assert detail["validation_errors"] == [
        "measurement_date 2024-11-30 falls in or before the contract base "
        "month 2024-12 — no PVC quarter exists yet"
    ]
    persist.assert_not_awaited()
