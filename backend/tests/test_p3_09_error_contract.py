"""P3-09 regression: structured error contract.

The reviewed implementation returned mixed `detail` shapes (sometimes a
string, sometimes a dict) and the frontend `apiFetch()` helper only
surfaced the string variant. Engine-blocked runs and idempotency conflicts
collapsed into generic toasts.

The remediation defines `ApiProblem` subclasses with a typed payload
{code, message, ...extra}, registered via FastAPI exception handlers
so every error response uses the same shape.
"""
from __future__ import annotations

from services.errors import (
    EngineValidationProblem,
    IdempotencyConflict,
    ImmutableApprovedRun,
    NotFoundProblem,
    ValidationProblem,
)


def test_engine_validation_includes_full_error_list():
    p = EngineValidationProblem(["missing index for 2025-05", "eligible=None for item-X"])
    detail = p.to_detail()
    assert detail["code"] == "engine_validation_error"
    assert detail["validation_errors"] == [
        "missing index for 2025-05",
        "eligible=None for item-X",
    ]
    assert p.status_code == 422


def test_idempotency_conflict_carries_existing_run_id():
    p = IdempotencyConflict("run-abc")
    assert p.to_detail() == {
        "code": "idempotency_conflict",
        "message": "A run already exists for this idempotency key",
        "run_id": "run-abc",
    }
    assert p.status_code == 409


def test_immutable_approved_run_uses_distinct_code():
    p = ImmutableApprovedRun("run-xyz")
    assert p.to_detail()["code"] == "immutable_approved_run"
    assert p.to_detail()["run_id"] == "run-xyz"
    assert p.status_code == 409


def test_validation_problem_passes_extra_fields():
    p = ValidationProblem("bad value", field="railway_zone", value="ZZ")
    detail = p.to_detail()
    assert detail["field"] == "railway_zone"
    assert detail["value"] == "ZZ"


def test_not_found_problem_returns_404():
    p = NotFoundProblem("missing", entity="contract", id="c-1")
    assert p.status_code == 404
    assert p.to_detail()["entity"] == "contract"
