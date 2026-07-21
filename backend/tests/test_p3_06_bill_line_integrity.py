"""P3-06 regression: bill-line creation verifies item ∈ bill's contract.

The reviewed endpoint only checked tenant ownership of the bill, so a
caller who learned another contract item's UUID could attach that foreign
item to their bill and contaminate W derivation.

The fix moves the check into a reusable service function
(`assert_item_belongs_to_contract`) called by the route handler. This
test verifies the function's behaviour against a tiny in-memory async
SQLAlchemy session backed by SQLite — fast, hermetic, no Postgres needed.
"""
from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from api.bills import BillLineCreate, create_bill_line
from services.auth import AuthUser
from services.errors import ConflictProblem, ValidationProblem
from services.pvc_service import assert_item_belongs_to_contract


class _PostgresIntegrityError(Exception):
    def __init__(self, sqlstate: str, constraint_name: str):
        super().__init__(constraint_name)
        self.sqlstate = sqlstate
        self.constraint_name = constraint_name


@pytest.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.execute(text(
            "CREATE TABLE contract_items (id TEXT PRIMARY KEY, contract_id TEXT NOT NULL)"
        ))
        await conn.execute(text(
            "INSERT INTO contract_items VALUES "
            "('item-own', 'contract-A'), ('item-foreign', 'contract-B')"
        ))
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as s:
        yield s
    await engine.dispose()


async def test_accepts_item_belonging_to_contract(session):
    # Does not raise.
    await assert_item_belongs_to_contract(session, "item-own", "contract-A")


async def test_rejects_item_from_different_contract(session):
    with pytest.raises(ValidationProblem) as exc:
        await assert_item_belongs_to_contract(session, "item-foreign", "contract-A")
    assert "does not belong" in exc.value.message
    assert exc.value.status_code == 422


async def test_rejects_unknown_item_id(session):
    with pytest.raises(ValidationProblem):
        await assert_item_belongs_to_contract(session, "item-does-not-exist", "contract-A")


@pytest.mark.asyncio
async def test_duplicate_bill_item_raises_structured_conflict():
    bill_gate = MagicMock()
    bill_gate.mappings.return_value.first.return_value = {
        "contract_id": "contract-A"
    }
    item_gate = MagicMock()
    item_gate.first.return_value = (1,)
    integrity = IntegrityError(
        "INSERT",
        {},
        _PostgresIntegrityError("23505", "bill_lines_bill_id_item_id_key"),
    )
    session = AsyncMock()
    session.execute = AsyncMock(side_effect=[bill_gate, item_gate, integrity])
    user = AuthUser(
        user_id="user-1",
        tenant_id="tenant-A",
        auth_id="auth-1",
        email="t@example.com",
        display_name="Test User",
    )

    with pytest.raises(ConflictProblem) as exc:
        await create_bill_line(
            bill_id="bill-1",
            body=BillLineCreate(
                item_id="item-own",
                amount_since_last=Decimal("100.00"),
            ),
            user=user,
            session=session,
        )

    assert exc.value.status_code == 409
    assert exc.value.extra == {"bill_id": "bill-1", "item_id": "item-own"}
    assert session.execute.await_count == 3


@pytest.mark.asyncio
async def test_non_unique_integrity_error_is_not_mislabeled_as_duplicate():
    bill_gate = MagicMock()
    bill_gate.mappings.return_value.first.return_value = {
        "contract_id": "contract-A"
    }
    item_gate = MagicMock()
    item_gate.first.return_value = (1,)
    foreign_key_error = IntegrityError(
        "INSERT",
        {},
        _PostgresIntegrityError("23503", "bill_lines_bill_id_fkey"),
    )
    session = AsyncMock()
    session.execute = AsyncMock(
        side_effect=[bill_gate, item_gate, foreign_key_error]
    )
    user = AuthUser(
        user_id="user-1",
        tenant_id="tenant-A",
        auth_id="auth-1",
        email="t@example.com",
        display_name="Test User",
    )

    with pytest.raises(IntegrityError) as exc:
        await create_bill_line(
            bill_id="bill-1",
            body=BillLineCreate(item_id="item-own"),
            user=user,
            session=session,
        )

    assert exc.value is foreign_key_error
