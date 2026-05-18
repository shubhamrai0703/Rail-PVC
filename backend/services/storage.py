"""Supabase Storage adapter for the documents endpoint (P3-BF-4).

Splits into pure and IO-bound layers like services/pvc_service.py:

  * **Pure functions** — `sanitize_filename`, `build_storage_path`,
    `VALID_DOCUMENT_TYPES`, `MAX_FILE_BYTES`. No env vars read, no
    network IO. Pinned by `tests/test_p3_bf_4_documents.py`.

  * **IO-bound** — `get_storage_client`, `upload_document`. Read env at
    call time so importing this module is side-effect-free.

The async Supabase client (`acreate_client` → `AsyncClient`) is used so
the upload doesn't block the FastAPI event loop. The client is cached
per-process so we don't pay the construction cost on every request.
"""
from __future__ import annotations

import os
import re
from functools import lru_cache
from uuid import uuid4

from .errors import StorageProblem

# Matches migration 008 `document_type` ENUM.
VALID_DOCUMENT_TYPES: frozenset[str] = frozenset({
    "agreement", "mb", "bill", "recovery", "workbook", "other",
})

# 50 MB hard cap per the original P3-011 spec. Enforced by streaming the
# upload in chunks and checking the cumulative byte count — never trust the
# Content-Length header on a multipart upload because clients can lie or omit it.
MAX_FILE_BYTES: int = 50 * 1024 * 1024

# Storage bucket configured in the Supabase project (created in P0-003).
STORAGE_BUCKET: str = "documents"


_UNSAFE_CHARS = re.compile(r"[^A-Za-z0-9._-]")


def sanitize_filename(filename: str) -> str:
    """Reduce a client-supplied filename to a safe storage-path component.

    Strips any directory components (defence against `../etc/passwd` and
    Windows backslash variants), collapses unsafe characters to `_`, and
    enforces a leading non-dot character (no `.htaccess`-style names).
    Returns `"upload"` if the result would be empty.

    Pure — no path normalization against the local filesystem; we only
    care about producing a string the Supabase Storage REST API will accept.
    """
    if not filename:
        return "upload"

    # Strip any path components from BOTH separator conventions. `basename`
    # on POSIX won't strip Windows-style `\` and vice versa, so we do both.
    name = filename.replace("\\", "/").rsplit("/", 1)[-1]

    # Collapse anything not in the safe alphabet.
    name = _UNSAFE_CHARS.sub("_", name)

    # Leading dot would create a hidden file in some storage browsers.
    name = name.lstrip(".")

    # Length cap — Supabase Storage accepts up to 255 chars per segment.
    name = name[:200]

    return name or "upload"


def build_storage_path(tenant_id: str, contract_id: str, filename: str) -> str:
    """Construct the Supabase Storage key for a contract-scoped upload.

    Format: `{tenant_id}/{contract_id}/{uuid4}_{sanitized_filename}`. The
    UUID prefix guarantees no path collision even if two users upload
    the same filename simultaneously; the tenant_id + contract_id prefix
    keeps tenants partitioned at the path level (in addition to the row
    filter on the documents table).

    Pure — accepts already-validated tenant_id/contract_id strings; the
    caller is responsible for confirming the contract belongs to the
    tenant before this is called.
    """
    safe = sanitize_filename(filename)
    return f"{tenant_id}/{contract_id}/{uuid4()}_{safe}"


# ---------------------------------------------------------------------------
# IO-bound layer — async Supabase client and upload
# ---------------------------------------------------------------------------


async def _build_client():
    """Construct an async Supabase client from env. Imported lazily so
    `import services.storage` does not require Supabase env vars (matches
    services/db.py)."""
    from supabase import acreate_client  # local import; package is heavy

    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        raise RuntimeError(
            "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set to upload documents"
        )
    return await acreate_client(url, key)


@lru_cache(maxsize=1)
def _client_holder() -> dict:
    """One-slot mutable cache for the lazily-built async client. lru_cache
    on the *factory* doesn't compose with async, so we cache a dict and
    fill it on first use."""
    return {}


async def get_storage_client():
    holder = _client_holder()
    if "client" not in holder:
        holder["client"] = await _build_client()
    return holder["client"]


async def upload_document(path: str, content: bytes, content_type: str) -> None:
    """Upload `content` to Supabase Storage at `path` under the documents
    bucket. Any failure from the storage SDK — network error, auth error,
    duplicate key, bucket missing — is wrapped in `StorageProblem(503)`
    so the route handler never leaks an untyped pg/HTTPX exception as a
    bare 500 (TEST-02 / M-2 finding from PR #4 review).

    The original exception is chained via `from exc` for log/trace
    debugging; only the typed error reaches the wire."""
    try:
        client = await get_storage_client()
        await client.storage.from_(STORAGE_BUCKET).upload(
            path=path,
            file=content,
            file_options={"content-type": content_type, "upsert": "false"},
        )
    except StorageProblem:
        raise
    except Exception as exc:  # noqa: BLE001 — storage SDK raises a wide tree
        raise StorageProblem(
            "Document storage backend is unavailable; please retry",
            path=path,
        ) from exc
