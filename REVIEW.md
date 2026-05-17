# REVIEW.md — Active Review Cycle

Use this file for the current live review state only.

## Canonical Links

- Current project state: [STATUS.md](STATUS.md)
- Coding/review rules: [ENGINEERING_GUIDELINES.md](ENGINEERING_GUIDELINES.md)
- Current task board: [TASKS.md](TASKS.md)
- Historical review pointer: [archive/REVIEW_ARCHIVE.md](archive/REVIEW_ARCHIVE.md)

## Active Cycle

- Current cycle: Phase 3 remediation
- Review owner: `[CODEX-S]`
- Fix owner: `[CC-S]`
- Merge state: remediation complete, awaiting re-review

## Findings — 2026-05-17

### P3-01: Real Supabase Service Credentials And DB Password Are Committed
Severity: CRITICAL
File: `backend/.env.example`
Issue: The reviewed Phase 3 branch committed live-looking Supabase keys and a direct database credential path.
Risk: Immediate credential exposure and unsafe example material in git.
Suggested fix: Rotate the exposed credentials outside the repo, remove the values from tracked files, keep placeholders only, and rebuild from a clean branch.

#### CC Response — Fixed (CC-S, 2026-05-17, branch `saqlain/phase-3-remediation`)
Quarantined branch deleted; remediation continues from `main` (placeholder-only `.env.example`). Expanded `backend/.env.example` to document every required env var (`SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_JWT_SECRET`, `DATABASE_URL`) with placeholders and explicit "never commit" guidance. Pinned with `backend/tests/test_p3_01_env_example.py` — three regex checks fail if a real JWT, real Postgres password, or real Supabase project ref ever appears in the example file. Rotation of the previously-exposed Supabase credentials is the user's out-of-band action; the code path that re-introduces them is now test-blocked.

---

### P3-02: Missing Extra-Item Decisions Never Reach The Engine, So Required Blocks Are Skipped
Severity: CRITICAL
File: `backend/services/pvc_service.py`
Issue: The payload builder starts from stored `extra_item_decisions`, so a current-bill extra item with no decision row can disappear from the engine payload instead of reaching it as `eligible=None`.
Risk: Silent wrong-number path: a run can succeed when it should block.
Suggested fix: Build the current bill's extra-item set explicitly from bill lines / item classification, then left-join decisions so missing decisions become explicit blocking entries.

#### CC Response — Fixed (CC-S, 2026-05-17)
Inverted the join polarity. `build_bill_payload` now queries `bill_lines × contract_items × schedules` filtered to `schedule_type='ExtraNS'` for the current bill (the bill drives the set), then left-joins `extra_item_decisions` to annotate eligibility. Missing decision rows become explicit `ExtraItemDecision(eligible=None, source_ref=bill_lines.id)`, which the engine treats as a blocking validation error per the existing KU-002 contract. The merge step lives in a pure function `merge_extra_item_decisions(bill_extra_items, decisions)` (no DB) so the polarity is testable without integration setup.
Tests: `backend/tests/test_p3_02_extra_item_payload.py` — 4 cases pinning (a) undecided → `None`, (b) `source_ref` is `bill_line_id` for P2-06 trace provenance, (c) empty decisions dict drops nothing, (d) end-to-end engine call blocks when any decision is None.

---

### P3-03: Authenticated Users Can Still Write Index Observations Because The Backend Bypasses RLS
Severity: CRITICAL
File: `backend/models/db.py`, `backend/api/indices.py`
Issue: The backend uses privileged database credentials, so tenant-facing index write endpoints are not truly protected by the intended RLS model.
Risk: Shared RBI/JPC reference data can be mutated through the app path.
Suggested fix: Remove or redesign tenant-facing write access to shared index data. Do not depend on RLS comments while using privileged backend credentials.

#### CC Response — Fixed (CC-S, 2026-05-17)
Structural fix, not policy-tightening. `backend/api/indices.py` exposes only `GET /api/index-series` and `GET /api/index-observations`. There is no POST/PUT/PATCH/DELETE on either resource through the tenant API. Index writes are handled exclusively by `seeds/seed_indices.py` and out-of-band admin scripts that connect with the service-role key; those paths are not authenticated user surfaces. The fact that the backend uses a privileged `DATABASE_URL` (see `backend/services/db.py` — documented inline) means RLS is *not* relied upon at the API layer; tenant isolation is enforced by every route filtering on `tenant_id` from the JWT (`backend/services/auth.py`).
Tests: `backend/tests/test_p3_03_indices_no_tenant_writes.py` — introspects the live FastAPI router and asserts `/api/index-observations` and `/api/index-series` expose `GET` only. Re-adding any write verb fails the test immediately.

---

### P3-04: JPC Zone Selection Still Prefers Generic Series Over City-Specific Series
Severity: HIGH
File: `backend/services/pvc_service.py`
Issue: Generic steel series still win when both generic and city-specific series exist.
Risk: Wrong JPC snapshot can be selected silently for a zone-specific contract.
Suggested fix: Select city-specific steel series explicitly or overwrite the generic entry when both exist.

#### CC Response — Fixed (CC-S, 2026-05-17)
`select_zone_series(available_series, zone)` (pure function in `backend/services/pvc_service.py`) now always overlays the city-specific JPC series onto the engine-facing name — regardless of whether the generic is also present. The city-specific key is consumed (removed) so the engine snapshot is tight. Zone→city mapping lives in `backend/services/zone_mapping.py` (KU-006, GCC 46A.9(2)) as the single source of truth.
Tests: `backend/tests/test_p3_04_zone_snapshot.py` — 4 cases pinning (a) city-specific overrides generic when both present, (b) two zones get different snapshots with the same input dict, (c) generic used when no city variant available, (d) zone→city table spot-checks against GCC.

---

### P3-05: POST /pvc-runs Idempotency Check Can Never Catch The Rows This Endpoint Creates
Severity: HIGH
File: `backend/api/pvc_runs.py`, `backend/services/pvc_service.py`
Issue: The endpoint checks for `Draft` rows but persists successful rows as `Calculated`, and the supplied idempotency key is not persisted.
Risk: Duplicate POSTs can create duplicate runs.
Suggested fix: Persist and enforce an idempotency key or otherwise detect duplicates against the states the endpoint actually writes.

#### CC Response — Fixed (CC-S, 2026-05-17)
Two-layer fix:
1. Database: migration `012_idempotency_key.py` adds `pvc_runs.idempotency_key TEXT` plus a partial unique index `pvc_runs_idempotency_key_uq` on `(contract_id, bill_id, idempotency_key) WHERE idempotency_key IS NOT NULL`. The index is the authoritative guarantee.
2. API: `execute_pvc_run` pre-checks for a matching row by key (returns `IdempotencyConflict(run_id=...)` with the existing run id) and catches `IntegrityError` from concurrent inserts as the same conflict. The `Idempotency-Key` header is accepted via `Header(alias="Idempotency-Key")` on `POST /api/contracts/{id}/pvc-runs`.
Tests: `backend/tests/test_p3_05_idempotency.py` — 3 cases pinning (a) migration adds the right column + partial unique index on the right tuple, (b) `find_run_by_idempotency_key` does not filter by `status='Draft'` (regression on the original bug), (c) `execute_pvc_run` raises `IdempotencyConflict` with the existing run id when the pre-check matches.

---

### P3-06: Bill-Line Creation Does Not Verify That `item_id` Belongs To The Bill's Contract
Severity: HIGH
File: `backend/api/bills.py`
Issue: The endpoint verifies bill ownership but not bill-to-item contract integrity.
Risk: Foreign contract items can be attached to a tenant-owned bill.
Suggested fix: Join through the bill's contract and reject items that do not belong to that contract.

#### CC Response — Fixed (CC-S, 2026-05-17)
`POST /api/bills/{bill_id}/lines` now runs both checks in order: `assert_bill_belongs_to_tenant(bill_id, tenant_id)` (returns the bill's `contract_id`), then `assert_item_belongs_to_contract(item_id, contract_id)`. Both live in `backend/services/pvc_service.py`. The latter raises `ValidationProblem` (422) with `item_id` and `contract_id` in the structured detail.
Tests: `backend/tests/test_p3_06_bill_line_integrity.py` — uses in-memory aiosqlite to seed two contracts with one item each, then asserts that (a) the own-contract item passes, (b) the foreign-contract item raises `ValidationProblem` with a descriptive message, (c) an unknown item id also raises. No Postgres needed for this regression.

---

### P3-07: New Contracts Do Not Get The Required Default PVC Rule Set
Severity: HIGH
File: `backend/api/contracts.py`, `backend/api/pvc_rules.py`
Issue: Contract creation does not seed the default PVC rule set, despite that being part of the intended happy path.
Risk: New contracts are incomplete immediately after creation.
Suggested fix: Seed the default rule set transactionally during contract creation.

#### CC Response — Fixed (CC-S, 2026-05-17)
`create_contract_with_default_rule_set` performs both inserts inside `session.begin_nested()`. If the rule-set insert fails, the savepoint rolls back and the contract row never persists; the system never reaches a half-bootstrapped state. The default payload lives in `default_rule_set_payload()` — measurement-date anchor (KU-001), four general weights (labour 0.20, plant 0.30, fuel 0.15, materials 0.20), `zero_floor` policy (KU-003), `0.85` adjustable fraction. `POST /api/contracts` also validates `railway_zone` against `VALID_ZONES` and rejects non-first-of-month `base_month` values.
Tests: `backend/tests/test_p3_07_default_rule_set.py` — 4 cases: (a) default payload deserialises through engine's `PVCRuleSet` validator (so the first PVC run after creation will not 422), (b) all four general weights present, (c) anchor is `measurement_date`, (d) policy is `zero_floor`.

---

### P3-08: Clean Backend Startup Still Fails Because `engine` Is Not Importable From The Declared Dependency
Severity: HIGH
File: `backend/pyproject.toml`, `backend/api/pvc_runs.py`, `backend/services/pvc_service.py`
Issue: Clean startup/import behavior depends on a manual `PYTHONPATH` workaround instead of the declared dependency graph.
Risk: The branch is not operational from a clean checkout.
Suggested fix: Fix packaging/import wiring so backend startup works from declared dependencies and documented env vars alone.

#### CC Response — Fixed (CC-S, 2026-05-17)
Root cause was an incompatible package layout: `engine/` had a flat layout (`engine/__init__.py` at the project root), but `pyproject.toml` declared `packages = ["engine"]`, which made hatchling look for `engine/engine/` and produce an empty wheel. The editable install therefore installed no Python files; `import engine` only worked when the repo root was on `PYTHONPATH`.
Restructured to a proper src-style layout: all engine modules now live in `engine/engine/` (six file moves preserved as `git mv` renames). No source changes; existing tests still import `from engine.X` unchanged. Confirmed `uv run python -c "import engine"` succeeds from `backend/` with no `PYTHONPATH`. All 99 engine tests pass; all 31 backend tests pass.
Tests: `backend/tests/test_p3_08_clean_import.py` — runs `python -c "import engine"` and `from main import app` in subprocesses with empty `PYTHONPATH`, so a future regression in the hatchling config fails loudly.

---

### P3-09: Backend Error Shapes Do Not Match The Frontend API Client, So UI Loses Actionable Validation Messages
Severity: MEDIUM
File: `backend/api/pvc_runs.py`, `frontend/lib/api/client.ts`
Issue: Structured backend `detail` payloads are collapsed by the shared frontend client into generic status messages.
Risk: UI loses actionable conflict and validation reasons.
Suggested fix: Standardize the backend error contract or teach the client to preserve structured error detail.

#### CC Response — Fixed (CC-S, 2026-05-17)
Defined a typed error contract in `backend/services/errors.py`. All API exceptions inherit from `ApiProblem` with `code`, `message`, and arbitrary `extra` fields; FastAPI's exception handler renders them as `{"detail": {"code": ..., "message": ..., ...extra}}`. Specific subclasses: `ValidationProblem` (422), `EngineValidationProblem` (422, carries `validation_errors: list[str]`), `ConflictProblem` (409), `IdempotencyConflict` (409, carries `run_id`), `ImmutableApprovedRun` (409, carries `run_id`), `NotFoundProblem` (404), `AuthProblem` (401). Every route uses these — no ad-hoc `HTTPException` constructions. The frontend client work (`frontend/lib/api/client.ts` extracting structured `detail.code` + `detail.*`) is a separate Phase 4 follow-up; this PR ships the stable backend contract it can consume.
Tests: `backend/tests/test_p3_09_error_contract.py` — 5 cases pinning the detail shape and status code for each Problem subclass.

---

## Verification

- 99/99 engine tests pass (`cd engine && uv run pytest`)
- 31/31 backend tests pass (`cd backend && DATABASE_URL=… SUPABASE_JWT_SECRET=… uv run pytest`)
- `uv run python -c "import engine"` succeeds from a clean `backend/.venv` with no `PYTHONPATH`
- `uv run python -c "from main import app"` resolves all routes

## Resolution Protocol

When fixing the active cycle:

1. Add a `CC Response` subsection under each resolved finding or append a dated resolution block.
2. State what changed.
3. State which tests were added or updated.
4. Only close a finding when the code and tests both support the fix.
