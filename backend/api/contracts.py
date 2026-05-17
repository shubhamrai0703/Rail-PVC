"""Contracts CRUD. Creation seeds the default PVC rule set transactionally
(P3-07). `railway_zone` is mandatory at create time (P3-PRE-04 contract)."""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from services.auth import AuthUser, get_current_user
from services.db import get_session
from services.errors import NotFoundProblem, ValidationProblem
from services.pvc_service import create_contract_with_default_rule_set
from services.zone_mapping import VALID_ZONES

router = APIRouter(prefix="/api/contracts", tags=["contracts"])


class ContractCreate(BaseModel):
    tender_number: str
    agreement_number: str | None = None
    loa_number: str | None = None
    loa_date: date | None = None
    contractor_name: str
    work_description: str | None = None
    contract_value: Decimal | None = None
    bid_amount: Decimal | None = None
    start_date: date | None = None
    completion_date: date | None = None
    base_month: date  # must be first-of-month
    gst_mode: str = "exclusive"
    pvc_applicable: bool = True
    overall_rebate: Decimal = Field(default=Decimal("0"))
    railway_zone: str   # P3-PRE-04: required, validated below


class ContractOut(BaseModel):
    id: str
    tender_number: str
    contractor_name: str
    base_month: date
    railway_zone: str
    status: str


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_contract(
    body: ContractCreate,
    user: AuthUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    if body.railway_zone not in VALID_ZONES:
        raise ValidationProblem(
            f"railway_zone must be one of {sorted(VALID_ZONES)}",
            field="railway_zone",
            value=body.railway_zone,
        )
    if body.base_month.day != 1:
        raise ValidationProblem(
            "base_month must be the first day of the month",
            field="base_month",
            value=body.base_month.isoformat(),
        )

    created = await create_contract_with_default_rule_set(
        session,
        tenant_id=user.tenant_id,
        contract_data=body.model_dump(mode="python"),
    )
    return {"id": created["id"], **body.model_dump(mode="json"), "status": "Draft"}


@router.get("")
async def list_contracts(
    user: AuthUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[dict[str, Any]]:
    rows = (
        await session.execute(
            text("""
                SELECT id::text AS id, tender_number, contractor_name,
                       base_month, railway_zone::text AS railway_zone, status::text AS status
                FROM contracts
                WHERE tenant_id = :tid
                ORDER BY created_at DESC
            """),
            {"tid": user.tenant_id},
        )
    ).mappings().all()
    return [dict(r) for r in rows]


@router.get("/{contract_id}")
async def get_contract(
    contract_id: str,
    user: AuthUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    row = (
        await session.execute(
            text("""
                SELECT id::text AS id, tender_number, contractor_name,
                       base_month, railway_zone::text AS railway_zone, status::text AS status
                FROM contracts
                WHERE id = :id AND tenant_id = :tid
            """),
            {"id": contract_id, "tid": user.tenant_id},
        )
    ).mappings().first()
    if row is None:
        raise NotFoundProblem("Contract not found", entity="contract", id=contract_id)
    return dict(row)
