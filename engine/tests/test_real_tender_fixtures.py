from __future__ import annotations

import json
from decimal import Decimal
from functools import cache
from pathlib import Path
from typing import Any

import pytest

from engine import calculate_pvc
from engine.types import BillPayload, IndexSnapshot, PVCRuleSet


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "real_tenders"


def _fixture_paths() -> list[Path]:
    return sorted(FIXTURE_DIR.glob("*.json"))


@cache
def _fixture_data(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


@pytest.mark.parametrize("path", _fixture_paths(), ids=lambda path: path.stem)
def test_real_tender_fixture_matches_expected_total(path: Path):
    data = _fixture_data(path)
    expected = data.get("expected", {})
    notes = data.get("notes", {})
    assert "total_pvc" in expected, f"{path.name} must define expected.total_pvc"

    result = calculate_pvc(
        bill=BillPayload.model_validate(data["bill"]),
        indices=IndexSnapshot.model_validate(data["indices"]),
        rules=PVCRuleSet.model_validate(data["rules"]),
    )

    if result.validation_errors:
        expected_errors = notes.get("expected_validation_errors")
        assert expected_errors is not None, (
            f"{path.name} has undocumented validation errors: {result.validation_errors}"
        )
        assert result.validation_errors == expected_errors, (
            f"{path.name} validation errors changed: actual={result.validation_errors}, "
            f"expected={expected_errors}"
        )
        assert notes.get("xfail_reason"), (
            f"{path.name} documents expected validation errors without an xfail reason"
        )
        pytest.xfail(notes["xfail_reason"])
    assert result.validation_errors == [], f"{path.name} blocked: {result.validation_errors}"
    assert result.total_pvc is not None
    expected_total = Decimal(str(expected["total_pvc"]))
    tolerance = Decimal(str(expected.get("tolerance", "0")))
    difference = abs(result.total_pvc - expected_total)
    if difference > tolerance and notes.get("xfail_reason"):
        pinned_total = notes.get("current_engine_total")
        assert pinned_total is not None, (
            f"{path.name} must pin notes.current_engine_total before xfail can hide a mismatch"
        )
        assert result.total_pvc == Decimal(str(pinned_total)), (
            f"{path.name} engine output changed independently of its documented mismatch: "
            f"actual={result.total_pvc}, pinned={pinned_total}"
        )
        pytest.xfail(notes["xfail_reason"])
    assert difference <= tolerance, (
        f"{path.name}: actual={result.total_pvc}, expected={expected_total}, "
        f"tolerance={tolerance}"
    )


def test_real_tender_fixture_directory_not_empty():
    """Phase 2 acceptance requires at least one real-tender regression fixture."""
    paths = _fixture_paths()
    assert paths, (
        "No real-tender fixtures found in engine/tests/fixtures/real_tenders/. "
        "At least one BCT-24-25-252 fixture (Bill-1/Bill-2) must be present to "
        "guard against engine-level numeric drift."
    )


def test_real_tender_fixture_documents_divergence_where_present():
    """Any fixture whose notes claim a workbook divergence must spell it out."""
    for path in _fixture_paths():
        data = _fixture_data(path)
        notes = data.get("notes", {})
        status = notes.get("reconciliation_status")
        if status == "workbook_divergence":
            assert notes.get("workbook_divergence"), (
                f"{path.name} has workbook_divergence status but no explanation"
            )
        verified = notes.get("verified_against", "")
        if "DIVERGES" in verified or "diverges" in verified.lower():
            assert notes.get("workbook_divergence"), (
                f"{path.name} flags a workbook divergence but does not document it "
                f"in notes.workbook_divergence"
            )


def test_real_tender_fixture_metadata_is_valid():
    for path in _fixture_paths():
        data = _fixture_data(path)
        expected = data.get("expected", {})
        tolerance = Decimal(str(expected.get("tolerance", "0")))
        assert tolerance.is_finite(), f"{path.name} expected.tolerance must be finite"
        assert Decimal("0") <= tolerance <= Decimal("0.15"), (
            f"{path.name} expected.tolerance must be between 0 and 0.15"
        )
        if tolerance > Decimal("0.01"):
            assert data.get("notes", {}).get("tolerance_reason"), (
                f"{path.name} must explain tolerance above 0.01"
            )

        reason = data.get("notes", {}).get("xfail_reason")
        if reason:
            assert reason.startswith("KU-001"), (
                f"{path.name} notes.xfail_reason must identify KU-001"
            )
            assert (
                data.get("notes", {}).get("current_engine_total") is not None
                or data.get("notes", {}).get("expected_validation_errors")
            ), f"{path.name} must pin the exact outcome hidden by xfail"

        status = data.get("notes", {}).get("reconciliation_status")
        if status is not None:
            assert status in {"reconciles", "ku_001_pending", "workbook_divergence"}, (
                f"{path.name} has unknown reconciliation_status={status!r}"
            )
