"""Run one real-tender fixture and compare its total using fixture tolerance."""
from __future__ import annotations

import argparse
import json
from decimal import Decimal
from pathlib import Path
from typing import Any, cast

from engine import calculate_pvc
from engine.types import BillPayload, IndexSnapshot, PVCRuleSet


def _load_fixture(path: Path) -> dict[str, Any]:
    data = cast(dict[str, Any], json.loads(path.read_text()))
    required = {"bill", "indices", "rules"}
    missing = required - data.keys()
    if missing:
        raise ValueError(f"Fixture missing required top-level keys: {sorted(missing)}")
    return data


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("fixture", type=Path)
    parser.add_argument(
        "--fail-on-mismatch",
        action="store_true",
        help="exit non-zero when expected.total_pvc differs beyond expected.tolerance",
    )
    args = parser.parse_args()

    payload = _load_fixture(args.fixture)
    result = calculate_pvc(
        bill=BillPayload.model_validate(payload["bill"]),
        indices=IndexSnapshot.model_validate(payload["indices"]),
        rules=PVCRuleSet.model_validate(payload["rules"]),
    )
    expected = payload.get("expected", {})
    expected_total = Decimal(str(expected["total_pvc"]))
    tolerance = Decimal(str(expected.get("tolerance", "0")))
    actual = result.total_pvc
    difference = abs(actual - expected_total) if actual is not None else None
    matches = (
        not result.validation_errors
        and difference is not None
        and difference <= tolerance
    )
    output = {
        "fixture": str(args.fixture),
        "quarter_used": result.quarter_used,
        "quarter_months": result.quarter_months,
        "validation_errors": result.validation_errors,
        "comparison": {
            "matches_total_pvc": matches,
            "actual_total_pvc": str(actual) if actual is not None else None,
            "expected_total_pvc": str(expected_total),
            "difference": str(difference) if difference is not None else None,
            "tolerance": str(tolerance),
        },
    }
    print(json.dumps(output, indent=2))
    return 1 if args.fail_on_mismatch and not matches else 0


if __name__ == "__main__":
    raise SystemExit(main())
