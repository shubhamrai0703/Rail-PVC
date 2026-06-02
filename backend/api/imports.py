"""Items-import templates + AI-assisted column mapping (P5-IMP).

The items-import flow in the frontend takes a raw BOQ Excel sheet (or
pasted TSV) and resolves it against the canonical `contract_items`
schema (item_code, description, unit, original_qty, revised_qty,
base_rate, agreement_rate, is_cement_item, steel_subtype).

Two pieces live here:

  1. **Template CRUD** — saved column-mapping templates per tenant. The
     frontend resolves `source_signature` (hash of normalized headers)
     to a saved template so the *second* import from the same vendor
     format is one click.

  2. **suggest-mapping** — calls Claude Haiku 4.5 with the source
     headers + a few sample rows, returns a proposed mapping plus
     value normalizations (e.g. "Cement" → true). The frontend uses
     this only when the deterministic header fuzzy-matcher (Option A)
     leaves required fields unmapped.

Tenant isolation follows the established pattern: every query filters
on `tenant_id` from the JWT (the privileged DB connection bypasses
RLS).
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from services.auth import AuthUser, get_current_user
from services.db import get_session
from services.errors import ConflictProblem, NotFoundProblem, ValidationProblem
from services.llm import suggest_mapping_via_llm

router = APIRouter(prefix="/api/imports", tags=["imports"])


# ---------------------------------------------------------------------------
# Target schema (mirrors frontend lib/fuzzyHeaderMap.ts TARGET_FIELDS)
# ---------------------------------------------------------------------------

_TARGET_FIELDS = frozenset({
    "item_code",
    "description",
    "unit",
    "original_qty",
    "revised_qty",
    "base_rate",
    "agreement_rate",
    "is_cement_item",
    "steel_subtype",
})


def _validate_mapping(mapping: dict[str, str | None]) -> None:
    """Reject mappings that point to unknown target fields.

    Empty / null target means "ignore this column" — allowed.
    """
    for src, tgt in mapping.items():
        if tgt is None or tgt == "":
            continue
        if tgt not in _TARGET_FIELDS:
            raise ValidationProblem(
                f"Unknown target field '{tgt}' for source column '{src}'",
                source=src,
                target=tgt,
                allowed=sorted(_TARGET_FIELDS),
            )


# ---------------------------------------------------------------------------
# Template CRUD
# ---------------------------------------------------------------------------


class TemplateCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    source_signature: str = Field(min_length=1, max_length=200)
    mapping: dict[str, str | None]
    value_normalizations: dict[str, dict[str, str]] = Field(default_factory=dict)


@router.get("/templates")
async def list_templates(
    source_signature: str | None = Query(default=None),
    user: AuthUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[dict[str, Any]]:
    sql = """
        SELECT id::text AS id, name, source_signature,
               mapping, value_normalizations,
               created_at, updated_at
        FROM import_templates
        WHERE tenant_id = :tenant_id
    """
    params: dict[str, Any] = {"tenant_id": user.tenant_id}
    if source_signature is not None:
        sql += " AND source_signature = :sig"
        params["sig"] = source_signature
    sql += " ORDER BY updated_at DESC"

    rows = (await session.execute(text(sql), params)).mappings().all()
    return [dict(r) for r in rows]


@router.post("/templates", status_code=201)
async def create_template(
    body: TemplateCreate,
    user: AuthUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    _validate_mapping(body.mapping)

    try:
        row = (
            await session.execute(
                text("""
                    INSERT INTO import_templates
                        (tenant_id, name, source_signature, mapping,
                         value_normalizations, created_by)
                    VALUES
                        (:tenant_id, :name, :sig,
                         CAST(:mapping AS JSONB),
                         CAST(:norms AS JSONB),
                         :created_by)
                    RETURNING id::text AS id, name, source_signature,
                              mapping, value_normalizations,
                              created_at, updated_at
                """),
                {
                    "tenant_id": user.tenant_id,
                    "name": body.name,
                    "sig": body.source_signature,
                    "mapping": _json_dump(body.mapping),
                    "norms": _json_dump(body.value_normalizations),
                    "created_by": user.user_id,
                },
            )
        ).mappings().first()
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise ConflictProblem(
            "A template with this name already exists for this tenant",
            name=body.name,
        )

    assert row is not None
    return dict(row)


@router.delete("/templates/{template_id}", status_code=204)
async def delete_template(
    template_id: str,
    user: AuthUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        text("""
            DELETE FROM import_templates
            WHERE id = :id AND tenant_id = :tenant_id
        """),
        {"id": template_id, "tenant_id": user.tenant_id},
    )
    if result.rowcount == 0:
        raise NotFoundProblem(
            "Import template not found",
            entity="import_template",
            id=template_id,
        )
    await session.commit()


# ---------------------------------------------------------------------------
# AI-assisted mapping (Option B)
# ---------------------------------------------------------------------------


class SuggestMappingBody(BaseModel):
    headers: list[str] = Field(min_length=1, max_length=100)
    sample_rows: list[list[str]] = Field(default_factory=list, max_length=10)


@router.post("/suggest-mapping")
async def suggest_mapping(
    body: SuggestMappingBody,
    _: AuthUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Propose a column mapping using Claude Haiku 4.5.

    Returns:
        {
          "mapping": { source_header: target_field | null, ... },
          "value_normalizations": { target_field: { source_value: canonical_value } },
          "confidence": 0..1,
          "unmapped": [source_header, ...],
          "notes": str | null,
        }

    The endpoint is read-only and does not persist anything. Errors from
    the LLM provider surface as 503 (`llm_unavailable`) so the frontend
    can fall back to the manual mapper.
    """
    return await suggest_mapping_via_llm(
        headers=body.headers,
        sample_rows=body.sample_rows,
        target_fields=sorted(_TARGET_FIELDS),
    )


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _json_dump(value: Any) -> str:
    import json
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
