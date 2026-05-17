"""POST /pvc-runs — synchronous engine call, atomic persistence, real
idempotency (P3-05), structured engine error surface (P3-09)."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Header, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from services.auth import AuthUser, get_current_user
from services.db import get_session
from services.errors import ImmutableApprovedRun, NotFoundProblem, ValidationProblem
from services.pvc_service import execute_pvc_run

router = APIRouter(prefix="/api", tags=["pvc_runs"])


class PVCRunCreate(BaseModel):
    bill_id: str


@router.post("/contracts/{contract_id}/pvc-runs", status_code=status.HTTP_201_CREATED)
async def create_pvc_run(
    contract_id: str,
    body: PVCRunCreate,
    user: AuthUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict[str, Any]:
    rule_set = (
        await session.execute(
            text("""
                SELECT rs.id::text AS id, rs.quarter_mode::text AS quarter_mode,
                       rs.component_weights, rs.adjustable_fraction,
                       rs.rounding_mode::text AS rounding_mode,
                       rs.negative_pvc_policy::text AS negative_pvc_policy
                FROM pvc_rule_sets rs
                JOIN contracts c ON c.id = rs.contract_id
                WHERE rs.contract_id = :cid AND c.tenant_id = :tid
                ORDER BY rs.version DESC LIMIT 1
            """),
            {"cid": contract_id, "tid": user.tenant_id},
        )
    ).mappings().first()
    if rule_set is None:
        raise NotFoundProblem(
            "No rule set for contract — contract must be created via POST /contracts",
            entity="pvc_rule_set",
            contract_id=contract_id,
        )

    bill = (
        await session.execute(
            text("""
                SELECT 1 FROM running_bills b
                JOIN contracts c ON c.id = b.contract_id
                WHERE b.id = :bid AND b.contract_id = :cid AND c.tenant_id = :tid
            """),
            {"bid": body.bill_id, "cid": contract_id, "tid": user.tenant_id},
        )
    ).first()
    if bill is None:
        raise ValidationProblem(
            "Bill not found for this contract",
            contract_id=contract_id,
            bill_id=body.bill_id,
        )

    return await execute_pvc_run(
        session,
        tenant_id=user.tenant_id,
        contract_id=contract_id,
        bill_id=body.bill_id,
        rule_set_row=dict(rule_set),
        idempotency_key=idempotency_key,
    )


@router.post("/pvc-runs/{run_id}/approve")
async def approve_run(
    run_id: str,
    user: AuthUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    row = (
        await session.execute(
            text("""
                SELECT r.id::text AS id, r.status::text AS status
                FROM pvc_runs r
                JOIN contracts c ON c.id = r.contract_id
                WHERE r.id = :rid AND c.tenant_id = :tid
            """),
            {"rid": run_id, "tid": user.tenant_id},
        )
    ).mappings().first()
    if row is None:
        raise NotFoundProblem("Run not found", entity="pvc_run", id=run_id)
    if row["status"] == "Approved":
        # The DB trigger (migration 011) would block this too; we 409 first
        # for a clean structured error rather than relying on the trigger
        # exception bubbling up.
        raise ImmutableApprovedRun(run_id)

    updated = (
        await session.execute(
            text("""
                UPDATE pvc_runs
                SET status = 'Approved', approved_by = :by, approved_at = NOW()
                WHERE id = :rid AND status <> 'Approved'
                RETURNING id::text AS id, approved_at
            """),
            {"rid": run_id, "by": user.display_name},
        )
    ).mappings().first()
    if updated is None:
        # Race: another caller just approved it.
        raise ImmutableApprovedRun(run_id)
    return {"id": updated["id"], "status": "Approved", "approved_at": updated["approved_at"]}


@router.get("/pvc-runs/{run_id}")
async def get_run(
    run_id: str,
    user: AuthUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    row = (
        await session.execute(
            text("""
                SELECT r.id::text AS id, r.contract_id::text AS contract_id,
                       r.bill_id::text AS bill_id, r.status::text AS status,
                       r.w_derivation, r.approved_by, r.approved_at, r.created_at
                FROM pvc_runs r
                JOIN contracts c ON c.id = r.contract_id
                WHERE r.id = :rid AND c.tenant_id = :tid
            """),
            {"rid": run_id, "tid": user.tenant_id},
        )
    ).mappings().first()
    if row is None:
        raise NotFoundProblem("Run not found", entity="pvc_run", id=run_id)

    components = (
        await session.execute(
            text("""
                SELECT category::text AS category, eligible_amount, base_index,
                       current_avg_index, weight, pvc_value
                FROM pvc_components WHERE run_id = :rid
                ORDER BY category
            """),
            {"rid": run_id},
        )
    ).mappings().all()
    return {**dict(row), "components": [dict(c) for c in components]}
