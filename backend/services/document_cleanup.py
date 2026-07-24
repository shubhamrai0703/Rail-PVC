"""Durable cleanup worker for Supabase document objects.

Postgres and Supabase Storage cannot share a transaction. Contract deletion
therefore writes document paths to ``document_cleanup_jobs`` in the same
transaction that removes the contract. This worker can safely retry pending
jobs: object removal is idempotent, and a path remains pending until the
successful attempt is recorded in Postgres.
"""
from __future__ import annotations

import asyncio
import json
import logging
import math
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from uuid import uuid4

from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from services.storage import delete_document

DEFAULT_BATCH_SIZE = 25
MAX_CONCURRENCY = 4
DELETE_TIMEOUT_SECONDS = 15
CLAIM_LEASE_SECONDS = (
    math.ceil(DEFAULT_BATCH_SIZE / MAX_CONCURRENCY) * DELETE_TIMEOUT_SECONDS
    + 60
)
RETRY_LOOP_SECONDS = 60
MAX_TENANTS_PER_CYCLE = 25
logger = logging.getLogger(__name__)


class CleanupResult(BaseModel):
    attempted: int
    succeeded: int
    failed: int
    quarantined: int = 0
    lost_claims: int = 0


@dataclass(frozen=True)
class _CleanupOutcome:
    id: str
    succeeded: bool
    quarantined: bool
    error: str | None


async def _remove_claimed_object(
    row: dict[str, str],
    semaphore: asyncio.Semaphore,
    *,
    tenant_id: str,
) -> _CleanupOutcome:
    expected_prefix = f"{tenant_id}/{row['source_contract_id']}/"
    if not row["storage_path"].startswith(expected_prefix):
        return _CleanupOutcome(
            id=row["id"],
            succeeded=False,
            quarantined=True,
            error="storage path does not match cleanup job ownership",
        )
    async with semaphore:
        try:
            await asyncio.wait_for(
                delete_document(row["storage_path"]),
                timeout=DELETE_TIMEOUT_SECONDS,
            )
        except Exception as exc:  # noqa: BLE001 — persist any storage failure
            return _CleanupOutcome(
                id=row["id"],
                succeeded=False,
                quarantined=False,
                error=str(exc)[:1000],
            )
        return _CleanupOutcome(
            id=row["id"],
            succeeded=True,
            quarantined=False,
            error=None,
        )


async def process_document_cleanup_jobs(
    session: AsyncSession,
    *,
    tenant_id: str,
    storage_paths: list[str] | None = None,
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> CleanupResult:
    """Attempt pending cleanup jobs owned by ``tenant_id``.

    A short transaction claims a bounded batch and commits before any Storage
    request. Outcomes are then written in one token-guarded transaction. If
    that write fails after object deletion, the lease expires and the
    idempotent removal is retried without losing the durable path.
    """
    if batch_size < 1:
        raise ValueError("batch_size must be at least 1")
    if batch_size > DEFAULT_BATCH_SIZE:
        raise ValueError(f"batch_size cannot exceed {DEFAULT_BATCH_SIZE}")

    claim_token = str(uuid4())
    path_filter = ""
    params: dict[str, object] = {
        "tenant_id": tenant_id,
        "claim_token": claim_token,
        "lease_seconds": CLAIM_LEASE_SECONDS,
        "batch_size": batch_size,
    }
    if storage_paths is not None:
        if not storage_paths:
            return CleanupResult(attempted=0, succeeded=0, failed=0)
        path_filter = " AND storage_path = ANY(:storage_paths)"
        params["storage_paths"] = storage_paths

    rows = (
        await session.execute(
            text(
                """
                WITH candidates AS (
                    SELECT id
                    FROM document_cleanup_jobs
                    WHERE tenant_id = :tenant_id
                      AND completed_at IS NULL
                      AND quarantined_at IS NULL
                      AND next_attempt_at <= NOW()
                      AND (
                          claim_token IS NULL
                          OR claim_expires_at IS NULL
                          OR claim_expires_at <= NOW()
                      )
                """
                + path_filter
                + """
                    ORDER BY created_at, id
                    LIMIT :batch_size
                    FOR UPDATE SKIP LOCKED
                )
                UPDATE document_cleanup_jobs AS job
                SET claim_token = CAST(:claim_token AS UUID),
                    claim_expires_at = (
                        NOW() + (:lease_seconds * INTERVAL '1 second')
                    )
                FROM candidates
                WHERE job.id = candidates.id
                  AND job.tenant_id = :tenant_id
                RETURNING job.id::text AS id,
                          job.source_contract_id::text AS source_contract_id,
                          job.storage_path
                """
            ),
            params,
        )
    ).mappings().all()
    await session.commit()

    if not rows:
        return CleanupResult(attempted=0, succeeded=0, failed=0)

    semaphore = asyncio.Semaphore(MAX_CONCURRENCY)
    outcomes = await asyncio.gather(
        *(
            _remove_claimed_object(
                dict(row),
                semaphore,
                tenant_id=tenant_id,
            )
            for row in rows
        )
    )

    recorded = (
        await session.execute(
            text("""
                WITH outcome AS (
                    SELECT *
                    FROM jsonb_to_recordset(CAST(:outcomes AS JSONB))
                        AS value(
                            id UUID,
                            succeeded BOOLEAN,
                            quarantined BOOLEAN,
                            error TEXT
                        )
                )
                UPDATE document_cleanup_jobs AS job
                SET attempt_count = attempt_count + 1,
                    last_attempt_at = NOW(),
                    last_error = outcome.error,
                    completed_at = CASE WHEN outcome.succeeded
                                        THEN NOW() ELSE NULL END,
                    quarantined_at = CASE WHEN outcome.quarantined
                                          THEN NOW() ELSE NULL END,
                    next_attempt_at = CASE
                        WHEN outcome.succeeded OR outcome.quarantined THEN NOW()
                        ELSE NOW() + (
                            LEAST(
                                3600,
                                POWER(2, LEAST(job.attempt_count, 7)) * 30
                                * (0.75 + random() * 0.5)
                            )
                        ) * INTERVAL '1 second'
                    END,
                    claim_token = NULL,
                    claim_expires_at = NULL
                FROM outcome
                WHERE job.id = outcome.id
                  AND job.tenant_id = :tenant_id
                  AND job.claim_token = CAST(:claim_token AS UUID)
                  AND job.completed_at IS NULL
                RETURNING outcome.succeeded, outcome.quarantined
            """),
            {
                "tenant_id": tenant_id,
                "claim_token": claim_token,
                "outcomes": json.dumps([
                    {
                        "id": outcome.id,
                        "succeeded": outcome.succeeded,
                        "quarantined": outcome.quarantined,
                        "error": outcome.error,
                    }
                    for outcome in outcomes
                ]),
            },
        )
    ).mappings().all()
    await session.commit()
    succeeded = sum(bool(row["succeeded"]) for row in recorded)
    quarantined = sum(bool(row["quarantined"]) for row in recorded)
    failed = len(recorded) - succeeded - quarantined
    return CleanupResult(
        attempted=len(outcomes),
        succeeded=succeeded,
        failed=failed,
        quarantined=quarantined,
        lost_claims=len(outcomes) - len(recorded),
    )


async def select_eligible_cleanup_tenants(
    session: AsyncSession,
) -> list[str]:
    rows = (
        await session.execute(
            text("""
                SELECT tenant_id::text AS tenant_id
                FROM document_cleanup_jobs
                WHERE completed_at IS NULL
                  AND quarantined_at IS NULL
                  AND next_attempt_at <= NOW()
                  AND (
                      claim_token IS NULL
                      OR claim_expires_at IS NULL
                      OR claim_expires_at <= NOW()
                  )
                GROUP BY tenant_id
                ORDER BY MIN(next_attempt_at), tenant_id
                LIMIT :limit
            """),
            {"limit": MAX_TENANTS_PER_CYCLE},
        )
    ).scalars().all()
    return list(rows)


async def drain_document_cleanup_cycle() -> None:
    from services.db import get_session_factory

    factory = get_session_factory()
    async with factory() as discovery:
        tenant_ids = await select_eligible_cleanup_tenants(discovery)
        await discovery.rollback()

    for tenant_id in tenant_ids:
        async with factory() as session:
            await process_document_cleanup_jobs(
                session,
                tenant_id=tenant_id,
            )


async def run_document_cleanup_loop(
    *,
    interval_seconds: float = RETRY_LOOP_SECONDS,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
) -> None:
    while True:
        try:
            await drain_document_cleanup_cycle()
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001 — one cycle must not kill retries
            logger.exception("Document cleanup background cycle failed")
        await sleep(interval_seconds)
