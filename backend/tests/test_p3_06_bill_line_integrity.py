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

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from services.errors import ValidationProblem
from services.pvc_service import assert_item_belongs_to_contract


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
