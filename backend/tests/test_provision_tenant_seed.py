"""Operator provisioning script: validation and idempotent DB flow."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest


SCRIPT = Path(__file__).resolve().parents[2] / "seeds" / "provision_tenant.py"
DEMO_SCRIPT = Path(__file__).resolve().parents[2] / "seeds" / "seed_demo_contract.py"


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _load_script():
    return _load_module("provision_tenant", SCRIPT)


def _load_demo_script():
    return _load_module("seed_demo_contract_for_test", DEMO_SCRIPT)


def test_demo_seed_requires_explicit_tenant(monkeypatch):
    module = _load_demo_script()
    monkeypatch.delenv("SEED_TENANT_ID", raising=False)

    with pytest.raises(SystemExit, match="SEED_TENANT_ID is required"):
        module.resolve_tenant_id()


def test_demo_seed_uses_process_tenant(monkeypatch):
    module = _load_demo_script()
    monkeypatch.setenv("SEED_TENANT_ID", "tenant-from-process")

    assert module.resolve_tenant_id() == "tenant-from-process"


def test_provision_config_normalizes_email(monkeypatch):
    module = _load_script()
    monkeypatch.setenv("PROVISION_TENANT_NAME", "  Example Railworks  ")
    monkeypatch.setenv("PROVISION_INVITE_EMAIL", "  First.User@Example.COM ")

    config = module.ProvisionConfig.from_env()

    assert config.tenant_name == "Example Railworks"
    assert config.invite_email == "first.user@example.com"


@pytest.mark.parametrize(
    ("name", "email", "message"),
    [
        (None, "user@example.com", "PROVISION_TENANT_NAME"),
        ("Example", None, "PROVISION_INVITE_EMAIL"),
        ("Example", "not-an-email", "valid email"),
    ],
)
def test_provision_config_rejects_missing_or_invalid_values(monkeypatch, name, email, message):
    module = _load_script()
    monkeypatch.delenv("PROVISION_TENANT_NAME", raising=False)
    monkeypatch.delenv("PROVISION_INVITE_EMAIL", raising=False)
    if name is not None:
        monkeypatch.setenv("PROVISION_TENANT_NAME", name)
    if email is not None:
        monkeypatch.setenv("PROVISION_INVITE_EMAIL", email)

    with pytest.raises(SystemExit, match=message):
        module.ProvisionConfig.from_env()


@pytest.mark.asyncio
async def test_provision_existing_invite_returns_original_tenant_without_duplicates():
    module = _load_script()
    conn = AsyncMock()
    transaction = MagicMock()
    transaction.__aenter__ = AsyncMock()
    transaction.__aexit__ = AsyncMock(return_value=None)
    conn.transaction = MagicMock(return_value=transaction)
    conn.fetchrow = AsyncMock(return_value={"tenant_id": "tenant-existing"})

    tenant_id, created = await module.provision(
        conn,
        module.ProvisionConfig("Renamed Tenant", "user@example.com"),
    )

    assert tenant_id == "tenant-existing"
    assert created is False
    assert conn.fetchrow.await_count == 1
    sql = str(conn.execute.await_args.args[0])
    assert "pg_advisory_xact_lock" in sql
    assert conn.execute.await_args.args[1] == "user@example.com"


@pytest.mark.asyncio
async def test_provision_creates_tenant_before_lowercase_invite():
    module = _load_script()
    conn = AsyncMock()
    transaction = MagicMock()
    transaction.__aenter__ = AsyncMock()
    transaction.__aexit__ = AsyncMock(return_value=None)
    conn.transaction = MagicMock(return_value=transaction)
    conn.fetchrow = AsyncMock(
        side_effect=[None, {"id": "tenant-new"}],
    )

    tenant_id, created = await module.provision(
        conn,
        module.ProvisionConfig("Example Railworks", "user@example.com"),
    )

    assert tenant_id == "tenant-new"
    assert created is True
    assert conn.fetchrow.await_count == 2
    invite_call = conn.execute.await_args_list[1]
    assert "INSERT INTO tenant_invites" in str(invite_call.args[0])
    assert invite_call.args[1:] == ("tenant-new", "user@example.com")
