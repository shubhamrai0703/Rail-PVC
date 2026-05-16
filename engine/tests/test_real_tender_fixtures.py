from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import pytest

from engine import calculate_pvc
from engine.types import BillPayload, IndexSnapshot, PVCRuleSet


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "real_tenders"


def _fixture_paths() -> list[Path]:
    return sorted(FIXTURE_DIR.glob("*.json"))


@pytest.mark.parametrize("path", _fixture_paths(), ids=lambda path: path.stem)
def test_real_tender_fixture_matches_expected_total(path: Path):
    data = json.loads(path.read_text())
    expected = data.get("expected", {})
    assert "total_pvc" in expected, f"{path.name} must define expected.total_pvc"

    result = calculate_pvc(
        bill=BillPayload.model_validate(data["bill"]),
        indices=IndexSnapshot.model_validate(data["indices"]),
        rules=PVCRuleSet.model_validate(data["rules"]),
    )

    assert result.validation_errors == [], f"{path.name} blocked: {result.validation_errors}"
    assert result.total_pvc == Decimal(str(expected["total_pvc"]))


def test_real_tender_fixture_directory_documented():
    if _fixture_paths():
        return
    pytest.skip("No real tender fixtures added yet. Add JSON files under engine/tests/fixtures/real_tenders/.")
