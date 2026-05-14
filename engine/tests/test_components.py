"""Unit tests for P2-007/008/009: PVC component formulas."""
from decimal import Decimal
from datetime import date

import pytest

from engine.components import (
    compute_cement_component,
    compute_general_w_components,
    compute_steel_components,
)
from engine.types import IndexSnapshot, PVCRuleSet, WDerivation

# Base month: Dec-2024 (BCT-24-25-252)
_BASE = date(2024, 12, 1)

# Real index values from BCT-24-25-252 workbook / seeds
_BASE_INDICES = {
    "labour":           Decimal("143.7"),
    "plant_machinery":  Decimal("160.0"),
    "fuel":             Decimal("160.48"),
    "other_materials":  Decimal("155.7"),
    "cement":           Decimal("130.2"),
    "steel_angles":     Decimal("58000.0"),
    "steel_plates":     Decimal("57370.0"),
    "steel_other_sections": Decimal("57727.5"),
    "steel_tmt":        Decimal("57812.5"),
}

# Q2-2025 averages (Apr/May/Jun 2025) — from seed_indices.py
_Q2_MONTHS = ["2025-04", "2025-05", "2025-06"]
_Q2_AVGS = {
    "labour":           Decimal("144.167"),
    "plant_machinery":  Decimal("161.5"),
    "fuel":             Decimal("157.0"),
    "other_materials":  Decimal("156.0"),
    "cement":           Decimal("129.5"),
    "steel_angles":     Decimal("57500.0"),
    "steel_plates":     Decimal("57000.0"),
    "steel_other_sections": Decimal("57200.0"),
    "steel_tmt":        Decimal("57000.0"),
}


def _snapshot(months: list[str], avgs: dict[str, Decimal]) -> IndexSnapshot:
    """Build IndexSnapshot with base month + given quarter months/averages."""
    series: dict[str, dict[str, Decimal]] = {}
    for s, base_val in _BASE_INDICES.items():
        series[s] = {"2024-12": base_val}
        for m in months:
            series[s][m] = avgs[s]
    return IndexSnapshot(base_month=_BASE, series=series)


def _rules(weights: dict[str, str] | None = None) -> PVCRuleSet:
    w = weights or {"labour": "0.20", "plant": "0.30", "fuel": "0.15", "materials": "0.20"}
    return PVCRuleSet(
        quarter_mode="measurement_date",
        component_weights={k: Decimal(v) for k, v in w.items()},
        adjustable_fraction=Decimal("0.85"),
        negative_pvc_policy="zero_floor",
        rounding_mode="round_2",
    )


def _derivation(
    w: str = "0",
    cement: str = "0",
    angles: str = "0",
    plates: str = "0",
    other: str = "0",
) -> WDerivation:
    return WDerivation(
        on_account_amount=Decimal("0"),
        cement=Decimal(cement),
        steel_angles=Decimal(angles),
        steel_plates=Decimal(plates),
        steel_other=Decimal(other),
        technical_withheld=Decimal("0"),
        extra_items=Decimal("0"),
        w=Decimal(w),
    )


# ---------------------------------------------------------------------------
# P2-007: General W components
# ---------------------------------------------------------------------------

class TestGeneralWComponents:
    def test_labour_formula(self):
        snap = _snapshot(_Q2_MONTHS, _Q2_AVGS)
        components, errs = compute_general_w_components(
            Decimal("1000000"), _rules({"labour": "0.20"}), snap, _Q2_MONTHS
        )
        assert errs == []
        c = next(c for c in components if c.category == "labour")
        assert c.eligible_amount == Decimal("200000")
        assert c.base_index == _BASE_INDICES["labour"]
        assert c.current_avg_index == _Q2_AVGS["labour"]
        # Match engine's exact evaluation order: eligible × (diff / base)
        eligible = Decimal("1000000") * Decimal("0.20")
        expected_pvc = eligible * ((_Q2_AVGS["labour"] - _BASE_INDICES["labour"]) / _BASE_INDICES["labour"])
        assert c.pvc_value == expected_pvc

    def test_four_components_returned_for_standard_weights(self):
        snap = _snapshot(_Q2_MONTHS, _Q2_AVGS)
        components, errs = compute_general_w_components(
            Decimal("8903877.99"), _rules(), snap, _Q2_MONTHS
        )
        assert errs == []
        cats = {c.category for c in components}
        assert cats == {"labour", "plant", "fuel", "materials"}

    def test_zero_weight_category_omitted(self):
        snap = _snapshot(_Q2_MONTHS, _Q2_AVGS)
        components, errs = compute_general_w_components(
            Decimal("1000000"), _rules({"labour": "0.20"}), snap, _Q2_MONTHS
        )
        assert errs == []
        cats = {c.category for c in components}
        assert "plant" not in cats

    def test_missing_base_index_returns_error(self):
        snap = IndexSnapshot(base_month=_BASE, series={})
        _, errs = compute_general_w_components(
            Decimal("1000000"), _rules({"labour": "0.20"}), snap, _Q2_MONTHS
        )
        assert len(errs) >= 1
        assert any("labour" in e for e in errs)

    def test_missing_quarter_index_returns_error(self):
        snap = IndexSnapshot(
            base_month=_BASE,
            series={"labour": {"2024-12": _BASE_INDICES["labour"]}},
        )
        _, errs = compute_general_w_components(
            Decimal("1000000"), _rules({"labour": "0.20"}), snap, _Q2_MONTHS
        )
        assert len(errs) >= 1

    def test_pvc_is_negative_when_index_falls(self):
        falling_avgs = {**_Q2_AVGS, "labour": _BASE_INDICES["labour"] - Decimal("5")}
        snap = _snapshot(_Q2_MONTHS, falling_avgs)
        components, errs = compute_general_w_components(
            Decimal("1000000"), _rules({"labour": "0.20"}), snap, _Q2_MONTHS
        )
        assert errs == []
        c = next(c for c in components if c.category == "labour")
        assert c.pvc_value < Decimal("0")


# ---------------------------------------------------------------------------
# P2-008: Cement component
# ---------------------------------------------------------------------------

class TestCementComponent:
    def test_cement_formula(self):
        snap = _snapshot(_Q2_MONTHS, _Q2_AVGS)
        c, errs = compute_cement_component(Decimal("500000"), Decimal("0.85"), snap, _Q2_MONTHS)
        assert errs == []
        assert c is not None
        assert c.eligible_amount == Decimal("500000") * Decimal("0.85")
        expected_pvc = (
            Decimal("500000") * Decimal("0.85")
            * (_Q2_AVGS["cement"] - _BASE_INDICES["cement"])
            / _BASE_INDICES["cement"]
        )
        assert c.pvc_value == expected_pvc

    def test_zero_cement_still_computes_if_index_present(self):
        snap = _snapshot(_Q2_MONTHS, _Q2_AVGS)
        c, errs = compute_cement_component(Decimal("0"), Decimal("0.85"), snap, _Q2_MONTHS)
        assert errs == []
        assert c is not None
        assert c.pvc_value == Decimal("0")

    def test_missing_cement_base_returns_error(self):
        snap = IndexSnapshot(base_month=_BASE, series={})
        c, errs = compute_cement_component(Decimal("100000"), Decimal("0.85"), snap, _Q2_MONTHS)
        assert c is None
        assert len(errs) == 1

    def test_category_is_cement(self):
        snap = _snapshot(_Q2_MONTHS, _Q2_AVGS)
        c, _ = compute_cement_component(Decimal("100000"), Decimal("0.85"), snap, _Q2_MONTHS)
        assert c is not None
        assert c.category == "cement"


# ---------------------------------------------------------------------------
# P2-009: Steel bucket sub-formulas
# ---------------------------------------------------------------------------

class TestSteelComponents:
    def test_angles_bucket_uses_steel_angles_series(self):
        snap = _snapshot(_Q2_MONTHS, _Q2_AVGS)
        d = _derivation(angles="300000")
        components, errs = compute_steel_components(d, snap, _Q2_MONTHS)
        assert errs == []
        c = next(c for c in components if c.category == "steel_angles")
        assert c.eligible_amount == Decimal("300000")
        assert c.base_index == _BASE_INDICES["steel_angles"]
        assert c.current_avg_index == _Q2_AVGS["steel_angles"]

    def test_steel_pvc_uses_five_sub_components(self):
        """PVC = amount × (0.10×ΔL + 0.10×ΔP + 0.10×ΔF + 0.05×ΔM + 0.50×ΔSa)."""
        snap = _snapshot(_Q2_MONTHS, _Q2_AVGS)
        d = _derivation(angles="1000000")
        components, errs = compute_steel_components(d, snap, _Q2_MONTHS)
        assert errs == []
        c = components[0]

        def chg(base, avg):
            return (avg - base) / base

        expected = Decimal("1000000") * (
            Decimal("0.10") * chg(_BASE_INDICES["labour"],          _Q2_AVGS["labour"])
            + Decimal("0.10") * chg(_BASE_INDICES["plant_machinery"], _Q2_AVGS["plant_machinery"])
            + Decimal("0.10") * chg(_BASE_INDICES["fuel"],           _Q2_AVGS["fuel"])
            + Decimal("0.05") * chg(_BASE_INDICES["other_materials"], _Q2_AVGS["other_materials"])
            + Decimal("0.50") * chg(_BASE_INDICES["steel_angles"],   _Q2_AVGS["steel_angles"])
        )
        assert c.pvc_value == expected

    def test_plates_uses_steel_plates_commodity(self):
        snap = _snapshot(_Q2_MONTHS, _Q2_AVGS)
        d = _derivation(plates="200000")
        components, errs = compute_steel_components(d, snap, _Q2_MONTHS)
        assert errs == []
        c = next(c for c in components if c.category == "steel_plates")
        assert c.base_index == _BASE_INDICES["steel_plates"]

    def test_steel_other_uses_other_sections_commodity(self):
        snap = _snapshot(_Q2_MONTHS, _Q2_AVGS)
        d = _derivation(other="100000")
        components, errs = compute_steel_components(d, snap, _Q2_MONTHS)
        assert errs == []
        c = next(c for c in components if c.category == "steel_other")
        assert c.base_index == _BASE_INDICES["steel_other_sections"]

    def test_zero_bucket_omitted(self):
        snap = _snapshot(_Q2_MONTHS, _Q2_AVGS)
        d = _derivation(angles="100000")
        components, _ = compute_steel_components(d, snap, _Q2_MONTHS)
        cats = {c.category for c in components}
        assert "steel_plates" not in cats
        assert "steel_other" not in cats

    def test_missing_commodity_index_returns_error(self):
        snap = IndexSnapshot(base_month=_BASE, series={
            "labour": {"2024-12": _BASE_INDICES["labour"], **{m: _Q2_AVGS["labour"] for m in _Q2_MONTHS}},
            "plant_machinery": {"2024-12": _BASE_INDICES["plant_machinery"], **{m: _Q2_AVGS["plant_machinery"] for m in _Q2_MONTHS}},
            "fuel": {"2024-12": _BASE_INDICES["fuel"], **{m: _Q2_AVGS["fuel"] for m in _Q2_MONTHS}},
            "other_materials": {"2024-12": _BASE_INDICES["other_materials"], **{m: _Q2_AVGS["other_materials"] for m in _Q2_MONTHS}},
            # steel_angles intentionally missing
        })
        d = _derivation(angles="100000")
        _, errs = compute_steel_components(d, snap, _Q2_MONTHS)
        assert len(errs) >= 1
