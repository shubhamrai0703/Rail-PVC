"""Schedules under a contract (P3-BF-1). A schedule is a BOQ grouping:
DSR (standard rate), NS (non-schedule), or ExtraNS (extra non-schedule —
items that bill in `on_account_amount` but must be excluded from W via
the eligibility flag).

Tenant isolation: every read/write filters by tenant_id via
`assert_contract_belongs_to_tenant`. The route NEVER trusts a
client-supplied contract_id — it comes from the URL after the gate.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from services.auth import AuthUser, get_current_user
from services.db import get_session
from services.errors import ValidationProblem
from services.pvc_service import assert_contract_belongs_to_tenant

router = APIRouter(prefix="/api", tags=["schedules"])


# Matches migration 002 `schedule_type` ENUM. Kept inline rather than imported
# from the engine because schedule_type is purely API/DB metadata — the engine
# has no opinion on schedule grouping.
VALID_SCHEDULE_TYPES = frozenset({"DSR", "NS", "ExtraNS"})


class ScheduleCreate(BaseModel):
    name: str
    schedule_type: str
    bid_discount_pct: Decimal = Field(default=Decimal("0"))


@router.post(
    "/contracts/{contract_id}/schedules",
    status_code=status.HTTP_201_CREATED,
)
async def create_schedule(
    contract_id: str,
    body: ScheduleCreate,
    user: AuthUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    if body.schedule_type not in VALID_SCHEDULE_TYPES:
        raise ValidationProblem(
            f"schedule_type must be one of {sorted(VALID_SCHEDULE_TYPES)}",
            field="schedule_type",
            value=body.schedule_type,
        )

    await assert_contract_belongs_to_tenant(session, contract_id, user.tenant_id)

    row = (
        await session.execute(
            text("""
                INSERT INTO schedules (contract_id, name, schedule_type, bid_discount_pct)
                VALUES (:cid, :name, :stype::schedule_type, :disc)
                RETURNING id::text AS id, created_at
            """),
            {
                "cid": contract_id,
                "name": body.name,
                "stype": body.schedule_type,
                "disc": body.bid_discount_pct,
            },
        )
    ).mappings().first()
    assert row is not None
    return {
        "id": row["id"],
        "contract_id": contract_id,
        **body.model_dump(mode="json"),
    }


@router.get("/contracts/{contract_id}/schedules")
async def list_schedules(
    contract_id: str,
    user: AuthUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[dict[str, Any]]:
    await assert_contract_belongs_to_tenant(session, contract_id, user.tenant_id)

    rows = (
        await session.execute(
            text("""
                SELECT id::text AS id,
                       contract_id::text AS contract_id,
                       name,
                       schedule_type::text AS schedule_type,
                       bid_discount_pct,
                       created_at
                FROM schedules
                WHERE contract_id = :cid
                ORDER BY created_at
            """),
            {"cid": contract_id},
        )
    ).mappings().all()
    return [dict(r) for r in rows]
