"""P7-REVIEW H1 + H2 regression pins.

H1 — a bill has exactly one approvable run:
  * `approve_run` rejects Superseded/ExceptionFlagged/Exported with a 422
    (only Draft/Calculated may become Approved; Approved itself stays 409).
  * `persist_run_result` supersedes prior Draft/Calculated runs for the bill
    at INSERT time — and only those (Approved rows are never touched).

H2 — a run renders its own bill lines, not live ones:
  * `persist_run_result` captures the bill's lines into `lines_snapshot`
    (migration 016) at INSERT.
  * `GET /pvc-runs/{id}` returns `lines_snapshot`.

Handlers use Postgres-specific SQL that aiosqlite cannot parse, so we stub
`session.execute` at the boundary — same pattern as test_d1_pvc_run_results.
"""
from __future__ import annotations

import json
from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from api.pvc_runs import approve_run, get_run
from services import pvc_service
from services.auth import AuthUser
from services.errors import ImmutableApprovedRun, ValidationProblem


def _user() -> AuthUser:
    return AuthUser(
        user_id="user-1",
        tenant_id="tenant-A",
        auth_id="auth-1",
        email="t@example.com",
        display_name="t@example.com",
    )


def _session_with(*results: tuple[str, object]) -> AsyncMock:
    """AsyncSession stub: each tuple is ("first" | "all", payload), consumed
    in `session.execute()` call order."""
    session = AsyncMock()
    mocked = []
    for kind, payload in results:
        result = MagicMock()
        mappings = MagicMock()
        if kind == "first":
            mappings.first.return_value = payload
        else:
            mappings.all.return_value = payload
        result.mappings.return_value = mappings
        result.first.return_value = payload if kind == "first" else None
        mocked.append(result)
    session.execute = AsyncMock(side_effect=mocked)
    return session


# ---------------------------------------------------------------------------
# H1a — approve gate: only Draft/Calculated may become Approved
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("status", ["Superseded", "ExceptionFlagged", "Exported"])
async def test_approve_rejects_non_current_statuses_with_422(status: str):
    session = _session_with(("first", {"id": "run-1", "status": status}))

    with pytest.raises(ValidationProblem) as exc:
        await approve_run(run_id="run-1", user=_user(), session=session)

    assert exc.value.status_code == 422
    assert exc.value.extra["status"] == status
    # The gate must fire before any UPDATE.
    assert session.execute.await_count == 1


@pytest.mark.asyncio
async def test_approve_still_409s_on_approved():
    session = _session_with(("first", {"id": "run-1", "status": "Approved"}))

    with pytest.raises(ImmutableApprovedRun):
        await approve_run(run_id="run-1", user=_user(), session=session)


@pytest.mark.asyncio
async def test_approve_succeeds_from_calculated():
    session = _session_with(
        ("first", {"id": "run-1", "status": "Calculated"}),
        ("first", {"id": "run-1", "approved_at": datetime(2026, 6, 11, 10, 0)}),
    )

    out = await approve_run(run_id="run-1", user=_user(), session=session)

    assert out["status"] == "Approved"
    # The UPDATE itself re-checks the status (race guard).
    update_sql = str(session.execute.await_args_list[1].args[0])
    assert "status IN ('Draft', 'Calculated')" in update_sql


# ---------------------------------------------------------------------------
# H1b + H2a — persist_run_result: supersede at INSERT + lines snapshot
# ---------------------------------------------------------------------------


def _engine_result() -> MagicMock:
    result = MagicMock()
    result.total_pvc = Decimal("100.00")
    result.negative_carry_forward = Decimal("0")
    result.quarter_used = "2026-Q1"
    result.w_derivation.model_dump_json.return_value = "{}"
    result.trace.model_dump_json.return_value = "{}"
    component = MagicMock()
    component.category = "cement"
    component.eligible_amount = Decimal("1")
    component.base_index = Decimal("1")
    component.current_avg_index = Decimal("1")
    component.weight = Decimal("1")
    component.pvc_value = Decimal("1")
    result.components = [component]
    return result


def _persist_session(line_rows: list[dict]) -> tuple[MagicMock, list]:
    """Session stub for persist_run_result. Returns (session, executed) where
    `executed` collects (sql_text, params) for every execute call."""
    executed: list[tuple[str, dict]] = []

    async def _execute(stmt, params=None):
        sql = str(stmt)
        executed.append((sql, params or {}))
        result = MagicMock()
        mappings = MagicMock()
        if "FROM bill_lines" in sql:
            mappings.all.return_value = line_rows
        elif "INSERT INTO pvc_runs" in sql:
            mappings.first.return_value = {"id": "run-new"}
        else:
            mappings.first.return_value = None
        result.mappings.return_value = mappings
        return result

    session = MagicMock()
    session.execute = AsyncMock(side_effect=_execute)
    # `async with session.begin_nested():` — MagicMock auto-provides the
    # async context-manager protocol on the returned mock.
    session.begin_nested = MagicMock()
    return session, executed


@pytest.mark.asyncio
async def test_persist_supersedes_prior_calculated_runs_only():
    session, executed = _persist_session(line_rows=[])
    bill_payload = MagicMock()
    bill_payload.model_dump_json.return_value = "{}"
    snapshot = MagicMock()
    snapshot.model_dump_json.return_value = "{}"

    out = await pvc_service.persist_run_result(
        session,
        contract_id="contract-1",
        bill_id="bill-1",
        rule_set_id="rs-1",
        bill_payload=bill_payload,
        snapshot=snapshot,
        result=_engine_result(),
        idempotency_key=None,
    )

    assert out["id"] == "run-new"
    supersedes = [
        (sql, params) for sql, params in executed if "'Superseded'" in sql
    ]
    assert len(supersedes) == 1
    sql, params = supersedes[0]
    # Scoped to this bill, excludes the new run, touches only Draft/Calculated
    # (never Approved — migration-011 immutability).
    assert params == {"rid": "run-new", "bid": "bill-1"}
    assert "id <> :rid" in sql
    assert "status IN ('Draft', 'Calculated')" in sql
    assert "superseded_by = :rid" in sql


@pytest.mark.asyncio
async def test_persist_snapshots_bill_lines_into_run():
    line_rows = [
        {
            "id": "line-1",
            "bill_id": "bill-1",
            "item_id": "item-1",
            "qty_up_to_last": "0",
            "qty_since_last": "5",
            "qty_up_to_date": "5",
            "amount_up_to_last": "0",
            "amount_since_last": "1000.00",
            "amount_up_to_date": "1000.00",
            "special_condition_amount": "0",
        }
    ]
    session, executed = _persist_session(line_rows=line_rows)
    bill_payload = MagicMock()
    bill_payload.model_dump_json.return_value = "{}"
    snapshot = MagicMock()
    snapshot.model_dump_json.return_value = "{}"

    await pvc_service.persist_run_result(
        session,
        contract_id="contract-1",
        bill_id="bill-1",
        rule_set_id="rs-1",
        bill_payload=bill_payload,
        snapshot=snapshot,
        result=_engine_result(),
        idempotency_key=None,
    )

    inserts = [
        (sql, params) for sql, params in executed if "INSERT INTO pvc_runs" in sql
    ]
    assert len(inserts) == 1
    _, params = inserts[0]
    assert json.loads(params["lines"]) == line_rows
    assert "lines_snapshot" in inserts[0][0]


# ---------------------------------------------------------------------------
# H2b — GET /pvc-runs/{id} returns the lines snapshot
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_run_returns_lines_snapshot():
    lines = [{"id": "line-1", "item_id": "item-1", "qty_up_to_date": "5"}]
    run_row = {
        "id": "run-1",
        "contract_id": "contract-own",
        "bill_id": "bill-1",
        "status": "Calculated",
        "total_pvc": Decimal("76959.55"),
        "negative_carry_forward": Decimal("0.00"),
        "quarter_used": "2024-Q4",
        "superseded_by": None,
        "w_derivation": None,
        "lines_snapshot": lines,
        "approved_by": None,
        "approved_at": None,
        "created_at": datetime(2026, 6, 9, 10, 0, 0),
    }
    session = _session_with(("first", run_row), ("all", []))

    out = await get_run(run_id="run-1", user=_user(), session=session)

    assert out["lines_snapshot"] == lines
