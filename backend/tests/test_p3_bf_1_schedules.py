"""P3-BF-1: tenant-scoped gate for endpoints nested under a contract URL.

Schedules, documents, and any other future nested resource ride on
`assert_contract_belongs_to_tenant`. Two failure modes must collapse into
the same 404 NotFoundProblem — "missing contract" and "wrong tenant" —
so a caller cannot probe foreign IDs by diffing error messages
(matches the P3-06 rationale for assert_bill_belongs_to_tenant).

Tests run against an in-memory aiosqlite session backed by a minimal
`contracts` table — fast, hermetic, no Postgres needed.
"""
from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from services.errors import NotFoundProblem
from services.pvc_service import assert_contract_belongs_to_tenant


@pytest.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.execute(text(
            "CREATE TABLE contracts (id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL)"
        ))
        await conn.execute(text(
            "INSERT INTO contracts VALUES "
            "('contract-own', 'tenant-A'), ('contract-foreign', 'tenant-B')"
        ))
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as s:
        yield s
    await engine.dispose()


async def test_accepts_contract_owned_by_tenant(session):
    # Does not raise.
    await assert_contract_belongs_to_tenant(session, "contract-own", "tenant-A")


async def test_rejects_contract_owned_by_different_tenant(session):
    with pytest.raises(NotFoundProblem) as exc:
        await assert_contract_belongs_to_tenant(session, "contract-foreign", "tenant-A")
    assert exc.value.status_code == 404
    assert exc.value.extra["entity"] == "contract"
    # Must NOT leak the existence of the foreign contract — the error message
    # is identical to the "doesn't exist" case below.
    assert exc.value.message == "Contract not found"


async def test_rejects_unknown_contract_id(session):
    with pytest.raises(NotFoundProblem) as exc:
        await assert_contract_belongs_to_tenant(session, "contract-does-not-exist", "tenant-A")
    assert exc.value.status_code == 404
    assert exc.value.message == "Contract not found"
