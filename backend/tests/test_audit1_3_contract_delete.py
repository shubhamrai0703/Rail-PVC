"""AUDIT-1-3: DELETE /api/contracts/{contract_id}.

Only Draft contracts may be deleted. Non-cascading audit records block
deletion, while document paths are durably queued before their metadata
cascades. The core paths are:
  - draft contract → 204 No Content; DELETE SQL runs
  - Draft contract with PVC runs/carry-forwards → structured 422
  - non-draft contract → ValidationProblem(422)
  - wrong tenant (or unknown id) → NotFoundProblem(404)
"""
from __future__ import annotations

import asyncio
import os
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from api.contracts import delete_contract
from services.auth import AuthUser
from services.errors import NotFoundProblem, ValidationProblem


def _user(tenant_id: str = "tenant-A") -> AuthUser:
    return AuthUser(
        user_id="user-1",
        tenant_id=tenant_id,
        auth_id="auth-1",
        email="t@example.com",
        display_name="t@example.com",
    )


def _status_row(
    status: str,
) -> MagicMock:
    result = MagicMock()
    mappings = MagicMock()
    mappings.first.return_value = {"status": status}
    result.mappings.return_value = mappings
    return result


def _blocker_row(
    *,
    has_pvc_runs: bool = False,
    has_carry_forwards: bool = False,
) -> MagicMock:
    result = MagicMock()
    result.mappings.return_value.one.return_value = {
        "has_pvc_runs": has_pvc_runs,
        "has_carry_forwards": has_carry_forwards,
    }
    return result


def _not_found_row() -> MagicMock:
    result = MagicMock()
    mappings = MagicMock()
    mappings.first.return_value = None
    result.mappings.return_value = mappings
    return result


@pytest.mark.asyncio
async def test_delete_draft_contract_succeeds():
    session = AsyncMock()
    queued_paths = MagicMock()
    queued_paths.scalars.return_value.all.return_value = [
        "tenant-A/contract-draft/agreement.pdf"
    ]
    session.execute = AsyncMock(
        side_effect=[
            _status_row("Draft"),
            _blocker_row(),
            queued_paths,
            AsyncMock(),
        ]
    )

    response = await delete_contract(
        contract_id="contract-draft",
        user=_user(),
        session=session,
    )

    assert response.status_code == 204
    assert session.execute.await_count == 4
    lock_sql = str(session.execute.await_args_list[0].args[0])
    blocker_sql = str(session.execute.await_args_list[1].args[0])
    enqueue_sql = str(session.execute.await_args_list[2].args[0])
    delete_sql = str(session.execute.await_args_list[3].args[0])
    assert "FOR UPDATE" in lock_sql
    assert "EXISTS" not in lock_sql
    assert "FOR UPDATE" not in blocker_sql
    assert "EXISTS" in blocker_sql
    assert "INSERT INTO document_cleanup_jobs" in enqueue_sql
    assert "DELETE FROM contracts" in delete_sql
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_delete_returns_after_durable_enqueue_without_waiting_for_storage():
    session = AsyncMock()
    queued_paths = MagicMock()
    session.execute = AsyncMock(
        side_effect=[
            _status_row("Draft"),
            _blocker_row(),
            queued_paths,
            MagicMock(),
        ]
    )

    with patch(
        "services.document_cleanup.process_document_cleanup_jobs",
        new=AsyncMock(side_effect=AssertionError("must run only in worker")),
    ) as cleanup:
        response = await delete_contract(
            contract_id="contract-draft",
            user=_user(),
            session=session,
        )

    assert response.status_code == 204
    session.commit.assert_awaited_once()
    cleanup.assert_not_awaited()
    session.rollback.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("contract_status", ["Configured", "Active", "Completed", "Archived"])
async def test_delete_non_draft_contract_raises_validation(contract_status):
    session = AsyncMock()
    session.execute = AsyncMock(side_effect=[_status_row(contract_status)])

    with pytest.raises(ValidationProblem) as exc:
        await delete_contract(
            contract_id="contract-active",
            user=_user(),
            session=session,
        )

    assert exc.value.status_code == 422
    assert exc.value.extra["field"] == "status"
    assert session.execute.await_count == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("has_pvc_runs", "has_carry_forwards", "expected_blockers"),
    [
        (True, False, ["pvc_runs"]),
        (False, True, ["carry_forwards"]),
        (True, True, ["pvc_runs", "carry_forwards"]),
    ],
)
async def test_delete_draft_with_audit_history_returns_structured_422(
    has_pvc_runs,
    has_carry_forwards,
    expected_blockers,
):
    session = AsyncMock()
    session.execute = AsyncMock(
        side_effect=[
            _status_row("Draft"),
            _blocker_row(
                has_pvc_runs=has_pvc_runs,
                has_carry_forwards=has_carry_forwards,
            ),
        ]
    )

    with pytest.raises(ValidationProblem) as exc:
        await delete_contract(
            contract_id="contract-with-history",
            user=_user(),
            session=session,
        )

    assert exc.value.status_code == 422
    assert exc.value.code == "contract_deletion_blocked"
    assert exc.value.extra["contract_id"] == "contract-with-history"
    assert exc.value.extra["blockers"] == expected_blockers
    assert session.execute.await_count == 2
    session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_delete_wrong_tenant_raises_not_found():
    session = AsyncMock()
    session.execute = AsyncMock(side_effect=[_not_found_row()])

    with pytest.raises(NotFoundProblem) as exc:
        await delete_contract(
            contract_id="contract-foreign",
            user=_user(),
            session=session,
        )

    assert exc.value.status_code == 404
    assert exc.value.extra["entity"] == "contract"
    assert session.execute.await_count == 1


class _FkViolation(Exception):
    def __init__(self, constraint_name: str):
        self.constraint_name = constraint_name


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("constraint_name", "blocker"),
    [
        ("pvc_runs_contract_id_fkey", "pvc_runs"),
        ("carry_forwards_contract_id_fkey", "carry_forwards"),
    ],
)
async def test_delete_defensively_translates_known_fk_race(
    constraint_name,
    blocker,
):
    session = AsyncMock()
    queued_paths = MagicMock()
    queued_paths.scalars.return_value.all.return_value = []
    session.execute = AsyncMock(
        side_effect=[
            _status_row("Draft"),
            _blocker_row(),
            queued_paths,
            IntegrityError("DELETE", {}, _FkViolation(constraint_name)),
        ]
    )

    with pytest.raises(ValidationProblem) as exc:
        await delete_contract(
            contract_id="contract-race",
            user=_user(),
            session=session,
        )

    assert exc.value.code == "contract_deletion_blocked"
    assert exc.value.extra["blockers"] == [blocker]
    session.commit.assert_not_awaited()


def test_delete_http_serializes_contract_deletion_blocked_detail():
    from fastapi.testclient import TestClient
    from sqlalchemy.ext.asyncio import AsyncSession

    from main import app
    from services.auth import get_current_user
    from services.db import get_session

    session = AsyncMock()
    session.execute = AsyncMock(
        side_effect=[
            _status_row("Draft"),
            _blocker_row(has_pvc_runs=True),
        ]
    )

    async def override_user() -> AuthUser:
        return _user()

    async def override_session() -> AsyncSession:  # type: ignore[return-value]
        return session

    app.dependency_overrides[get_current_user] = override_user
    app.dependency_overrides[get_session] = override_session
    try:
        response = TestClient(app).delete("/api/contracts/contract-history")
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_session, None)

    assert response.status_code == 422
    assert response.json() == {
        "detail": {
            "code": "contract_deletion_blocked",
            "message": "Contract cannot be deleted because it has calculation history",
            "contract_id": "contract-history",
            "blockers": ["pvc_runs"],
        }
    }


@pytest.mark.asyncio
@pytest.mark.parametrize("blocking_table", ["pvc_runs", "carry_forwards"])
async def test_real_postgres_non_cascading_history_blocks_delete(blocking_table):
    """Exercise the actual PostgreSQL FK/locking behavior when configured.

    CI can supply an isolated ``TEST_DATABASE_URL``. We never fall back to
    ``DATABASE_URL`` because that may point at the production Supabase DB.
    """
    database_url = os.environ.get("TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("TEST_DATABASE_URL is not configured")
    if database_url.startswith("postgresql://"):
        database_url = database_url.replace(
            "postgresql://", "postgresql+asyncpg://", 1
        )

    schema = f"audit_delete_{uuid4().hex}"
    tenant_id = str(uuid4())
    contract_id = str(uuid4())
    child_id = str(uuid4())
    engine = create_async_engine(database_url)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with engine.begin() as conn:
            await conn.execute(text(f'CREATE SCHEMA "{schema}"'))
            await conn.execute(text(
                f'CREATE TYPE "{schema}".contract_status AS ENUM '
                "('Draft', 'Configured', 'Active', 'Completed', 'Archived')"
            ))
            await conn.execute(text(f"""
                CREATE TABLE "{schema}".contracts (
                    id UUID PRIMARY KEY,
                    tenant_id UUID NOT NULL,
                    status "{schema}".contract_status NOT NULL
                )
            """))
            await conn.execute(text(f"""
                CREATE TABLE "{schema}".pvc_runs (
                    id UUID PRIMARY KEY,
                    contract_id UUID NOT NULL
                        REFERENCES "{schema}".contracts(id)
                )
            """))
            await conn.execute(text(f"""
                CREATE TABLE "{schema}".carry_forwards (
                    id UUID PRIMARY KEY,
                    contract_id UUID NOT NULL
                        REFERENCES "{schema}".contracts(id)
                )
            """))
            await conn.execute(text(
                f'INSERT INTO "{schema}".contracts VALUES '
                "(:id, :tenant_id, 'Draft')"
            ), {"id": contract_id, "tenant_id": tenant_id})
            await conn.execute(text(
                f'INSERT INTO "{schema}".{blocking_table} VALUES (:id, :contract_id)'
            ), {"id": child_id, "contract_id": contract_id})

        async with factory() as session:
            await session.execute(text(f'SET search_path TO "{schema}"'))
            with pytest.raises(ValidationProblem) as exc:
                await delete_contract(
                    contract_id=contract_id,
                    user=_user(tenant_id),
                    session=session,
                )
            assert exc.value.code == "contract_deletion_blocked"
            assert exc.value.extra["blockers"] == [blocking_table]

            still_exists = (
                await session.execute(
                    text("SELECT EXISTS (SELECT 1 FROM contracts WHERE id = :id)"),
                    {"id": contract_id},
                )
            ).scalar_one()
            assert still_exists is True
    finally:
        async with engine.begin() as conn:
            await conn.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        await engine.dispose()


@pytest.mark.asyncio
async def test_real_postgres_row_lock_closes_child_insert_race():
    database_url = os.environ.get("TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("TEST_DATABASE_URL is not configured")
    if database_url.startswith("postgresql://"):
        database_url = database_url.replace(
            "postgresql://", "postgresql+asyncpg://", 1
        )

    schema = f"audit_delete_race_{uuid4().hex}"
    tenant_id = str(uuid4())
    contract_id = str(uuid4())
    engine = create_async_engine(database_url)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with engine.begin() as conn:
            await conn.execute(text(f'CREATE SCHEMA "{schema}"'))
            await conn.execute(text(
                f'CREATE TYPE "{schema}".contract_status AS ENUM '
                "('Draft', 'Configured', 'Active', 'Completed', 'Archived')"
            ))
            await conn.execute(text(f"""
                CREATE TABLE "{schema}".contracts (
                    id UUID PRIMARY KEY,
                    tenant_id UUID NOT NULL,
                    status "{schema}".contract_status NOT NULL
                )
            """))
            for table_name in ("pvc_runs", "carry_forwards"):
                await conn.execute(text(f"""
                    CREATE TABLE "{schema}".{table_name} (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        contract_id UUID NOT NULL
                            REFERENCES "{schema}".contracts(id)
                    )
                """))
            await conn.execute(text(f"""
                CREATE TABLE "{schema}".documents (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    contract_id UUID NOT NULL
                        REFERENCES "{schema}".contracts(id) ON DELETE CASCADE,
                    storage_path TEXT NOT NULL
                )
            """))
            await conn.execute(text(f"""
                CREATE TABLE "{schema}".document_cleanup_jobs (
                    tenant_id UUID NOT NULL,
                    source_contract_id UUID NOT NULL,
                    storage_path TEXT UNIQUE NOT NULL
                )
            """))
            await conn.execute(
                text(
                    f'INSERT INTO "{schema}".contracts '
                    "VALUES (:id, :tenant_id, 'Draft')"
                ),
                {"id": contract_id, "tenant_id": tenant_id},
            )

        locked = asyncio.Event()
        continue_delete = asyncio.Event()

        class PausingSession:
            def __init__(self, real_session):
                self.real_session = real_session
                self.execute_count = 0

            async def execute(self, *args, **kwargs):
                result = await self.real_session.execute(*args, **kwargs)
                self.execute_count += 1
                if self.execute_count == 1:
                    locked.set()
                    await continue_delete.wait()
                return result

            async def commit(self):
                await self.real_session.commit()

            async def rollback(self):
                await self.real_session.rollback()

        async with factory() as delete_db, factory() as insert_db:
            await delete_db.execute(text(f'SET search_path TO "{schema}"'))
            await insert_db.execute(text(f'SET search_path TO "{schema}"'))
            delete_session = PausingSession(delete_db)
            deleting = asyncio.create_task(delete_contract(
                contract_id=contract_id,
                user=_user(tenant_id),
                session=delete_session,  # type: ignore[arg-type]
            ))
            await locked.wait()

            inserting = asyncio.create_task(insert_db.execute(
                text("INSERT INTO pvc_runs (contract_id) VALUES (:id)"),
                {"id": contract_id},
            ))
            await asyncio.sleep(0.05)
            assert inserting.done() is False

            continue_delete.set()
            response = await asyncio.wait_for(deleting, timeout=2)
            assert response.status_code == 204
            with pytest.raises(IntegrityError):
                await asyncio.wait_for(inserting, timeout=2)
            await insert_db.rollback()
    finally:
        async with engine.begin() as conn:
            await conn.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        await engine.dispose()
