"""KU-001-STC-AVG backend persistence and run-threading regression tests.

The quarter-average precision policy belongs to the versioned rule-set row.
These tests pin every backend boundary that must carry it: migration,
contract bootstrap, rule-set API reads/updates, run selection, and the engine
payload constructed for a run.
"""
from __future__ import annotations

import importlib.util
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import ValidationError
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import create_async_engine

from api.pvc_rules import RuleSetUpdate, get_rule_set, update_rule_set
from api.pvc_runs import PVCRunCreate, create_pvc_run
from engine.types import BillPayload, IndexSnapshot
from services import pvc_service
from services.auth import AuthUser


MIGRATION = (
    Path(__file__).resolve().parent.parent
    / "migrations"
    / "versions"
    / "018_quarter_avg_precision.py"
)


def _user() -> AuthUser:
    return AuthUser(
        user_id="user-1",
        tenant_id="tenant-A",
        auth_id="auth-1",
        email="t@example.com",
        display_name="t@example.com",
    )


def _result(*, mapping: Any = None, first: Any = None) -> MagicMock:
    result = MagicMock()
    result.mappings.return_value.first.return_value = mapping
    result.first.return_value = first
    return result


def _rule_set_row(precision: str = "half_up_2dp") -> dict[str, object]:
    return {
        "id": "rule-2",
        "version": 2,
        "quarter_mode": "measurement_date",
        "component_weights": {
            "labour": "0.20",
            "plant": "0.30",
            "fuel": "0.15",
            "materials": "0.20",
        },
        "adjustable_fraction": "0.85",
        "rounding_mode": "round_2",
        "negative_pvc_policy": "zero_floor",
        "quarter_avg_precision": precision,
    }


def _rule_update(precision: str = "half_up_2dp") -> RuleSetUpdate:
    return RuleSetUpdate(
        component_weights={
            "labour": Decimal("0.20"),
            "plant": Decimal("0.30"),
            "fuel": Decimal("0.15"),
            "materials": Decimal("0.20"),
        },
        adjustable_fraction=Decimal("0.85"),
        rounding_mode="round_2",
        negative_pvc_policy="zero_floor",
        quarter_avg_precision=precision,
    )


@pytest.mark.asyncio
async def test_migration_defaults_to_full_and_rejects_unknown_policy(monkeypatch):
    assert MIGRATION.exists(), "migration 018 must persist quarter_avg_precision"
    spec = importlib.util.spec_from_file_location("migration_018", MIGRATION)
    assert spec is not None and spec.loader is not None
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)

    statements: list[str] = []
    monkeypatch.setattr(migration.op, "execute", lambda stmt: statements.append(str(stmt)))
    migration.upgrade()

    assert migration.revision == "018"
    assert migration.down_revision == "017"
    assert len(statements) == 1
    alter_sql = statements[0]
    assert "quarter_avg_precision TEXT NOT NULL DEFAULT 'full'" in alter_sql
    assert "CHECK (quarter_avg_precision IN ('full', 'half_up_2dp'))" in alter_sql

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    try:
        async with engine.begin() as conn:
            await conn.execute(text("CREATE TABLE pvc_rule_sets (id TEXT PRIMARY KEY)"))
            await conn.execute(text(alter_sql))
            await conn.execute(text("INSERT INTO pvc_rule_sets (id) VALUES ('default')"))
            default_value = (
                await conn.execute(
                    text(
                        "SELECT quarter_avg_precision FROM pvc_rule_sets "
                        "WHERE id = 'default'"
                    )
                )
            ).scalar_one()
            assert default_value == "full"

            with pytest.raises(IntegrityError):
                await conn.execute(
                    text(
                        "INSERT INTO pvc_rule_sets (id, quarter_avg_precision) "
                        "VALUES ('invalid', 'bankers_2dp')"
                    )
                )
    finally:
        await engine.dispose()


def test_default_rule_set_explicitly_uses_full_precision():
    assert pvc_service.default_rule_set_payload()["quarter_avg_precision"] == "full"


@pytest.mark.asyncio
async def test_contract_bootstrap_inserts_default_precision():
    contract_row = {"id": "contract-1", "created_at": datetime(2026, 7, 19)}
    session = MagicMock()
    session.begin_nested = MagicMock()
    session.execute = AsyncMock(
        side_effect=[_result(mapping=contract_row), _result()]
    )

    await pvc_service.create_contract_with_default_rule_set(
        session,
        tenant_id="tenant-A",
        contract_data={},
    )

    rule_insert = session.execute.await_args_list[1]
    sql = str(rule_insert.args[0])
    params = rule_insert.args[1]
    assert "quarter_avg_precision" in sql
    assert ":quarter_avg_precision" in sql
    assert params["quarter_avg_precision"] == "full"


@pytest.mark.asyncio
async def test_rule_get_selects_and_returns_precision():
    row = _rule_set_row()
    session = AsyncMock()
    session.execute = AsyncMock(return_value=_result(mapping=row))

    out = await get_rule_set("contract-1", user=_user(), session=session)

    assert out["quarter_avg_precision"] == "half_up_2dp"
    sql = str(session.execute.await_args.args[0])
    assert "rs.quarter_avg_precision" in sql
    assert "ORDER BY rs.version DESC LIMIT 1" in sql


def test_rule_update_rejects_unknown_precision():
    with pytest.raises(ValidationError):
        _rule_update("bankers_2dp")


@pytest.mark.asyncio
async def test_rule_update_persists_precision():
    session = AsyncMock()
    session.execute = AsyncMock(
        side_effect=[
            _result(first=(1,)),
            _result(first=None),
            _result(mapping={"id": "rule-2", "version": 2}),
        ]
    )

    await update_rule_set(
        "contract-1", body=_rule_update(), user=_user(), session=session
    )

    update_call = session.execute.await_args_list[2]
    sql = str(update_call.args[0])
    params = update_call.args[1]
    assert "quarter_avg_precision = COALESCE(:qap, quarter_avg_precision)" in sql
    assert params["qap"] == "half_up_2dp"


@pytest.mark.asyncio
async def test_rule_update_omitted_precision_preserves_stored_policy():
    """A pre-KU-001-STC-AVG client that PUTs without the field must not
    silently reset a half_up_2dp rule set back to full precision."""
    body = RuleSetUpdate(
        component_weights={
            "labour": Decimal("0.20"),
            "plant": Decimal("0.30"),
            "fuel": Decimal("0.15"),
            "materials": Decimal("0.20"),
        },
        adjustable_fraction=Decimal("0.85"),
        rounding_mode="round_2",
        negative_pvc_policy="zero_floor",
    )
    assert "quarter_avg_precision" not in body.model_fields_set
    assert body.quarter_avg_precision is None

    session = AsyncMock()
    session.execute = AsyncMock(
        side_effect=[
            _result(first=(1,)),
            _result(first=None),
            _result(
                mapping={
                    "id": "rule-2",
                    "version": 2,
                    "quarter_avg_precision": "half_up_2dp",
                }
            ),
        ]
    )

    out = await update_rule_set(
        "contract-1", body=body, user=_user(), session=session
    )

    update_call = session.execute.await_args_list[2]
    sql = str(update_call.args[0])
    params = update_call.args[1]
    assert "COALESCE(:qap, quarter_avg_precision)" in sql
    assert params["qap"] is None
    assert out["quarter_avg_precision"] == "half_up_2dp"


@pytest.mark.asyncio
async def test_run_route_selects_latest_precision_and_passes_selected_row(monkeypatch):
    row = _rule_set_row()
    session = AsyncMock()
    session.execute = AsyncMock(
        side_effect=[_result(mapping=row), _result(first=(1,))]
    )
    execute = AsyncMock(return_value={"id": "run-1"})
    monkeypatch.setattr("api.pvc_runs.execute_pvc_run", execute)

    await create_pvc_run(
        contract_id="contract-1",
        body=PVCRunCreate(bill_id="bill-1"),
        user=_user(),
        session=session,
        idempotency_key=None,
    )

    select_sql = str(session.execute.await_args_list[0].args[0])
    assert "rs.quarter_avg_precision" in select_sql
    assert "ORDER BY rs.version DESC LIMIT 1" in select_sql
    selected = execute.await_args.kwargs["rule_set_row"]
    assert selected["id"] == "rule-2"
    assert selected["quarter_avg_precision"] == "half_up_2dp"


@pytest.mark.asyncio
async def test_execute_run_threads_stored_precision_into_engine_rules(monkeypatch):
    session = AsyncMock()
    session.execute = AsyncMock(
        return_value=_result(
            mapping={"base_month": date(2024, 1, 1), "railway_zone": "NR"}
        )
    )
    bill = BillPayload(
        on_account_amount=Decimal("100"),
        cement_amount=Decimal("0"),
        steel_angles_amount=Decimal("0"),
        steel_plates_amount=Decimal("0"),
        steel_tmt_amount=Decimal("0"),
        steel_other_amount=Decimal("0"),
        technical_withheld=Decimal("0"),
        recoveries_affecting_pvc=Decimal("0"),
        extra_item_decisions=[],
        carry_forwards=[],
        measurement_date=date(2024, 4, 15),
    )
    snapshot = IndexSnapshot(base_month=date(2024, 1, 1), series={})
    monkeypatch.setattr(pvc_service, "build_bill_payload", AsyncMock(return_value=bill))
    monkeypatch.setattr(
        pvc_service, "build_index_snapshot", AsyncMock(return_value=snapshot)
    )
    captured: dict[str, object] = {}
    result = MagicMock(validation_errors=[])

    def _calculate(_bill, _snapshot, rules):
        captured["rules"] = rules
        return result

    monkeypatch.setattr(pvc_service, "calculate_pvc", _calculate)
    persist = AsyncMock(return_value={"id": "run-1"})
    monkeypatch.setattr(pvc_service, "persist_run_result", persist)

    await pvc_service.execute_pvc_run(
        session,
        tenant_id="tenant-A",
        contract_id="contract-1",
        bill_id="bill-1",
        rule_set_row=_rule_set_row(),
        idempotency_key=None,
    )

    rules = captured["rules"]
    assert rules.quarter_avg_precision == "half_up_2dp"
    assert persist.await_args.kwargs["rule_set_id"] == "rule-2"
