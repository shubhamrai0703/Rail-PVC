"""Migration 019 pins the invite table's security and uniqueness contract."""
from __future__ import annotations

import importlib.util
from pathlib import Path


MIGRATION = (
    Path(__file__).resolve().parents[1]
    / "migrations"
    / "versions"
    / "019_tenant_invites.py"
)


def _load_migration():
    spec = importlib.util.spec_from_file_location("migration_019", MIGRATION)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_migration_019_creates_case_insensitive_private_invites(monkeypatch):
    migration = _load_migration()
    statements: list[str] = []
    monkeypatch.setattr(migration.op, "execute", lambda value: statements.append(str(value)))

    migration.upgrade()

    sql = "\n".join(statements)
    assert migration.revision == "019"
    assert migration.down_revision == "018"
    assert "CREATE TABLE tenant_invites" in sql
    assert "tenant_id" in sql and "REFERENCES tenants(id)" in sql
    assert "consumed_at" in sql
    assert "UNIQUE INDEX tenant_invites_email_lower_uidx" in sql
    assert "lower(email)" in sql
    assert "ENABLE ROW LEVEL SECURITY" in sql
    assert "FORCE ROW LEVEL SECURITY" in sql
