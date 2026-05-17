# SESSION_LOG.md — Current Operational Log

Keep this file small.

Use it for current milestone decisions and recent sessions only.

## Canonical Links

- Current state: [STATUS.md](STATUS.md)
- Active task board: [TASKS.md](TASKS.md)
- Active review cycle: [REVIEW.md](REVIEW.md)
- Historical archive pointer: [archive/SESSION_LOG_ARCHIVE.md](archive/SESSION_LOG_ARCHIVE.md)

## Current Project State

- Phase 0, 1, and 2 are complete
- Phase 3 remediation complete on `saqlain/phase-3-remediation`; awaiting Codex-S re-review
- Phase 4 scaffolding parked on `saqlain/phase-4`; will rebase after P3 merge

## Recent Sessions

### Session 10 — 2026-05-17 (Phase 3 remediation, branch `saqlain/phase-3-remediation`)

Closed all merge-blocking findings `P3-01…P3-08` plus the MEDIUM `P3-09` in one pass. CC responses in [REVIEW.md](REVIEW.md) per finding.

Key design decisions:

- **Engine packaging is src-layout now.** Root cause for `P3-08` was hatchling's `packages = ["engine"]` looking for `engine/engine/` against a flat layout that put modules at `engine/*.py`. Moved modules into `engine/engine/` as `git mv` renames. No source changes; tests import unchanged. Pinned by a subprocess test that runs `import engine` with empty `PYTHONPATH`.
- **Tenant isolation is the API layer's job, not RLS's.** The backend uses a privileged `DATABASE_URL`, so RLS is documentation. Every route filters on `tenant_id` derived from the JWT (`backend/services/auth.py`). For shared global tables (`index_observations`, `index_series`), the tenant API exposes `GET` only — writes are out-of-band via seed/admin scripts using the service-role key. This is the structural fix for `P3-03`.
- **Domain logic lives in pure functions; routes are thin SQL wrappers.** `merge_extra_item_decisions`, `select_zone_series`, `default_rule_set_payload`, `assert_item_belongs_to_contract` — all unit-testable without Postgres. The route handlers compose them with `text()` SQL. This is what makes the P3 fixes pinnable without integration setup.
- **Idempotency is enforced at the database, not in application code.** Migration `012` adds a partial unique index `(contract_id, bill_id, idempotency_key) WHERE idempotency_key IS NOT NULL`. The API pre-check produces a friendly `409` with the existing `run_id`; the index is the actual guarantee.
- **Typed error contract is the API surface.** `services/errors.py` defines `ApiProblem` subclasses; FastAPI exception handlers render them as `{"detail": {"code", "message", ...extra}}`. Engine `validation_errors` come through as `code="engine_validation_error"` with the full list, idempotency conflicts as `code="idempotency_conflict"` with `run_id`. The frontend client work to consume these is queued as `P4-007`.

Files changed:

- `engine/` — six `git mv` renames into `engine/engine/`; `engine/pyproject.toml` unchanged
- `backend/.env.example` — placeholders only, documents all required env vars
- `backend/pyproject.toml` — adds `pyjwt`, `httpx`/`pytest`/`pytest-asyncio`/`aiosqlite` (dev), `pytest.ini_options`
- `backend/main.py` — wires all routers and `register_exception_handlers`
- `backend/api/` — new: `contracts`, `bills`, `extra_items`, `carry_forwards`, `indices`, `pvc_rules`, `pvc_runs`
- `backend/services/` — new: `db`, `auth`, `errors`, `zone_mapping`, `pvc_service`
- `backend/migrations/versions/012_idempotency_key.py` — new
- `backend/tests/` — 8 test modules, one per finding (`test_p3_01` … `test_p3_09`)

Verification:

- 99 engine tests + 31 backend tests = 130 passing, 0 failing
- `uv run python -c "import engine"` succeeds from a clean `backend/.venv` with no `PYTHONPATH`
- `uv run python -c "from main import app"` resolves all routes

Out-of-band action required:

- Rotate the previously-exposed Supabase project keys + Postgres password. The test in `backend/tests/test_p3_01_env_example.py` will block any future re-introduction.

## Current Decisions

- Active docs should be read in this order:
  1. [STATUS.md](STATUS.md)
  2. [PRODUCT.md](PRODUCT.md)
  3. [ARCHITECTURE.md](ARCHITECTURE.md)
  4. [TASKS.md](TASKS.md)
  5. [REVIEW.md](REVIEW.md)
- Historical detail should not live in the active context set when a summary/link is sufficient
- `CLAUDE.md` and `CODEX.md` should act as startup instructions, not duplicate project context

## Next Actions

1. Codex-S runs `P3-RE-REVIEW` against `saqlain/phase-3-remediation`
2. CC-S addresses any new findings; merge to `main` once clean
3. Rebase `saqlain/phase-4` on top of merged `main` and resume P4-001 / P4-004 / P4-007
