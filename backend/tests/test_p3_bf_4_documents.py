"""P3-BF-4: documents upload pure helpers + error contract.

The IO-bound layer (Supabase upload, DB insert) is not exercised here —
it depends on live network + a writable bucket. The pure layer is where
the security-relevant logic lives:

  * `sanitize_filename` decides whether a path-traversal attempt makes
    it into a storage key.
  * `build_storage_path` decides whether two tenants can collide on the
    same path.
  * `PayloadTooLargeProblem` decides whether the frontend gets a usable
    413 with a concrete ceiling, or has to guess.

If any of these regress, integration tests against the live API would
catch it eventually — but only AFTER the bad path has shipped. These
tests catch it on the diff.
"""
from __future__ import annotations

import re

from services.errors import PayloadTooLargeProblem
from services.storage import (
    MAX_FILE_BYTES,
    VALID_DOCUMENT_TYPES,
    build_storage_path,
    sanitize_filename,
)


_UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")


# ---------------------------------------------------------------------------
# sanitize_filename
# ---------------------------------------------------------------------------


def test_sanitize_strips_posix_path_traversal():
    assert sanitize_filename("../../etc/passwd") == "passwd"


def test_sanitize_strips_windows_path_traversal():
    assert sanitize_filename(r"..\..\windows\system32\config\SAM") == "SAM"


def test_sanitize_collapses_unsafe_characters():
    # Spaces, ampersands, and other shell-meaningful chars must not survive.
    assert sanitize_filename("invoice 2024 & co.pdf") == "invoice_2024___co.pdf"


def test_sanitize_strips_leading_dots():
    assert sanitize_filename(".htaccess") == "htaccess"


def test_sanitize_caps_length():
    long = "a" * 500 + ".pdf"
    result = sanitize_filename(long)
    assert len(result) <= 200


def test_sanitize_empty_returns_upload_fallback():
    assert sanitize_filename("") == "upload"


def test_sanitize_only_dots_returns_upload_fallback():
    # `.` stripped from the front + `_` would also be stripped if all that
    # remained were the dot-prefix; current behaviour returns "upload" only
    # when the post-sanitize result is empty. A bare "." satisfies that.
    assert sanitize_filename(".") == "upload"


# ---------------------------------------------------------------------------
# build_storage_path
# ---------------------------------------------------------------------------


def test_storage_path_format_includes_tenant_contract_uuid_filename():
    path = build_storage_path("tenant-A", "contract-X", "report.pdf")
    parts = path.split("/")
    assert parts[0] == "tenant-A"
    assert parts[1] == "contract-X"
    # parts[2] = "{uuid}_report.pdf"
    uuid_prefix, _, filename = parts[2].partition("_")
    assert _UUID_RE.match(uuid_prefix), f"missing UUID prefix in {parts[2]!r}"
    assert filename == "report.pdf"


def test_storage_path_uuid_prevents_collision_on_same_filename():
    a = build_storage_path("tenant-A", "contract-X", "report.pdf")
    b = build_storage_path("tenant-A", "contract-X", "report.pdf")
    assert a != b, "two uploads of the same filename collided"


def test_storage_path_sanitizes_filename_into_key():
    path = build_storage_path("tenant-A", "contract-X", "../../etc/passwd")
    # The traversal must NOT escape the tenant/contract prefix.
    assert path.startswith("tenant-A/contract-X/")
    assert "../" not in path


# ---------------------------------------------------------------------------
# constants + error contract
# ---------------------------------------------------------------------------


def test_max_file_bytes_is_50mb():
    # Pinned because the frontend renders this as a user-facing cap.
    assert MAX_FILE_BYTES == 50 * 1024 * 1024


def test_valid_document_types_matches_migration_008_enum():
    assert VALID_DOCUMENT_TYPES == frozenset({
        "agreement", "mb", "bill", "recovery", "workbook", "other",
    })


def test_payload_too_large_problem_carries_max_bytes():
    p = PayloadTooLargeProblem(MAX_FILE_BYTES)
    detail = p.to_detail()
    assert p.status_code == 413
    assert detail["code"] == "payload_too_large"
    assert detail["max_bytes"] == MAX_FILE_BYTES
    # The frontend renders the message verbatim — pin it loosely.
    assert "50" in detail["message"] or str(MAX_FILE_BYTES) in detail["message"]
