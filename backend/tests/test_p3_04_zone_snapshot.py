"""P3-04 regression: when both a generic steel series and a city-specific
variant are present, the city-specific value MUST win.

The reviewed implementation aliased the city-suffixed series to the engine
name only when the generic was absent. With both seeded, the generic won
and two contracts in different zones received identical snapshots.
"""
from __future__ import annotations

from decimal import Decimal

import pytest

from services.zone_mapping import city_for_zone
from services.pvc_service import select_zone_series


def _val(v: str) -> dict[str, Decimal]:
    return {"2025-01": Decimal(v)}


def test_city_specific_steel_overrides_generic_when_both_present():
    available = {
        "steel_tmt": _val("100"),                # generic — must NOT win
        "steel_tmt_kolkata": _val("200"),        # city-specific for ER → Kolkata
        "steel_angles_kolkata": _val("210"),
        "steel_plates_kolkata": _val("220"),
        "cement": _val("50"),
    }
    out = select_zone_series(available, "ER")
    assert out["steel_tmt"]["2025-01"] == Decimal("200"), (
        "city-specific Kolkata price must override the generic series for ER zone"
    )
    assert "steel_tmt_kolkata" not in out, "city-specific key should be consumed, not duplicated"
    assert out["cement"]["2025-01"] == Decimal("50"), "non-steel series passes through unchanged"


def test_two_zones_get_different_snapshots_when_city_data_seeded():
    available = {
        "steel_tmt": _val("100"),
        "steel_tmt_kolkata": _val("200"),
        "steel_tmt_delhi": _val("300"),
        "steel_angles_kolkata": _val("1"),
        "steel_plates_kolkata": _val("1"),
        "steel_angles_delhi": _val("1"),
        "steel_plates_delhi": _val("1"),
    }
    er = select_zone_series(available, "ER")    # → Kolkata
    nr = select_zone_series(available, "NR")    # → Delhi
    assert er["steel_tmt"]["2025-01"] == Decimal("200")
    assert nr["steel_tmt"]["2025-01"] == Decimal("300")


def test_generic_used_when_no_city_specific_available():
    available = {
        "steel_tmt": _val("100"),
        "steel_angles": _val("110"),
        "steel_plates": _val("120"),
    }
    out = select_zone_series(available, "NR")
    assert out["steel_tmt"]["2025-01"] == Decimal("100")


def test_zone_to_city_mapping_matches_gcc():
    # KU-006: spot-check each zone group to make sure the mapping table itself
    # didn't drift. If you change a mapping, this test should fail and force
    # you to re-read GCC 46A.9(2).
    assert city_for_zone("NR") == "Delhi"
    assert city_for_zone("ER") == "Kolkata"
    assert city_for_zone("CR") == "Mumbai"
    assert city_for_zone("SR") == "Chennai"
    with pytest.raises(ValueError):
        city_for_zone("INVALID-ZONE")
