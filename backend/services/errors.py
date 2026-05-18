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
