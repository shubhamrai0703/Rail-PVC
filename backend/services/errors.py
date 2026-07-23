"""Structured error contract shared by the API layer (P3-09 remediation).

The frontend `apiFetch()` helper expects every non-2xx response to carry an
actionable `detail` payload it can render to the user without inventing copy.
We standardise on three shapes:

  * `ValidationProblem`   — 422 — engine validation_errors or input-format issues
  * `ConflictProblem`     — 409 — idempotency / immutability collisions
  * `NotFoundProblem`     — 404 — entity not visible to caller (also used for
                             "wrong tenant" so callers cannot probe IDs)

All three serialise as `{ "detail": { "code": str, "message": str, ... } }`
so the frontend can switch on `detail.code` and render the rest as context.

The corresponding exception classes carry the same payload shape and are
mapped to JSONResponses by `register_exception_handlers`.
"""
from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel


class ApiProblemDetail(BaseModel):
    code: str
    message: str
    contract_id: str | None = None
    blockers: list[str] | None = None
    entity: str | None = None
    id: str | None = None
    field: str | None = None
    value: Any | None = None


class ApiProblemResponse(BaseModel):
    detail: ApiProblemDetail


class ApiProblem(Exception):
    """Base class for all structured API errors."""

    status_code: int = 500
    code: str = "internal_error"

    def __init__(self, message: str, **extra: Any) -> None:
        super().__init__(message)
        self.message = message
        self.extra = extra

    def to_detail(self) -> dict[str, Any]:
        return {"code": self.code, "message": self.message, **self.extra}


class ValidationProblem(ApiProblem):
    status_code = 422
    code = "validation_error"


class ContractDeletionBlocked(ValidationProblem):
    """A Draft contract has immutable/audit-bearing children.

    Those rows intentionally do not cascade. Returning their categories lets
    the UI explain why deletion is unavailable without exposing row contents.
    """

    code = "contract_deletion_blocked"

    def __init__(self, contract_id: str, blockers: list[str]) -> None:
        super().__init__(
            "Contract cannot be deleted because it has calculation history",
            contract_id=contract_id,
            blockers=blockers,
        )


class FieldNotNullableProblem(ValidationProblem):
    """Caller sent an explicit `null` for a column declared NOT NULL in the
    schema. We surface this as a structured 422 (`code=field_not_nullable`)
    so clients can render an actionable inline error instead of receiving
    the raw asyncpg/Postgres 500 that the constraint would otherwise raise."""

    code = "field_not_nullable"

    def __init__(self, field: str) -> None:
        super().__init__(
            f"Field '{field}' cannot be cleared (column is NOT NULL)",
            field=field,
        )


class CementSteelConflictProblem(ValidationProblem):
    """An item cannot belong to both the cement and steel W-derivation
    buckets — they are mutually exclusive in the engine. Reject at the API
    boundary so wrong PVC numbers can't be produced from valid-looking
    inputs."""

    code = "cement_steel_conflict"

    def __init__(self) -> None:
        super().__init__(
            "An item cannot be both a cement item and a steel item",
        )


class RunNotApprovedProblem(ValidationProblem):
    """A PVC run can only be exported once it has been Approved. Draft and
    superseded runs are rejected at the export boundary with a structured
    422 (`code=run_not_approved`) so the frontend can disable/explain the
    download rather than handing the user a half-formed report."""

    code = "run_not_approved"

    def __init__(self, run_id: str, status: str) -> None:
        super().__init__(
            f"Run must be Approved to export (current status: {status})",
            run_id=run_id,
            status=status,
        )


class EngineValidationProblem(ApiProblem):
    """Engine returned validation_errors — surface them as a structured list."""

    status_code = 422
    code = "engine_validation_error"

    def __init__(self, errors: list[str]) -> None:
        super().__init__(
            message="PVC run blocked by engine validation",
            validation_errors=errors,
        )


class ConflictProblem(ApiProblem):
    status_code = 409
    code = "conflict"


class IdempotencyConflict(ConflictProblem):
    code = "idempotency_conflict"

    def __init__(self, run_id: str) -> None:
        super().__init__(
            message="A run already exists for this idempotency key",
            run_id=run_id,
        )


class ImmutableApprovedRun(ConflictProblem):
    code = "immutable_approved_run"

    def __init__(self, run_id: str) -> None:
        super().__init__(
            message="Approved runs are immutable; create a superseding run instead",
            run_id=run_id,
        )


class NotFoundProblem(ApiProblem):
    status_code = 404
    code = "not_found"


class AuthProblem(ApiProblem):
    status_code = 401
    code = "unauthenticated"


class ForbiddenProblem(ApiProblem):
    status_code = 403
    code = "forbidden"


class StorageProblem(ApiProblem):
    """503 Service Unavailable — used when the external storage backend
    (Supabase Storage) fails an upload/download. We surface 503 rather
    than letting the underlying SDK exception escape as an untyped 500
    so the frontend can render an actionable "storage unavailable —
    please retry" message and route the user accordingly."""

    status_code = 503
    code = "storage_unavailable"


class PayloadTooLargeProblem(ApiProblem):
    """413 Payload Too Large — used by the documents upload (P3-BF-4) when
    a multipart body exceeds the per-file size cap. Carries `max_bytes` so
    the frontend can render an exact ceiling rather than guessing."""

    status_code = 413
    code = "payload_too_large"

    def __init__(self, max_bytes: int) -> None:
        super().__init__(
            message=f"File exceeds the {max_bytes}-byte upload cap",
            max_bytes=max_bytes,
        )


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiProblem)
    async def _handle(_: Request, exc: ApiProblem) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.to_detail()},
        )
