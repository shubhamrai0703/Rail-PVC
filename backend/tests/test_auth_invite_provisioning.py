"""Invite-only tenant provisioning through the real auth dependency.

JWT signature verification and Postgres execution are boundary-controlled; the
tests otherwise call ``get_current_user`` directly so bearer parsing, claim
handling, provisioning decisions, and the returned tenant context stay real.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import Request

from services import auth
from services.errors import AuthProblem


def _request() -> Request:
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/api/contracts",
            "headers": [(b"authorization", b"Bearer test-token")],
        }
    )


def _session_returning(*rows: dict[str, object] | None) -> AsyncMock:
    session = AsyncMock()
    results = []
    for row in rows:
        result = MagicMock()
        mappings = MagicMock()
        mappings.first.return_value = row
        result.mappings.return_value = mappings
        results.append(result)
    session.execute = AsyncMock(side_effect=results)
    return session


def _claims(monkeypatch: pytest.MonkeyPatch, *, email: str | None) -> None:
    claims: dict[str, str] = {"sub": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"}
    if email is not None:
        claims["email"] = email
    monkeypatch.setattr(auth, "_decode", lambda _token: claims)


@pytest.mark.asyncio
async def test_invite_hit_provisions_user_and_consumes_invite(monkeypatch):
    _claims(monkeypatch, email="First.User@Example.COM")
    provisioned = {
        "id": "user-1",
        "tenant_id": "tenant-1",
        "email": "first.user@example.com",
        "is_admin": False,
    }
    session = _session_returning(None, provisioned)

    user = await auth.get_current_user(_request(), session)

    assert user.user_id == "user-1"
    assert user.tenant_id == "tenant-1"
    assert user.email == "first.user@example.com"
    assert user.is_admin is False
    session.commit.assert_awaited_once()

    statement, params = session.execute.await_args_list[1].args
    sql = str(statement)
    assert "FROM tenant_invites" in sql
    assert "FOR UPDATE" in sql
    assert "INSERT INTO users" in sql
    assert "ON CONFLICT (supabase_auth_id) DO NOTHING" in sql
    assert "UPDATE tenant_invites" in sql
    assert params == {
        "auth_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        "email": "first.user@example.com",
    }


@pytest.mark.asyncio
async def test_second_request_reuses_provisioned_user_without_consuming_again(monkeypatch):
    _claims(monkeypatch, email="first.user@example.com")
    provisioned = {
        "id": "user-1",
        "tenant_id": "tenant-1",
        "email": "first.user@example.com",
        "is_admin": False,
    }
    session = _session_returning(None, provisioned, provisioned)

    first = await auth.get_current_user(_request(), session)
    second = await auth.get_current_user(_request(), session)

    assert first == second
    assert session.execute.await_count == 3
    session.commit.assert_awaited_once()
    provisioning_statements = [
        str(call.args[0])
        for call in session.execute.await_args_list
        if "tenant_invites" in str(call.args[0])
    ]
    assert len(provisioning_statements) == 1


@pytest.mark.asyncio
async def test_invite_miss_keeps_existing_rejection(monkeypatch):
    _claims(monkeypatch, email="uninvited@example.com")
    session = _session_returning(None, None)

    with pytest.raises(AuthProblem) as exc:
        await auth.get_current_user(_request(), session)

    assert exc.value.message == "Authenticated user has no provisioned tenant"
    assert exc.value.status_code == 401
    assert session.execute.await_count == 2
    session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_concurrent_winner_is_reselected_after_invite_lock(monkeypatch):
    _claims(monkeypatch, email="first.user@example.com")
    provisioned = {
        "id": "user-1",
        "tenant_id": "tenant-1",
        "email": "first.user@example.com",
        "is_admin": False,
    }
    session = _session_returning(None, {"retry_lookup": True}, provisioned)

    user = await auth.get_current_user(_request(), session)

    assert user.user_id == "user-1"
    assert session.execute.await_count == 3
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_missing_email_claim_cannot_provision(monkeypatch):
    _claims(monkeypatch, email=None)
    session = _session_returning(None)

    with pytest.raises(AuthProblem) as exc:
        await auth.get_current_user(_request(), session)

    assert exc.value.message == "Authenticated user has no provisioned tenant"
    assert session.execute.await_count == 1
    session.commit.assert_not_awaited()
