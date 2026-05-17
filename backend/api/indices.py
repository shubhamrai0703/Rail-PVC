"""Index series and observations — READ-ONLY for tenant-facing API.

P3-03 remediation: writes to `index_observations` are intentionally NOT
exposed here. The previous implementation surfaced POST/PUT endpoints that
relied on RLS to gate writes, but the backend connects with a privileged
DATABASE_URL that bypasses RLS, so those endpoints were effectively open
to every authenticated user. Index data is global; any cross-tenant
contamination would silently change PVC outputs for every contract.

Index data is written exclusively by `seeds/seed_indices.py` and the
manual admin script, both of which run with the service-role key out of
band — never through the tenant API surface.
"""
from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from services.auth import AuthUser, get_current_user
from services.db import get_session

router = APIRouter(prefix="/api", tags=["indices"])


@router.get("/index-series")
async def list_series(
    _: AuthUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[dict[str, Any]]:
    rows = (
        await session.execute(
            text("""
                SELECT id::text AS id, name, source_publication::text AS source_publication
                FROM index_series
                ORDER BY name
            """)
        )
    ).mappings().all()
    return [dict(r) for r in rows]


@router.get("/index-observations")
async def list_observations(
    series_id: str | None = Query(default=None),
    month_from: date | None = Query(default=None, alias="from"),
    month_to: date | None = Query(default=None, alias="to"),
    _: AuthUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[dict[str, Any]]:
    sql = """
        SELECT o.id::text AS id, o.series_id::text AS series_id,
               o.month, o.value, o.revision_flag, o.revised_at, o.created_at
        FROM index_observations o
        WHERE TRUE
    """
    params: dict[str, Any] = {}
    if series_id is not None:
        sql += " AND o.series_id = :sid"
        params["sid"] = series_id
    if month_from is not None:
        sql += " AND o.month >= :mf"
        params["mf"] = month_from
    if month_to is not None:
        sql += " AND o.month <= :mt"
        params["mt"] = month_to
    sql += " ORDER BY o.month"

    rows = (await session.execute(text(sql), params)).mappings().all()
    return [dict(r) for r in rows]
