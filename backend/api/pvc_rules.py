"""PVC rule set GET/PUT. The default rule set is seeded by contract
creation (P3-07) so GET always succeeds for a valid contract."""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, field_validator
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from engine.types import REQUIRED_GENERAL_WEIGHTS  # parity with engine validator
from services.auth import AuthUser, get_current_user
from services.db import get_session
from services.errors import NotFoundProblem, ValidationProblem

router = APIRouter(prefix="/api", tags=["pvc_rules"])


class RuleSetUpdate(BaseModel):
    component_weights: dict[str, Decimal]
    adjustable_fraction: Decimal
    rounding_mode: str
    negative_pvc_policy: str

    @field_validator("component_weights")
    @classmethod
    def _weights_parity_with_engine(cls, v: dict[str, Decimal]) -> dict[str, Decimal]:
        keys = set(v)
        missing = REQUIRED_GENERAL_WEIGHTS - keys
        unknown = keys - REQUIRED_GENERAL_WEIGHTS
        if missing or unknown:
            raise ValueError(
                f"component_weights must contain exactly {sorted(REQUIRED_GENERAL_WEIGHTS)}"
                f" (missing={sorted(missing)}, unknown={sorted(unknown)})"
            )
        return v


@router.get("/contracts/{contract_id}/pvc-rule-set")
async def get_rule_set(
    contract_id: str,
    user: AuthUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    row = (
        await session.execute(
            text("""
                SELECT rs.id::text AS id, rs.version, rs.quarter_mode::text AS quarter_mode,
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
    if row is None:
        raise NotFoundProblem(
            "Rule set not found — contract not visible or never bootstrapped",
            entity="pvc_rule_set",
            contract_id=contract_id,
        )
    return dict(row)


@router.put("/contracts/{contract_id}/pvc-rule-set")
async def update_rule_set(
    contract_id: str,
    body: RuleSetUpdate,
    user: AuthUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    owns = (
        await session.execute(
            text("SELECT 1 FROM contracts WHERE id = :id AND tenant_id = :tid"),
            {"id": contract_id, "tid": user.tenant_id},
        )
    ).first()
    if owns is None:
        raise NotFoundProblem("Contract not found", entity="contract", id=contract_id)

    # Refuse to overwrite a rule set referenced by an Approved run (audit trail
    # for P3-REVIEW item 17). Creating a new versioned rule set instead is the
    # post-MVP enhancement; this is the MVP guardrail.
    locked = (
        await session.execute(
            text("""
                SELECT 1 FROM pvc_runs r
                JOIN pvc_rule_sets rs ON rs.id = r.rule_set_id
                WHERE rs.contract_id = :cid AND r.status = 'Approved'
                LIMIT 1
            """),
            {"cid": contract_id},
        )
    ).first()
    if locked is not None:
        raise ValidationProblem(
            "Rule set is referenced by an Approved PVC run and cannot be modified",
            contract_id=contract_id,
        )

    import json
    row = (
        await session.execute(
            text("""
                UPDATE pvc_rule_sets
                SET component_weights = CAST(:cw AS JSONB),
                    adjustable_fraction = :af,
                    rounding_mode = :rm,
                    negative_pvc_policy = :np
                WHERE contract_id = :cid
                RETURNING id::text AS id, version
            """),
            {
                "cid": contract_id,
                "cw": json.dumps({k: str(v) for k, v in body.component_weights.items()}),
                "af": body.adjustable_fraction,
                "rm": body.rounding_mode,
                "np": body.negative_pvc_policy,
            },
        )
    ).mappings().first()
    if row is None:
        raise NotFoundProblem("Rule set not found", entity="pvc_rule_set", contract_id=contract_id)
    return dict(row)
