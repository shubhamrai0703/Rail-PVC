"""C-3: PUT /api/bills/{id}, DELETE /api/bills/{id}/recoveries/{rid}, and the
computed net_amount.

Route SQL is Postgres-specific, so the handler tests stub `session.execute` at
the boundary (same pattern as the other bills tests). The net_amount formula is
the one piece of real financial logic, so it is exercised against an in-memory
aiosqlite DB running the EXACT exported `_NET_AMOUNT_EXPR` — not a re-implementation.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from api.bills import (
    BillUpdate,
    _NET_AMOUNT_EXPR,
    delete_recovery,
    update_bill,
)
from services.auth import AuthUser
from services.errors import (
    ConflictProblem,
    FieldNotNullableProblem,
    NotFoundProblem,
    ValidationProblem,
)


def _user() -> AuthUser:
    return AuthUser(
        user_id="user-1",
        tenant_id="tenant-A",
        auth_id="auth-1",
        email="t@example.com",
        display_name="t@example.com",
    )


def _res(value):
    """Result stub whose `.first()` and `.mappings().first()` both yield value."""
    r = MagicMock()
    r.first.return_value = value
    m = MagicMock()
    m.first.return_value = value
    r.mappings.return_value = m
    return r


_GATE_PASS = {"contract_id": "contract-1"}
_BILL_ROW = {
    "id": "bill-1",
    "contract_id": "contract-1",
    "bill_number": 2,
    "bill_date": "2026-01-15",
    "measurement_date": "2026-01-31",
    "gross_amount": Decimal("100000.00"),
    "net_amount": Decimal("90000.00"),
    "status": "Draft",
    "created_at": "2026-01-15T10:00:00+00:00",
}


# ── PUT /api/bills/{id} ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_update_bill_valid_returns_computed_row():
    session = AsyncMock()
    session.execute = AsyncMock(
        side_effect=[_res(_GATE_PASS), _res(None), _res(_BILL_ROW)]
    )
    out = await update_bill(
        bill_id="bill-1",
        body=BillUpdate(gross_amount=Decimal("100000.00")),
        user=_user(),
        session=session,
    )
    assert out["id"] == "bill-1"
    assert out["net_amount"] == Decimal("90000.00")
    assert session.execute.await_count == 3  # gate, UPDATE, re-select


@pytest.mark.asyncio
async def test_update_bill_empty_body_is_noop_returns_current():
    session = AsyncMock()
    session.execute = AsyncMock(side_effect=[_res(_GATE_PASS), _res(_BILL_ROW)])
    out = await update_bill(
        bill_id="bill-1", body=BillUpdate(), user=_user(), session=session
    )
    assert out["id"] == "bill-1"
    assert session.execute.await_count == 2  # gate, re-select (no UPDATE)


@pytest.mark.asyncio
async def test_update_bill_wrong_tenant_raises_not_found():
    session = AsyncMock()
    session.execute = AsyncMock(side_effect=[_res(None)])
    with pytest.raises(NotFoundProblem) as exc:
        await update_bill(
            bill_id="bill-foreign",
            body=BillUpdate(gross_amount=Decimal("1")),
            user=_user(),
            session=session,
        )
    assert exc.value.status_code == 404
    assert session.execute.await_count == 1  # gate only; no UPDATE


@pytest.mark.asyncio
async def test_update_bill_duplicate_number_raises_conflict():
    integrity = IntegrityError("UPDATE", {}, Exception("duplicate key"))
    session = AsyncMock()
    session.execute = AsyncMock(side_effect=[_res(_GATE_PASS), integrity])
    with pytest.raises(ConflictProblem) as exc:
        await update_bill(
            bill_id="bill-1",
            body=BillUpdate(bill_number=5),
            user=_user(),
            session=session,
        )
    assert exc.value.status_code == 409
    assert exc.value.extra["bill_number"] == 5


@pytest.mark.asyncio
@pytest.mark.parametrize("number", [0, -1])
async def test_update_bill_non_positive_number_raises_validation(number):
    session = AsyncMock()
    session.execute = AsyncMock(side_effect=[_res(_GATE_PASS)])
    with pytest.raises(ValidationProblem) as exc:
        await update_bill(
            bill_id="bill-1",
            body=BillUpdate(bill_number=number),
            user=_user(),
            session=session,
        )
    assert exc.value.extra["field"] == "bill_number"
    assert session.execute.await_count == 1  # gate ran; UPDATE did not


@pytest.mark.asyncio
@pytest.mark.parametrize("gross", [Decimal("0"), Decimal("-100")])
async def test_update_bill_non_positive_gross_raises_validation(gross):
    session = AsyncMock()
    session.execute = AsyncMock(side_effect=[_res(_GATE_PASS)])
    with pytest.raises(ValidationProblem) as exc:
        await update_bill(
            bill_id="bill-1",
            body=BillUpdate(gross_amount=gross),
            user=_user(),
            session=session,
        )
    assert exc.value.extra["field"] == "gross_amount"


@pytest.mark.asyncio
async def test_update_bill_explicit_null_gross_rejected():
    session = AsyncMock()
    session.execute = AsyncMock(side_effect=[_res(_GATE_PASS)])
    with pytest.raises(ValidationProblem) as exc:
        await update_bill(
            bill_id="bill-1",
            body=BillUpdate(gross_amount=None),
            user=_user(),
            session=session,
        )
    assert exc.value.extra["field"] == "gross_amount"


@pytest.mark.asyncio
async def test_update_bill_explicit_null_measurement_date_rejected():
    session = AsyncMock()
    session.execute = AsyncMock(side_effect=[_res(_GATE_PASS)])
    with pytest.raises(FieldNotNullableProblem) as exc:
        await update_bill(
            bill_id="bill-1",
            body=BillUpdate(measurement_date=None),
            user=_user(),
            session=session,
        )
    assert exc.value.status_code == 422
    assert exc.value.extra["field"] == "measurement_date"


# ── DELETE /api/bills/{id}/recoveries/{rid} ──────────────────────────────────

@pytest.mark.asyncio
async def test_delete_recovery_valid():
    session = AsyncMock()
    # gate pass, recovery-under-bill SELECT truthy, DELETE
    session.execute = AsyncMock(
        side_effect=[_res(_GATE_PASS), _res((1,)), _res(None)]
    )
    await delete_recovery(
        bill_id="bill-1", recovery_id="rec-1", user=_user(), session=session
    )
    assert session.execute.await_count == 3


@pytest.mark.asyncio
async def test_delete_recovery_wrong_tenant_raises_not_found():
    session = AsyncMock()
    session.execute = AsyncMock(side_effect=[_res(None)])
    with pytest.raises(NotFoundProblem) as exc:
        await delete_recovery(
            bill_id="bill-foreign", recovery_id="rec-1", user=_user(), session=session
        )
    assert exc.value.extra["entity"] == "running_bill"
    assert session.execute.await_count == 1  # gate only; no DELETE


@pytest.mark.asyncio
async def test_delete_recovery_not_under_bill_raises_not_found():
    session = AsyncMock()
    session.execute = AsyncMock(side_effect=[_res(_GATE_PASS), _res(None)])
    with pytest.raises(NotFoundProblem) as exc:
        await delete_recovery(
            bill_id="bill-1", recovery_id="rec-foreign", user=_user(), session=session
        )
    assert exc.value.extra["entity"] == "recovery"
    assert session.execute.await_count == 2  # gate + lookup; no DELETE


# ── net_amount formula (real SQL via aiosqlite) ──────────────────────────────

@pytest.fixture
async def net_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.execute(text(
            "CREATE TABLE running_bills (id TEXT PRIMARY KEY, gross_amount NUMERIC)"
        ))
        await conn.execute(text(
            "CREATE TABLE recoveries (id TEXT PRIMARY KEY, bill_id TEXT, "
            "amount NUMERIC, affects_pvc_base BOOLEAN)"
        ))
        await conn.execute(text(
            "INSERT INTO running_bills VALUES ('bill-1', 100000)"
        ))
        # One non-PVC recovery (counts) and one PVC-affecting recovery (excluded
        # by the affects_pvc_base = FALSE filter under the current decision).
        await conn.execute(text(
            "INSERT INTO recoveries VALUES "
            "('r1', 'bill-1', 10000, 0), ('r2', 'bill-1', 5000, 1)"
        ))
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as s:
        yield s
    await engine.dispose()


async def test_net_amount_excludes_pvc_affecting_recoveries(net_session):
    row = (
        await net_session.execute(
            text(f"SELECT id, {_NET_AMOUNT_EXPR} FROM running_bills WHERE id = :bid"),
            {"bid": "bill-1"},
        )
    ).mappings().first()
    # 100000 − 10000 (FALSE) ; the 5000 TRUE recovery is NOT subtracted.
    assert Decimal(str(row["net_amount"])) == Decimal("90000")


async def test_net_amount_equals_gross_when_no_recoveries(net_session):
    await net_session.execute(
        text("INSERT INTO running_bills VALUES ('bill-2', 50000)")
    )
    row = (
        await net_session.execute(
            text(f"SELECT id, {_NET_AMOUNT_EXPR} FROM running_bills WHERE id = :bid"),
            {"bid": "bill-2"},
        )
    ).mappings().first()
    assert Decimal(str(row["net_amount"])) == Decimal("50000")
