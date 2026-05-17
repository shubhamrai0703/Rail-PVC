"""Carry-forwards. The schema stores `paid_qty_source` and `recorded_qty`;
`paid_ratio` is derived server-side. The API never accepts a client-supplied
ratio (P3-05 acceptance / engine model invariant)."""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from services.auth import AuthUser, get_current_user
from services.db import get_session
from services.errors import NotFoundProblem, ValidationProblem

router = APIRouter(prefix="/api", tags=["carry_forwards"])


class CarryForwardUpdate(BaseModel):
    paid_qty_source: Decimal = Field(ge=Decimal("0"))


@router.get("/contracts/{contract_id}/carry-forwards")
async def list_carry_forwards(
    contract_id: str,
    user: AuthUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[dict[str, Any]]:
    rows = (
        await session.execute(
            text("""
                SELECT cf.id::text AS id, cf.item_id::text AS item_id,
                       cf.recorded_qty, cf.paid_qty_source, cf.paid_ratio, cf.carry_qty,
                       cf.source_bill_id::text AS source_bill_id,
                       cf.target_bill_id::text AS target_bill_id
                FROM carry_forwards cf
                JOIN contracts c ON c.id = cf.contract_id
                WHERE cf.contract_id = :cid AND c.tenant_id = :tid
            """),
            {"cid": contract_id, "tid": user.tenant_id},
        )
    ).mappings().all()
    return [dict(r) for r in rows]


@router.put("/carry-forwards/{cf_id}")
async def update_carry_forward(
    cf_id: str,
    body: CarryForwardUpdate,
    user: AuthUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    cf = (
        await session.execute(
            text("""
                SELECT cf.id::text AS id, cf.recorded_qty
                FROM carry_forwards cf
                JOIN contracts c ON c.id = cf.contract_id
                WHERE cf.id = :id AND c.tenant_id = :tid
            """),
            {"id": cf_id, "tid": user.tenant_id},
        )
    ).mappings().first()
    if cf is None:
        raise NotFoundProblem("Carry-forward not found", entity="carry_forward", id=cf_id)

    recorded = Decimal(cf["recorded_qty"])
    if body.paid_qty_source > recorded:
        raise ValidationProblem(
            "paid_qty_source cannot exceed recorded_qty",
            recorded_qty=str(recorded),
            paid_qty_source=str(body.paid_qty_source),
        )

    # paid_ratio + carry_qty are derived — never accepted from caller.
    ratio = body.paid_qty_source / recorded if recorded > 0 else Decimal("0")
    carry_qty = recorded - body.paid_qty_source

    row = (
        await session.execute(
            text("""
                UPDATE carry_forwards
                SET paid_qty_source = :pqs, paid_ratio = :ratio, carry_qty = :cq
                WHERE id = :id
                RETURNING id::text AS id, recorded_qty, paid_qty_source, paid_ratio, carry_qty
            """),
            {"id": cf_id, "pqs": body.paid_qty_source, "ratio": ratio, "cq": carry_qty},
        )
    ).mappings().first()
    return dict(row)
