from __future__ import annotations

import argparse
import json
from decimal import Decimal
from pathlib import Path
from typing import Any

from engine import calculate_pvc
from engine.types import BillPayload, IndexSnapshot, PVCRuleSet


def _json_default(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def _load_fixture(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text())
    required = {"bill", "indices", "rules"}
    missing = required - data.keys()
    if missing:
        raise ValueError(f"Fixture missing required top-level keys: {sorted(missing)}")
    return data


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the RailPVC engine against a real tender fixture and compare to an expected PVC value."
    )
    parser.add_argument("fixture", type=Path, help="Path to fixture JSON")
    parser.add_argument(
        "--fail-on-mismatch",
        action="store_true",
        help="Exit non-zero when expected.total_pvc does not match the engine output.",
    )
    args = parser.parse_args()

    payload = _load_fixture(args.fixture)

    bill = BillPayload.model_validate(payload["bill"])
    indices = IndexSnapshot.model_validate(payload["indices"])
    rules = PVCRuleSet.model_validate(payload["rules"])
    expected = payload.get("expected", {})

    result = calculate_pvc(bill=bill, indices=indices, rules=rules)

    output = {
        "fixture": str(args.fixture),
        "result": result.model_dump(mode="python"),
        "expected": expected,
    }

    if expected.get("total_pvc") is not None:
        actual = result.total_pvc
        expected_total = Decimal(str(expected["total_pvc"]))
        output["comparison"] = {
            "matches_total_pvc": actual == expected_total,
            "actual_total_pvc": str(actual) if actual is not None else None,
            "expected_total_pvc": str(expected_total),
        }

    print(json.dumps(output, indent=2, default=_json_default))

    mismatch = output.get("comparison", {}).get("matches_total_pvc") is False
    if mismatch and args.fail_on_mismatch:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
