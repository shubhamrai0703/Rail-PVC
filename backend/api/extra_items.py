"""Extra-item eligibility decisions. NULL `eligible` is valid (undecided)
and the engine treats it as a blocking validation error (P3-02 keeps that
guarantee end-to-end)."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from services.auth import AuthUser, get_current_user
from services.db import get_session
from services.errors import NotFoundProblem, ValidationProblem

router = APIRouter(prefix="/api", tags=["extra_items"])


class ExtraItemDecisionUpsert(BaseModel):
    item_id: str
    eligible: bool | None  # explicit None allowed
    notes: str | None = None


@router.get("/contracts/{contract_id}/extra-item-decisions")
async def list_decisions(
    contract_id: str,
    user: AuthUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[dict[str, Any]]:
    owns = (
        await session.execute(
            text("SELECT 1 FROM contracts WHERE id = :id AND tenant_id = :tid"),
            {"id": contract_id, "tid": user.tenant_id},
        )
    ).first()
    if owns is None:
        raise NotFoundProblem("Contract not found", entity="contract", id=contract_id)

    rows = (
        await session.execute(
            text("""
                SELECT id::text AS id, item_id::text AS item_id, eligible,
                       decided_by, decided_at, notes
                FROM extra_item_decisions
                WHERE contract_id = :cid
            """),
            {"cid": contract_id},
        )
    ).mappings().all()
    return [dict(r) for r in rows]


@router.post(
    "/contracts/{contract_id}/extra-item-decisions",
    status_code=status.HTTP_201_CREATED,
)
async def upsert_decision(
    contract_id: str,
    body: ExtraItemDecisionUpsert,
    user: AuthUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    # Verify both the contract belongs to tenant AND the item belongs to the contract.
    owns = (
        await session.execute(
            text("""
                SELECT 1
                FROM contracts c
                JOIN contract_items ci ON ci.contract_id = c.id
                WHERE c.id = :cid AND c.tenant_id = :tid AND ci.id = :iid
            """),
            {"cid": contract_id, "tid": user.tenant_id, "iid": body.item_id},
        )
    ).first()
    if owns is None:
        raise ValidationProblem(
            "item_id does not belong to this contract",
            contract_id=contract_id,
            item_id=body.item_id,
        )

    row = (
        await session.execute(
            text("""
                INSERT INTO extra_item_decisions (
                    contract_id, item_id, eligible, decided_by, decided_at, notes
                )
                VALUES (:cid, :iid, :elig, :db, NOW(), :notes)
                ON CONFLICT (contract_id, item_id) DO UPDATE
                  SET eligible = EXCLUDED.eligible,
                      decided_by = EXCLUDED.decided_by,
                      decided_at = NOW(),
                      notes = EXCLUDED.notes
                RETURNING id::text AS id
            """),
            {
                "cid": contract_id,
                "iid": body.item_id,
                "elig": body.eligible,
                "db": user.display_name,
                "notes": body.notes,
            },
        )
    ).mappings().first()
    assert row is not None
    return {"id": row["id"], **body.model_dump()}
