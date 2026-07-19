"""P5-IMP-FUP-1: import templates CRUD + AI suggest-mapping route.

Follows the session-mock pattern from test_sh_p5_bills_get.py — SQL uses
Postgres-specific casts that aiosqlite can't execute, so we stub
session.execute at the boundary.

For suggest-mapping the LLM call is mocked to keep tests hermetic; one
additional test exercises the real _client() no-key path (deterministic via
monkeypatch) to confirm the 503 contract without hitting the Anthropic API.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.exc import IntegrityError

from api.imports import (
    SuggestMappingBody,
    TemplateCreate,
    create_template,
    delete_template,
    list_templates,
    suggest_mapping,
)
from services.auth import AuthUser
from services.errors import ConflictProblem, NotFoundProblem
from services.llm import LLMUnavailableProblem


def _user() -> AuthUser:
    return AuthUser(
        user_id="user-1",
        tenant_id="tenant-A",
        auth_id="auth-1",
        email="t@example.com",
        display_name="t@example.com",
    )


def _session_with(*results: tuple[str, object]) -> AsyncMock:
    """AsyncSession stub.

      - ("first",    row | None)  — `.mappings().first()` returns row
      - ("all",      list[row])   — `.mappings().all()` returns list
      - ("rowcount", n)           — `.rowcount` equals n
    """
    session = AsyncMock()
    mocked = []
    for kind, payload in results:
        result = MagicMock()
        if kind == "first":
            mappings = MagicMock()
            mappings.first.return_value = payload
            result.mappings.return_value = mappings
            result.first.return_value = payload
        elif kind == "all":
            mappings = MagicMock()
            mappings.all.return_value = payload
            result.mappings.return_value = mappings
        elif kind == "rowcount":
            result.rowcount = payload
        else:  # pragma: no cover
            raise ValueError(f"unknown result kind: {kind}")
        mocked.append(result)
    session.execute = AsyncMock(side_effect=mocked)
    return session


# ---------------------------------------------------------------------------
# Template CRUD — list
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_templates_empty():
    session = _session_with(("all", []))
    out = await list_templates(source_signature=None, user=_user(), session=session)
    assert out == []
    assert session.execute.await_count == 1


@pytest.mark.asyncio
async def test_list_templates_with_rows():
    rows = [
        {
            "id": "t-1",
            "name": "Template A",
            "source_signature": "abc123",
            "mapping": {"Col A": "item_code"},
            "value_normalizations": {},
            "created_at": "2026-01-01T00:00:00",
            "updated_at": "2026-01-01T00:00:00",
        },
    ]
    session = _session_with(("all", rows))
    out = await list_templates(source_signature=None, user=_user(), session=session)
    assert out == rows
    assert session.execute.await_count == 1


@pytest.mark.asyncio
async def test_list_templates_with_signature_filter():
    rows = [
        {
            "id": "t-2",
            "name": "Template B",
            "source_signature": "def456",
            "mapping": {},
            "value_normalizations": {},
            "created_at": "2026-01-01T00:00:00",
            "updated_at": "2026-01-01T00:00:00",
        },
    ]
    session = _session_with(("all", rows))
    out = await list_templates(source_signature="def456", user=_user(), session=session)
    assert out == rows
    assert session.execute.await_count == 1


# ---------------------------------------------------------------------------
# Template CRUD — create
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_template_happy():
    row = {
        "id": "t-3",
        "name": "My Template",
        "source_signature": "sig-1",
        "mapping": {"Header": "description"},
        "value_normalizations": {},
        "created_at": "2026-01-01T00:00:00",
        "updated_at": "2026-01-01T00:00:00",
    }
    session = _session_with(("first", row))

    out = await create_template(
        body=TemplateCreate(
            name="My Template",
            source_signature="sig-1",
            mapping={"Header": "description"},
        ),
        user=_user(),
        session=session,
    )

    assert out == row
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_template_duplicate_name_raises_conflict():
    session = AsyncMock()
    session.execute = AsyncMock(side_effect=IntegrityError("unique", None, None))

    with pytest.raises(ConflictProblem) as exc:
        await create_template(
            body=TemplateCreate(
                name="Existing",
                source_signature="sig-2",
                mapping={"Col": "item_code"},
            ),
            user=_user(),
            session=session,
        )

    assert exc.value.status_code == 409
    assert exc.value.extra["name"] == "Existing"
    session.rollback.assert_awaited_once()


# ---------------------------------------------------------------------------
# Template CRUD — delete
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_template_happy():
    session = _session_with(("rowcount", 1))
    result = await delete_template(template_id="t-1", user=_user(), session=session)
    assert result is None
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_delete_template_not_found():
    session = _session_with(("rowcount", 0))
    with pytest.raises(NotFoundProblem) as exc:
        await delete_template(template_id="t-unknown", user=_user(), session=session)
    assert exc.value.status_code == 404
    assert exc.value.extra["entity"] == "import_template"
    assert exc.value.extra["id"] == "t-unknown"


@pytest.mark.asyncio
async def test_delete_template_wrong_tenant():
    # Tenant filter is in the WHERE clause; a foreign-tenant ID yields
    # rowcount=0 — same 404 as "not found" so callers can't probe IDs.
    session = _session_with(("rowcount", 0))
    with pytest.raises(NotFoundProblem) as exc:
        await delete_template(template_id="t-foreign", user=_user(), session=session)
    assert exc.value.status_code == 404


# ---------------------------------------------------------------------------
# AI suggest-mapping
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_suggest_mapping_happy():
    llm_result = {
        "mapping": {"BOQ Item": "item_code", "Description": "description"},
        "value_normalizations": {},
        "confidence": 0.92,
        "unmapped": [],
        "notes": None,
    }
    with patch(
        "api.imports.suggest_mapping_via_llm",
        AsyncMock(return_value=llm_result),
    ) as mock_llm:
        out = await suggest_mapping(
            body=SuggestMappingBody(
                headers=["BOQ Item", "Description"],
                sample_rows=[["1.1", "Earthwork"]],
            ),
            _=_user(),
            session=AsyncMock(),
        )

    assert out == llm_result
    mock_llm.assert_awaited_once()
    call_kwargs = mock_llm.call_args.kwargs
    assert call_kwargs["headers"] == ["BOQ Item", "Description"]
    assert call_kwargs["sample_rows"] == [["1.1", "Earthwork"]]
    assert "item_code" in call_kwargs["target_fields"]


@pytest.mark.asyncio
async def test_suggest_mapping_llm_unavailable_raises_503():
    with patch(
        "api.imports.suggest_mapping_via_llm",
        AsyncMock(side_effect=LLMUnavailableProblem("service down")),
    ):
        with pytest.raises(LLMUnavailableProblem) as exc:
            await suggest_mapping(
                body=SuggestMappingBody(headers=["Col A"]),
                _=_user(),
                session=AsyncMock(),
            )

    assert exc.value.status_code == 503


@pytest.mark.asyncio
async def test_suggest_mapping_no_api_key_raises_503(monkeypatch):
    """No OPENROUTER_API_KEY → 503 without mocking the LLM function.

    Uses monkeypatch + cache_clear to be deterministic regardless of dev env.
    The real _client() raises LLMUnavailableProblem when the key is absent;
    suggest_mapping_via_llm re-raises it; the handler propagates it.
    """
    from services.llm import _client as _llm_client

    _llm_client.cache_clear()
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    with pytest.raises(LLMUnavailableProblem) as exc:
        await suggest_mapping(
            body=SuggestMappingBody(headers=["Col A"]),
            _=_user(),
            session=AsyncMock(),
        )

    assert exc.value.status_code == 503
