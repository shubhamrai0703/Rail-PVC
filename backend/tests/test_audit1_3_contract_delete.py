"""AUDIT-1-3: DELETE /api/contracts/{contract_id}.

Only Draft contracts may be deleted. The FK cascade in the DB handles
child records (schedules, items, bills, documents). Three paths:
  - draft contract → 204 No Content; DELETE SQL runs
  - non-draft contract → ValidationProblem(422)
  - wrong tenant (or unknown id) → NotFoundProblem(404)
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from api.contracts import delete_contract
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


def _status_row(status: str) -> MagicMock:
    result = MagicMock()
    mappings = MagicMock()
    mappings.first.return_value = {"status": status}
    result.mappings.return_value = mappings
    return result


def _not_found_row() -> MagicMock:
    result = MagicMock()
    mappings = MagicMock()
    mappings.first.return_value = None
    result.mappings.return_value = mappings
    return result


@pytest.mark.asyncio
async def test_delete_draft_contract_succeeds():
    session = AsyncMock()
    session.execute = AsyncMock(side_effect=[_status_row("Draft"), AsyncMock()])

    response = await delete_contract(
        contract_id="contract-draft",
        user=_user(),
        session=session,
    )

    assert response.status_code == 204
    assert session.execute.await_count == 2


@pytest.mark.asyncio
@pytest.mark.parametrize("contract_status", ["Approved", "Superseded", "ExceptionFlagged"])
async def test_delete_non_draft_contract_raises_validation(contract_status):
    session = AsyncMock()
    session.execute = AsyncMock(side_effect=[_status_row(contract_status)])

    with pytest.raises(ValidationProblem) as exc:
        await delete_contract(
            contract_id="contract-active",
            user=_user(),
            session=session,
        )

    assert exc.value.status_code == 422
    assert exc.value.extra["field"] == "status"
    assert session.execute.await_count == 1


@pytest.mark.asyncio
async def test_delete_wrong_tenant_raises_not_found():
    session = AsyncMock()
    session.execute = AsyncMock(side_effect=[_not_found_row()])

    with pytest.raises(NotFoundProblem) as exc:
        await delete_contract(
            contract_id="contract-foreign",
            user=_user(),
            session=session,
        )

    assert exc.value.status_code == 404
    assert exc.value.extra["entity"] == "contract"
    assert session.execute.await_count == 1
