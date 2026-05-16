from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, Field, computed_field, field_validator, model_validator


class ExtraItemDecision(BaseModel):
    item_id: str
    amount: Decimal
    eligible: bool | None = None  # None = undecided; blocks run
    # P2-06: opaque caller-supplied reference (e.g. bill_lines.id). The engine
    # never interprets it — only echoes it into the trace so the frontend can
    # link a deduction back to its source row without re-joining on item_id.
    source_ref: str | None = None


class CarryForwardPayload(BaseModel):
    """Steel carry-forward from a prior bill.

    Inputs are deliberately minimal — `paid_ratio` and `carry_qty` are derived,
    so the model cannot represent contradictory state (e.g., ratio > 1 or
    carry_qty < 0).
    """
    item_id: str
    recorded_qty: Decimal = Field(gt=Decimal("0"))
    paid_qty_source: Decimal = Field(ge=Decimal("0"))
    amount: Decimal = Field(ge=Decimal("0"))
    steel_subtype: Literal["angles", "plates", "other_sections", "tmt"] | None = None
    source_ref: str | None = None  # opaque pass-through for trace bill_line_ref

    @model_validator(mode="after")
    def _paid_qty_within_recorded(self) -> "CarryForwardPayload":
        if self.paid_qty_source > self.recorded_qty:
            raise ValueError(
                f"paid_qty_source ({self.paid_qty_source}) cannot exceed "
                f"recorded_qty ({self.recorded_qty})"
            )
        return self

    @computed_field  # type: ignore[prop-decorator]
    @property
    def paid_ratio(self) -> Decimal:
        return self.paid_qty_source / self.recorded_qty

    @computed_field  # type: ignore[prop-decorator]
    @property
    def carry_qty(self) -> Decimal:
        return self.recorded_qty - self.paid_qty_source


class BillPayload(BaseModel):
    on_account_amount: Decimal
    cement_amount: Decimal
    steel_angles_amount: Decimal
    steel_plates_amount: Decimal
    steel_tmt_amount: Decimal                   # GCC 46A.9 SL1 — TMT/rebar items (required; zero must be explicit)
    steel_other_amount: Decimal                 # GCC 46A.9 SL4 — other sections
    technical_withheld: Decimal
    extra_item_decisions: list[ExtraItemDecision]  # P2-004: eligible=None blocks run
    carry_forwards: list[CarryForwardPayload]
    measurement_date: date  # must be the "To" date of the measurement period
    prior_negative_carry_forward: Decimal = Decimal("0")  # recovery from previous bill


class IndexSnapshot(BaseModel):
    base_month: date
    series: dict[str, dict[str, Decimal]]  # {series_name: {"YYYY-MM": value}}


REQUIRED_GENERAL_WEIGHTS: frozenset[str] = frozenset(
    {"labour", "plant", "fuel", "materials"}
)


class PVCRuleSet(BaseModel):
    # Only measurement_date is a valid quarter anchor (KU-001). The historical
    # "bill_date" mode never existed; rejecting it at the schema level
    # prevents silent miscomputation downstream.
    quarter_mode: Literal["measurement_date"]
    component_weights: dict[str, Decimal]
    adjustable_fraction: Decimal           # typically 0.85
    negative_pvc_policy: Literal["allow", "block", "zero_floor"]
    rounding_mode: Literal["round_2", "truncate_2"]

    @field_validator("component_weights")
    @classmethod
    def _weights_complete_and_known(cls, v: dict[str, Decimal]) -> dict[str, Decimal]:
        keys = set(v)
        missing = REQUIRED_GENERAL_WEIGHTS - keys
        unknown = keys - REQUIRED_GENERAL_WEIGHTS
        if missing or unknown:
            parts = []
            if missing:
                parts.append(f"missing keys: {sorted(missing)}")
            if unknown:
                parts.append(f"unknown keys: {sorted(unknown)}")
            raise ValueError(
                "component_weights must contain exactly "
                f"{sorted(REQUIRED_GENERAL_WEIGHTS)} ({'; '.join(parts)})"
            )
        for k, w in v.items():
            if w < Decimal("0"):
                raise ValueError(f"component_weights[{k}] must be >= 0, got {w}")
        return v


class WDerivation(BaseModel):
    on_account_amount: Decimal
    cement: Decimal
    steel_angles: Decimal
    steel_plates: Decimal
    steel_tmt: Decimal      # GCC 46A.9 SL1 — TMT/rebar items
    steel_other: Decimal    # GCC 46A.9 SL4 — other sections
    technical_withheld: Decimal
    extra_items: Decimal  # sum of excluded (eligible=False) extra item amounts
    w: Decimal


class PVCComponent(BaseModel):
    category: str
    eligible_amount: Decimal
    base_index: Decimal
    current_avg_index: Decimal
    weight: Decimal
    pvc_value: Decimal


# ---------------------------------------------------------------------------
# Trace contract (P2-06)
#
# Every PVC run produces a structured TraceContract. The contract is the
# audit substrate for revision_snapshots and the Phase 7 results UI: every
# numeric output is traceable to (a) the input field that fed it, (b) the
# formula identifier used to combine inputs, and (c) the index series/months
# (with values echoed) or bill-line source (via opaque source_ref).
#
# Schema is versioned. Bump TRACE_SCHEMA_VERSION on any breaking change.
# ---------------------------------------------------------------------------

TRACE_SCHEMA_VERSION: Literal["1.0"] = "1.0"


class IndexBaseValue(BaseModel):
    month: str  # "YYYY-MM"
    value: Decimal


class IndexQuarterValues(BaseModel):
    months: list[str]
    values: list[Decimal]
    avg: Decimal


class IndexRef(BaseModel):
    """Single-series index reference, base + quarter values fully echoed."""
    kind: Literal["single"] = "single"
    series: str
    base: IndexBaseValue
    quarter: IndexQuarterValues


class DerivedAvgIndexRef(BaseModel):
    """GCC 46A.9 SL4: commodity index = average across multiple series."""
    kind: Literal["derived_avg"] = "derived_avg"
    series_list: list[str]
    per_series: list[IndexRef]
    base_avg: Decimal
    quarter_avg: Decimal


IndexRefUnion = Annotated[IndexRef | DerivedAvgIndexRef, Field(discriminator="kind")]


class SteelSubComponentTrace(BaseModel):
    weight: Decimal
    index_ref: IndexRef


class ComponentTrace(BaseModel):
    """Per-component provenance.

    For general (labour/plant/fuel/materials) and cement: `index_ref` is set,
    `commodity_index_ref`/`sub_components` are None.
    For steel buckets: `commodity_index_ref` and `sub_components` are set,
    `index_ref` is None.
    """
    category: str
    formula: str                       # stable identifier (e.g. "steel_bucket_pvc")
    formula_expanded: str              # human-readable formula string
    input_field: str
    eligible_amount: Decimal
    weight: Decimal
    pvc_value: Decimal
    index_ref: IndexRef | None = None
    commodity_index_ref: IndexRefUnion | None = None
    sub_components: dict[str, SteelSubComponentTrace] | None = None


class CarryForwardContribution(BaseModel):
    item_id: str
    source_ref: str | None
    prorated_amount: Decimal


class WDerivationLine(BaseModel):
    value: Decimal
    input_field: str
    carry_forward_contributions: list[CarryForwardContribution] = []


class WDerivationTrace(BaseModel):
    formula: str
    inputs: dict[str, WDerivationLine]
    w: Decimal


class CarryForwardTrace(BaseModel):
    item_id: str
    bill_line_ref: str | None          # echoed source_ref
    input_field: str
    formula: str
    recorded_qty: Decimal
    paid_qty_source: Decimal
    paid_ratio: Decimal
    amount: Decimal
    prorated_amount: Decimal
    steel_subtype: Literal["angles", "plates", "other_sections", "tmt"] | None
    applied_to_bucket: str | None


class ExtraItemTrace(BaseModel):
    item_id: str
    bill_line_ref: str | None          # echoed source_ref
    input_field: str
    formula: str
    amount: Decimal
    eligible: bool | None
    applied_to_w_subtraction: bool     # True only if eligible is False


class TraceContract(BaseModel):
    schema_version: Literal["1.0"] = TRACE_SCHEMA_VERSION
    quarter_used: str | None
    quarter_months: list[str]
    base_month: str
    prior_negative_carry_forward: Decimal
    w_derivation: WDerivationTrace | None  # None when run is blocked before W is derived
    components: dict[str, ComponentTrace]
    carry_forwards: list[CarryForwardTrace]
    extra_item_decisions: list[ExtraItemTrace]


class PVCRunResult(BaseModel):
    w: Decimal | None
    w_derivation: WDerivation | None
    components: list[PVCComponent]
    total_pvc: Decimal | None
    negative_carry_forward: Decimal  # amount to recover from next bill (zero_floor policy)
    quarter_used: str | None
    quarter_months: list[str]
    trace: TraceContract
    validation_errors: list[str]
