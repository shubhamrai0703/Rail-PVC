"""P2-013: Hypothesis property tests — W derivation invariants."""
from decimal import Decimal
from datetime import date

from hypothesis import given, settings
from hypothesis import strategies as st

from engine.types import BillPayload, ExtraItemDecision
from engine.w_derivation import derive_w

_POS_DEC = st.decimals(min_value=Decimal("0"), max_value=Decimal("10000000"), allow_nan=False, allow_infinity=False).map(lambda x: x.quantize(Decimal("0.01")))
_SMALL_DEC = st.decimals(min_value=Decimal("0"), max_value=Decimal("1000000"), allow_nan=False, allow_infinity=False).map(lambda x: x.quantize(Decimal("0.01")))


def _make_bill(
    on_account: Decimal,
    cement: Decimal,
    angles: Decimal,
    plates: Decimal,
    steel_other: Decimal,
    tech_withheld: Decimal,
    excluded_extra: Decimal,
) -> BillPayload:
    return BillPayload(
        on_account_amount=on_account,
        cement_amount=cement,
        steel_angles_amount=angles,
        steel_plates_amount=plates,
        steel_other_amount=steel_other,
        technical_withheld=tech_withheld,
        extra_item_decisions=[
            ExtraItemDecision(item_id="E1", amount=excluded_extra, eligible=False)
        ] if excluded_extra > Decimal("0") else [],
        carry_forwards=[],
        measurement_date=date(2025, 6, 18),
    )


@given(
    on_account=_POS_DEC,
    cement=_SMALL_DEC,
    angles=_SMALL_DEC,
    plates=_SMALL_DEC,
    steel_other=_SMALL_DEC,
    tech_withheld=_SMALL_DEC,
    excluded_extra=_SMALL_DEC,
)
@settings(max_examples=200)
def test_sum_identity(on_account, cement, angles, plates, steel_other, tech_withheld, excluded_extra):
    """W + all deductions == on_account_amount (no loss of money)."""
    bill = _make_bill(on_account, cement, angles, plates, steel_other, tech_withheld, excluded_extra)
    d, errs = derive_w(bill)
    assert errs == []
    total = d.w + d.cement + d.steel_angles + d.steel_plates + d.steel_other + d.technical_withheld + d.extra_items
    assert total == on_account


@given(
    on_account=_POS_DEC,
    cement=_SMALL_DEC,
    angles=_SMALL_DEC,
    plates=_SMALL_DEC,
    steel_other=_SMALL_DEC,
    tech_withheld=_SMALL_DEC,
)
@settings(max_examples=200)
def test_w_at_most_on_account(on_account, cement, angles, plates, steel_other, tech_withheld):
    """W ≤ on_account_amount when all deductions are non-negative."""
    bill = _make_bill(on_account, cement, angles, plates, steel_other, tech_withheld, Decimal("0"))
    d, errs = derive_w(bill)
    assert errs == []
    assert d.w <= on_account


@given(
    on_account=_POS_DEC,
    cement=_SMALL_DEC,
    angles=_SMALL_DEC,
    plates=_SMALL_DEC,
    steel_other=_SMALL_DEC,
    tech_withheld=_SMALL_DEC,
)
@settings(max_examples=200)
def test_w_derivation_is_deterministic(on_account, cement, angles, plates, steel_other, tech_withheld):
    """Same inputs always produce the same W."""
    bill = _make_bill(on_account, cement, angles, plates, steel_other, tech_withheld, Decimal("0"))
    d1, _ = derive_w(bill)
    d2, _ = derive_w(bill)
    assert d1.w == d2.w


@given(extra=_SMALL_DEC)
@settings(max_examples=100)
def test_undecided_item_always_blocks(extra):
    """Any bill with an undecided extra item must return a validation error."""
    bill = BillPayload(
        on_account_amount=Decimal("1000000"),
        cement_amount=Decimal("0"),
        steel_angles_amount=Decimal("0"),
        steel_plates_amount=Decimal("0"),
        steel_other_amount=Decimal("0"),
        technical_withheld=Decimal("0"),
        extra_item_decisions=[ExtraItemDecision(item_id="X", amount=extra, eligible=None)],
        carry_forwards=[],
        measurement_date=date(2025, 6, 18),
    )
    _, errs = derive_w(bill)
    assert len(errs) >= 1
