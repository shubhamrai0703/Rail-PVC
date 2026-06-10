"""D-1 (Phase 7): run-results completeness + run-history list.

`GET /pvc-runs/{id}` must now surface the engine result totals
(`total_pvc`, `negative_carry_forward`, `quarter_used`) that migration 015
persists on `pvc_runs`, alongside the component breakdown. `GET
/contracts/{id}/pvc-runs` is the run-history list, gated like its sibling
`GET /contracts/{id}/bills`: a foreign/unknown contract 404s, an owned
contract with zero runs returns an empty list.

Handlers use Postgres-specific `::text` casts that aiosqlite cannot parse,
so we stub `session.execute` at the boundary — same pattern as
`test_sh_p5_bills_get.py`.
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from api.pvc_runs import get_run, list_runs
from services.auth import AuthUser
from services.errors import NotFoundProblem


def _user() -> AuthUser:
    return AuthUser(
        user_id="user-1",
        tenant_id="tenant-A",
        auth_id="auth-1",
        email="t@example.com",
        display_name="t@example.com",
    )


def _session_with(*results: tuple[str, object]) -> AsyncMock:
    """AsyncSession stub. Each tuple is (kind, payload):

      - ("first", row | None) — `.mappings().first()` / bare `.first()`
      - ("all",   list[row])  — `.mappings().all()`

    Calls to `session.execute()` consume the tuples in order.
    """
    session = AsyncMock()
    mocked = []
    for kind, payload in results:
        result = MagicMock()
        mappings = MagicMock()
        if kind == "first":
            mappings.first.return_value = payload
        elif kind == "all":
            mappings.all.return_value = payload
        else:  # pragma: no cover — defensive
            raise ValueError(f"unknown result kind: {kind}")
        result.mappings.return_value = mappings
        result.first.return_value = payload if kind == "first" else None
        mocked.append(result)
    session.execute = AsyncMock(side_effect=mocked)
    return session


# ---------------------------------------------------------------------------
# D-1a — GET /pvc-runs/{id} surfaces result totals + components
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_run_returns_totals_and_components():
    run_row = {
        "id": "run-1",
        "contract_id": "contract-own",
        "bill_id": "bill-1",
        "status": "Calculated",
        "total_pvc": Decimal("76959.55"),
        "negative_carry_forward": Decimal("0.00"),
        "quarter_used": "2024-Q4",
        "superseded_by": None,
        "w_derivation": {"formula": "W = OnAccount - ...", "w": "8000000"},
        "approved_by": None,
        "approved_at": None,
        "created_at": datetime(2026, 6, 9, 10, 0, 0),
    }
    components = [
        {
            "category": "cement",
            "eligible_amount": Decimal("1000000"),
            "base_index": Decimal("120.0"),
            "current_avg_index": Decimal("125.0"),
            "weight": Decimal("0.08"),
            "pvc_value": Decimal("3333.33"),
        }
    ]
    session = _session_with(("first", run_row), ("all", components))

    out = await get_run(run_id="run-1", user=_user(), session=session)

    # Result totals (migration 015) ride alongside the component breakdown.
    assert out["total_pvc"] == Decimal("76959.55")
    assert out["negative_carry_forward"] == Decimal("0.00")
    assert out["quarter_used"] == "2024-Q4"
    assert out["superseded_by"] is None
    assert out["components"] == components
    assert session.execute.await_count == 2


@pytest.mark.asyncio
async def test_get_run_wrong_tenant_raises_not_found():
    # Gate SELECT (run JOIN contract on tenant) returns None → 404 before
    # the components query runs.
    session = _session_with(("first", None))

    with pytest.raises(NotFoundProblem) as exc:
        await get_run(run_id="run-foreign", user=_user(), session=session)

    assert exc.value.status_code == 404
    assert exc.value.extra["entity"] == "pvc_run"
    assert session.execute.await_count == 1


# ---------------------------------------------------------------------------
# D-1b — GET /contracts/{id}/pvc-runs run-history list
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_runs_returns_rows_newest_first():
    run_rows = [
        {
            "id": "run-2",
            "bill_id": "bill-2",
            "bill_number": 2,
            "status": "Approved",
            "total_pvc": Decimal("76959.55"),
            "negative_carry_forward": Decimal("0.00"),
            "quarter_used": "2024-Q4",
            "superseded_by": None,
            "approved_at": datetime(2026, 6, 9, 11, 0, 0),
            "created_at": datetime(2026, 6, 9, 10, 0, 0),
        },
        {
            "id": "run-1",
            "bill_id": "bill-1",
            "bill_number": 1,
            "status": "Calculated",
            "total_pvc": Decimal("0.00"),
            "negative_carry_forward": Decimal("0.00"),
            "quarter_used": "2024-Q2",
            "superseded_by": None,
            "approved_at": None,
            "created_at": datetime(2026, 6, 8, 10, 0, 0),
        },
    ]
    # Gate SELECT (assert_contract_belongs_to_tenant) returns truthy → list runs.
    session = _session_with(("first", (1,)), ("all", run_rows))

    out = await list_runs(
        contract_id="contract-own", user=_user(), session=session
    )

    assert out == run_rows
    assert session.execute.await_count == 2


@pytest.mark.asyncio
async def test_list_runs_empty_returns_empty_list_not_404():
    # Owned contract, no runs yet — empty list, never 404.
    session = _session_with(("first", (1,)), ("all", []))

    out = await list_runs(
        contract_id="contract-own", user=_user(), session=session
    )

    assert out == []
    assert session.execute.await_count == 2


@pytest.mark.asyncio
async def test_list_runs_wrong_tenant_raises_not_found():
    # Gate returns None → NotFoundProblem(entity="contract"); list SELECT
    # must not run.
    session = _session_with(("first", None))

    with pytest.raises(NotFoundProblem) as exc:
        await list_runs(
            contract_id="contract-foreign", user=_user(), session=session
        )

    assert exc.value.status_code == 404
    assert exc.value.extra["entity"] == "contract"
    assert exc.value.extra["id"] == "contract-foreign"
    assert session.execute.await_count == 1
