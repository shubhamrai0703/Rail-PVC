"""Contract items (BOQ line items) under a schedule (P3-BF-2).

A contract_item is a single BOQ row: item_code, description, quantities,
rates, and the two classification flags that drive engine routing:
`is_cement_item` (cement bucket subtraction) and `steel_subtype`
(steel bucket — angles / plates / other_sections / tmt, NULL for
non-steel items).

Trust model: the route NEVER accepts a client-supplied `contract_id`.
The parent schedule's contract_id is the only authoritative source,
returned by `assert_schedule_belongs_to_tenant`. Without this discipline
a caller who learned a foreign schedule's UUID could attach an item to
their own contract — which then drives W derivation through the engine.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from services.auth import AuthUser, get_current_user
from services.db import get_session
from services.errors import ValidationProblem
from services.pvc_service import assert_schedule_belongs_to_tenant

router = APIRouter(prefix="/api", tags=["contract_items"])


# Matches migration 002 `steel_subtype` ENUM. NULL is a valid value —
# it marks the item as non-steel (cement, labour-driven items, etc.).
# The engine maps each subtype to a JPC series (see KU-004 / KU-005).
VALID_STEEL_SUBTYPES = frozenset({"angles", "plates", "other_sections", "tmt"})


class ContractItemCreate(BaseModel):
    item_code: str
    description: str | None = None
    unit: str | None = None
    original_qty: Decimal | None = None
    revised_qty: Decimal | None = None
    base_rate: Decimal | None = None
    agreement_rate: Decimal | None = None
    is_cement_item: bool = False
    steel_subtype: str | None = None


@router.post(
    "/schedules/{schedule_id}/items",
    status_code=status.HTTP_201_CREATED,
)
async def create_contract_item(
    schedule_id: str,
    body: ContractItemCreate,
    user: AuthUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    if body.steel_subtype is not None and body.steel_subtype not in VALID_STEEL_SUBTYPES:
        raise ValidationProblem(
            f"steel_subtype must be null or one of {sorted(VALID_STEEL_SUBTYPES)}",
            field="steel_subtype",
            value=body.steel_subtype,
        )

    # P3-BF-2 trust boundary: contract_id derives from the schedule's parent,
    # NEVER from a client-supplied field. The helper also handles tenant
    # isolation — 404 if the schedule is missing or belongs to another tenant.
    contract_id = await assert_schedule_belongs_to_tenant(
        session, schedule_id, user.tenant_id
    )

    row = (
        await session.execute(
            text("""
                INSERT INTO contract_items (
                    contract_id, schedule_id, item_code, description, unit,
                    original_qty, revised_qty, base_rate, agreement_rate,
                    is_cement_item, steel_subtype
                )
                VALUES (
                    :cid, :sid, :code, :desc, :unit,
                    :oqty, :rqty, :brate, :arate,
                    :cement, CAST(:stype AS steel_subtype)
                )
                RETURNING id::text AS id, created_at
            """),
            {
                "cid": contract_id,
                "sid": schedule_id,
                "code": body.item_code,
                "desc": body.description,
                "unit": body.unit,
                "oqty": body.original_qty,
                "rqty": body.revised_qty,
                "brate": body.base_rate,
                "arate": body.agreement_rate,
                "cement": body.is_cement_item,
                "stype": body.steel_subtype,
            },
        )
    ).mappings().first()
    assert row is not None
    return {
        "id": row["id"],
        "contract_id": contract_id,
        "schedule_id": schedule_id,
        **body.model_dump(mode="json"),
    }


@router.get("/schedules/{schedule_id}/items")
async def list_contract_items(
    schedule_id: str,
    user: AuthUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[dict[str, Any]]:
    await assert_schedule_belongs_to_tenant(session, schedule_id, user.tenant_id)

    rows = (
        await session.execute(
            text("""
                SELECT id::text AS id,
                       contract_id::text AS contract_id,
                       schedule_id::text AS schedule_id,
                       item_code,
                       description,
                       unit,
                       original_qty,
                       revised_qty,
                       base_rate,
                       agreement_rate,
                       is_cement_item,
                       steel_subtype::text AS steel_subtype,
                       created_at
                FROM contract_items
                WHERE schedule_id = :sid
                ORDER BY item_code
            """),
            {"sid": schedule_id},
        )
    ).mappings().all()
    return [dict(r) for r in rows]
