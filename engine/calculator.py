"""Main engine entry point. Orchestrates P2-002 through P2-011."""
from __future__ import annotations

from decimal import ROUND_DOWN, Decimal

from .components import (
    _COMMON_SERIES,
    _STEEL_BUCKET_COMMODITY_SERIES,
    _STEEL_SUB_WEIGHTS,
    compute_cement_component,
    compute_general_w_components,
    compute_steel_components,
)
from .quarter import resolve_quarter
from .types import (
    BillPayload,
    CarryForwardContribution,
    CarryForwardTrace,
    ComponentTrace,
    DerivedAvgIndexRef,
    ExtraItemTrace,
    IndexBaseValue,
    IndexQuarterValues,
    IndexRef,
    IndexSnapshot,
    PVCComponent,
    PVCRunResult,
    PVCRuleSet,
    SteelSubComponentTrace,
    TraceContract,
    WDerivation,
    WDerivationLine,
    WDerivationTrace,
)
from .w_derivation import _SUBTYPE_TO_BUCKET, derive_w

_CENT = Decimal("0.01")
_THREE = Decimal("3")
_W_FORMULA = (
    "W = on_account_amount - cement - steel_angles - steel_plates "
    "- steel_tmt - steel_other - technical_withheld - extra_items_excluded"
)


def _round(value: Decimal, mode: str) -> Decimal:
    if mode == "round_2":
        return value.quantize(_CENT)
    # truncate_2
    return value.quantize(_CENT, rounding=ROUND_DOWN)


def _build_index_ref(
    snapshot: IndexSnapshot, series: str, quarter_months: list[str]
) -> IndexRef | None:
    base_month_key = snapshot.base_month.strftime("%Y-%m")
    base_val = snapshot.series.get(series, {}).get(base_month_key)
    if base_val is None:
        return None
    q_values: list[Decimal] = []
    for m in quarter_months:
        v = snapshot.series.get(series, {}).get(m)
        if v is None:
            return None
        q_values.append(v)
    return IndexRef(
        series=series,
        base=IndexBaseValue(month=base_month_key, value=base_val),
        quarter=IndexQuarterValues(
            months=list(quarter_months),
            values=q_values,
            avg=sum(q_values, Decimal("0")) / _THREE,
        ),
    )


def _build_derived_avg_ref(
    snapshot: IndexSnapshot, series_list: list[str], quarter_months: list[str]
) -> DerivedAvgIndexRef | None:
    per_series: list[IndexRef] = []
    for s in series_list:
        ref = _build_index_ref(snapshot, s, quarter_months)
        if ref is None:
            return None
        per_series.append(ref)
    n = Decimal(len(per_series))
    return DerivedAvgIndexRef(
        series_list=list(series_list),
        per_series=per_series,
        base_avg=sum((r.base.value for r in per_series), Decimal("0")) / n,
        quarter_avg=sum((r.quarter.avg for r in per_series), Decimal("0")) / n,
    )


def _build_component_trace(
    c: PVCComponent,
    rules: PVCRuleSet,
    snapshot: IndexSnapshot,
    quarter_months: list[str],
) -> ComponentTrace:
    # General works components (labour/plant/fuel/materials)
    if c.category in _COMMON_SERIES:
        series = _COMMON_SERIES[c.category]
        index_ref = _build_index_ref(snapshot, series, quarter_months)
        return ComponentTrace(
            category=c.category,
            formula="general_w_component",
            formula_expanded="W × weight × (Qavg − base) / base",
            input_field=f"WDerivation.w × PVCRuleSet.component_weights.{c.category}",
            eligible_amount=c.eligible_amount,
            weight=c.weight,
            pvc_value=c.pvc_value,
            index_ref=index_ref,
        )

    if c.category == "cement":
        index_ref = _build_index_ref(snapshot, "cement", quarter_months)
        return ComponentTrace(
            category="cement",
            formula="cement_component",
            formula_expanded="cement_amount × adjustable_fraction × (Qavg − base) / base",
            input_field="BillPayload.cement_amount",
            eligible_amount=c.eligible_amount,
            weight=c.weight,
            pvc_value=c.pvc_value,
            index_ref=index_ref,
        )

    # Steel buckets
    commodity_series = _STEEL_BUCKET_COMMODITY_SERIES[c.category]
    if isinstance(commodity_series, list):
        commodity_ref = _build_derived_avg_ref(snapshot, commodity_series, quarter_months)
        formula_id = "steel_bucket_pvc_derived_avg"
        formula_expanded = (
            "bucket × ( Σ sub_weight×(ΔI/I₀)_sub for labour/plant/fuel/materials "
            "+ 0.50×(ΔI/I₀)_commodity ) ; commodity index = avg(SL1,SL2,SL3)"
        )
    else:
        commodity_ref = _build_index_ref(snapshot, commodity_series, quarter_months)
        formula_id = "steel_bucket_pvc"
        formula_expanded = (
            "bucket × ( Σ sub_weight×(ΔI/I₀)_sub for labour/plant/fuel/materials "
            "+ 0.50×(ΔI/I₀)_commodity )"
        )

    sub_components: dict[str, SteelSubComponentTrace] = {}
    for sub_cat, series in _COMMON_SERIES.items():
        sub_ref = _build_index_ref(snapshot, series, quarter_months)
        if sub_ref is None:
            continue
        sub_components[sub_cat] = SteelSubComponentTrace(
            weight=_STEEL_SUB_WEIGHTS[sub_cat],
            index_ref=sub_ref,
        )

    return ComponentTrace(
        category=c.category,
        formula=formula_id,
        formula_expanded=formula_expanded,
        input_field=f"WDerivation.{c.category} (= BillPayload.{c.category}_amount + carry-forwards)",
        eligible_amount=c.eligible_amount,
        weight=c.weight,
        pvc_value=c.pvc_value,
        commodity_index_ref=commodity_ref,
        sub_components=sub_components,
    )


def _build_w_derivation_trace(
    bill: BillPayload, w_derivation: WDerivation
) -> WDerivationTrace:
    """Build provenance for each line of W. Steel buckets enumerate the
    specific carry-forwards that contributed to them."""
    cf_by_bucket: dict[str, list[CarryForwardContribution]] = {
        "steel_angles": [],
        "steel_plates": [],
        "steel_tmt": [],
        "steel_other": [],
    }
    for cf in bill.carry_forwards:
        if cf.steel_subtype is None:
            continue
        bucket = _SUBTYPE_TO_BUCKET[cf.steel_subtype]
        cf_by_bucket[bucket].append(
            CarryForwardContribution(
                item_id=cf.item_id,
                source_ref=cf.source_ref,
                prorated_amount=cf.amount * cf.paid_ratio,
            )
        )

    inputs: dict[str, WDerivationLine] = {
        "on_account_amount": WDerivationLine(
            value=w_derivation.on_account_amount,
            input_field="BillPayload.on_account_amount",
        ),
        "cement": WDerivationLine(
            value=w_derivation.cement,
            input_field="BillPayload.cement_amount",
        ),
        "steel_angles": WDerivationLine(
            value=w_derivation.steel_angles,
            input_field="BillPayload.steel_angles_amount + Σ carry_forwards(subtype=angles).amount × paid_ratio",
            carry_forward_contributions=cf_by_bucket["steel_angles"],
        ),
        "steel_plates": WDerivationLine(
            value=w_derivation.steel_plates,
            input_field="BillPayload.steel_plates_amount + Σ carry_forwards(subtype=plates).amount × paid_ratio",
            carry_forward_contributions=cf_by_bucket["steel_plates"],
        ),
        "steel_tmt": WDerivationLine(
            value=w_derivation.steel_tmt,
            input_field="BillPayload.steel_tmt_amount + Σ carry_forwards(subtype=tmt).amount × paid_ratio",
            carry_forward_contributions=cf_by_bucket["steel_tmt"],
        ),
        "steel_other": WDerivationLine(
            value=w_derivation.steel_other,
            input_field="BillPayload.steel_other_amount + Σ carry_forwards(subtype=other_sections).amount × paid_ratio",
            carry_forward_contributions=cf_by_bucket["steel_other"],
        ),
        "technical_withheld": WDerivationLine(
            value=w_derivation.technical_withheld,
            input_field="BillPayload.technical_withheld",
        ),
        "extra_items_excluded": WDerivationLine(
            value=w_derivation.extra_items,
            input_field="Σ extra_item_decisions[].amount where eligible == False",
        ),
    }
    return WDerivationTrace(
        formula=_W_FORMULA,
        inputs=inputs,
        w=w_derivation.w,
    )


def _build_carry_forward_traces(bill: BillPayload) -> list[CarryForwardTrace]:
    traces: list[CarryForwardTrace] = []
    for cf in bill.carry_forwards:
        applied_bucket = (
            _SUBTYPE_TO_BUCKET[cf.steel_subtype] if cf.steel_subtype is not None else None
        )
        traces.append(CarryForwardTrace(
            item_id=cf.item_id,
            bill_line_ref=cf.source_ref,
            input_field="CarryForwardPayload.amount",
            formula="amount × (paid_qty_source / recorded_qty)",
            recorded_qty=cf.recorded_qty,
            paid_qty_source=cf.paid_qty_source,
            paid_ratio=cf.paid_ratio,
            amount=cf.amount,
            prorated_amount=cf.amount * cf.paid_ratio,
            steel_subtype=cf.steel_subtype,
            applied_to_bucket=applied_bucket,
        ))
    return traces


def _build_extra_item_traces(bill: BillPayload) -> list[ExtraItemTrace]:
    traces: list[ExtraItemTrace] = []
    for d in bill.extra_item_decisions:
        traces.append(ExtraItemTrace(
            item_id=d.item_id,
            bill_line_ref=d.source_ref,
            input_field="ExtraItemDecision.amount",
            formula="if eligible is False: subtract from W; if True: retained in W; if None: block run",
            amount=d.amount,
            eligible=d.eligible,
            applied_to_w_subtraction=(d.eligible is False),
        ))
    return traces


def _build_trace(
    bill: BillPayload,
    quarter_label: str,
    quarter_months: list[str],
    snapshot: IndexSnapshot,
    rules: PVCRuleSet,
    w_derivation: WDerivation | None,
    components: list[PVCComponent],
) -> TraceContract:
    base_month_key = snapshot.base_month.strftime("%Y-%m")
    w_trace = _build_w_derivation_trace(bill, w_derivation) if w_derivation is not None else None
    component_traces: dict[str, ComponentTrace] = {
        c.category: _build_component_trace(c, rules, snapshot, quarter_months)
        for c in components
    }
    return TraceContract(
        quarter_used=quarter_label,
        quarter_months=quarter_months,
        base_month=base_month_key,
        prior_negative_carry_forward=bill.prior_negative_carry_forward,
        w_derivation=w_trace,
        components=component_traces,
        carry_forwards=_build_carry_forward_traces(bill),
        extra_item_decisions=_build_extra_item_traces(bill),
    )


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
            trace=_build_trace(bill, quarter_label, quarter_months, indices, rules, None, []),
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
            trace=_build_trace(bill, quarter_label, quarter_months, indices, rules, w_derivation, []),
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
                trace=_build_trace(bill, quarter_label, quarter_months, indices, rules, w_derivation, all_components),
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
        trace=_build_trace(bill, quarter_label, quarter_months, indices, rules, w_derivation, all_components),
        validation_errors=[],
    )


