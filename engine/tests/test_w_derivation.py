"""Unit tests for W derivation — P2-002, P2-003, P2-004, P2-005."""
from decimal import Decimal
from datetime import date

from engine.types import BillPayload, CarryForwardPayload, ExtraItemDecision
from engine.w_derivation import derive_w, prorate_carry_forwards


def _bill(
    on_account: str = "0",
    cement: str = "0",
    angles: str = "0",
    plates: str = "0",
    steel_other: str = "0",
    tech_withheld: str = "0",
    extra_decisions: list[ExtraItemDecision] | None = None,
    carry_forwards: list[CarryForwardPayload] | None = None,
) -> BillPayload:
    return BillPayload(
        on_account_amount=Decimal(on_account),
        cement_amount=Decimal(cement),
        steel_angles_amount=Decimal(angles),
        steel_plates_amount=Decimal(plates),
        steel_other_amount=Decimal(steel_other),
        technical_withheld=Decimal(tech_withheld),
        extra_item_decisions=extra_decisions or [],
        carry_forwards=carry_forwards or [],
        measurement_date=date(2025, 6, 18),
    )


def _cf(
    item_id: str,
    recorded_qty: str,
    paid_qty: str,
    paid_ratio: str,
    carry_qty: str,
    amount: str,
    subtype: str | None = None,
) -> CarryForwardPayload:
    return CarryForwardPayload(
        item_id=item_id,
        recorded_qty=Decimal(recorded_qty),
        paid_qty_source=Decimal(paid_qty),
        paid_ratio=Decimal(paid_ratio),
        carry_qty=Decimal(carry_qty),
        amount=Decimal(amount),
        steel_subtype=subtype,
    )


# ---------------------------------------------------------------------------
# P2-002: cement subtraction
# ---------------------------------------------------------------------------

class TestCementSubtraction:
    def test_zero_cement_leaves_w_unchanged(self):
        d, errs = derive_w(_bill(on_account="1000000"))
        assert errs == []
        assert d.w == Decimal("1000000")
        assert d.cement == Decimal("0")

    def test_cement_reduces_w_exactly(self):
        d, errs = derive_w(_bill(on_account="1000000", cement="150000"))
        assert errs == []
        assert d.w == Decimal("850000")

    def test_cement_equals_on_account_gives_zero_w(self):
        d, errs = derive_w(_bill(on_account="500000", cement="500000"))
        assert errs == []
        assert d.w == Decimal("0")


# ---------------------------------------------------------------------------
# P2-003: steel bucket subtraction
# ---------------------------------------------------------------------------

class TestSteelSubtraction:
    def test_angles_only(self):
        d, errs = derive_w(_bill(on_account="2000000", angles="300000"))
        assert errs == []
        assert d.w == Decimal("1700000")
        assert d.steel_angles == Decimal("300000")

    def test_plates_only(self):
        d, errs = derive_w(_bill(on_account="2000000", plates="200000"))
        assert errs == []
        assert d.w == Decimal("1800000")

    def test_steel_other_only(self):
        d, errs = derive_w(_bill(on_account="2000000", steel_other="100000"))
        assert errs == []
        assert d.w == Decimal("1900000")

    def test_all_three_steel_buckets(self):
        d, errs = derive_w(_bill(
            on_account="5000000",
            angles="300000",
            plates="200000",
            steel_other="100000",
        ))
        assert errs == []
        assert d.w == Decimal("4400000")

    def test_subtypes_are_independent(self):
        d_a, _ = derive_w(_bill(on_account="1000000", angles="100000"))
        d_p, _ = derive_w(_bill(on_account="1000000", plates="100000"))
        assert d_a.steel_angles == Decimal("100000")
        assert d_a.steel_plates == Decimal("0")
        assert d_p.steel_plates == Decimal("100000")
        assert d_p.steel_angles == Decimal("0")

    def test_all_deductions_combined(self):
        d, errs = derive_w(_bill(
            on_account="10000000",
            cement="500000",
            angles="300000",
            plates="200000",
            steel_other="100000",
            tech_withheld="50000",
            extra_decisions=[ExtraItemDecision(item_id="X1", amount=Decimal("75000"), eligible=False)],
        ))
        assert errs == []
        assert d.w == Decimal("8775000")


# ---------------------------------------------------------------------------
# P2-004: extra-item exclusion
# ---------------------------------------------------------------------------

class TestExtraItemExclusion:
    def test_undecided_item_blocks_run(self):
        decisions = [ExtraItemDecision(item_id="E1", amount=Decimal("100000"), eligible=None)]
        d, errs = derive_w(_bill(on_account="1000000", extra_decisions=decisions))
        assert len(errs) == 1
        assert "E1" in errs[0]
        assert "undecided" in errs[0].lower()

    def test_multiple_undecided_items_reported_together(self):
        decisions = [
            ExtraItemDecision(item_id="E1", amount=Decimal("50000"), eligible=None),
            ExtraItemDecision(item_id="E2", amount=Decimal("60000"), eligible=None),
        ]
        d, errs = derive_w(_bill(on_account="1000000", extra_decisions=decisions))
        assert len(errs) == 1
        assert "E1" in errs[0] and "E2" in errs[0]

    def test_eligible_false_item_subtracted_from_w(self):
        decisions = [ExtraItemDecision(item_id="E1", amount=Decimal("1600000"), eligible=False)]
        d, errs = derive_w(_bill(on_account="10000000", extra_decisions=decisions))
        assert errs == []
        assert d.extra_items == Decimal("1600000")
        assert d.w == Decimal("8400000")

    def test_eligible_true_item_not_subtracted(self):
        decisions = [ExtraItemDecision(item_id="E1", amount=Decimal("500000"), eligible=True)]
        d, errs = derive_w(_bill(on_account="1000000", extra_decisions=decisions))
        assert errs == []
        assert d.extra_items == Decimal("0")
        assert d.w == Decimal("1000000")

    def test_mixed_decisions_only_ineligible_subtracted(self):
        decisions = [
            ExtraItemDecision(item_id="E1", amount=Decimal("200000"), eligible=True),
            ExtraItemDecision(item_id="E2", amount=Decimal("300000"), eligible=False),
        ]
        d, errs = derive_w(_bill(on_account="1000000", extra_decisions=decisions))
        assert errs == []
        assert d.extra_items == Decimal("300000")
        assert d.w == Decimal("700000")

    def test_undecided_blocks_even_if_others_decided(self):
        decisions = [
            ExtraItemDecision(item_id="E1", amount=Decimal("100000"), eligible=True),
            ExtraItemDecision(item_id="E2", amount=Decimal("200000"), eligible=None),
        ]
        d, errs = derive_w(_bill(on_account="1000000", extra_decisions=decisions))
        assert len(errs) == 1
        assert "E2" in errs[0]

    def test_empty_decisions_no_extra_subtraction(self):
        d, errs = derive_w(_bill(on_account="1000000"))
        assert errs == []
        assert d.extra_items == Decimal("0")
        assert d.w == Decimal("1000000")


# ---------------------------------------------------------------------------
# P2-005: carry-forward proration
# ---------------------------------------------------------------------------

class TestCarryForwardProration:
    def test_bct_2425_252_item_10_2_ratio(self):
        """BCT-24-25-252 sample: recorded 6172.57, paid 5600, ratio 0.9072."""
        cf = _cf("10.2", "6172.57", "5600", "0.9072", "572.57", "100000", subtype="angles")
        additions = prorate_carry_forwards([cf])
        assert additions["steel_angles"] == Decimal("100000") * Decimal("0.9072")
        assert additions["steel_plates"] == Decimal("0")
        assert additions["steel_other"] == Decimal("0")

    def test_tmt_maps_to_steel_other_bucket(self):
        cf = _cf("1", "100", "90", "0.9", "10", "50000", subtype="tmt")
        additions = prorate_carry_forwards([cf])
        assert additions["steel_other"] == Decimal("50000") * Decimal("0.9")
        assert additions["steel_angles"] == Decimal("0")

    def test_no_steel_subtype_does_not_affect_buckets(self):
        cf = _cf("2", "100", "80", "0.8", "20", "40000", subtype=None)
        additions = prorate_carry_forwards([cf])
        assert all(v == Decimal("0") for v in additions.values())

    def test_multiple_carry_forwards_accumulate(self):
        cfs = [
            _cf("A", "100", "80", "0.8", "20", "10000", subtype="angles"),
            _cf("B", "200", "160", "0.8", "40", "20000", subtype="angles"),
        ]
        additions = prorate_carry_forwards(cfs)
        assert additions["steel_angles"] == Decimal("24000")

    def test_carry_forward_steel_added_before_w(self):
        cf = _cf("10.2", "6172.57", "5600", "0.9072", "572.57", "100000", subtype="angles")
        bill = _bill(on_account="1000000", angles="50000", carry_forwards=[cf])
        d, errs = derive_w(bill)
        assert errs == []
        expected_angles = Decimal("50000") + Decimal("100000") * Decimal("0.9072")
        assert d.steel_angles == expected_angles
        assert d.w == Decimal("1000000") - expected_angles

    def test_zero_paid_ratio_contributes_nothing(self):
        bill_no_cf = _bill(on_account="1000000", angles="100000")
        bill_with_cf = _bill(
            on_account="1000000",
            angles="100000",
            carry_forwards=[_cf("x", "100", "0", "0", "100", "50000", subtype="angles")],
        )
        d_no_cf, _ = derive_w(bill_no_cf)
        d_with_cf, _ = derive_w(bill_with_cf)
        assert d_with_cf.w == d_no_cf.w

    def test_sum_identity(self):
        """W + all deductions == on_account_amount."""
        d, _ = derive_w(_bill(
            on_account="8903877.99",
            cement="300000",
            angles="200000",
            plates="150000",
            steel_other="80000",
            tech_withheld="100000",
            extra_decisions=[ExtraItemDecision(item_id="E1", amount=Decimal("50000"), eligible=False)],
        ))
        total = (
            d.w + d.cement + d.steel_angles + d.steel_plates
            + d.steel_other + d.technical_withheld + d.extra_items
        )
        assert total == Decimal("8903877.99")
