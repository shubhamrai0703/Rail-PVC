from engine import calculate_pvc
from engine.types import BillPayload, IndexSnapshot, PVCRuleSet
from decimal import Decimal
from datetime import date


def test_calculate_pvc_importable():
    assert callable(calculate_pvc)


def test_calculate_pvc_returns_result():
    bill = BillPayload(
        on_account_amount=Decimal("1000000"),
        cement_amount=Decimal("0"),
        steel_angles_amount=Decimal("0"),
        steel_plates_amount=Decimal("0"),
        steel_other_amount=Decimal("0"),
        technical_withheld=Decimal("0"),
        extra_item_decisions=[],
        carry_forwards=[],
        measurement_date=date(2025, 5, 15),
    )
    indices = IndexSnapshot(
        base_month=date(2024, 12, 1),
        series={},
    )
    rules = PVCRuleSet(
        quarter_mode="measurement_date",
        component_weights={"labour": Decimal("0.20"), "plant": Decimal("0.30")},
        adjustable_fraction=Decimal("0.85"),
        negative_pvc_policy="allow",
        rounding_mode="round_2",
    )
    result = calculate_pvc(bill, indices, rules)
    assert isinstance(result.validation_errors, list)
