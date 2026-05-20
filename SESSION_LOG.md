# SESSION_LOG.md — Current Operational Log

Keep this file small.

Use it for current milestone decisions and recent sessions only.

## Canonical Links

- Current state: [STATUS.md](STATUS.md)
- Active task board: [TASKS.md](TASKS.md)
- Active review cycle: [REVIEW.md](REVIEW.md)
- Historical archive pointer: [archive/SESSION_LOG_ARCHIVE.md](archive/SESSION_LOG_ARCHIVE.md)

## Current Project State

- Phases 0–4 + Phase 3 backfill + TEST-P3P4: all complete on `main` as of 2026-05-19.
- **Phase 5 UI complete and merged to `main` 2026-05-20 (P5-001…P5-008 + P5-F1…F5 + P5-REVIEW remediation).**
- Active (parallel): GET bill endpoints + export backend (Shubham, `shubham/phase-5-backend`).
- Test suite on `main`: **82/82 backend** (clean venv, `fastapi==0.115.12`), 99/99 engine, 16/16 frontend vitest, `next build` + `npm run lint` clean. No open CRITICAL/HIGH findings.
- Local backend: `cd backend && source .venv/bin/activate && uvicorn main:app --reload --port 8000`
- Local frontend: `cd frontend && npm run build && npm start` (port 3000) — always rebuild after code changes
- DB: Supabase at `ivselmhloegjmqrjekcy.supabase.co`, migrations at head (012).
- Tenant provisioned for `saqlainmmomin@gmail.com` — tenant_id `bd589426-93ba-4847-b5f3-1f69b020b4c0`.

## Recent Sessions

### Session 19 — 2026-05-20 (P5-REVIEW remediation + merge to `main`)

CC-S ran the adversarial review on `saqlain/phase-5` (Codex-S unavailable this cycle) and posted 14 findings to `REVIEW.md`. Then the same chat remediated all of them. Worked one finding at a time with TDD inside the loop — failing test first, fix, green — and audited each finding for the same class of bug elsewhere before patching the one line the review named.

- **C-1 (CRITICAL).** Root cause was the interaction between `from __future__ import annotations` (PEP 563) and FastAPI 0.115.x's deferred resolution of `-> None` on a 204 handler. The string `"None"` resolves to `NoneType` (the class), FastAPI builds a non-None `response_field`, and the 204-no-body assertion fires at decorator time. Dropped `-> None` on `delete_contract_item`. Audit: single 204 handler and single `-> None` handler in the whole backend; same line. All 10 api modules use the future import, so the bug class would re-arm on any future 204 endpoint someone adds — left an inline comment as a tripwire for the next contributor. Regression pin is the pre-existing `test_p3_08_clean_import.py` which failed-to-collect before the fix.

- **H-1 / M-2.** `parseTsvImport` silently coerced anything-not-in-`["true","1","yes"]` to false for `is_cement_item`, and let any string through verbatim as `steel_subtype`. Extracted the parser to `frontend/lib/parseTsvImport.ts` (pure module) with explicit accept-lists; "Tru" and "TMT" now reject the row to `errors[]`. Added `vitest@2.1.9` and 12 parser tests. Also gated the "Add N rows" button so any parse error blocks the import (M-2).

- **H-2 / M-3 / M-6 / L-4.** Added `FieldNotNullableProblem` (code `field_not_nullable`) and `CementSteelConflictProblem` to `services/errors.py`. Both PUT handlers now reject explicit `null` on NOT NULL columns at the API boundary instead of letting Postgres raise an unstructured 500. PUT uses an effective-row merge for the cement+steel check so a PUT that only sets one field is also caught. UPDATE/DELETE on `contract_items` scoped to `(id, schedule_id)` for defense in depth. 15 new backend tests across `test_p5_001_contracts_put.py` and `test_p5_f3_items_crud.py` — all fail on the pre-remediation handlers.

- **H-3.** `setError` moved out of `ContractForm`'s render body into `useEffect([serverFieldError, setError])`. No RTL test added — installing `@testing-library/react` for one render-lifecycle assertion is bigger scope than the finding warrants; the verification gate's manual smoke covers the behavior pin.

- **M-4.** Zod schema now emits `null` for cleared nullable optional fields (`agreement_number`, `loa_*`, `*_date`, `contract_value`, `bid_amount`, `work_description`) so the Edit form actually clears those columns. `overall_rebate` keeps "blank → drop from body" because it's NOT NULL — and H-2's backend rule would reject an explicit null on that column anyway, so the schema must not surface one. Required typing the form against `z.input` (raw `string | undefined`) and `z.infer` (post-resolver `string | null`) via `useForm<FormInput, unknown, ContractFormValues>`. 4 schema-test cases pin the null semantics.

- **M-5.** `ExtraItemDecisionList.saveChanges` previously blew away `pending` on success — a toggle mid-flight got silently discarded. Now snapshots `savedKeys` at the start of save and uses functional `setPending(prev => filter)` to clear only the saved keys.

- **L-4** inline. **L-1 / L-2 / L-3** deferred to `P5-FUP-L1/L2/L3` in TASKS.md with acceptance criteria.

- **Lint dirt.** The branch had two pre-existing `react-hooks/set-state-in-effect` errors on `ItemsGrid.tsx` (modal reset effect + items-loaded hydration effect). Saqlain asked these to be cleared before merge. Modal: parent now gates the JSX on `importOpen` so the modal mounts fresh each open — the reset effect is dead code. Hydration: replaced the effect with React 19's documented "adjust state during render" pattern, guarded by `hydratedAt` (TanStack Query's `dataUpdatedAt` timestamp). Also removed two now-stale `eslint-disable-next-line no-console` directives in app-level error boundaries. `npm run lint` is now 0/0.

- **Verification gate (clean Python 3.11 venv, declared dep floor `fastapi==0.115.12`):** 82/82 backend (up from 67; 15 new regression pins), 99/99 engine, 16/16 frontend vitest (new infra), `next build` clean, `npm run lint` clean. The previous "67/67" was correct against the implementer's locally-installed FastAPI 0.136 (which has the upstream fix); on the declared floor the suite couldn't even be collected. Now reproducible.

- **Merge.** Fast-forwarded `main` to `saqlain/phase-5` after the verification gate passed. **Not pushed** — awaits manual push by Saqlain. Saqlain will run the WORKPLAN smoke table in tomorrow's session.

- **Lessons captured during the cycle (worth memorising):**
  - "Same dep range" doesn't mean "same FastAPI minor." The implementer's `0.136.1` had the upstream `response_field` fix the `0.115.12` floor lacks. A clean venv built straight from `pyproject.toml` against the *floor* is the only way to actually certify "clean checkout boots from declared deps."
  - Pydantic v2's `Optional[T] = None` field shape is ambiguous in PUT semantics — "client sent null" and "client omitted the key" both produce `None`. The fix is a per-model NOT NULL set + iterate `model_fields_set` at the handler; don't try to express it at the field level.
  - For "external query state → local editable state," React 19's "adjust state during render guarded by a snapshot key" pattern beats `useEffect`. Lint won't yell, and TanStack Query's `dataUpdatedAt` is the natural snapshot key.

### Session 18 — 2026-05-20 (P5-F1…F5 implementation landed)

- Implemented all five UX polish fixes in one session on `saqlain/phase-5`.
- **F1** — `TooltipHeader` custom AG Grid `headerComponent` with ⓘ icon + native `title` attribute; wired on `original_qty`, `revised_qty`, `base_rate`, `agreement_rate`, `is_cement_item`, `steel_subtype`. No external tooltip library.
- **F2** — "Import rows" toolbar button opens `ImportRowsModal` (absolutely-positioned overlay, no modal lib). `parseTsvImport` splits on `\n` / `\t`, normalises `is_cement_item` (TRUE/true/1/yes → true), and accepts blank `steel_subtype` as null. Preview table + parse-error list before commit; rows append as `_rowState: "new"`.
- **F3 backend** — `PUT` + `DELETE /api/schedules/{schedule_id}/items/{item_id}` in `backend/api/contract_items.py`. New helper `_assert_item_under_schedule_for_tenant` runs the two-step gate: first `assert_schedule_belongs_to_tenant` (tenant ownership of the schedule), then verify the item's `schedule_id` matches the URL. Either failure → 404 NotFoundProblem. `ContractItemUpdate` uses the established `model_fields_set` partial-update pattern; `steel_subtype` keeps the explicit ENUM cast (`CAST(:steel_subtype AS steel_subtype)`). 6 new tests in `test_p5_f3_items_crud.py` (PUT valid / wrong-schedule / wrong-tenant; DELETE valid / wrong-schedule / wrong-tenant). Route count assertion in `test_p3_08_clean_import.py` bumped 29 → 31.
- **F3 frontend** — `_rowState: "new" | "dirty" | "persisted"` per row. Loaded items default to `persisted`; cell edits demote `persisted → dirty` (never demote `new`). Save All routes `new → POST`, `dirty → PUT`, `persisted → skip`. Added a multi-select checkbox column (`checkboxSelection` on `item_code`, `headerCheckboxSelection`, `rowSelection="multiple"`, `suppressRowClickSelection`). "Delete selected (N)" appears when ≥1 row is selected; new rows are removed in-memory without API calls or confirms; persisted/dirty rows trigger `window.confirm(...)` then sequential `DELETE` calls, with the query invalidated only when persisted rows were touched.
- **F4** — One-line banner copy rewrite ("One or more items are marked as both a cement item and a steel item. Each item can only belong to one — please correct before saving.").
- **F5** — `ExtraItemDecisionList` rewritten around a local `pending: Record<itemId, Verdict>` map. Toggling a row updates `pending` only; clicking back to the server value drops the entry (so it stops showing as unsaved). Effective verdict for a row = `pending[id] ?? serverVerdict`; the undecided-count banner reads this merged view. "Save changes (N)" is enabled only when `pending` is non-empty, runs `Promise.all` of POSTs with `silent: true` (we render our own toast), preserves `pending` on failure for retry, and invalidates the decisions query on success. Per-row amber dot indicates a pending change.
- **Verification** — `cd backend && uv run python -m pytest -x -q` → 67 passed (61 prior + 6 new). `cd frontend && npm run build` → clean, 0 TS errors.
- **Lessons captured (used during implementation):**
  - aiosqlite doesn't bind `Decimal` to parameter values — tests with NUMERIC columns must use plain ints/floats. The Postgres `::text` casts in SELECT-back paths still fail under aiosqlite; the established pattern is to catch `OperationalError` and verify the UPDATE/DELETE landed via a plain follow-up `SELECT` (see `test_p5_001_contracts_put.py`).
  - The two-step gate (`assert_schedule_belongs_to_tenant` then per-item membership check) preserves the "wrong-tenant collapses to the same 404 as wrong-schedule" rule — no information leak.
  - `apiFetch` supports `{ silent: true }` to suppress the default Sonner toast; useful when the caller renders its own success/error UI (F5 batch save).

### Session 17 — 2026-05-20 (Smoke test complete; BUG-1 fixed; P5-F1…F5 planned)

- Restarted backend + frontend. BUG-1 diagnosed from browser devtools Network tab: actual error was **500 Internal Server Error**, not a network failure. The "Network error" toast was a misdiagnosis from the previous session.
- Root cause of 500: `INSERT INTO schedules VALUES (:stype::schedule_type …)` — SQLAlchemy's asyncpg dialect left `:stype` unsubstituted because `::schedule_type` immediately follows and breaks named-param parsing. Fix: `CAST(:stype AS schedule_type)`. One-line change in `backend/api/schedules.py`. CORS and auth were never the issue.
- Smoke test completed: all 7 flows green (Create, Edit, Validation, Schedules, Items, Mutual-exclusion warning, Extra-items).
- Saqlain ran live testing and raised 5 UX observations:
  1. Column tooltips needed on confusing Items grid fields (original_qty, revised_qty, base_rate, agreement_rate, is_cement_item, steel_subtype)
  2. No Excel paste support — multi-row copy from Excel collapses into a single cell. Decision: Option B (paste-area import dialog with TSV parsing + row preview), with Option C (file import) as a post-MVP addition.
  3. Items Save All always creates new rows — no update or delete. Decision: Option B (checkbox-select + "Delete selected" with confirmation; Save All distinguishes new/dirty/persisted rows; backend needs PUT + DELETE endpoints for items).
  4. Mutual-exclusion warning uses engine jargon ("engine treats these as mutually exclusive buckets"). Fix: user-facing copy.
  5. Extra-items auto-save feels unsafe. Decision: Option B (staged local changes + explicit "Save changes" button; batch POST on save).
- All 5 issues captured as P5-F1…F5 in TASKS.md. Implementation prompt written in WORKPLAN.md.
- P5-REVIEW is now gated on P5-F1…F5 landing.

### Session 16 — 2026-05-20 (Partial smoke; BUG-1 misdiagnosed as network error)

- Rebuilt frontend after finding stale bundle. Flows 1–3 (Create, Edit, Validation) passed.
- Flow 4 (Schedules) blocked — "Network error" toast on schedule POST. Investigated CORS + auth, found nothing. Root cause not identified (diagnosed in Session 17).
- `base_month` edit-mode fix committed to working tree (`toFormDefaults` slices to `YYYY-MM`).
- Servers shut down at end of session.

### Session 15 — 2026-05-19 (Phase 5 UI implementation — P5-001…P5-008 landed on `saqlain/phase-5`)

- Implemented all eight Phase 5 tasks end-to-end in a single session: backend PUT + expanded GET (P5-001), frontend deps + zod/zone constants (P5-002), `/contracts/new` form (P5-003), `/contracts/[id]` detail with tab shell (P5-004), Overview inline edit (P5-005), Schedules tab + `ScheduleForm` (P5-006), Items tab + AG Grid `ItemsGrid` (P5-007), extra-items decision page (P5-008).
- Backend: 6 new tests in `test_p5_001_contracts_put.py` (wrong-tenant 404, unknown 404, invalid zone 422, base_month day≠1 422, `model_fields_set` semantics, valid partial update); route count assertion in `test_p3_08` bumped 28 → 29.
- Frontend: `base_month` field uses `setValueAs` to auto-append `-01` before submit; `overall_rebate` UI says "as decimal, 0.15 = 15%" per OQ-5; items grid renders a soft warning when a row is marked both `is_cement_item=true` AND has `steel_subtype` set (engine buckets are mutually exclusive); decision toggles use TanStack `onMutate` for optimistic update + rollback on error.
- AG Grid theming via `themeQuartz.withParams({…})` + `AllCommunityModule` registration (v35 API; the docs are right, training data was wrong).
- Verified: 61/61 backend pass; `next build` reports 11 routes including 3 new (`/contracts/new`, `/contracts/[id]`, `/contracts/[id]/extra-items`).
- Branch `saqlain/phase-5` is **uncommitted** as of this entry — needs commit + push + PR + live smoke before P5-REVIEW.

### Session 14 — 2026-05-19 (TEST-P3P4 closed; Phase 5 + SH-P5 parallel tracks opened)

- TEST-P3P4 (TEST-01…07) confirmed complete and merged to `main` (fast-forwarded from `saqlain/test-p3p4`). M-1/M-2 closed.
- OQ-2 decided: B-5 items grid uses **explicit "Save All" button** — validates whole sheet client-side, then POSTs rows sequentially with progress indicator. Rationale: BOQ entry is one-time bulk import; per-row save has no atomicity and creates silent partial imports on failure.
- Shubham's parallel track (SH-P5) defined: GET bill endpoints (G-1/G-2) + export routes (G-3) on `shubham/phase-5-backend`.
- WORKPLAN.md + backend/Untitled pushed to `main` (commit `b5c0d13`).
- All context docs audited and brought to current state.

### Sessions 10–13 — 2026-05-17 (archived)

Detailed notes moved to git history and [archive/SESSION_LOG_ARCHIVE.md](archive/SESSION_LOG_ARCHIVE.md). Summary:

- **Session 10:** Phase 3 remediation (P3-01…P3-09) on `saqlain/phase-3-remediation`. Key decisions: src-layout engine packaging, API-layer tenant isolation (no RLS), pure-function domain logic, DB-enforced idempotency, typed error contract.
- **Session 11:** PR #3 merged; Codex-S post-merge regression clean (99/99 engine + 31/31 backend).
- **Session 12:** Phase 4 P4-001/002/007 — Supabase auth wiring, login/signup pages, typed `ApiProblem` client.
- **Session 13:** Phase 4 P4-004/006 complete — contract list dashboard + typed API schema generated. Infra: switched to JWKS/ES256, rotated DB password, applied DDL for migrations 010–012, provisioned tenant.

## Current Decisions

- Active docs should be read in this order: STATUS → PRODUCT → ARCHITECTURE → TASKS → REVIEW
- Historical detail should not live in the active context set when a summary/link is sufficient
- `CLAUDE.md` and `CODEX.md` act as startup instructions, not duplicate project context
- B-5 items grid: **Save All button** (not per-row save). Decided 2026-05-19. See Session 14.

## Next Actions

1. [Saqlain] Run the WORKPLAN smoke table tomorrow against the merged `main` (Create, Edit + clear optional field, Validation, Schedules, Items + bad-row TSV paste, Mutual-exclusion, Extra-items + mid-flight toggle, 409 inline error). Confirm `main` is push-ready.
2. [Saqlain] Push `main` to origin once smokes pass.
3. [CC-S] Address `P5-FUP-L1/L2/L3` (deferred LOW findings) post-merge.
4. [CC-SH] Continue SH-P5 (G-1 → G-2 → G-3); request `SH-P5-REVIEW` before merge.
