"""P2-012: Integration tests — calculate_pvc end-to-end."""
from decimal import Decimal
from datetime import date

from engine import calculate_pvc
from engine.types import (
    BillPayload,
    CarryForwardPayload,
    ExtraItemDecision,
    IndexSnapshot,
    PVCRuleSet,
)

_BASE = date(2024, 12, 1)
_BASE_INDICES = {
    "labour":               Decimal("143.7"),
    "plant_machinery":      Decimal("160.0"),
    "fuel":                 Decimal("160.48"),
    "other_materials":      Decimal("155.7"),
    "cement":               Decimal("130.2"),
    "steel_angles":         Decimal("58000.0"),
    "steel_plates":         Decimal("57370.0"),
    "steel_other_sections": Decimal("57727.5"),
    "steel_tmt":            Decimal("57812.5"),
}
_Q2_MONTHS = ["2025-04", "2025-05", "2025-06"]
_Q2_AVGS = {
    "labour":               Decimal("144.167"),
    "plant_machinery":      Decimal("161.5"),
    "fuel":                 Decimal("157.0"),
    "other_materials":      Decimal("156.0"),
    "cement":               Decimal("129.5"),
    "steel_angles":         Decimal("57500.0"),
    "steel_plates":         Decimal("57000.0"),
    "steel_other_sections": Decimal("57200.0"),
    "steel_tmt":            Decimal("57000.0"),
}


def _full_snapshot(months: list[str], avgs: dict[str, Decimal]) -> IndexSnapshot:
    series: dict[str, dict[str, Decimal]] = {}
    for s, base_val in _BASE_INDICES.items():
        series[s] = {"2024-12": base_val}
        for m in months:
            series[s][m] = avgs[s]
    return IndexSnapshot(base_month=_BASE, series=series)


def _standard_rules(**overrides) -> PVCRuleSet:
    return PVCRuleSet(
        quarter_mode="measurement_date",
        component_weights={
            "labour":    Decimal("0.20"),
            "plant":     Decimal("0.30"),
            "fuel":      Decimal("0.15"),
            "materials": Decimal("0.20"),
        },
        adjustable_fraction=Decimal("0.85"),
        negative_pvc_policy=overrides.get("negative_pvc_policy", "zero_floor"),
        rounding_mode=overrides.get("rounding_mode", "round_2"),
    )


def _bill(
    on_account: str = "0",
    cement: str = "0",
    angles: str = "0",
    plates: str = "0",
    tmt: str = "0",
    steel_other: str = "0",
    tech_withheld: str = "0",
    extra_decisions: list[ExtraItemDecision] | None = None,
    carry_forwards: list[CarryForwardPayload] | None = None,
    measurement_date: date = date(2025, 6, 18),
    prior_negative: str = "0",
) -> BillPayload:
    return BillPayload(
        on_account_amount=Decimal(on_account),
        cement_amount=Decimal(cement),
        steel_angles_amount=Decimal(angles),
        steel_plates_amount=Decimal(plates),
        steel_tmt_amount=Decimal(tmt),
        steel_other_amount=Decimal(steel_other),
        technical_withheld=Decimal(tech_withheld),
        extra_item_decisions=extra_decisions or [],
        carry_forwards=carry_forwards or [],
        measurement_date=measurement_date,
        prior_negative_carry_forward=Decimal(prior_negative),
    )


# ---------------------------------------------------------------------------
# Validation blocking
# ---------------------------------------------------------------------------

class TestValidationBlocking:
    def test_undecided_extra_item_blocks_run(self):
        snap = _full_snapshot(_Q2_MONTHS, _Q2_AVGS)
        bill = _bill(
            on_account="8903877.99",
            extra_decisions=[ExtraItemDecision(item_id="NS1", amount=Decimal("100000"), eligible=None)],
        )
        result = calculate_pvc(bill, snap, _standard_rules())
        assert len(result.validation_errors) > 0
        assert result.total_pvc is None
        assert result.w is None

    def test_missing_index_blocks_run(self):
        snap = IndexSnapshot(base_month=_BASE, series={})
        bill = _bill(on_account="8903877.99")
        result = calculate_pvc(bill, snap, _standard_rules())
        assert len(result.validation_errors) > 0
        assert result.total_pvc is None

    def test_partial_index_blocks_run(self):
        # Only base month present, no quarter months
        snap = IndexSnapshot(
            base_month=_BASE,
            series={"labour": {"2024-12": _BASE_INDICES["labour"]}},
        )
        bill = _bill(on_account="8903877.99")
        result = calculate_pvc(bill, snap, _standard_rules())
        assert result.total_pvc is None

    def test_empty_bill_no_components_still_runs(self):
        """All-zero bill with complete indices should run without errors."""
        snap = _full_snapshot(_Q2_MONTHS, _Q2_AVGS)
        bill = _bill(on_account="1000000")
        result = calculate_pvc(bill, snap, _standard_rules())
        assert result.validation_errors == []
        assert result.total_pvc is not None


# ---------------------------------------------------------------------------
# Quarter assignment
# ---------------------------------------------------------------------------

class TestQuarterAssignment:
    def test_bill1_measurement_date_assigns_q2_fy2025_26(self):
        snap = _full_snapshot(_Q2_MONTHS, _Q2_AVGS)
        bill = _bill(on_account="8903877.99", measurement_date=date(2025, 6, 18))
        result = calculate_pvc(bill, snap, _standard_rules())
        assert result.quarter_used == "Q2-FY2025-26"
        assert result.quarter_months == ["2025-04", "2025-05", "2025-06"]

    def test_quarter_stored_even_when_validation_fails(self):
        """Quarter is resolved before validation; stored even on blocked runs."""
        snap = IndexSnapshot(base_month=_BASE, series={})
        bill = _bill(on_account="1000000", measurement_date=date(2025, 11, 4))
        result = calculate_pvc(bill, snap, _standard_rules())
        assert result.quarter_used == "Q4-FY2025-26"


# ---------------------------------------------------------------------------
# Negative PVC policies (P2-007 / KU-003)
# ---------------------------------------------------------------------------

class TestNegativePVCPolicy:
    def _falling_index_snapshot(self) -> IndexSnapshot:
        falling = {k: v - Decimal("10") for k, v in _Q2_AVGS.items()}
        return _full_snapshot(_Q2_MONTHS, falling)

    def test_zero_floor_sets_total_to_zero(self):
        snap = self._falling_index_snapshot()
        bill = _bill(on_account="1000000")
        result = calculate_pvc(bill, snap, _standard_rules(negative_pvc_policy="zero_floor"))
        assert result.validation_errors == []
        assert result.total_pvc == Decimal("0.00")
        assert result.negative_carry_forward > Decimal("0")

    def test_zero_floor_carry_forward_equals_absolute_raw_pvc(self):
        snap = self._falling_index_snapshot()
        bill = _bill(on_account="1000000")
        result_allow = calculate_pvc(bill, snap, _standard_rules(negative_pvc_policy="allow"))
        result_floor = calculate_pvc(bill, snap, _standard_rules(negative_pvc_policy="zero_floor"))
        assert result_floor.negative_carry_forward == abs(result_allow.total_pvc)

    def test_allow_policy_returns_negative_total(self):
        snap = self._falling_index_snapshot()
        bill = _bill(on_account="1000000")
        result = calculate_pvc(bill, snap, _standard_rules(negative_pvc_policy="allow"))
        assert result.total_pvc < Decimal("0")
        assert result.negative_carry_forward == Decimal("0")

    def test_block_policy_blocks_run(self):
        snap = self._falling_index_snapshot()
        bill = _bill(on_account="1000000")
        result = calculate_pvc(bill, snap, _standard_rules(negative_pvc_policy="block"))
        assert len(result.validation_errors) > 0
        assert result.total_pvc is None

    def test_prior_negative_carry_forward_deducted(self):
        snap = _full_snapshot(_Q2_MONTHS, _Q2_AVGS)
        bill_no_prior = _bill(on_account="1000000")
        bill_with_prior = _bill(on_account="1000000", prior_negative="50000")
        r_no = calculate_pvc(bill_no_prior, snap, _standard_rules(negative_pvc_policy="allow"))
        r_with = calculate_pvc(bill_with_prior, snap, _standard_rules(negative_pvc_policy="allow"))
        assert r_with.total_pvc == r_no.total_pvc - Decimal("50000")

    def test_positive_pvc_has_zero_negative_carry_forward(self):
        snap = _full_snapshot(_Q2_MONTHS, _Q2_AVGS)
        bill = _bill(on_account="1000000")
        result = calculate_pvc(bill, snap, _standard_rules())
        if result.total_pvc is not None and result.total_pvc >= Decimal("0"):
            assert result.negative_carry_forward == Decimal("0")


# ---------------------------------------------------------------------------
# Rounding modes
# ---------------------------------------------------------------------------

class TestRounding:
    def test_round_2_rounds_to_nearest_cent(self):
        snap = _full_snapshot(_Q2_MONTHS, _Q2_AVGS)
        bill = _bill(on_account="1000000")
        result = calculate_pvc(bill, snap, _standard_rules(rounding_mode="round_2"))
        assert result.validation_errors == []
        if result.total_pvc is not None:
            # Should have at most 2 decimal places
            assert result.total_pvc == result.total_pvc.quantize(Decimal("0.01"))

    def test_truncate_2_truncates(self):
        snap = _full_snapshot(_Q2_MONTHS, _Q2_AVGS)
        bill = _bill(on_account="1000000")
        result = calculate_pvc(bill, snap, _standard_rules(rounding_mode="truncate_2"))
        assert result.validation_errors == []


# ---------------------------------------------------------------------------
# Trace structure (P2-011)
# ---------------------------------------------------------------------------

class TestTrace:
    def test_trace_contains_quarter_info(self):
        snap = _full_snapshot(_Q2_MONTHS, _Q2_AVGS)
        bill = _bill(on_account="1000000")
        result = calculate_pvc(bill, snap, _standard_rules())
        assert result.trace.quarter_used == "Q2-FY2025-26"
        assert result.trace.quarter_months == _Q2_MONTHS

    def test_trace_contains_component_detail(self):
        snap = _full_snapshot(_Q2_MONTHS, _Q2_AVGS)
        bill = _bill(on_account="1000000")
        result = calculate_pvc(bill, snap, _standard_rules())
        assert result.validation_errors == []
        assert "labour" in result.trace.components
        labour = result.trace.components["labour"]
        assert labour.eligible_amount is not None
        assert labour.pvc_value is not None

    def test_trace_blocked_run_still_has_quarter(self):
        snap = IndexSnapshot(base_month=_BASE, series={})
        bill = _bill(on_account="1000000", measurement_date=date(2025, 6, 18))
        result = calculate_pvc(bill, snap, _standard_rules())
        assert result.trace.quarter_used == "Q2-FY2025-26"

    def test_trace_extra_item_decisions_recorded(self):
        snap = _full_snapshot(_Q2_MONTHS, _Q2_AVGS)
        bill = _bill(
            on_account="1000000",
            extra_decisions=[ExtraItemDecision(item_id="NS1", amount=Decimal("50000"), eligible=False)],
        )
        result = calculate_pvc(bill, snap, _standard_rules())
        assert result.validation_errors == []
        decisions = result.trace.extra_item_decisions
        assert len(decisions) == 1
        assert decisions[0].item_id == "NS1"

    # P2-06: expanded trace contract — schema_version, provenance, and full echo
    def test_trace_schema_version_is_pinned(self):
        snap = _full_snapshot(_Q2_MONTHS, _Q2_AVGS)
        result = calculate_pvc(_bill(on_account="1000000"), snap, _standard_rules())
        assert result.trace.schema_version == "1.0"

    def test_trace_w_derivation_has_per_field_provenance(self):
        snap = _full_snapshot(_Q2_MONTHS, _Q2_AVGS)
        bill = _bill(on_account="1000000", cement="100000", angles="50000")
        result = calculate_pvc(bill, snap, _standard_rules())
        wt = result.trace.w_derivation
        assert wt is not None
        assert "W = on_account_amount" in wt.formula
        assert wt.inputs["on_account_amount"].input_field == "BillPayload.on_account_amount"
        assert wt.inputs["cement"].input_field == "BillPayload.cement_amount"
        assert "carry_forwards(subtype=tmt)" in wt.inputs["steel_tmt"].input_field
        assert wt.w == result.w

    def test_trace_w_derivation_is_none_when_run_blocked_pre_w(self):
        snap = _full_snapshot(_Q2_MONTHS, _Q2_AVGS)
        # Undecided extra item blocks W derivation entirely
        bill = _bill(
            on_account="1000000",
            extra_decisions=[ExtraItemDecision(item_id="X", amount=Decimal("1000"), eligible=None)],
        )
        result = calculate_pvc(bill, snap, _standard_rules())
        assert result.validation_errors  # blocked
        assert result.trace.w_derivation is None

    def test_trace_general_component_echoes_index_values(self):
        snap = _full_snapshot(_Q2_MONTHS, _Q2_AVGS)
        result = calculate_pvc(_bill(on_account="1000000"), snap, _standard_rules())
        labour = result.trace.components["labour"]
        assert labour.formula == "general_w_component"
        assert labour.index_ref is not None
        assert labour.index_ref.series == "labour"
        assert labour.index_ref.base.month == "2024-12"
        assert labour.index_ref.base.value == _BASE_INDICES["labour"]
        assert labour.index_ref.quarter.months == _Q2_MONTHS
        assert labour.index_ref.quarter.avg == _Q2_AVGS["labour"]

    def test_trace_steel_tmt_uses_single_commodity_ref(self):
        snap = _full_snapshot(_Q2_MONTHS, _Q2_AVGS)
        result = calculate_pvc(_bill(on_account="1000000", tmt="200000"), snap, _standard_rules())
        tmt = result.trace.components["steel_tmt"]
        assert tmt.formula == "steel_bucket_pvc"
        ref = tmt.commodity_index_ref
        assert ref is not None and ref.kind == "single"
        assert ref.series == "steel_tmt"
        assert tmt.sub_components is not None
        assert set(tmt.sub_components.keys()) == {"labour", "plant", "fuel", "materials"}

    def test_trace_steel_other_uses_derived_avg_commodity_ref(self):
        snap = _full_snapshot(_Q2_MONTHS, _Q2_AVGS)
        result = calculate_pvc(_bill(on_account="1000000", steel_other="200000"), snap, _standard_rules())
        other = result.trace.components["steel_other"]
        assert other.formula == "steel_bucket_pvc_derived_avg"
        ref = other.commodity_index_ref
        assert ref is not None and ref.kind == "derived_avg"
        assert ref.series_list == ["steel_tmt", "steel_angles", "steel_plates"]
        assert len(ref.per_series) == 3

    def test_trace_carry_forward_echoes_source_ref(self):
        snap = _full_snapshot(_Q2_MONTHS, _Q2_AVGS)
        cf = CarryForwardPayload(
            item_id="10.2",
            recorded_qty=Decimal("100"),
            paid_qty_source=Decimal("80"),
            amount=Decimal("50000"),
            steel_subtype="angles",
            source_ref="bill_line_uuid_xyz",
        )
        result = calculate_pvc(
            _bill(on_account="1000000", carry_forwards=[cf]),
            snap, _standard_rules(),
        )
        cft = result.trace.carry_forwards[0]
        assert cft.bill_line_ref == "bill_line_uuid_xyz"
        assert cft.applied_to_bucket == "steel_angles"
        # And the W derivation trace surfaces the same contribution
        contribs = result.trace.w_derivation.inputs["steel_angles"].carry_forward_contributions
        assert any(c.source_ref == "bill_line_uuid_xyz" for c in contribs)

    def test_trace_extra_item_echoes_source_ref_and_applied_flag(self):
        snap = _full_snapshot(_Q2_MONTHS, _Q2_AVGS)
        bill = _bill(
            on_account="1000000",
            extra_decisions=[
                ExtraItemDecision(item_id="NS-1", amount=Decimal("10000"),
                                  eligible=False, source_ref="bl-1"),
                ExtraItemDecision(item_id="NS-2", amount=Decimal("20000"),
                                  eligible=True, source_ref="bl-2"),
            ],
        )
        result = calculate_pvc(bill, snap, _standard_rules())
        by_id = {t.item_id: t for t in result.trace.extra_item_decisions}
        assert by_id["NS-1"].bill_line_ref == "bl-1"
        assert by_id["NS-1"].applied_to_w_subtraction is True
        assert by_id["NS-2"].bill_line_ref == "bl-2"
        assert by_id["NS-2"].applied_to_w_subtraction is False


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_all_steel_bill_no_general_w_components(self):
        """Bill where all amount is in steel buckets; W=0, no general components."""
        snap = _full_snapshot(_Q2_MONTHS, _Q2_AVGS)
        bill = _bill(on_account="1000000", angles="1000000")
        result = calculate_pvc(bill, snap, _standard_rules())
        assert result.validation_errors == []
        assert result.w == Decimal("0")
        general_cats = {c.category for c in result.components if c.category in {"labour", "plant", "fuel", "materials"}}
        # With w=0, general components have zero eligible_amount so they may be zero or absent
        for cat in general_cats:
            c = next(c for c in result.components if c.category == cat)
            assert c.eligible_amount == Decimal("0")

    def test_carry_forward_increases_steel_bucket(self):
        snap = _full_snapshot(_Q2_MONTHS, _Q2_AVGS)
        cf = CarryForwardPayload(
            item_id="10.2",
            recorded_qty=Decimal("6172.57"),
            paid_qty_source=Decimal("5600"),
            amount=Decimal("100000"),
            steel_subtype="angles",
        )
        bill_no_cf = _bill(on_account="1000000", angles="50000")
        bill_with_cf = _bill(on_account="1000000", angles="50000", carry_forwards=[cf])
        r_no = calculate_pvc(bill_no_cf, snap, _standard_rules())
        r_with = calculate_pvc(bill_with_cf, snap, _standard_rules())
        assert r_with.w_derivation is not None
        assert r_with.w_derivation.steel_angles > r_no.w_derivation.steel_angles  # type: ignore[union-attr]
