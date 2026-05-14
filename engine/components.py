"""P2-007/008/009: PVC component formulas.

Series names as stored in IndexSnapshot.series (matching seed data):
  RBI: labour, plant_machinery, fuel, other_materials, cement
  JPC: steel_tmt, steel_angles, steel_plates, steel_other_sections
"""
from __future__ import annotations

from decimal import Decimal

from .types import IndexSnapshot, PVCComponent, PVCRuleSet, WDerivation

_TWO = Decimal("2")
_THREE = Decimal("3")

# Fixed steel sub-component weights under GCC Clause 46A
_STEEL_SUB_WEIGHTS: dict[str, Decimal] = {
    "labour":    Decimal("0.10"),
    "plant":     Decimal("0.10"),
    "fuel":      Decimal("0.10"),
    "materials": Decimal("0.05"),
    "commodity": Decimal("0.50"),
}
assert sum(_STEEL_SUB_WEIGHTS.values()) == Decimal("0.85")

_STEEL_BUCKET_COMMODITY_SERIES: dict[str, str] = {
    "steel_angles": "steel_angles",
    "steel_plates": "steel_plates",
    "steel_other":  "steel_other_sections",  # covers both other_sections and tmt
}

_COMMON_SERIES: dict[str, str] = {
    "labour":    "labour",
    "plant":     "plant_machinery",
    "fuel":      "fuel",
    "materials": "other_materials",
}


def _base_value(snapshot: IndexSnapshot, series: str) -> Decimal | None:
    month_key = snapshot.base_month.strftime("%Y-%m")
    return snapshot.series.get(series, {}).get(month_key)


def _quarter_avg(snapshot: IndexSnapshot, series: str, quarter_months: list[str]) -> Decimal | None:
    values = []
    for m in quarter_months:
        v = snapshot.series.get(series, {}).get(m)
        if v is None:
            return None
        values.append(v)
    return sum(values) / _THREE


def _index_change(base: Decimal, avg: Decimal) -> Decimal:
    return (avg - base) / base


# ---------------------------------------------------------------------------
# P2-007: General W components (labour, plant, fuel, materials)
# ---------------------------------------------------------------------------

def compute_general_w_components(
    w: Decimal,
    rules: PVCRuleSet,
    snapshot: IndexSnapshot,
    quarter_months: list[str],
) -> tuple[list[PVCComponent], list[str]]:
    components: list[PVCComponent] = []
    errors: list[str] = []

    for cat, series in _COMMON_SERIES.items():
        weight = rules.component_weights.get(cat)
        if not weight:
            continue

        base_idx = _base_value(snapshot, series)
        avg_idx = _quarter_avg(snapshot, series, quarter_months)

        if base_idx is None:
            errors.append(f"missing base index: series='{series}'")
            continue
        if avg_idx is None:
            errors.append(f"missing quarter index: series='{series}' months={quarter_months}")
            continue

        eligible_amount = w * weight
        pvc_value = eligible_amount * _index_change(base_idx, avg_idx)

        components.append(PVCComponent(
            category=cat,
            eligible_amount=eligible_amount,
            base_index=base_idx,
            current_avg_index=avg_idx,
            weight=weight,
            pvc_value=pvc_value,
        ))

    return components, errors


# ---------------------------------------------------------------------------
# P2-008: Cement sub-formula
# ---------------------------------------------------------------------------

def compute_cement_component(
    cement_amount: Decimal,
    adjustable_fraction: Decimal,
    snapshot: IndexSnapshot,
    quarter_months: list[str],
) -> tuple[PVCComponent | None, list[str]]:
    series = "cement"
    base_idx = _base_value(snapshot, series)
    avg_idx = _quarter_avg(snapshot, series, quarter_months)

    if base_idx is None:
        return None, [f"missing base index: series='{series}'"]
    if avg_idx is None:
        return None, [f"missing quarter index: series='{series}' months={quarter_months}"]

    eligible_amount = cement_amount * adjustable_fraction
    pvc_value = eligible_amount * _index_change(base_idx, avg_idx)

    return PVCComponent(
        category="cement",
        eligible_amount=eligible_amount,
        base_index=base_idx,
        current_avg_index=avg_idx,
        weight=adjustable_fraction,
        pvc_value=pvc_value,
    ), []


# ---------------------------------------------------------------------------
# P2-009: Steel bucket sub-formulas
# ---------------------------------------------------------------------------

def _steel_bucket_pvc(
    bucket_amount: Decimal,
    commodity_series: str,
    snapshot: IndexSnapshot,
    quarter_months: list[str],
) -> tuple[Decimal | None, Decimal | None, Decimal | None, list[str]]:
    """
    Returns (base_commodity_idx, avg_commodity_idx, pvc_value, errors).
    pvc_value = bucket × sum_over_sub_components(weight × ΔI/I₀).
    """
    errors: list[str] = []
    pvc = Decimal("0")

    for sub_cat, series in _COMMON_SERIES.items():
        weight = _STEEL_SUB_WEIGHTS[sub_cat]
        base_idx = _base_value(snapshot, series)
        avg_idx = _quarter_avg(snapshot, series, quarter_months)
        if base_idx is None or avg_idx is None:
            errors.append(f"missing index for series='{series}' (steel {sub_cat} sub-component)")
            return None, None, None, errors
        pvc += bucket_amount * weight * _index_change(base_idx, avg_idx)

    base_comm = _base_value(snapshot, commodity_series)
    avg_comm = _quarter_avg(snapshot, commodity_series, quarter_months)
    if base_comm is None:
        errors.append(f"missing base index: series='{commodity_series}'")
        return None, None, None, errors
    if avg_comm is None:
        errors.append(f"missing quarter index: series='{commodity_series}' months={quarter_months}")
        return None, None, None, errors

    pvc += bucket_amount * _STEEL_SUB_WEIGHTS["commodity"] * _index_change(base_comm, avg_comm)
    return base_comm, avg_comm, pvc, []


def compute_steel_components(
    derivation: WDerivation,
    snapshot: IndexSnapshot,
    quarter_months: list[str],
) -> tuple[list[PVCComponent], list[str]]:
    components: list[PVCComponent] = []
    errors: list[str] = []

    buckets = {
        "steel_angles": derivation.steel_angles,
        "steel_plates": derivation.steel_plates,
        "steel_other":  derivation.steel_other,
    }

    for cat, amount in buckets.items():
        if amount == Decimal("0"):
            continue

        commodity_series = _STEEL_BUCKET_COMMODITY_SERIES[cat]
        base_comm, avg_comm, pvc_value, errs = _steel_bucket_pvc(
            amount, commodity_series, snapshot, quarter_months
        )
        if errs:
            errors.extend(errs)
            continue

        components.append(PVCComponent(
            category=cat,
            eligible_amount=amount,
            base_index=base_comm,      # type: ignore[arg-type]
            current_avg_index=avg_comm,  # type: ignore[arg-type]
            weight=_STEEL_SUB_WEIGHTS["commodity"],
            pvc_value=pvc_value,       # type: ignore[arg-type]
        ))

    return components, errors
