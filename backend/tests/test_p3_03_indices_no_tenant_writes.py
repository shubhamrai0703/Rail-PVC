"""P3-03 regression: the tenant-facing API exposes NO write paths to
`index_observations`.

The reviewed branch left POST/PUT endpoints in `api/indices.py` and relied
on the migration-011 RLS policy to gate them. Because the backend uses a
privileged DB connection (services/db.py), RLS doesn't apply, and any
authenticated user could mutate the shared price index.

The fix is structural — removing the endpoints entirely. This test
inspects the live FastAPI router so adding them back fails immediately.
"""
from __future__ import annotations

import os

os.environ.setdefault("DATABASE_URL", "postgresql://stub:stub@localhost:5432/stub")
# TEST-04: services/auth.py verifies via Supabase JWKS (ES256/HS256) at request
# time — module-level import has no auth dep to satisfy, so no fake secret is
# needed here. Tests that exercise protected routes use FastAPI's
# `app.dependency_overrides[get_current_user]` to bypass JWKS entirely (see
# test_p3_bf_4_documents.py::test_upload_route_returns_503_when_storage_raises).

from main import app  # noqa: E402


def _routes_for(path: str) -> set[str]:
    methods: set[str] = set()
    for route in app.routes:
        if getattr(route, "path", None) == path:
            methods |= set(route.methods or set())
    return methods


def test_no_write_endpoints_on_index_observations():
    methods = _routes_for("/api/index-observations")
    assert "GET" in methods, "tenants must be able to read indices"
    for verb in ("POST", "PUT", "PATCH", "DELETE"):
        assert verb not in methods, (
            f"P3-03: index_observations must not expose {verb} via the tenant API "
            f"(privileged DB connection bypasses RLS)"
        )


def test_no_write_endpoints_on_index_series():
    methods = _routes_for("/api/index-series")
    for verb in ("POST", "PUT", "PATCH", "DELETE"):
        assert verb not in methods, (
            f"P3-03: index_series must not expose {verb} via the tenant API"
        )
