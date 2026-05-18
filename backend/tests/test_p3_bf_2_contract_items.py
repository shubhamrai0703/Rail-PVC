"""P3-BF-2: tenant-scoped gate + parent-contract lookup for items.

`assert_schedule_belongs_to_tenant` is load-bearing for two reasons:

1. **Tenant isolation:** rejects schedules whose parent contract belongs
   to a different tenant (same 404-don't-distinguish discipline as the
   contract / bill / item assertions).

2. **Trusted contract_id source:** returns the parent contract_id so the
   contract_items INSERT can populate that FK from the server, not from
   the client. Without this discipline, a caller who learned a foreign
   schedule's UUID could attach an item to their own contract — which
   then feeds W derivation through the engine. The returned value is the
   trust boundary; tests below pin both the value and the rejection
   behaviour against a minimal aiosqlite schema.
"""
from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from services.errors import NotFoundProblem
from services.pvc_service import assert_schedule_belongs_to_tenant


@pytest.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.execute(text(
            "CREATE TABLE contracts (id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL)"
        ))
        await conn.execute(text(
            "CREATE TABLE schedules (id TEXT PRIMARY KEY, contract_id TEXT NOT NULL)"
        ))
        await conn.execute(text(
            "INSERT INTO contracts VALUES "
            "('contract-own', 'tenant-A'), ('contract-foreign', 'tenant-B')"
        ))
        await conn.execute(text(
            "INSERT INTO schedules VALUES "
            "('sched-own', 'contract-own'), ('sched-foreign', 'contract-foreign')"
        ))
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as s:
        yield s
    await engine.dispose()


async def test_returns_contract_id_for_owned_schedule(session):
    contract_id = await assert_schedule_belongs_to_tenant(
        session, "sched-own", "tenant-A"
    )
    # This is the value the route hands to the INSERT — must come from the
    # JOIN against contracts, not be reflected from input.
    assert contract_id == "contract-own"


async def test_rejects_schedule_under_different_tenants_contract(session):
    with pytest.raises(NotFoundProblem) as exc:
        await assert_schedule_belongs_to_tenant(session, "sched-foreign", "tenant-A")
    assert exc.value.status_code == 404
    assert exc.value.extra["entity"] == "schedule"
    # Identical message to the "doesn't exist" case below — no information leak.
    assert exc.value.message == "Schedule not found"


async def test_rejects_unknown_schedule_id(session):
    with pytest.raises(NotFoundProblem) as exc:
        await assert_schedule_belongs_to_tenant(session, "sched-missing", "tenant-A")
    assert exc.value.status_code == 404
    assert exc.value.message == "Schedule not found"
