from decimal import Decimal

import pytest

from scripts.extract_pvc_fixtures import _decimal, _optional_decimal


@pytest.mark.parametrize("value", [None, "", "-"])
def test_required_decimal_rejects_blank_cached_values(value):
    with pytest.raises(ValueError, match="cached numeric value is required"):
        _decimal(value, source="Workbook!A1")


@pytest.mark.parametrize("value", [None, "", "-"])
def test_optional_decimal_maps_blank_deductions_to_zero(value):
    assert _optional_decimal(value, source="Workbook!A1") == Decimal("0")


def test_required_decimal_accepts_indian_grouping():
    assert _decimal("14,50,835.73", source="Workbook!A1") == Decimal("1450835.73")
