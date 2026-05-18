"""Bills, bill lines, recoveries. Bill-line creation enforces the full
parent-child path (P3-06): the line's contract_item must belong to the
bill's contract, not just to the caller's tenant.

Recoveries (P3-BF-3) are a flat child of running_bills: reuse
`assert_bill_belongs_to_tenant` for the tenant gate; no item-level
cross-table check is needed because recoveries don't reference
contract_items."""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from services.auth import AuthUser, get_current_user
from services.db import get_session
from services.errors import NotFoundProblem, ValidationProblem
from services.pvc_service import (
    assert_bill_belongs_to_tenant,
    assert_item_belongs_to_contract,
)

router = APIRouter(prefix="/api", tags=["bills"])


# Matches migration 003 `recovery_type` ENUM. The `affects_pvc_base` flag
# on the row drives whether the recovery is subtracted from the engine's
# on_account amount during W derivation — set conservatively (default False).
VALID_RECOVERY_TYPES = frozenset({
    "security_deposit", "income_tax", "labour_cess", "water", "other",
})


class BillCreate(BaseModel):
    bill_number: int
    bill_date: date | None = None
    measurement_date: date
    gross_amount: Decimal | None = None
    net_amount: Decimal | None = None


@router.post("/contracts/{contract_id}/bills", status_code=status.HTTP_201_CREATED)
async def create_bill(
    contract_id: str,
    body: BillCreate,
    user: AuthUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    # Tenant ownership check on the contract first.
    owns = (
        await session.execute(
            text("SELECT 1 FROM contracts WHERE id = :id AND tenant_id = :tid"),
            {"id": contract_id, "tid": user.tenant_id},
        )
    ).first()
    if owns is None:
        raise NotFoundProblem("Contract not found", entity="contract", id=contract_id)

    row = (
        await session.execute(
            text("""
                INSERT INTO running_bills (
                    contract_id, bill_number, bill_date, measurement_date,
                    gross_amount, net_amount, status
                )
                VALUES (:cid, :num, :bd, :md, :ga, :na, 'Draft')
                RETURNING id::text AS id, created_at
            """),
            {
                "cid": contract_id,
                "num": body.bill_number,
                "bd": body.bill_date,
                "md": body.measurement_date,
                "ga": body.gross_amount,
                "na": body.net_amount,
            },
        )
    ).mappings().first()
    assert row is not None
    return {"id": row["id"], **body.model_dump(mode="json")}


class BillLineCreate(BaseModel):
    item_id: str
    qty_up_to_last: Decimal = Decimal("0")
    qty_since_last: Decimal = Decimal("0")
    qty_up_to_date: Decimal = Decimal("0")
    amount_up_to_last: Decimal = Decimal("0")
    amount_since_last: Decimal = Decimal("0")
    amount_up_to_date: Decimal = Decimal("0")
    special_condition_amount: Decimal = Decimal("0")


@router.post("/bills/{bill_id}/lines", status_code=status.HTTP_201_CREATED)
async def create_bill_line(
    bill_id: str,
    body: BillLineCreate,
    user: AuthUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    # P3-06: tenant ownership of the bill + cross-contract integrity on the item.
    contract_id = await assert_bill_belongs_to_tenant(session, bill_id, user.tenant_id)
    await assert_item_belongs_to_contract(session, body.item_id, contract_id)

    row = (
        await session.execute(
            text("""
                INSERT INTO bill_lines (
                    bill_id, item_id, qty_up_to_last, qty_since_last, qty_up_to_date,
                    amount_up_to_last, amount_since_last, amount_up_to_date,
                    special_condition_amount
                )
                VALUES (
                    :bid, :iid, :qul, :qsl, :qutd, :aul, :asl, :autd, :sca
                )
                RETURNING id::text AS id
            """),
            {
                "bid": bill_id,
                "iid": body.item_id,
                "qul": body.qty_up_to_last,
                "qsl": body.qty_since_last,
                "qutd": body.qty_up_to_date,
                "aul": body.amount_up_to_last,
                "asl": body.amount_since_last,
                "autd": body.amount_up_to_date,
                "sca": body.special_condition_amount,
            },
        )
    ).mappings().first()
    assert row is not None
    return {"id": row["id"], "bill_id": bill_id, **body.model_dump(mode="json")}


class RecoveryCreate(BaseModel):
    recovery_type: str
    amount: Decimal
    affects_pvc_base: bool = False


@router.post("/bills/{bill_id}/recoveries", status_code=status.HTTP_201_CREATED)
async def create_recovery(
    bill_id: str,
    body: RecoveryCreate,
    user: AuthUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    if body.recovery_type not in VALID_RECOVERY_TYPES:
        raise ValidationProblem(
            f"recovery_type must be one of {sorted(VALID_RECOVERY_TYPES)}",
            field="recovery_type",
            value=body.recovery_type,
        )

    # Tenant gate. We discard the returned contract_id — recoveries don't
    # have a cross-contract integrity dimension; they're a flat child of
    # the bill.
    await assert_bill_belongs_to_tenant(session, bill_id, user.tenant_id)

    row = (
        await session.execute(
            text("""
                INSERT INTO recoveries (
                    bill_id, recovery_type, amount, affects_pvc_base
                )
                VALUES (
                    :bid, CAST(:rtype AS recovery_type), :amt, :pvc
                )
                RETURNING id::text AS id
            """),
            {
                "bid": bill_id,
                "rtype": body.recovery_type,
                "amt": body.amount,
                "pvc": body.affects_pvc_base,
            },
        )
    ).mappings().first()
    assert row is not None
    return {"id": row["id"], "bill_id": bill_id, **body.model_dump(mode="json")}
