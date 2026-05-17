"""P3-05 regression: POST /pvc-runs idempotency is real.

The reviewed implementation looked for an existing row with status='Draft',
but successful runs are persisted with status='Calculated'. The header
key was neither stored nor compared, so replays produced N runs.

The remediation:
  * Migration 012 adds `idempotency_key` + a partial unique index on
    (contract_id, bill_id, idempotency_key WHERE NOT NULL).
  * `execute_pvc_run` pre-checks for a row with the same key (raises
    IdempotencyConflict with the existing run_id) and catches IntegrityError
    from concurrent inserts as the same conflict.

These tests pin both layers.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest
from sqlalchemy.exc import IntegrityError

MIGRATION = Path(__file__).resolve().parent.parent / "migrations" / "versions" / "012_idempotency_key.py"


def test_migration_adds_idempotency_column_and_unique_index():
    body = MIGRATION.read_text()
    assert "ADD COLUMN idempotency_key" in body
    assert "CREATE UNIQUE INDEX" in body
    # Partial index so historical rows with NULL key can coexist.
    assert "WHERE idempotency_key IS NOT NULL" in body
    # The uniqueness scope must match the API tuple, not just bill_id.
    assert re.search(r"\(contract_id,\s*bill_id,\s*idempotency_key\)", body), (
        "idempotency uniqueness must include contract + bill"
    )


def test_pre_check_function_signature_uses_persisted_status():
    """The dedup query MUST NOT filter by status='Draft'. Runs are persisted
    as 'Calculated' the moment the engine succeeds — that was the bug."""
    body = (
        Path(__file__).resolve().parent.parent / "services" / "pvc_service.py"
    ).read_text()
    # Locate the find function body and verify it filters on idempotency_key only.
    fn_match = re.search(
        r"async def find_run_by_idempotency_key.*?(?=async def |\Z)",
        body,
        re.DOTALL,
    )
    assert fn_match, "find_run_by_idempotency_key not found"
    fn_body = fn_match.group(0)
    assert "idempotency_key" in fn_body
    assert "status = 'Draft'" not in fn_body, (
        "the pre-check must not filter to Draft — the bug it replaces did that "
        "and missed every Calculated run"
    )


@pytest.mark.asyncio
async def test_execute_pvc_run_raises_idempotency_conflict_on_existing_key(monkeypatch):
    """Unit-level: stub the DB lookup and ensure execute_pvc_run raises a
    structured IdempotencyConflict carrying the existing run_id."""
    from services import pvc_service
    from services.errors import IdempotencyConflict

    async def _fake_find(_session, _cid, _bid, _key):
        return "existing-run-id"

    monkeypatch.setattr(pvc_service, "find_run_by_idempotency_key", _fake_find)

    with pytest.raises(IdempotencyConflict) as exc:
        await pvc_service.execute_pvc_run(
            session=None,  # never reached
            tenant_id="t-1", contract_id="c-1", bill_id="b-1",
            rule_set_row={"id": "rs-1"},
            idempotency_key="abc",
        )
    assert exc.value.extra["run_id"] == "existing-run-id"
    assert exc.value.status_code == 409
