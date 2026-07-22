"""Document uploads under a contract (P3-BF-4).

Three endpoints:

  * `POST /api/contracts/{contract_id}/documents` — multipart upload. Streams
    the file in 1 MB chunks to enforce the 50 MB cap without loading an
    oversized blob into memory. Uploads to Supabase Storage, then records
    one row in `documents` with the storage_path.
  * `GET  /api/contracts/{contract_id}/documents` — list documents under
    the contract.
  * `GET  /api/documents/{document_id}/download-url` — tenant-gated,
    short-lived download URL for the private bucket.

No parsing in v1; the file is stored as-is for download/audit only.
"""
from __future__ import annotations

import logging
from datetime import datetime
from tempfile import TemporaryFile
from typing import BinaryIO, Literal

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from services.auth import AuthUser, get_current_user
from services.db import get_session
from services.errors import NotFoundProblem, PayloadTooLargeProblem, ValidationProblem
from services.pvc_service import assert_contract_belongs_to_tenant
from services.storage import (
    MAX_FILE_BYTES,
    VALID_DOCUMENT_TYPES,
    build_storage_path,
    create_document_download_url,
    delete_document,
    upload_document,
)

router = APIRouter(prefix="/api", tags=["documents"])
logger = logging.getLogger(__name__)


# 1 MB chunk — small enough that an oversized client gets rejected after
# overshooting by at most one chunk; large enough that a 50 MB legitimate
# upload completes in ~50 reads.
_CHUNK_BYTES = 1024 * 1024
DocumentType = Literal["agreement", "mb", "bill", "recovery", "workbook", "other"]


class DocumentRecord(BaseModel):
    id: str
    contract_id: str
    file_type: DocumentType
    storage_path: str
    original_filename: str
    uploaded_at: datetime


class DocumentDownload(BaseModel):
    download_url: str


async def _copy_capped(file: UploadFile, target: BinaryIO) -> None:
    """Copy an upload to disk while enforcing the limit from actual bytes."""
    total = 0
    while chunk := await file.read(_CHUNK_BYTES):
        total += len(chunk)
        if total > MAX_FILE_BYTES:
            raise PayloadTooLargeProblem(MAX_FILE_BYTES)
        target.write(chunk)
    target.seek(0)


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
) -> DocumentRecord:
    if file_type not in VALID_DOCUMENT_TYPES:
        raise ValidationProblem(
            f"file_type must be one of {sorted(VALID_DOCUMENT_TYPES)}",
            field="file_type",
            value=file_type,
        )

    await assert_contract_belongs_to_tenant(session, contract_id, user.tenant_id)

    storage_path = build_storage_path(user.tenant_id, contract_id, file.filename or "")
    # An unbuffered TemporaryFile is a FileIO accepted by storage3. This keeps
    # the 50 MB cap without holding two full in-memory copies of the upload.
    with TemporaryFile(mode="w+b", buffering=0) as content:
        await _copy_capped(file, content)
        await upload_document(
            path=storage_path,
            content=content,
            content_type=file.content_type or "application/octet-stream",
        )

    try:
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
        # Storage and Postgres cannot share a transaction. Commit here so a
        # commit failure can still be compensated by removing the object.
        await session.commit()
    except Exception:
        try:
            await session.rollback()
        except Exception:  # noqa: BLE001 — preserve the original DB failure
            logger.exception("Failed to roll back document metadata insert")
        try:
            await delete_document(storage_path)
        except Exception:  # noqa: BLE001 — preserve the original DB failure
            logger.exception("Failed to remove orphaned document %s", storage_path)
        raise
    return DocumentRecord(
        id=row["id"],
        contract_id=contract_id,
        file_type=file_type,
        storage_path=storage_path,
        original_filename=file.filename or "",
        uploaded_at=row["uploaded_at"],
    )


@router.get("/contracts/{contract_id}/documents")
async def list_contract_documents(
    contract_id: str,
    user: AuthUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[DocumentRecord]:
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
    return [DocumentRecord.model_validate(dict(row)) for row in rows]


@router.get("/documents/{document_id}/download-url")
async def get_document_download_url(
    document_id: str,
    user: AuthUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> DocumentDownload:
    row = (
        await session.execute(
            text("""
                SELECT d.storage_path, d.original_filename
                FROM documents d
                JOIN contracts c ON c.id = d.contract_id
                WHERE d.id = :did AND c.tenant_id = :tid
            """),
            {"did": document_id, "tid": user.tenant_id},
        )
    ).mappings().first()
    if row is None:
        raise NotFoundProblem("Document not found", entity="document", id=document_id)

    return DocumentDownload(
        download_url=await create_document_download_url(
            row["storage_path"], row["original_filename"]
        )
    )
