"""P3-02 regression: missing extra-item decisions must reach the engine
as explicit `eligible=None` entries, so the engine blocks the run.

The reviewed implementation drove the payload from the `extra_item_decisions`
table and left-joined bill lines. Items present in the current bill but
absent from `extra_item_decisions` were silently dropped — the engine never
saw them, so its eligible=None guard never fired and the run produced a
plausible-but-wrong number.

These tests pin the inverted polarity: drive from the bill side, attach
decisions where they exist, pass through `None` everywhere else.
"""
from __future__ import annotations

from decimal import Decimal

import pytest

from engine import calculate_pvc
from engine.types import (
    BillPayload,
    IndexSnapshot,
    PVCRuleSet,
)
from services.pvc_service import ExtraItemInput, merge_extra_item_decisions


def _input(item_id: str, amount: str = "1000") -> ExtraItemInput:
    return ExtraItemInput(
        item_id=item_id,
        bill_line_id=f"bl-{item_id}",
        amount=Decimal(amount),
    )


def test_item_without_decision_row_becomes_explicit_undecided():
    bill_extras = [_input("item-A"), _input("item-B"), _input("item-C")]
    decisions = {"item-A": True, "item-C": False}  # item-B is undecided

    out = merge_extra_item_decisions(bill_extras, decisions)

    by_id = {d.item_id: d for d in out}
    assert by_id["item-A"].eligible is True
    assert by_id["item-B"].eligible is None, (
        "item present in current bill but missing from decisions must surface as None "
        "(blocks engine)"
    )
    assert by_id["item-C"].eligible is False


def test_source_ref_is_bill_line_id_for_trace_provenance():
    out = merge_extra_item_decisions([_input("item-X")], {})
    assert out[0].source_ref == "bl-item-X"


def test_no_silent_drop_even_when_decisions_dict_is_empty():
    out = merge_extra_item_decisions([_input("only-item")], {})
    assert len(out) == 1
    assert out[0].eligible is None


def _snapshot() -> IndexSnapshot:
    base = "2024-12"
    q = {"2025-04": Decimal("110"), "2025-05": Decimal("110"), "2025-06": Decimal("110")}
    series = {"labour": q, "plant": q, "fuel": q, "materials": q,
              "cement": q, "steel_tmt": q, "steel_angles": q, "steel_plates": q}
    for s in series.values():
        s["2024-12"] = Decimal("100")
    from datetime import date
    return IndexSnapshot(base_month=date(2024, 12, 1), series=series)


def _rules() -> PVCRuleSet:
    return PVCRuleSet(
        quarter_mode="measurement_date",
        component_weights={
            "labour": Decimal("0.20"), "plant": Decimal("0.30"),
            "fuel": Decimal("0.15"), "materials": Decimal("0.20"),
        },
        adjustable_fraction=Decimal("0.85"),
        negative_pvc_policy="zero_floor",
        rounding_mode="round_2",
    )


def test_end_to_end_undecided_item_blocks_engine_run():
    """Integration check: the merge function feeds the engine, and the engine
    refuses to compute when any decision is None. This is the contract the
    P3-02 fix is preserving."""
    from datetime import date

    extras = merge_extra_item_decisions(
        [_input("item-undecided", "5000")],
        decisions={},  # no decision row exists
    )
    bill = BillPayload(
        on_account_amount=Decimal("10000"),
        cement_amount=Decimal("0"),
        steel_angles_amount=Decimal("0"),
        steel_plates_amount=Decimal("0"),
        steel_tmt_amount=Decimal("0"),
        steel_other_amount=Decimal("0"),
        technical_withheld=Decimal("0"),
        extra_item_decisions=extras,
        carry_forwards=[],
        measurement_date=date(2025, 5, 15),
    )
    result = calculate_pvc(bill, _snapshot(), _rules())
    assert result.validation_errors, "engine must block when any extra item is undecided"
    assert result.total_pvc is None
