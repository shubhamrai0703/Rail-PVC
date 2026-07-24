"""Durable Supabase object cleanup for deleted contracts."""
from __future__ import annotations

import asyncio
import importlib.util
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from api.documents import retry_pending_document_cleanups
from services.auth import AuthUser
from services.document_cleanup import (
    CLAIM_LEASE_SECONDS,
    DEFAULT_BATCH_SIZE,
    DELETE_TIMEOUT_SECONDS,
    MAX_CONCURRENCY,
    CleanupResult,
    process_document_cleanup_jobs,
    run_document_cleanup_loop,
    select_eligible_cleanup_tenants,
)


MIGRATION = (
    Path(__file__).resolve().parents[1]
    / "migrations"
    / "versions"
    / "020_document_cleanup_jobs.py"
)


def _user(tenant_id: str = "tenant-A") -> AuthUser:
    return AuthUser(
        user_id="user-1",
        tenant_id=tenant_id,
        auth_id="auth-1",
        email="t@example.com",
        display_name="t@example.com",
    )


def _jobs(*rows: dict[str, str]) -> MagicMock:
    result = MagicMock()
    enriched = []
    for row in rows:
        value = dict(row)
        value.setdefault("source_contract_id", value["storage_path"].split("/")[1])
        enriched.append(value)
    result.mappings.return_value.all.return_value = enriched
    return result


def _recorded(*rows: dict[str, bool]) -> MagicMock:
    result = MagicMock()
    result.mappings.return_value.all.return_value = list(rows)
    return result


def test_migration_creates_private_durable_cleanup_queue(monkeypatch):
    assert MIGRATION.exists()
    spec = importlib.util.spec_from_file_location("migration_020", MIGRATION)
    assert spec is not None and spec.loader is not None
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)

    statements: list[str] = []
    monkeypatch.setattr(migration.op, "execute", lambda value: statements.append(str(value)))
    migration.upgrade()

    sql = "\n".join(statements)
    assert migration.revision == "020"
    assert migration.down_revision == "019"
    assert "CREATE TABLE document_cleanup_jobs" in sql
    assert "tenant_id" in sql
    assert "source_contract_id" in sql
    assert "storage_path" in sql
    assert "attempt_count" in sql
    assert "last_error" in sql
    assert "completed_at" in sql
    assert "next_attempt_at" in sql
    assert "quarantined_at" in sql
    assert "claim_token" in sql
    assert "claim_expires_at" in sql
    assert "UNIQUE (storage_path)" in sql
    assert "tenant_id::text || '/' ||" in sql
    assert "source_contract_id::text || '/%'" in sql
    assert "DROP POLICY IF EXISTS documents_insert" in sql
    assert "DROP POLICY IF EXISTS documents_delete" in sql
    assert "ENABLE ROW LEVEL SECURITY" in sql
    assert "FORCE ROW LEVEL SECURITY" in sql
    assert "CREATE POLICY" not in sql

    downgrade_statements: list[str] = []
    monkeypatch.setattr(
        migration.op,
        "execute",
        lambda value: downgrade_statements.append(str(value)),
    )
    migration.downgrade()
    downgrade_sql = "\n".join(downgrade_statements)
    assert "pending document cleanup jobs exist" in downgrade_sql
    assert "CREATE POLICY documents_insert" in downgrade_sql
    assert "CREATE POLICY documents_delete" in downgrade_sql


def test_openapi_exposes_delete_204_and_tenant_cleanup_retry():
    from main import app

    paths = app.openapi()["paths"]
    delete_operation = paths["/api/contracts/{contract_id}"]["delete"]
    retry_operation = paths["/api/documents/cleanup-pending"]["post"]

    assert "204" in delete_operation["responses"]
    assert "200" not in delete_operation["responses"]
    for status_code in ("404", "422"):
        error_schema = delete_operation["responses"][status_code]["content"][
            "application/json"
        ]["schema"]
        assert error_schema["$ref"].endswith("/ApiProblemResponse")
    retry_schema = retry_operation["responses"]["200"]["content"][
        "application/json"
    ]["schema"]
    assert retry_schema["$ref"].endswith("/CleanupResult")


@pytest.mark.asyncio
async def test_cleanup_success_marks_job_complete():
    session = AsyncMock()
    session.execute = AsyncMock(
        side_effect=[
            _jobs({"id": "job-1", "storage_path": "tenant-A/c-1/doc.pdf"}),
            _recorded({"succeeded": True, "quarantined": False}),
        ]
    )

    with patch(
        "services.document_cleanup.delete_document",
        new=AsyncMock(return_value=None),
    ) as remove:
        result = await process_document_cleanup_jobs(
            session,
            tenant_id="tenant-A",
        )

    assert result.model_dump() == {
        "attempted": 1,
        "succeeded": 1,
        "failed": 0,
        "quarantined": 0,
        "lost_claims": 0,
    }
    remove.assert_awaited_once_with("tenant-A/c-1/doc.pdf")
    claim_sql = str(session.execute.await_args_list[0].args[0])
    claim_params = session.execute.await_args_list[0].args[1]
    outcome_sql = str(session.execute.await_args_list[1].args[0])
    outcome_params = session.execute.await_args_list[1].args[1]
    assert "tenant_id = :tenant_id" in claim_sql
    assert "completed_at IS NULL" in claim_sql
    assert "quarantined_at IS NULL" in claim_sql
    assert "next_attempt_at <= NOW()" in claim_sql
    assert "claim_expires_at <= NOW()" in claim_sql
    assert "ORDER BY created_at, id" in claim_sql
    assert "LIMIT :batch_size" in claim_sql
    assert "FOR UPDATE SKIP LOCKED" in claim_sql
    assert claim_params["tenant_id"] == "tenant-A"
    assert claim_params["batch_size"] == 25
    assert claim_params["lease_seconds"] > 0
    assert claim_params["claim_token"]
    assert "jsonb_to_recordset" in outcome_sql
    assert "tenant_id = :tenant_id" in outcome_sql
    assert "claim_token = CAST(:claim_token AS UUID)" in outcome_sql
    assert "completed_at = CASE WHEN outcome.succeeded" in outcome_sql
    outcomes = json.loads(outcome_params["outcomes"])
    assert outcomes == [{
        "id": "job-1",
        "succeeded": True,
        "quarantined": False,
        "error": None,
    }]
    assert outcome_params["tenant_id"] == "tenant-A"
    assert outcome_params["claim_token"] == claim_params["claim_token"]
    assert session.commit.await_count == 2


@pytest.mark.asyncio
async def test_cleanup_failure_preserves_pending_path_and_records_retry_evidence():
    session = AsyncMock()
    session.execute = AsyncMock(
        side_effect=[
            _jobs({"id": "job-1", "storage_path": "tenant-A/c-1/doc.pdf"}),
            _recorded({"succeeded": False, "quarantined": False}),
        ]
    )

    with patch(
        "services.document_cleanup.delete_document",
        new=AsyncMock(side_effect=RuntimeError("storage offline")),
    ):
        result = await process_document_cleanup_jobs(
            session,
            tenant_id="tenant-A",
        )

    assert result.model_dump() == {
        "attempted": 1,
        "succeeded": 0,
        "failed": 1,
        "quarantined": 0,
        "lost_claims": 0,
    }
    claim_params = session.execute.await_args_list[0].args[1]
    outcome_sql = str(session.execute.await_args_list[1].args[0])
    outcome_params = session.execute.await_args_list[1].args[1]
    assert "attempt_count = attempt_count + 1" in outcome_sql
    assert "last_error = outcome.error" in outcome_sql
    assert "POWER(2" in outcome_sql
    assert "random()" in outcome_sql
    assert "LEAST(" in outcome_sql
    assert "claim_token = CAST(:claim_token AS UUID)" in outcome_sql
    assert json.loads(outcome_params["outcomes"]) == [
        {
            "id": "job-1",
            "succeeded": False,
            "quarantined": False,
            "error": "storage offline",
        }
    ]
    assert outcome_params["claim_token"] == claim_params["claim_token"]
    assert session.commit.await_count == 2


@pytest.mark.asyncio
async def test_failed_cleanup_is_retried_and_then_completed():
    session = AsyncMock()
    session.execute = AsyncMock(
        side_effect=[
            _jobs({"id": "job-1", "storage_path": "tenant-A/c-1/doc.pdf"}),
            _recorded({"succeeded": False, "quarantined": False}),
            _jobs({"id": "job-1", "storage_path": "tenant-A/c-1/doc.pdf"}),
            _recorded({"succeeded": True, "quarantined": False}),
        ]
    )
    remove = AsyncMock(side_effect=[RuntimeError("storage offline"), None])

    with patch("services.document_cleanup.delete_document", new=remove):
        first = await process_document_cleanup_jobs(session, tenant_id="tenant-A")
        second = await process_document_cleanup_jobs(session, tenant_id="tenant-A")

    assert first.failed == 1
    assert second.succeeded == 1
    assert remove.await_count == 2
    assert session.commit.await_count == 4
    first_claim = session.execute.await_args_list[0].args[1]["claim_token"]
    second_claim = session.execute.await_args_list[2].args[1]["claim_token"]
    assert first_claim != second_claim


@pytest.mark.asyncio
async def test_outcome_commit_failure_retries_idempotent_storage_delete_after_lease():
    first_session = AsyncMock()
    first_session.execute = AsyncMock(
        side_effect=[
            _jobs({"id": "job-1", "storage_path": "tenant-A/c-1/doc.pdf"}),
            _recorded({"succeeded": True, "quarantined": False}),
        ]
    )
    first_session.commit = AsyncMock(
        side_effect=[None, RuntimeError("outcome commit unavailable")]
    )
    retry_session = AsyncMock()
    retry_session.execute = AsyncMock(
        side_effect=[
            _jobs({"id": "job-1", "storage_path": "tenant-A/c-1/doc.pdf"}),
            _recorded({"succeeded": True, "quarantined": False}),
        ]
    )
    remove = AsyncMock(return_value=None)

    with patch("services.document_cleanup.delete_document", new=remove):
        with pytest.raises(RuntimeError, match="outcome commit unavailable"):
            await process_document_cleanup_jobs(
                first_session,
                tenant_id="tenant-A",
            )
        # The durable claim remains until claim_expires_at. This second claim
        # models a later retry after lease expiry; object removal is idempotent.
        retry = await process_document_cleanup_jobs(
            retry_session,
            tenant_id="tenant-A",
        )

    assert retry.succeeded == 1
    assert remove.await_count == 2
    first_claim_sql = str(first_session.execute.await_args_list[0].args[0])
    assert "claim_expires_at <= NOW()" in first_claim_sql
    assert first_session.commit.await_count == 2
    assert retry_session.commit.await_count == 2


@pytest.mark.asyncio
async def test_cleanup_commits_claim_before_storage_and_limits_concurrency():
    rows = [
        {"id": f"job-{number}", "storage_path": f"tenant-A/c-1/{number}.pdf"}
        for number in range(8)
    ]
    session = AsyncMock()
    session.execute = AsyncMock(
        side_effect=[
            _jobs(*rows),
            _recorded(*[
                {"succeeded": True, "quarantined": False}
                for _ in rows
            ]),
        ]
    )
    active = 0
    max_active = 0

    async def remove(_path: str) -> None:
        nonlocal active, max_active
        assert session.commit.await_count == 1
        active += 1
        max_active = max(max_active, active)
        await asyncio.sleep(0)
        active -= 1

    with patch("services.document_cleanup.delete_document", new=remove):
        result = await process_document_cleanup_jobs(
            session,
            tenant_id="tenant-A",
        )

    assert result.succeeded == 8
    assert max_active == 4
    assert session.commit.await_count == 2


@pytest.mark.asyncio
async def test_cleanup_respects_explicit_batch_size():
    session = AsyncMock()
    session.execute = AsyncMock(side_effect=[_jobs(), MagicMock()])

    result = await process_document_cleanup_jobs(
        session,
        tenant_id="tenant-A",
        batch_size=7,
    )

    assert result.attempted == 0
    claim_params = session.execute.await_args_list[0].args[1]
    assert claim_params["batch_size"] == 7
    assert session.execute.await_count == 1
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_invalid_storage_path_is_quarantined_without_service_role_delete():
    session = AsyncMock()
    session.execute = AsyncMock(
        side_effect=[
            _jobs({
                "id": "job-1",
                "source_contract_id": "c-1",
                "storage_path": "tenant-B/c-1/doc.pdf",
            }),
            _recorded({"succeeded": False, "quarantined": True}),
        ]
    )

    with patch(
        "services.document_cleanup.delete_document",
        new=AsyncMock(),
    ) as remove:
        result = await process_document_cleanup_jobs(
            session,
            tenant_id="tenant-A",
        )

    remove.assert_not_awaited()
    assert result.quarantined == 1
    assert result.failed == 0
    outcomes = json.loads(session.execute.await_args_list[1].args[1]["outcomes"])
    assert outcomes[0]["quarantined"] is True
    assert "ownership" in outcomes[0]["error"]


@pytest.mark.asyncio
async def test_delete_uses_bounded_timeout_and_lease_covers_worst_case():
    session = AsyncMock()
    session.execute = AsyncMock(
        side_effect=[
            _jobs({"id": "job-1", "storage_path": "tenant-A/c-1/doc.pdf"}),
            _recorded({"succeeded": True, "quarantined": False}),
        ]
    )
    observed_timeout = None

    async def immediate_wait_for(coro, *, timeout):
        nonlocal observed_timeout
        observed_timeout = timeout
        await coro

    with patch(
        "services.document_cleanup.asyncio.wait_for",
        new=immediate_wait_for,
    ), patch(
        "services.document_cleanup.delete_document",
        new=AsyncMock(return_value=None),
    ):
        await process_document_cleanup_jobs(session, tenant_id="tenant-A")

    assert observed_timeout == DELETE_TIMEOUT_SECONDS
    assert DELETE_TIMEOUT_SECONDS <= 20
    worst_case = (
        (DEFAULT_BATCH_SIZE + MAX_CONCURRENCY - 1)
        // MAX_CONCURRENCY
    ) * DELETE_TIMEOUT_SECONDS
    assert CLAIM_LEASE_SECONDS > worst_case


@pytest.mark.asyncio
async def test_lost_claim_is_reported_only_from_guarded_returning_rows():
    session = AsyncMock()
    session.execute = AsyncMock(
        side_effect=[
            _jobs({"id": "job-1", "storage_path": "tenant-A/c-1/doc.pdf"}),
            _recorded(),
        ]
    )

    with patch(
        "services.document_cleanup.delete_document",
        new=AsyncMock(return_value=None),
    ):
        result = await process_document_cleanup_jobs(
            session,
            tenant_id="tenant-A",
        )

    assert result.attempted == 1
    assert result.succeeded == 0
    assert result.failed == 0
    assert result.lost_claims == 1


@pytest.mark.asyncio
async def test_scheduler_selects_only_eligible_retry_tenants():
    result = MagicMock()
    result.scalars.return_value.all.return_value = ["tenant-A", "tenant-B"]
    session = AsyncMock()
    session.execute.return_value = result

    tenants = await select_eligible_cleanup_tenants(session)

    sql = str(session.execute.await_args.args[0])
    assert "next_attempt_at <= NOW()" in sql
    assert "quarantined_at IS NULL" in sql
    assert "claim_expires_at <= NOW()" in sql
    assert tenants == ["tenant-A", "tenant-B"]


@pytest.mark.asyncio
async def test_background_loop_drains_before_sleep_and_propagates_cancellation():
    drain = AsyncMock(return_value=None)
    sleep = AsyncMock(side_effect=asyncio.CancelledError)

    with patch(
        "services.document_cleanup.drain_document_cleanup_cycle",
        new=drain,
    ):
        with pytest.raises(asyncio.CancelledError):
            await run_document_cleanup_loop(
                interval_seconds=0,
                sleep=sleep,
            )

    drain.assert_awaited_once()
    sleep.assert_awaited_once_with(0)


def test_app_lifespan_starts_and_cancels_cleanup_loop():
    from fastapi.testclient import TestClient

    from main import app

    async def wait_forever():
        await asyncio.Event().wait()

    loop = AsyncMock(side_effect=wait_forever)
    with patch("main.run_document_cleanup_loop", new=loop):
        with TestClient(app):
            assert loop.await_count == 1

    assert loop.await_count == 1


@pytest.mark.asyncio
async def test_retry_endpoint_is_scoped_to_authenticated_tenant():
    session = AsyncMock()
    expected = CleanupResult(attempted=2, succeeded=1, failed=1)

    with patch(
        "api.documents.process_document_cleanup_jobs",
        new=AsyncMock(return_value=expected),
    ) as process:
        response = await retry_pending_document_cleanups(
            user=_user("tenant-A"),
            session=session,
        )

    assert response == expected
    process.assert_awaited_once_with(session, tenant_id="tenant-A")
