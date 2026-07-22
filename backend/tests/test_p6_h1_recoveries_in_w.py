"""P6-H1-FUP-C: affects_pvc_base recoveries must reduce the PVC base (W)
through a dedicated `recoveries_affecting_pvc` bucket, distinct from genuine
technical withholding.

DECISION (2026-06-04, Saqlain; superseded 2026-07-02): interim approach A
summed these recoveries into the engine's `technical_withheld` bucket. The
agreed end-state, approach C, is implemented here: a dedicated
`recoveries_affecting_pvc` field on `BillPayload` keeps the subtraction NAMED
in `w_derivation` (PRODUCT.md rule 1) while disaggregating it from genuine
technical withholding (sourced from `bill_lines.special_condition_amount`).
`on_account_amount` stays at the bill's gross — the deduction is NOT silently
netted off on_account (that would be approach B, rejected for auditability).

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


def _session(
    recovery_withheld: Decimal,
    technical_withheld: Decimal = Decimal("0"),
) -> AsyncMock:
    """Stub the six execute() calls build_bill_payload makes, in order:
    bill, W-buckets, extra-item inputs, decisions, carry-forwards, recoveries."""
    session = AsyncMock()
    session.execute = AsyncMock(
        side_effect=[
            _result(first={"measurement_date": date(2026, 1, 31), "gross_amount": Decimal("100000")}),
            _result(first={
                "cement": 0,
                "steel_angles": 0,
                "steel_plates": 0,
                "steel_tmt": 0,
                "steel_other": 0,
                "technical_withheld": technical_withheld,
            }),
            _result(rows=[]),   # extra_inputs
            _result(rows=[]),   # decision_rows
            _result(rows=[]),   # cf_rows
            _result(first={"withheld": recovery_withheld}),  # recoveries (affects_pvc_base=TRUE sum)
        ]
    )
    return session


@pytest.mark.asyncio
async def test_affects_pvc_base_recoveries_feed_recoveries_affecting_pvc():
    # One affects_pvc_base=TRUE recovery of 10000 on a 100000 gross bill.
    payload = await build_bill_payload(
        _session(Decimal("10000")), bill_id="bill-1", contract_id="contract-1"
    )
    # Approach C: recovery lands in the dedicated recoveries_affecting_pvc bucket…
    assert payload.recoveries_affecting_pvc == Decimal("10000")
    # …and no bill-line technical withholding remains zero…
    assert payload.technical_withheld == Decimal("0")
    # …and on_account is NOT netted — it stays at the bill's gross.
    assert payload.on_account_amount == Decimal("100000")


@pytest.mark.asyncio
async def test_no_affecting_recoveries_keeps_bucket_zero():
    # SQL filters affects_pvc_base=TRUE, so a bill with none sums to 0.
    payload = await build_bill_payload(
        _session(Decimal("0")), bill_id="bill-1", contract_id="contract-1"
    )
    assert payload.recoveries_affecting_pvc == Decimal("0")
    assert payload.technical_withheld == Decimal("0")
    assert payload.on_account_amount == Decimal("100000")


@pytest.mark.asyncio
async def test_bill_line_special_condition_amount_feeds_technical_withholding():
    payload = await build_bill_payload(
        _session(Decimal("0"), technical_withheld=Decimal("1249")),
        bill_id="bill-1",
        contract_id="contract-1",
    )

    assert payload.technical_withheld == Decimal("1249")
    assert payload.recoveries_affecting_pvc == Decimal("0")
    assert payload.on_account_amount == Decimal("100000")


@pytest.mark.asyncio
async def test_bill_line_special_condition_amount_preserves_sign():
    payload = await build_bill_payload(
        _session(Decimal("0"), technical_withheld=Decimal("-1249")),
        bill_id="bill-1",
        contract_id="contract-1",
    )

    assert payload.technical_withheld == Decimal("-1249")
