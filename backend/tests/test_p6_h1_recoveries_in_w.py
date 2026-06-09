"""P6-H1: affects_pvc_base recoveries must reduce the PVC base (W).

DECISION (2026-06-04, Saqlain): interim approach **A** — sum recoveries where
`affects_pvc_base = TRUE` into the engine's existing `technical_withheld`
bucket. This keeps the subtraction NAMED in `w_derivation` (PRODUCT.md rule 1)
with no engine-model change. `on_account_amount` stays at the bill's gross —
the deduction is NOT silently netted off on_account (that would be approach B,
rejected for auditability). Approach **C** (a dedicated `RecoveriesAffectingPVC`
W bucket, distinct from technical withholding) is the agreed end-state and is
tracked as a follow-up; A is explicitly an interim, not the best long-term shape.

The route SQL is Postgres-specific, so we stub `session.execute` at the
boundary and assert the payload `build_bill_payload` constructs — same pattern
as the bills/recoveries route tests.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from services.pvc_service import build_bill_payload


def _result(*, first=None, rows=None):
    """A Result-shaped stub whose `.mappings()` supports `.first()`, `.all()`,
    and iteration — covering every call shape in build_bill_payload."""
    rows = rows or []
    mappings = MagicMock()
    mappings.first.return_value = first if first is not None else (rows[0] if rows else None)
    mappings.all.return_value = rows
    mappings.__iter__.return_value = iter(rows)
    result = MagicMock()
    result.mappings.return_value = mappings
    return result


def _session(withheld: Decimal) -> AsyncMock:
    """Stub the six execute() calls build_bill_payload makes, in order:
    bill, W-buckets, extra-item inputs, decisions, carry-forwards, recoveries."""
    session = AsyncMock()
    session.execute = AsyncMock(
        side_effect=[
            _result(first={"measurement_date": date(2026, 1, 31), "gross_amount": Decimal("100000")}),
            _result(first={"cement": 0, "steel_angles": 0, "steel_plates": 0, "steel_tmt": 0, "steel_other": 0}),
            _result(rows=[]),   # extra_inputs
            _result(rows=[]),   # decision_rows
            _result(rows=[]),   # cf_rows
            _result(first={"withheld": withheld}),  # recoveries (affects_pvc_base=TRUE sum)
        ]
    )
    return session


@pytest.mark.asyncio
async def test_affects_pvc_base_recoveries_feed_technical_withheld():
    # One affects_pvc_base=TRUE recovery of 10000 on a 100000 gross bill.
    payload = await build_bill_payload(
        _session(Decimal("10000")), bill_id="bill-1", contract_id="contract-1"
    )
    # Approach A: recovery lands in the named technical_withheld bucket…
    assert payload.technical_withheld == Decimal("10000")
    # …and on_account is NOT netted — it stays at the bill's gross.
    assert payload.on_account_amount == Decimal("100000")


@pytest.mark.asyncio
async def test_no_affecting_recoveries_keeps_withheld_zero():
    # SQL filters affects_pvc_base=TRUE, so a bill with none sums to 0.
    payload = await build_bill_payload(
        _session(Decimal("0")), bill_id="bill-1", contract_id="contract-1"
    )
    assert payload.technical_withheld == Decimal("0")
    assert payload.on_account_amount == Decimal("100000")
