from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel


class ExtraItemDecision(BaseModel):
    item_id: str
    amount: Decimal
    eligible: bool | None = None  # None = undecided; blocks run


class CarryForwardPayload(BaseModel):
    item_id: str
    recorded_qty: Decimal
    paid_qty_source: Decimal
    paid_ratio: Decimal
    carry_qty: Decimal
    amount: Decimal  # total monetary value of this carry-forward item
    steel_subtype: Literal["angles", "plates", "other_sections", "tmt"] | None = None


class BillPayload(BaseModel):
    on_account_amount: Decimal
    cement_amount: Decimal
    steel_angles_amount: Decimal
    steel_plates_amount: Decimal
    steel_other_amount: Decimal
    technical_withheld: Decimal
    extra_item_decisions: list[ExtraItemDecision]  # P2-004: eligible=None blocks run
    carry_forwards: list[CarryForwardPayload]
    measurement_date: date  # must be the "To" date of the measurement period
    prior_negative_carry_forward: Decimal = Decimal("0")  # recovery from previous bill


class IndexSnapshot(BaseModel):
    base_month: date
    series: dict[str, dict[str, Decimal]]  # {series_name: {"YYYY-MM": value}}


class PVCRuleSet(BaseModel):
    quarter_mode: Literal["measurement_date", "bill_date"]
    component_weights: dict[str, Decimal]  # weights for general W components
    adjustable_fraction: Decimal           # typically 0.85
    negative_pvc_policy: Literal["allow", "block", "zero_floor"]
    rounding_mode: Literal["round_2", "truncate_2"]


class WDerivation(BaseModel):
    on_account_amount: Decimal
    cement: Decimal
    steel_angles: Decimal
    steel_plates: Decimal
    steel_other: Decimal
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


class PVCRunResult(BaseModel):
    w: Decimal | None
    w_derivation: WDerivation | None
    components: list[PVCComponent]
    total_pvc: Decimal | None
    negative_carry_forward: Decimal  # amount to recover from next bill (zero_floor policy)
    quarter_used: str | None
    quarter_months: list[str]
    trace: dict
    validation_errors: list[str]
