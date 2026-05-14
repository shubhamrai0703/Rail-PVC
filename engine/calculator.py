"""Main engine entry point. Orchestrates P2-002 through P2-011."""
from __future__ import annotations

from decimal import ROUND_DOWN, Decimal

from .components import (
    compute_cement_component,
    compute_general_w_components,
    compute_steel_components,
)
from .quarter import resolve_quarter
from .types import BillPayload, IndexSnapshot, PVCComponent, PVCRunResult, PVCRuleSet
from .w_derivation import derive_w

_CENT = Decimal("0.01")


def _round(value: Decimal, mode: str) -> Decimal:
    if mode == "round_2":
        return value.quantize(_CENT)
    # truncate_2
    return value.quantize(_CENT, rounding=ROUND_DOWN)


def _build_trace(
    bill: BillPayload,
    quarter_label: str,
    quarter_months: list[str],
    snapshot: IndexSnapshot,
    components: list[PVCComponent],
) -> dict:
    base_month_key = snapshot.base_month.strftime("%Y-%m")
    component_trace = {}
    for c in components:
        component_trace[c.category] = {
            "eligible_amount": str(c.eligible_amount),
            "base_index": str(c.base_index),
            "current_avg_index": str(c.current_avg_index),
            "weight": str(c.weight),
            "pvc_value": str(c.pvc_value),
            "quarter_months": quarter_months,
        }
    carry_trace = [
        {
            "item_id": cf.item_id,
            "recorded_qty": str(cf.recorded_qty),
            "paid_qty_source": str(cf.paid_qty_source),
            "paid_ratio": str(cf.paid_ratio),
            "amount": str(cf.amount),
            "steel_subtype": cf.steel_subtype,
            "prorated_amount": str(cf.amount * cf.paid_ratio),
        }
        for cf in bill.carry_forwards
    ]
    extra_trace = [
        {"item_id": d.item_id, "amount": str(d.amount), "eligible": d.eligible}
        for d in bill.extra_item_decisions
    ]
    return {
        "quarter_used": quarter_label,
        "quarter_months": quarter_months,
        "base_month": base_month_key,
        "prior_negative_carry_forward": str(bill.prior_negative_carry_forward),
        "components": component_trace,
        "carry_forwards": carry_trace,
        "extra_item_decisions": extra_trace,
    }


def calculate_pvc(
    bill: BillPayload,
    indices: IndexSnapshot,
    rules: PVCRuleSet,
) -> PVCRunResult:
    """
    Pure function — same inputs always produce the same output.
    No database calls. No HTTP calls. No global state.
    If validation_errors is non-empty, total_pvc is None and the run is blocked.
    """
    errors: list[str] = []

    # P2-006: resolve quarter
    quarter_label, quarter_months = resolve_quarter(bill.measurement_date)

    # P2-002/003/004/005: derive W (also validates extra item decisions)
    w_derivation, w_errors = derive_w(bill)
    errors.extend(w_errors)

    if errors:
        return PVCRunResult(
            w=None,
            w_derivation=None,
            components=[],
            total_pvc=None,
            negative_carry_forward=Decimal("0"),
            quarter_used=quarter_label,
            quarter_months=quarter_months,
            trace=_build_trace(bill, quarter_label, quarter_months, indices, []),
            validation_errors=errors,
        )

    # P2-010: validate index coverage before any calculation
    # (component functions emit errors for missing indices; we collect them first)
    all_components: list[PVCComponent] = []
    component_errors: list[str] = []

    gen_components, gen_errs = compute_general_w_components(
        w_derivation.w, rules, indices, quarter_months
    )
    component_errors.extend(gen_errs)
    all_components.extend(gen_components)

    cement_component, cem_errs = compute_cement_component(
        w_derivation.cement, rules.adjustable_fraction, indices, quarter_months
    )
    component_errors.extend(cem_errs)
    if cement_component:
        all_components.append(cement_component)

    steel_components, steel_errs = compute_steel_components(
        w_derivation, indices, quarter_months
    )
    component_errors.extend(steel_errs)
    all_components.extend(steel_components)

    if component_errors:
        errors.extend(component_errors)
        return PVCRunResult(
            w=None,
            w_derivation=None,
            components=[],
            total_pvc=None,
            negative_carry_forward=Decimal("0"),
            quarter_used=quarter_label,
            quarter_months=quarter_months,
            trace=_build_trace(bill, quarter_label, quarter_months, indices, []),
            validation_errors=errors,
        )

    # P2-011: compute total PVC
    raw_total = sum((c.pvc_value for c in all_components), Decimal("0"))
    raw_total -= bill.prior_negative_carry_forward

    # P2-007 (KU-003): negative PVC policy
    negative_carry_forward = Decimal("0")
    if raw_total < Decimal("0"):
        if rules.negative_pvc_policy == "zero_floor":
            negative_carry_forward = _round(abs(raw_total), rules.rounding_mode)
            raw_total = Decimal("0")
        elif rules.negative_pvc_policy == "block":
            errors.append(f"negative PVC ({raw_total}) — run blocked by negative_pvc_policy=block")
            return PVCRunResult(
                w=None,
                w_derivation=None,
                components=[],
                total_pvc=None,
                negative_carry_forward=Decimal("0"),
                quarter_used=quarter_label,
                quarter_months=quarter_months,
                trace=_build_trace(bill, quarter_label, quarter_months, indices, []),
                validation_errors=errors,
            )
        # "allow": keep raw_total as-is

    total_pvc = _round(raw_total, rules.rounding_mode)

    return PVCRunResult(
        w=w_derivation.w,
        w_derivation=w_derivation,
        components=all_components,
        total_pvc=total_pvc,
        negative_carry_forward=negative_carry_forward,
        quarter_used=quarter_label,
        quarter_months=quarter_months,
        trace=_build_trace(bill, quarter_label, quarter_months, indices, all_components),
        validation_errors=[],
    )
