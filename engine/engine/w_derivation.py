"""P2-002/003/004/005: W derivation pipeline."""
from __future__ import annotations

from decimal import Decimal

from .types import BillPayload, CarryForwardPayload, WDerivation

# GCC 46A.9: four steel categories — TMT is SL1, angles SL2, plates SL3,
# other_sections SL4. Each is a separate W subtraction bucket.
_SUBTYPE_TO_BUCKET: dict[str, str] = {
    "angles":         "steel_angles",
    "plates":         "steel_plates",
    "other_sections": "steel_other",
    "tmt":            "steel_tmt",
}


def prorate_carry_forwards(
    carry_forwards: list[CarryForwardPayload],
) -> dict[str, Decimal]:
    """P2-005: prorated steel additions {bucket: amount} for this bill.

    `paid_ratio` is derived from `paid_qty_source / recorded_qty`; a zero paid
    quantity (and therefore a fully unpaid record) contributes nothing, while a
    fully paid record contributes the entire amount. Invariants are enforced
    on CarryForwardPayload itself, so we never see ratio < 0 or > 1 here.
    """
    additions: dict[str, Decimal] = {
        "steel_angles": Decimal("0"),
        "steel_plates": Decimal("0"),
        "steel_tmt":    Decimal("0"),
        "steel_other":  Decimal("0"),
    }
    for cf in carry_forwards:
        if cf.steel_subtype is not None:
            bucket = _SUBTYPE_TO_BUCKET[cf.steel_subtype]
            additions[bucket] += cf.amount * cf.paid_ratio
    return additions


def derive_w(bill: BillPayload) -> tuple[WDerivation, list[str]]:
    """
    P2-002/003/004/005: Derive W = OnAccount - Cement - Steel - TechWithheld - ExcludedExtraItems.
    P2-004: blocks if any extra_item_decision has eligible=None.
    P2-005: carry-forward steel amounts are prorated before subtraction.
    Returns (WDerivation, validation_errors); non-empty errors block the run.
    """
    errors: list[str] = []

    # P2-004: block on undecided extra items — never default include or exclude
    undecided = [d.item_id for d in bill.extra_item_decisions if d.eligible is None]
    if undecided:
        errors.append(f"undecided extra items block the run: {undecided}")
        return WDerivation(
            on_account_amount=bill.on_account_amount,
            cement=Decimal("0"),
            steel_angles=Decimal("0"),
            steel_plates=Decimal("0"),
            steel_tmt=Decimal("0"),
            steel_other=Decimal("0"),
            technical_withheld=Decimal("0"),
            extra_items=Decimal("0"),
            w=Decimal("0"),
        ), errors

    excluded_extra = sum(
        (d.amount for d in bill.extra_item_decisions if d.eligible is False),
        Decimal("0"),
    )

    # P2-005: prorate carry-forward steel amounts before adding to buckets
    carry_steel = prorate_carry_forwards(bill.carry_forwards)

    steel_angles = bill.steel_angles_amount + carry_steel["steel_angles"]
    steel_plates = bill.steel_plates_amount + carry_steel["steel_plates"]
    steel_tmt    = bill.steel_tmt_amount    + carry_steel["steel_tmt"]
    steel_other  = bill.steel_other_amount  + carry_steel["steel_other"]

    w = (
        bill.on_account_amount
        - bill.cement_amount
        - steel_angles
        - steel_plates
        - steel_tmt
        - steel_other
        - bill.technical_withheld
        - excluded_extra
    )

    return WDerivation(
        on_account_amount=bill.on_account_amount,
        cement=bill.cement_amount,
        steel_angles=steel_angles,
        steel_plates=steel_plates,
        steel_tmt=steel_tmt,
        steel_other=steel_other,
        technical_withheld=bill.technical_withheld,
        extra_items=excluded_extra,
        w=w,
    ), []
