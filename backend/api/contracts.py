"""Contracts CRUD. Creation seeds the default PVC rule set transactionally
(P3-07). `railway_zone` is mandatory at create time (P3-PRE-04 contract)."""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from services.auth import AuthUser, get_current_user
from services.db import get_session
from services.errors import (
    FieldNotNullableProblem,
    NotFoundProblem,
    ValidationProblem,
)
from services.pvc_service import (
    assert_contract_belongs_to_tenant,
    create_contract_with_default_rule_set,
)
from services.zone_mapping import VALID_ZONES

router = APIRouter(prefix="/api/contracts", tags=["contracts"])

# Columns declared NOT NULL in migration 002 (contracts table). An explicit
# `null` for any of these in a PUT body must be rejected at the API boundary
# rather than crashing at Postgres. See REVIEW.md H-2.
_CONTRACT_NOT_NULL_FIELDS = frozenset({
    "tender_number",
    "contractor_name",
    "base_month",
    "gst_mode",
    "pvc_applicable",
    "overall_rebate",
    "railway_zone",
})


# Columns returned by GET /api/contracts/{id} and PUT /api/contracts/{id}.
# Kept as a single SELECT-list constant so the two endpoints can't drift.
_CONTRACT_SELECT = """
    SELECT id::text AS id,
           tender_number,
           agreement_number,
           loa_number,
           loa_date,
           contractor_name,
           work_description,
           contract_value,
           bid_amount,
           start_date,
           completion_date,
           base_month,
           gst_mode,
           pvc_applicable,
           overall_rebate,
           railway_zone::text AS railway_zone,
           status::text AS status
    FROM contracts
"""


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


class ContractUpdate(BaseModel):
    """Partial update — only fields actually present in the request body are
    written. We use `model_fields_set` in the handler to build the SET clause
    so unset Optional fields do not overwrite existing values with NULL."""
    tender_number: str | None = None
    agreement_number: str | None = None
    loa_number: str | None = None
    loa_date: date | None = None
    contractor_name: str | None = None
    work_description: str | None = None
    contract_value: Decimal | None = None
    bid_amount: Decimal | None = None
    start_date: date | None = None
    completion_date: date | None = None
    base_month: date | None = None
    gst_mode: str | None = None
    pvc_applicable: bool | None = None
    overall_rebate: Decimal | None = None
    railway_zone: str | None = None


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
                SELECT id::text AS id, tender_number, contractor_name, contract_value,
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
            text(_CONTRACT_SELECT + " WHERE id = :id AND tenant_id = :tid"),
            {"id": contract_id, "tid": user.tenant_id},
        )
    ).mappings().first()
    if row is None:
        raise NotFoundProblem("Contract not found", entity="contract", id=contract_id)
    return dict(row)


@router.delete("/{contract_id}")
async def delete_contract(
    contract_id: str,
    user: AuthUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Response:
    row = (
        await session.execute(
            text(
                "SELECT status::text AS status "
                "FROM contracts WHERE id = :id AND tenant_id = :tid"
            ),
            {"id": contract_id, "tid": user.tenant_id},
        )
    ).mappings().first()
    if row is None:
        raise NotFoundProblem("Contract not found", entity="contract", id=contract_id)
    if row["status"] != "Draft":
        raise ValidationProblem(
            "Only Draft contracts can be deleted",
            field="status",
            value=row["status"],
        )
    await session.execute(
        text("DELETE FROM contracts WHERE id = :id AND tenant_id = :tid"),
        {"id": contract_id, "tid": user.tenant_id},
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put("/{contract_id}")
async def update_contract(
    contract_id: str,
    body: ContractUpdate,
    user: AuthUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    # Same "wrong tenant collapses to 404" rule as the other nested endpoints.
    await assert_contract_belongs_to_tenant(session, contract_id, user.tenant_id)

    fields = body.model_fields_set
    if not fields:
        # Nothing to update — return the current row.
        row = (
            await session.execute(
                text(_CONTRACT_SELECT + " WHERE id = :id AND tenant_id = :tid"),
                {"id": contract_id, "tid": user.tenant_id},
            )
        ).mappings().first()
        return dict(row)  # type: ignore[arg-type]

    # H-2: reject explicit-null on NOT NULL columns BEFORE the railway_zone
    # check — that gate's "not in VALID_ZONES" would also fail for null but
    # the error message would be misleading.
    for f in fields:
        if f in _CONTRACT_NOT_NULL_FIELDS and getattr(body, f) is None:
            raise FieldNotNullableProblem(f)

    if "railway_zone" in fields and body.railway_zone not in VALID_ZONES:
        raise ValidationProblem(
            f"railway_zone must be one of {sorted(VALID_ZONES)}",
            field="railway_zone",
            value=body.railway_zone,
        )
    if "base_month" in fields and body.base_month is not None and body.base_month.day != 1:
        raise ValidationProblem(
            "base_month must be the first day of the month",
            field="base_month",
            value=body.base_month.isoformat(),
        )

    set_clause = ", ".join(f"{f} = :{f}" for f in fields)
    params: dict[str, Any] = {f: getattr(body, f) for f in fields}
    params["id"] = contract_id
    params["tid"] = user.tenant_id

    await session.execute(
        text(
            f"UPDATE contracts SET {set_clause} "
            f"WHERE id = :id AND tenant_id = :tid"
        ),
        params,
    )

    row = (
        await session.execute(
            text(_CONTRACT_SELECT + " WHERE id = :id AND tenant_id = :tid"),
            {"id": contract_id, "tid": user.tenant_id},
        )
    ).mappings().first()
    return dict(row)  # type: ignore[arg-type]
