"""P3-07 regression: contract creation seeds a default PVC rule set.

The reviewed implementation inserted only the `contracts` row, so a freshly
created contract immediately 404'd on GET /pvc-rule-set. The fix is to
seed the version-1 rule set transactionally; this test pins the payload
shape so any future drift surfaces before a contract gets stuck.
"""
from __future__ import annotations

from decimal import Decimal

from engine.types import PVCRuleSet
from services.pvc_service import default_rule_set_payload


def test_default_payload_matches_engine_validator():
    """The seeded payload must satisfy the engine's own PVCRuleSet validator —
    otherwise the first PVC run after contract creation would 422."""
    payload = default_rule_set_payload()
    PVCRuleSet(
        quarter_mode=payload["quarter_mode"],
        component_weights={k: Decimal(v) for k, v in payload["component_weights"].items()},
        adjustable_fraction=Decimal(payload["adjustable_fraction"]),
        negative_pvc_policy=payload["negative_pvc_policy"],
        rounding_mode=payload["rounding_mode"],
    )


def test_default_payload_has_all_four_general_weights():
    weights = default_rule_set_payload()["component_weights"]
    assert set(weights) == {"labour", "plant", "fuel", "materials"}


def test_default_payload_uses_measurement_date_anchor():
    # KU-001: only measurement_date is valid; the seeded rule set must reflect that.
    assert default_rule_set_payload()["quarter_mode"] == "measurement_date"


def test_default_payload_uses_zero_floor_for_negative_pvc():
    # KU-003: zero-floor on this bill, carry-forward to next.
    assert default_rule_set_payload()["negative_pvc_policy"] == "zero_floor"
