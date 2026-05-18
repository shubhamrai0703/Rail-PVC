"""P3-BF-3 / TEST-01: recoveries endpoint validation + tenant gate.

The route under test (`api/bills.py::create_recovery`) has two pre-INSERT
gates the frontend depends on:

  * `recovery_type` must be in `VALID_RECOVERY_TYPES` — otherwise the
    Postgres ENUM CAST would 500 with a leaky pg error. We surface it as
    a typed `ValidationProblem(field="recovery_type")` so the form can
    point at the offending field.

  * The bill must belong to the caller's tenant — `assert_bill_belongs_to_tenant`
    raises `NotFoundProblem` (deliberately not 403, to avoid ID-probing
    side channels — same discipline as P3-06).

The INSERT itself is Postgres-specific (`CAST(:rtype AS recovery_type)`,
`id::text`) so we test through `AsyncMock` at the session boundary
rather than aiosqlite. That keeps the test hermetic and pins the actual
route-handler logic, not a re-implementation of it.
"""
from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from api.bills import RecoveryCreate, create_recovery
from services.auth import AuthUser
from services.errors import NotFoundProblem, ValidationProblem


def _user() -> AuthUser:
    return AuthUser(
        user_id="user-1",
        tenant_id="tenant-A",
        auth_id="auth-1",
        email="t@example.com",
        display_name="t@example.com",
    )


def _session_returning(*rows) -> AsyncMock:
    """AsyncSession stub. Each call to `session.execute()` returns a
    Result-shaped object whose `.mappings().first()` (and `.first()`)
    yields the next supplied row, in order. `None` is a legitimate row."""
    session = AsyncMock()
    results = []
    for row in rows:
        result = MagicMock()
        mappings = MagicMock()
        mappings.first.return_value = row
        result.mappings.return_value = mappings
        result.first.return_value = row
        results.append(result)
    session.execute = AsyncMock(side_effect=results)
    return session


@pytest.mark.asyncio
async def test_valid_recovery_type_succeeds():
    # First execute = assert_bill_belongs_to_tenant SELECT → returns contract_id.
    # Second execute = INSERT … RETURNING id → returns inserted row.
    session = _session_returning(
        {"contract_id": "contract-own"},
        {"id": "recovery-1"},
    )
    body = RecoveryCreate(
        recovery_type="security_deposit",
        amount=Decimal("100.00"),
        affects_pvc_base=False,
    )
    out = await create_recovery(
        bill_id="bill-own", body=body, user=_user(), session=session
    )
    assert out["id"] == "recovery-1"
    assert out["bill_id"] == "bill-own"
    assert out["recovery_type"] == "security_deposit"


@pytest.mark.asyncio
async def test_invalid_recovery_type_raises_validation_problem():
    # Validation fires before any DB call — session.execute must not be invoked.
    session = AsyncMock()
    session.execute = AsyncMock()

    body = RecoveryCreate(
        recovery_type="bogus_type",
        amount=Decimal("10.00"),
    )
    with pytest.raises(ValidationProblem) as exc:
        await create_recovery(
            bill_id="bill-own", body=body, user=_user(), session=session
        )

    assert exc.value.status_code == 422
    assert exc.value.code == "validation_error"
    assert exc.value.extra["field"] == "recovery_type"
    assert exc.value.extra["value"] == "bogus_type"
    session.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_wrong_tenant_bill_raises_not_found():
    # `assert_bill_belongs_to_tenant` returns None → NotFoundProblem(404).
    # The route must surface 404 (NOT 403) so callers can't probe IDs.
    session = _session_returning(None)

    body = RecoveryCreate(
        recovery_type="security_deposit",
        amount=Decimal("100.00"),
    )
    with pytest.raises(NotFoundProblem) as exc:
        await create_recovery(
            bill_id="bill-foreign", body=body, user=_user(), session=session
        )

    assert exc.value.status_code == 404
    assert exc.value.extra["entity"] == "running_bill"
    assert exc.value.extra["id"] == "bill-foreign"
