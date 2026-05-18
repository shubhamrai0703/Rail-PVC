"""Document uploads under a contract (P3-BF-4).

Two endpoints:

  * `POST /api/contracts/{contract_id}/documents` — multipart upload. Streams
    the file in 1 MB chunks to enforce the 50 MB cap without loading an
    oversized blob into memory. Uploads to Supabase Storage, then records
    one row in `documents` with the storage_path.
  * `GET  /api/contracts/{contract_id}/documents` — list documents under
    the contract.

No parsing in v1; the file is stored as-is for download/audit only.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from services.auth import AuthUser, get_current_user
from services.db import get_session
from services.errors import PayloadTooLargeProblem, ValidationProblem
from services.pvc_service import assert_contract_belongs_to_tenant
from services.storage import (
    MAX_FILE_BYTES,
    VALID_DOCUMENT_TYPES,
    build_storage_path,
    upload_document,
)

router = APIRouter(prefix="/api", tags=["documents"])


# 1 MB chunk — small enough that an oversized client gets rejected after
# overshooting by at most one chunk; large enough that a 50 MB legitimate
# upload completes in ~50 reads.
_CHUNK_BYTES = 1024 * 1024


async def _read_capped(file: UploadFile) -> bytes:
    """Drain `file` into a bytes buffer, raising PayloadTooLargeProblem the
    moment the running total exceeds MAX_FILE_BYTES. Never trusts a
    Content-Length header — multipart clients can lie or omit it."""
    buffer = bytearray()
    while chunk := await file.read(_CHUNK_BYTES):
        buffer.extend(chunk)
        if len(buffer) > MAX_FILE_BYTES:
            raise PayloadTooLargeProblem(MAX_FILE_BYTES)
    return bytes(buffer)


@router.post(
    "/contracts/{contract_id}/documents",
    status_code=status.HTTP_201_CREATED,
)
async def upload_contract_document(
    contract_id: str,
    file_type: str = Form(...),
    file: UploadFile = File(...),
    user: AuthUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    if file_type not in VALID_DOCUMENT_TYPES:
        raise ValidationProblem(
            f"file_type must be one of {sorted(VALID_DOCUMENT_TYPES)}",
            field="file_type",
            value=file_type,
        )

    await assert_contract_belongs_to_tenant(session, contract_id, user.tenant_id)

    content = await _read_capped(file)
    storage_path = build_storage_path(user.tenant_id, contract_id, file.filename or "")
    await upload_document(
        path=storage_path,
        content=content,
        content_type=file.content_type or "application/octet-stream",
    )

    row = (
        await session.execute(
            text("""
                INSERT INTO documents (
                    contract_id, file_type, storage_path, original_filename
                )
                VALUES (
                    :cid, CAST(:ftype AS document_type), :path, :fname
                )
                RETURNING id::text AS id, uploaded_at
            """),
            {
                "cid": contract_id,
                "ftype": file_type,
                "path": storage_path,
                "fname": file.filename or "",
            },
        )
    ).mappings().first()
    assert row is not None
    return {
        "id": row["id"],
        "contract_id": contract_id,
        "file_type": file_type,
        "storage_path": storage_path,
        "original_filename": file.filename or "",
        "uploaded_at": row["uploaded_at"],
    }


@router.get("/contracts/{contract_id}/documents")
async def list_contract_documents(
    contract_id: str,
    user: AuthUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[dict[str, Any]]:
    await assert_contract_belongs_to_tenant(session, contract_id, user.tenant_id)

    rows = (
        await session.execute(
            text("""
                SELECT id::text AS id,
                       contract_id::text AS contract_id,
                       file_type::text AS file_type,
                       storage_path,
                       original_filename,
                       uploaded_at
                FROM documents
                WHERE contract_id = :cid
                ORDER BY uploaded_at DESC
            """),
            {"cid": contract_id},
        )
    ).mappings().all()
    return [dict(r) for r in rows]
