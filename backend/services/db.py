"""Async database engine and session factory.

DATABASE_URL is the **privileged** Postgres connection used by Alembic and the
backend. Because it bypasses RLS, every tenant-facing query path MUST filter
by tenant_id explicitly — RLS is documentation, not enforcement, on this path
(P3-03 remediation).

The async engine is created lazily so importing this module does not require
the env var to be set (matters for tests that override the dependency).
"""
from __future__ import annotations

import os
from collections.abc import AsyncIterator
from functools import lru_cache

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


def _resolve_database_url() -> str:
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError(
            "DATABASE_URL is not set. See backend/.env.example for the expected format."
        )
    # asyncpg requires the +asyncpg driver in the URL. Accept either form so
    # operators can paste the Supabase-provided URL without translating it.
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


@lru_cache(maxsize=1)
def _engine():
    return create_async_engine(_resolve_database_url(), pool_pre_ping=True)


@lru_cache(maxsize=1)
def _session_factory() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(_engine(), expire_on_commit=False, class_=AsyncSession)


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency yielding an AsyncSession with commit-on-exit."""
    async with _session_factory()() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
