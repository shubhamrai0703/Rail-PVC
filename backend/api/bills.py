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
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from services.auth import AuthUser, get_current_user
from services.db import get_session
from services.errors import (
    ConflictProblem,
    FieldNotNullableProblem,
    NotFoundProblem,
    ValidationProblem,
)
from services.pvc_service import (
    assert_bill_belongs_to_tenant,
    assert_contract_belongs_to_tenant,
    assert_item_belongs_to_contract,
)

router = APIRouter(prefix="/api", tags=["bills"])


# C-3: net_amount (net payable) is a DERIVED financial value the backend owns —
# never supplied or computed by the client (ENGINEERING_GUIDELINES). It is
# computed on read, not persisted, so it can never drift from the recoveries.
#
# DECISION (Saqlain, 2026-06-08) — FLAGGED FOR REVISIT (C-3-FUP-NET):
#   net_amount = gross_amount − Σ(recoveries WHERE affects_pvc_base = FALSE)
# i.e. PVC-affecting recoveries are treated as NOTIONAL here — they reduce the
# PVC base W (via P6-H1, into technical_withheld) but NOT net payable. This is
# the documented interim choice; if field-account reconciliation shows net
# payable should net ALL recoveries, flip the filter. This is NOT certain to be
# the best model — revisit with a real submission before relying on it.
_NET_AMOUNT_EXPR = (
    "gross_amount - COALESCE("
    "(SELECT SUM(amount) FROM recoveries "
    "WHERE bill_id = running_bills.id AND affects_pvc_base = FALSE), 0) "
    "AS net_amount"
)


# Matches migration 003 `recovery_type` ENUM. The `affects_pvc_base` flag
# on the row drives whether the recovery reduces the PVC base (W): when TRUE,
# `build_bill_payload` sums it into the engine's `technical_withheld` bucket so
# it shows as a named W subtraction (P6-H1, approach A). Default False.
VALID_RECOVERY_TYPES = frozenset({
    "security_deposit", "income_tax", "labour_cess", "water", "other",
})


class BillCreate(BaseModel):
    # net_amount is intentionally absent: it is a derived value
    # (gross − non-PVC recoveries, C-3) the backend owns, never a client
    # input. ENGINEERING_GUIDELINES: the frontend must not supply financial
    # values the backend/engine derives.
    bill_number: int
    bill_date: date
    measurement_date: date
    gross_amount: Decimal


@router.post("/contracts/{contract_id}/bills", status_code=status.HTTP_201_CREATED)
async def create_bill(
    contract_id: str,
    body: BillCreate,
    user: AuthUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    # P6-H2: positivity is enforced at the boundary, not just in the UI — a
    # zero/negative gross would otherwise become BillPayload.on_account_amount
    # and feed a plausible-but-wrong PVC run.
    if body.bill_number <= 0:
        raise ValidationProblem(
            "bill_number must be a positive integer",
            field="bill_number",
            value=body.bill_number,
        )
    if body.gross_amount <= 0:
        raise ValidationProblem(
            "gross_amount must be greater than zero",
            field="gross_amount",
            value=str(body.gross_amount),
        )

    await assert_contract_belongs_to_tenant(session, contract_id, user.tenant_id)

    try:
        row = (
            await session.execute(
                text("""
                    INSERT INTO running_bills (
                        contract_id, bill_number, bill_date, measurement_date,
                        gross_amount, status
                    )
                    VALUES (:cid, :num, :bd, :md, :ga, 'Draft')
                    RETURNING id::text AS id, created_at
                """),
                {
                    "cid": contract_id,
                    "num": body.bill_number,
                    "bd": body.bill_date,
                    "md": body.measurement_date,
                    "ga": body.gross_amount,
                },
            )
        ).mappings().first()
    except IntegrityError as exc:
        # UNIQUE(contract_id, bill_number) in migration 003. Translate the
        # raw constraint violation into a structured 409 the UI can render.
        raise ConflictProblem(
            f"Bill number {body.bill_number} already exists for this contract",
            bill_number=body.bill_number,
        ) from exc

    assert row is not None
    return {"id": row["id"], **body.model_dump(mode="json")}


class BillUpdate(BaseModel):
    # C-3: partial header edit. Every field Optional; only keys present in the
    # request body (model_fields_set) are written, so an omitted field is left
    # untouched while an explicit null is a deliberate clear (rejected below on
    # NOT NULL columns). net_amount is absent — it is derived, never client-set.
    bill_number: int | None = None
    bill_date: date | None = None
    measurement_date: date | None = None
    gross_amount: Decimal | None = None


# NOT NULL columns on running_bills (migration 003) that this endpoint can
# touch — an explicit null for either is rejected with a structured 422.
_BILL_NOT_NULL_FIELDS = frozenset({"bill_number", "measurement_date"})


@router.put("/bills/{bill_id}")
async def update_bill(
    bill_id: str,
    body: BillUpdate,
    user: AuthUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    contract_id = await assert_bill_belongs_to_tenant(session, bill_id, user.tenant_id)

    fields = body.model_fields_set
    if not fields:
        return await _select_bill(session, bill_id)

    # Reject explicit-null on NOT NULL columns before value checks so the error
    # names the real problem (FieldNotNullableProblem) rather than a vague one.
    for f in fields:
        if f in _BILL_NOT_NULL_FIELDS and getattr(body, f) is None:
            raise FieldNotNullableProblem(f)

    # P6-H2 parity: positivity is a backend invariant, not just a UI guard.
    if "bill_number" in fields and body.bill_number <= 0:
        raise ValidationProblem(
            "bill_number must be a positive integer",
            field="bill_number",
            value=body.bill_number,
        )
    if "gross_amount" in fields:
        if body.gross_amount is None:
            raise ValidationProblem(
                "gross_amount cannot be cleared",
                field="gross_amount",
                value=None,
            )
        if body.gross_amount <= 0:
            raise ValidationProblem(
                "gross_amount must be greater than zero",
                field="gross_amount",
                value=str(body.gross_amount),
            )

    set_clause = ", ".join(f"{f} = :{f}" for f in fields)
    params: dict[str, Any] = {f: getattr(body, f) for f in fields}
    params["bid"] = bill_id

    try:
        await session.execute(
            text(f"UPDATE running_bills SET {set_clause} WHERE id = :bid"),
            params,
        )
    except IntegrityError as exc:
        # UNIQUE(contract_id, bill_number) — same 409 contract as create_bill.
        raise ConflictProblem(
            f"Bill number {body.bill_number} already exists for this contract",
            bill_number=body.bill_number,
        ) from exc

    # contract_id from the gate is unused for shaping (the SELECT re-projects
    # everything) but proves the row is the caller's before we touch it.
    del contract_id
    return await _select_bill(session, bill_id)


async def _select_bill(session: AsyncSession, bill_id: str) -> dict[str, Any]:
    """Re-project a single bill with the computed net_amount."""
    row = (
        await session.execute(
            text(f"""
                SELECT id::text AS id,
                       contract_id::text AS contract_id,
                       bill_number,
                       bill_date,
                       measurement_date,
                       gross_amount,
                       {_NET_AMOUNT_EXPR},
                       status::text AS status,
                       created_at
                FROM running_bills
                WHERE id = :bid
            """),
            {"bid": bill_id},
        )
    ).mappings().first()
    assert row is not None
    return dict(row)


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
    # P6-H2: a non-positive recovery is meaningless and (once H1 wires
    # affects_pvc_base into W) could inflate the PVC base. Block at the boundary.
    if body.amount <= 0:
        raise ValidationProblem(
            "amount must be greater than zero",
            field="amount",
            value=str(body.amount),
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


async def _assert_recovery_under_bill_for_tenant(
    session: AsyncSession,
    bill_id: str,
    recovery_id: str,
    tenant_id: str,
) -> None:
    """Two-step gate for nested recovery endpoints: (1) the bill must belong to
    the tenant, (2) the recovery must belong to that bill. Either failure
    collapses to a 404 so callers cannot probe foreign IDs (P3-06 discipline)."""
    await assert_bill_belongs_to_tenant(session, bill_id, tenant_id)
    row = (
        await session.execute(
            text("SELECT 1 FROM recoveries WHERE id = :rid AND bill_id = :bid"),
            {"rid": recovery_id, "bid": bill_id},
        )
    ).first()
    if row is None:
        raise NotFoundProblem("Recovery not found", entity="recovery", id=recovery_id)


@router.delete(
    "/bills/{bill_id}/recoveries/{recovery_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_recovery(
    bill_id: str,
    recovery_id: str,
    user: AuthUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    # No `-> None` annotation: with PEP 563 it resolves to NoneType and trips
    # the 204-no-body assertion on fastapi 0.115.x (same as delete_contract_item).
    await _assert_recovery_under_bill_for_tenant(
        session, bill_id, recovery_id, user.tenant_id
    )
    await session.execute(
        text("DELETE FROM recoveries WHERE id = :rid AND bill_id = :bid"),
        {"rid": recovery_id, "bid": bill_id},
    )


# ---------------------------------------------------------------------------
# SH-P5-1..4 — GET endpoints feeding the Phase 6 bill-entry UI.
#
# All four use the existing tenant-gate helpers (no new helpers needed).
# Empty list (not 404) is the contract for the *list* endpoints — the
# caller already proved they own the parent, so an empty child set is a
# legitimate state, not a missing entity.
# ---------------------------------------------------------------------------


@router.get("/contracts/{contract_id}/bills")
async def list_bills(
    contract_id: str,
    user: AuthUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[dict[str, Any]]:
    await assert_contract_belongs_to_tenant(session, contract_id, user.tenant_id)

    rows = (
        await session.execute(
            text(f"""
                SELECT id::text AS id,
                       contract_id::text AS contract_id,
                       bill_number,
                       bill_date,
                       measurement_date,
                       gross_amount,
                       {_NET_AMOUNT_EXPR},
                       status::text AS status,
                       created_at
                FROM running_bills
                WHERE contract_id = :cid
                ORDER BY bill_number
            """),
            {"cid": contract_id},
        )
    ).mappings().all()
    return [dict(r) for r in rows]


@router.get("/bills/{bill_id}")
async def get_bill(
    bill_id: str,
    user: AuthUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    # Gate already proves existence + tenant ownership; the follow-up SELECT
    # is for the field projection (incl. computed net_amount).
    await assert_bill_belongs_to_tenant(session, bill_id, user.tenant_id)
    return await _select_bill(session, bill_id)


@router.get("/bills/{bill_id}/lines")
async def list_bill_lines(
    bill_id: str,
    user: AuthUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[dict[str, Any]]:
    await assert_bill_belongs_to_tenant(session, bill_id, user.tenant_id)

    # bill_lines has no created_at column (migration 003); order by id for
    # deterministic output.
    rows = (
        await session.execute(
            text("""
                SELECT id::text AS id,
                       bill_id::text AS bill_id,
                       item_id::text AS item_id,
                       qty_up_to_last,
                       qty_since_last,
                       qty_up_to_date,
                       amount_up_to_last,
                       amount_since_last,
                       amount_up_to_date,
                       special_condition_amount
                FROM bill_lines
                WHERE bill_id = :bid
                ORDER BY id
            """),
            {"bid": bill_id},
        )
    ).mappings().all()
    return [dict(r) for r in rows]


@router.get("/bills/{bill_id}/recoveries")
async def list_recoveries(
    bill_id: str,
    user: AuthUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[dict[str, Any]]:
    await assert_bill_belongs_to_tenant(session, bill_id, user.tenant_id)

    rows = (
        await session.execute(
            text("""
                SELECT id::text AS id,
                       bill_id::text AS bill_id,
                       recovery_type::text AS recovery_type,
                       amount,
                       affects_pvc_base
                FROM recoveries
                WHERE bill_id = :bid
                ORDER BY id
            """),
            {"bid": bill_id},
        )
    ).mappings().all()
    return [dict(r) for r in rows]
