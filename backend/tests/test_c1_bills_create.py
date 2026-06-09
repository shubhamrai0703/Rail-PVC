"""C-1: POST /api/contracts/{contract_id}/bills.

The handler uses Postgres-specific SQL (UUID/ENUM casts), so we stub
`session.execute` at the boundary — same pattern as
`test_sh_p5_bills_get.py`. The mock consumes one result per execute call
in order: (1) the tenant gate SELECT, (2) the INSERT ... RETURNING.

Three paths matter for correctness:
  - valid create → 201-shaped dict echoing the body + new id
  - wrong tenant → NotFoundProblem(404), and the INSERT must NOT run
  - duplicate (contract_id, bill_number) → the UNIQUE constraint in
    migration 003 raises IntegrityError; the route must translate that
    into a structured ConflictProblem(409) rather than leaking a 500.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.exc import IntegrityError

from api.bills import BillCreate, create_bill
from services.auth import AuthUser
from services.errors import ConflictProblem, NotFoundProblem, ValidationProblem


def _user() -> AuthUser:
    return AuthUser(
        user_id="user-1",
        tenant_id="tenant-A",
        auth_id="auth-1",
        email="t@example.com",
        display_name="t@example.com",
    )


def _body() -> BillCreate:
    return BillCreate(
        bill_number=1,
        bill_date=date(2026, 1, 15),
        measurement_date=date(2026, 1, 31),
        gross_amount=Decimal("100000.00"),
    )


def _gate_pass() -> MagicMock:
    """A result whose `.first()` is truthy → contract gate passes."""
    result = MagicMock()
    result.first.return_value = {1: 1}
    return result


def _insert_returning(row: dict) -> MagicMock:
    result = MagicMock()
    mappings = MagicMock()
    mappings.first.return_value = row
    result.mappings.return_value = mappings
    return result


@pytest.mark.asyncio
async def test_create_bill_valid_returns_created():
    inserted = {"id": "bill-new", "created_at": "2026-01-15T10:00:00+00:00"}
    session = AsyncMock()
    session.execute = AsyncMock(
        side_effect=[_gate_pass(), _insert_returning(inserted)]
    )

    out = await create_bill(
        contract_id="contract-own",
        body=_body(),
        user=_user(),
        session=session,
    )

    assert out["id"] == "bill-new"
    assert out["bill_number"] == 1
    assert out["gross_amount"] == "100000.00"
    assert session.execute.await_count == 2


@pytest.mark.asyncio
async def test_create_bill_wrong_tenant_raises_not_found():
    # Gate SELECT returns None → NotFoundProblem; the INSERT must not run.
    gate_miss = MagicMock()
    gate_miss.first.return_value = None
    session = AsyncMock()
    session.execute = AsyncMock(side_effect=[gate_miss])

    with pytest.raises(NotFoundProblem) as exc:
        await create_bill(
            contract_id="contract-foreign",
            body=_body(),
            user=_user(),
            session=session,
        )

    assert exc.value.status_code == 404
    assert exc.value.extra["entity"] == "contract"
    assert exc.value.extra["id"] == "contract-foreign"
    assert session.execute.await_count == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("gross", [Decimal("0"), Decimal("-1"), Decimal("-100000.00")])
async def test_create_bill_non_positive_gross_raises_validation(gross):
    # P6-H2: gross_amount must be > 0. Validation fires before any DB call
    # (and before the tenant gate) so session.execute must not run.
    session = AsyncMock()
    session.execute = AsyncMock()
    body = _body()
    body.gross_amount = gross

    with pytest.raises(ValidationProblem) as exc:
        await create_bill(
            contract_id="contract-own", body=body, user=_user(), session=session
        )

    assert exc.value.status_code == 422
    assert exc.value.extra["field"] == "gross_amount"
    session.execute.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("number", [0, -1])
async def test_create_bill_non_positive_number_raises_validation(number):
    # P6-H2: bill_number must be a positive integer.
    session = AsyncMock()
    session.execute = AsyncMock()
    body = _body()
    body.bill_number = number

    with pytest.raises(ValidationProblem) as exc:
        await create_bill(
            contract_id="contract-own", body=body, user=_user(), session=session
        )

    assert exc.value.status_code == 422
    assert exc.value.extra["field"] == "bill_number"
    session.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_create_bill_duplicate_number_raises_conflict():
    # Gate passes, INSERT hits UNIQUE(contract_id, bill_number) → IntegrityError.
    integrity = IntegrityError("INSERT", {}, Exception("duplicate key"))
    session = AsyncMock()
    session.execute = AsyncMock(side_effect=[_gate_pass(), integrity])

    with pytest.raises(ConflictProblem) as exc:
        await create_bill(
            contract_id="contract-own",
            body=_body(),
            user=_user(),
            session=session,
        )

    assert exc.value.status_code == 409
    assert exc.value.extra["bill_number"] == 1
    assert session.execute.await_count == 2
