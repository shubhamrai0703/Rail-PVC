# TASKS.md — RailPVC Active Task Board

Use this file for current and upcoming work only.

Start with [STATUS.md](STATUS.md) for current blockers and branch state.

## Canonical Links

- Current state: [STATUS.md](STATUS.md)
- Product truth: [PRODUCT.md](PRODUCT.md)
- Architecture: [ARCHITECTURE.md](ARCHITECTURE.md)
- Coding/review rules: [ENGINEERING_GUIDELINES.md](ENGINEERING_GUIDELINES.md)
- Active review cycle: [REVIEW.md](REVIEW.md)
- Current log: [SESSION_LOG.md](SESSION_LOG.md)

## Owners

- `[CC-S]` — Claude Saqlain: engine, auth, business logic, critical UI, review responses
- `[CC-SH]` — Claude Shubham: UI generation tasks and non-critical API/UI scaffolding
- `[CODEX-S]` — Codex Saqlain: adversarial review checkpoints only; writes to `REVIEW.md`

## Working Rules

- `BLOCKED: <reason>` means stop and resolve the blocker before continuing
- Do not merge with open `CRITICAL` or `HIGH` findings in [REVIEW.md](REVIEW.md)

## Completed Milestones

- Phase 0 scaffolding: complete
- Phase 1 data model + migrations (001–011): complete
- Phase 2 engine: complete
- P2 review/fix cycle: complete
- P3 pre-review hardening: complete
- P3 initial implementation branch: quarantined after review failure
- **P3 remediation (P3-01…P3-09): merged to `main` via PR #3 (2026-05-17)**
- **Phase 4 frontend (P4-001…P4-007): all complete on `main` (2026-05-17)**
- **Phase 3 backfill (P3-BF-1…P3-BF-4): merged to `main` via PR #4 (2026-05-18)**
- **TEST-P3P4 (TEST-01…TEST-07): merged to `main` (2026-05-19) — M-1/M-2 closed, 55/55 backend tests, 99/99 engine tests**
- **Phase 5 UI implementation (P5-001…P5-008): complete on `saqlain/phase-5` (2026-05-19) — 61/61 backend tests, `next build` clean. Awaiting commit + P5-REVIEW.**
- **P5-REVIEW remediation + Phase 5 merge to `main` (2026-05-20):** C-1 + H-1/H-2/H-3 + M-1…M-6 + L-4 closed. Pre-existing lint dirt also cleared. **82/82 backend** on `fastapi==0.115.12`, 99/99 engine, 16/16 frontend vitest, `next build` clean, `npm run lint` 0/0. Local merge complete; awaiting Saqlain's smoke pass + push. L-1/L-2/L-3 deferred to P5-FUP rows below.

## Current Workstreams

### Phase 3 — Backfill endpoints

Status: **merged via PR #4 (2026-05-18)**. Two medium findings from CC-S review tracked below in TEST-P3P4.

| ID | Title | Owner | Status | Notes |
|---|---|---|---|---|
| P3-BF-1 | `POST/GET /api/contracts/{id}/schedules` | [CC-SH] | complete | Merged PR #4 |
| P3-BF-2 | `POST/GET /api/schedules/{id}/items` (contract_items) | [CC-SH] | complete | Merged PR #4 |
| P3-BF-3 | `POST /api/bills/{id}/recoveries` | [CC-SH] | complete | Merged PR #4 |
| P3-BF-4 | `POST/GET /api/contracts/{id}/documents` | [CC-SH] | complete | Merged PR #4 |

### TEST-P3P4 — Full test pass: Phase 3 backfill + Phase 4 findings

Status: **complete — merged to `main` (2026-05-19)**. All findings closed; suite green.

| ID | Title | Owner | Status | Notes |
|---|---|---|---|---|
| TEST-01 | Add `test_p3_bf_3_recoveries.py` | [CC-S] | complete | 3 tests: valid type, invalid → ValidationProblem(422), wrong-tenant → NotFoundProblem(404). Mocks at session boundary (route SQL is Postgres-specific) |
| TEST-02 | Wrap storage errors in `StorageProblem(503)` | [CC-S] | complete | `StorageProblem` added to `services/errors.py`; `upload_document` wraps SDK exceptions; route returns 503/`storage_unavailable` (test via TestClient + dep overrides) |
| TEST-03 | Pin route count assertion in `test_p3_08` | [CC-S] | complete | Asserts `len(app.routes) == 28` with a "bump-when-you-add-a-route" hint message |
| TEST-04 | Fix backend auth test tokens (HS256 → ES256) | [CC-S] | complete | No HS256 token-minting existed; all auth-gated tests use `app.dependency_overrides[get_current_user]`. Stripped the leftover `SUPABASE_JWT_SECRET=test-secret` env from test_p3_03 + updated misleading "HS256" comment in test_p3_01 |
| TEST-05 | Full backend suite green | [CC-S] | complete | 55/55 passing (49 baseline + 5 new TEST-01/02 tests + 1 storage problem class test) |
| TEST-06 | Engine regression clean | [CC-S] | complete | 99/99 still clean |
| TEST-07 | Frontend smoke | [CC-S] | complete | `next build` clean (no type errors); live browser flow not run in this CC-S session — see PR description |

### Phase 4 — Frontend Shell + Navigation

Status: scaffold complete (on main); live integration unblocked

| ID | Title | Owner | Status | Notes |
|---|---|---|---|---|
| P4-001 | Supabase auth client wiring | [CC-S] | complete | `lib/supabase/{client,server}.ts`; middleware; auth header injection in `apiFetch`; user menu + sign-out in Header |
| P4-002 | Auth pages: login, signup | [CC-S] | complete | `(auth)/login` + `(auth)/signup`; `/auth/callback` route handler |
| P4-003 | App shell | [CC-S] | complete | Scaffold landed |
| P4-004 | Contract list dashboard | [CC-S] | complete | TanStack Query against live `GET /api/contracts`; empty state + row table |
| P4-005 | Error boundaries/global handling | [CC-S] | complete | Backend error contract on main (P3-09); pairs with P4-007 |
| P4-006 | TanStack Query + typed API integration | [CC-S] | complete | `lib/api/schema.ts` generated from live `/openapi.json` (970 lines) |
| P4-007 | `frontend/lib/api/client.ts` switches on `detail.code` | [CC-S] | complete | `ApiProblem` union + `ApiError.detail`; toast copy per code |

### Phase 5 UI — Contract Setup `[CC-S]`

Status: **implementation complete (P5-001…P5-008 on 2026-05-19; P5-F1…F5 on 2026-05-20)** — branch `saqlain/phase-5`. 67/67 backend tests + `next build` clean. Smoke passed 2026-05-20. Awaiting `P5-REVIEW`.

| ID | Title | Owner | Status | Notes |
|---|---|---|---|---|
| P5-001 | Backend: `PUT /api/contracts/{id}` + expanded GET | [CC-S] | complete | `ContractUpdate` partial via `model_fields_set`; 5 new tests; route count 28→29 |
| P5-002 | Frontend deps + shared constants (`zones.ts`, `contracts-schema.ts`) | [CC-S] | complete | `react-hook-form` 7.76.0, `@hookform/resolvers` 5.2.2, `zod` 4.4.3, `ag-grid-community` + `ag-grid-react` 35.3.0 |
| P5-003 / B-1 | `/contracts/new` creation form | [CC-S] | complete | `ContractForm` + `ZoneSelect`; `base_month` auto-appends `-01`; 409 → inline error |
| P5-004 / B-2 | `/contracts/[id]` detail + tab shell | [CC-S] | complete | TanStack Query; `?tab=` URL state; ExtraNS link auto-shows when schedule exists |
| P5-005 / B-3 | Overview tab inline edit | [CC-S] | complete | Calls PUT; cancel discards; 409 inline; query invalidation on save |
| P5-006 / B-4 | Schedules tab + `ScheduleForm` | [CC-S] | complete | DSR/NS/ExtraNS select; `bid_discount_pct` as fraction; deferred fetch via `enabled` |
| P5-007 / B-5 | Items tab — `ItemsGrid` (AG Grid) | [CC-S] | complete | Community module registration; cement+steel mutual-exclusion warning; **Save All** with sequential POST + progress |
| P5-008 | `/contracts/[id]/extra-items` page | [CC-S] | complete | Optimistic Yes/No/Undecided toggles; banner switches on undecided count |
| P5-F1 | Items grid: column-header tooltips (ⓘ icon) | [CC-S] | complete | `TooltipHeader` AG Grid header component; ⓘ + native `title` on 6 columns |
| P5-F2 | Items grid: Excel paste import dialog | [CC-S] | complete | "Import rows" button → `ImportRowsModal` with `<textarea>` → `parseTsvImport` → preview table → append as `_rowState: "new"` |
| P5-F3 | Items grid: proper CRUD (update + delete) | [CC-S] | complete | Backend: `PUT/DELETE /api/schedules/{id}/items/{item_id}` with two-step tenant gate (`_assert_item_under_schedule_for_tenant`) + 6 new tests; route count 29→31. Frontend: `_rowState: new/dirty/persisted`; Save All routes new→POST, dirty→PUT; checkbox column + "Delete selected (N)" with confirm for persisted rows |
| P5-F4 | Items grid: fix mutual-exclusion warning copy | [CC-S] | complete | Banner rewritten to user-facing copy |
| P5-F5 | Extra-items: explicit Save button (staged changes) | [CC-S] | complete | `pending` local map; toggles update state only; "Save changes (N)" runs `Promise.all` POSTs; amber dot per dirty row; on failure pending preserved; banner reads merged view |

### P5-REVIEW deferred follow-ups (post-merge)

| ID | Title | Owner | Status | Notes |
|---|---|---|---|---|
| P5-FUP-L1 | Partial-success state drift in `ExtraItemDecisionList.saveChanges` | [CC-S] | complete | Session 20 (2026-05-21). `Promise.all` → `Promise.allSettled`; drop fulfilled keys from `pending`; failed keys retained for retry (POST is idempotent). Toast copy: "N of M failed to save" on partial failure. |
| P5-FUP-L2 | Delete-selected confirm wording overclaims for mixed selection | [CC-SH] | complete | Merged via PR #9 (2026-05-30). Saved vs unsaved counts now separate; new-only skips modal. |
| P5-FUP-L3 | Remove unreachable 409 → inline-error path on `agreement_number` | [CC-S] | complete | Session 20 (2026-05-21). Removed `serverFieldError` prop + `useEffect` from `ContractForm.tsx`; removed try/catch + `useState` from `contracts/new/page.tsx`; removed `onError` 409 branch + state from `OverviewTab`. WORKPLAN Q6 updated to drop false "server owns uniqueness" claim. |

### SH-P5 — GET Bill Endpoints + Export Backend `[CC-SH]`

Status: **ready to start**. Branch: `shubham/phase-5-backend`. These run in parallel with Phase 5 UI and unblock Phase 6.

Missing backend routes that Phase 6 UI needs:

| ID | Title | Owner | Status | Notes |
|---|---|---|---|---|
| SH-P5-1 | `GET /api/contracts/{id}/bills` | [CC-SH] | complete | Merged via PR #7 (2026-05-30) |
| SH-P5-2 | `GET /api/bills/{id}` | [CC-SH] | complete | Merged via PR #7 (2026-05-30) |
| SH-P5-3 | `GET /api/bills/{id}/lines` | [CC-SH] | complete | Merged via PR #7 (2026-05-30) |
| SH-P5-4 | `GET /api/bills/{id}/recoveries` | [CC-SH] | complete | Merged via PR #7 (2026-05-30) |
| SH-P5-5 | `GET /api/pvc-runs/{id}/export/excel` | [CC-SH] | complete | `api/exports.py` + `services/exports.py` (openpyxl). Tenant 404 → status 422 `run_not_approved` → attachment. No engine export module existed → built from run+component rows. Route count 38→40. 2026-06-02 |
| SH-P5-6 | `GET /api/pvc-runs/{id}/export/pdf` | [CC-SH] | complete | Same gate; PDF via **fpdf2** (pure-Python) instead of WeasyPrint — GTK native deps aren't pip-installable on the Windows test env, violating "clean checkout boots from declared deps". Format parity deferred to P8-REVIEW. 9 tests in `test_sh_p5_exports.py`. 2026-06-02 |
| SH-P5-7 | Tests for SH-P5-1…4 | [CC-SH] | complete | 12 tests in `test_sh_p5_bills_get.py`; merged PR #7 |

**Acceptance criteria for SH-P5-1…4:** same tenant-check pattern as existing POST routes; empty list (not 404) for zero rows.

**Acceptance criteria for SH-P5-5…6:** approved run → file download; unapproved run → 422 with `run_not_approved` code.

**Dependency for SH-P5-5…6:** verify `engine/` has export logic before writing route (check `engine/engine/` for export module).

### IDX — Index Data & Manager UI (WPI / JPC) `[unassigned]` — flagged 2026-05-26

Status: **flagged, not started.** Captures the open gap around RBI WPI + JPC index data input. Tracking only — no implementation planned in this entry. Owner to be assigned by CC-S.

Gap surface:

| ID | Title | Owner | Status | Notes |
|---|---|---|---|---|
| IDX-1 | Source RBI WPI All-Commodities + series values for Apr-2022 → Nov-2024 | unassigned | pending | Data sourcing task, not code. Lower urgency — seed Dec-2024→Dec-2025 covers forward work |
| IDX-2 | Backend: `POST /api/indices/{series}/months` + `GET /api/indices` + `GET /api/indices/{series}` | [CC-S] | complete | Migration 013 (`users.is_admin`); `require_admin` dep; 3 new routes; 10 tests; route count 35→38. 2026-05-30 |
| IDX-3 | Backend read endpoints (list + detail) | [CC-S] | complete | Merged with IDX-2 (2026-05-30) |
| IDX-4 | Frontend: replace `/indices` page stub with series list + monthly entry form | [CC-SH] | complete | `/indices` series list + `/indices/[series]` detail (observations table + `IndexMonthForm`). Optimistic UI — backend `require_admin` stays sole enforcement; 403/409 surfaced inline. `lib/indices.ts` + 3 vitest. Frontend-only, route count stays 38. 2026-06-02 |
| IDX-5 | Retroactive index revision alerting (Phase 2 deferred per `PRODUCT.md`) | unassigned | pending | Post-MVP |

**Why this is flagged now:** the Index Manager is a v1 product requirement (`PRODUCT.md`) but has no task ID anywhere in the workplan. Phase 7 (PVC Run UI) will exercise these series, and Phase 8 (Export UI) bills will reference them — without monthly entry, the system can't ingest new months as they're published.

**Out of scope here:** docs-only flag — no code, no engine/migration changes. This row exists to make the gap visible so CC-S can scope and assign before Phase 7 begins.

### Phase 6 — Bill Entry UI `[CC-S]`

Status: **C-1 + C-2 + two demo smoke-test fixes merged to `main` (2026-06-02).** C-3 next. See WORKPLAN.md Phase 6 section for the route map.

| ID | Title | Owner | Status | Notes |
|---|---|---|---|---|
| C-1 | `POST /api/contracts/{id}/bills` 409 hardening + bills list/create UI | [CC-S] | complete | Route already existed (P3 remediation); added `ConflictProblem` on `UNIQUE(contract_id, bill_number)`, gated via `assert_contract_belongs_to_tenant`, dropped client `net_amount`. 3 tests (`test_c1_bills_create.py`). Frontend: separate `/contracts/[id]/bills` page + `BillForm` (inline 409). Route count stays 38. |
| C-2 | Bill detail `/contracts/[id]/bills/[billId]` | [CC-S] | complete | Frontend only — all GET routes exist (SH-P5). Header fields + read-only lines table (empty until Phase 7) + recoveries table & `RecoveryForm` (`POST /api/bills/{id}/recoveries`). |
| C-2-FIX-A | Items grid "Invalid Number" fix | [CC-S] | complete | AG Grid v35 `cellDataType: "number"` formatter printed literal "Invalid Number" (type-inference re-applied). Data path was clean. Fix in `ItemsGrid.tsx`: `cellDataType: false` + module-scope `numberValueParser`/`numberValueFormatter` on the 4 numeric columns. |
| C-2-FIX-B | "Calculate PVC" trigger card on bill detail | [CC-S] | complete | Engine endpoint `POST /api/contracts/{id}/pvc-runs` existed but had no caller. Added PVC card to `bills/[billId]/page.tsx`: `useMutation` with fresh `Idempotency-Key`, renders total_pvc/carry-forward/quarter, inline errors (`silent:true`), invalidates `bill` + `bill-lines`. |
| C-3 | Bill header inline edit + recovery delete + computed net_amount | [CC-S] | complete | `PUT /api/bills/{id}` (partial via `model_fields_set`, NOT-NULL + positivity guards, 409 on dup bill_number) + `DELETE /api/bills/{id}/recoveries/{rid}` (two-step gate, 204). `net_amount` computed server-side on read via `_NET_AMOUNT_EXPR` (gross − Σ recoveries where `affects_pvc_base=FALSE`). FE: `BillHeaderForm` inline edit (409 inline) + per-row recovery delete + net label note. Route count 40→42. +15 backend / FE clean. |
| C-3-FUP-NET | Validate the net_amount formula against a real submission | [CC-S] | pending | **FLAGGED decision (2026-06-08):** net = gross − Σ(`affects_pvc_base=FALSE`) treats PVC-affecting recoveries as notional (reduce W only, not net payable). Not certain to be the best model — confirm with a Railway field account; if net payable should net ALL recoveries, flip the filter in `_NET_AMOUNT_EXPR`. |

**Resolved Phase 6 open questions:** (1) `bill_number` uniqueness — already `UNIQUE(contract_id, bill_number)` in migration 003, so **per-contract**; no migration needed. (2) Page vs tab — **separate `/contracts/[id]/bills` page** (avoids tab overload; natural parent for the `[billId]` sub-route).

### P6-REVIEW — Codex-S adversarial findings `[CODEX-S → CC-S]`

Status: **open (2026-06-04).** Codex-S pass on the merged Phase 6 Bill Entry UI. 2 HIGH, 2 MEDIUM, 0 CRITICAL/LOW. Detail + CC Responses in [REVIEW.md](REVIEW.md). Prompt archived at `REVIEW_P6_PROMPT.md`.

| ID | Title | Owner | Status | Notes |
|---|---|---|---|---|
| P6-H1 | `affects_pvc_base=TRUE` recoveries ignored by PVC calc | [CC-S] | complete (interim A) | **Decision: A now, C later** (Saqlain 2026-06-04). `build_bill_payload` sums `affects_pvc_base=TRUE` recoveries into `technical_withheld` (named W subtraction; `on_account` not netted). +2 tests (`test_p6_h1_recoveries_in_w.py`). 125/125 backend. |
| P6-H2 | Backend accepts non-positive bill/recovery amounts | [CC-S] | complete | `ValidationProblem` on `bill_number<=0`, `gross_amount<=0` (before tenant gate), recovery `amount<=0`. +8 tests. 125/125 backend. |
| P6-M3 | Malformed AG Grid numeric edits silently null the cell | [CC-S] | complete | Pure `lib/parseNumericCell.ts` (strip separators, reject non-decimal); parser keeps `oldValue` + toasts on reject. +5 vitest. |
| P6-M4 | Calculate-PVC error drops engine `validation_errors` list | [CC-S] | complete | Pure `lib/pvcRunError.ts::describePvcRunError`; PVC card renders the list. +4 vitest. |
| P6-H1-FUP-C | Replace interim A with a dedicated `RecoveriesAffectingPVC` W bucket | [CC-S] | complete | 2026-07-02. `recoveries_affecting_pvc: Decimal = 0` added to engine `BillPayload`/`WDerivation`, subtracted in `derive_w()`, traced in `calculator.py`. `technical_withheld` now genuinely empty (no producer yet) — recoveries flow into the new bucket. Backend/frontend/ARCHITECTURE.md updated. 103/103 engine, 153/153 backend, 54/54 vitest green. |

### DEMO — Seed Test Dataset for PVC Cycle Walk-Through `[CODEX-S → CC-S]`

Status: **Codex generating the seed script.** Purpose: a realistic, idempotent demo dataset so the team can visualise the Phase 5–6 UI end-to-end and (via scripts) reconcile against pinned engine outputs. The PVC-run UI itself is Phase 7 — until then, PVC numbers are visible only through `scripts/run_engine_fixture.py`.

| ID | Title | Owner | Status | Notes |
|---|---|---|---|---|
| DEMO-1 | `seeds/seed_demo_contract.py` — Banjara/COLABA BP 252 (BCT-24-25-252) | [CODEX-S] | blocked | Script now requires an explicit `SEED_TENANT_ID`; the unsafe personal-tenant fallback and `.env` override were removed. Production run remains blocked by DEMO-2 reconciliation: current service-shaped inputs/current indices calculate Bill 1 `63,253.98` and Bill 2 `100,772.51`, not pinned `0.00` / `76,959.55`. |
| DEMO-2 | CC-S review of Codex's `seed_demo_contract.py` before first run | [CC-S] | reviewed — failed reconciliation gate | Passed: tenant/zone/base month, FK order, Decimal handling, sequential rerun idempotency, fixture bucket/header mapping. Blockers: technical-withheld is stored in `special_condition_amount` but not fed to the engine field; Bill 2 carry-forward is fixture-direct amount vs service-derived quantity x rate; live seeded index observations differ from historical fixture snapshots. Per the no-number/no-engine-change constraint, do not run the demo seed live until the authoritative data contract is decided. |

**Why this exists:** captures the demo/test-data effort so it doesn't get lost. The seed lets Saqlain click through contract → schedules → items → bills → recoveries with real numbers, and serves as the canonical demo piece. Index coverage (Dec-2024→Dec-2025) from `seed_indices.py` already supports the Bill-1/Bill-2 measurement quarters.

### P5-IMP — Smart Items Import (xlsx + fuzzy mapper) `[CC-S]`

Status: **frontend complete on `saqlain/p5-imp` (2026-06-02)**. Replaces the Session-15 positional-paste flow with file upload + paste, sheet/header picker, and auto-mapping via a deterministic header fuzzy matcher (Option A). AI mapper (Option B) backend code is on disk but not wired — follow-up branch.

| ID | Title | Owner | Status | Notes |
|---|---|---|---|---|
| P5-IMP-4 | Frontend: `lib/parseXlsx.ts` (exceljs wrapper, lazy-loaded) | [CC-S] | complete | xlsx-from-npm has open CVEs; used `exceljs` instead. Returns normalized `{sheets: [{name, rows}]}` |
| P5-IMP-5 | Frontend: `lib/fuzzyHeaderMap.ts` (Option A synonym matcher) | [CC-S] | complete | Token-set scoring + per-target synonym tables (railway vocabulary: BOQ Item, UOM, SOR Rate, Quoted Rate, etc.); collision resolution; missing-required detection |
| P5-IMP-6 | Frontend: `lib/normalizeImportRows.ts` | [CC-S] | complete | Mapping + raw rows → ParsedRow[]; preserves H-1 strict-token rule for cement/steel; thousand-separator stripping; value_normalizations hook for future AI mapper |
| P5-IMP-7 | Frontend: `ImportRowsModal` v2 | [CC-S] | complete | Tabbed source (file/paste), sheet+header picker, mapping table with auto-map + manual override, AI button stubbed (disabled with tooltip), preview, commit. Replaces inline modal in `ItemsGrid.tsx`. |
| P5-IMP-9 | Vitest tests | [CC-S] | complete | 17 new tests (fuzzy matcher + row normalizer). 33/33 total. `next build` + `npm run lint` clean. |
| P5-IMP-10 | Docs sync | [CC-S] | complete | This entry + SESSION_LOG Session 23 |
| P5-IMP-1 | Migration 014 — `import_templates` table | [CC-S] | code on disk | Not in head; lands with follow-up branch |
| P5-IMP-2 | Backend: template CRUD (`/api/imports/templates`) | [CC-S] | code on disk | `backend/api/imports.py` exists; not wired into `main.py` |
| P5-IMP-3 | Backend: AI mapper (`POST /api/imports/suggest-mapping`, Claude Haiku 4.5) | [CC-S] | code on disk | `backend/services/llm.py` exists; needs `anthropic` dep + `ANTHROPIC_API_KEY` env + route-count bump 38→42. Frontend AI button stays disabled until landed. |
| P5-IMP-FUP-1 | Wire backend (router include, anthropic dep, env, route-count bump, pytest) | [CC-S] | complete | 2026-07-02. `imports.router` wired in `main.py`; `anthropic>=0.40` added to `pyproject.toml`; `ANTHROPIC_API_KEY=` added to `.env.example`; route count bumped 43→47; 11 new tests in `test_p5_imp_imports.py`. 164/164 backend. |
| P5-IMP-FUP-2 | Templates apply/save UI in `ImportRowsModal` | [Fable] | complete | 2026-07-16, in working tree (not committed). `ImportTemplateControls` bar in the mapping step: list/apply/delete saved templates + save current mapping under a name (409 duplicate-name rendered inline). Pure helpers in `lib/importTemplates.ts` (FNV-1a `headerSignature`, normalized-header `applyTemplateMapping`) + 11 vitest (65 total). `schema.ts` regenerated (47 routes). Browser smoke test done against a mock API — Supabase project unreachable (paused?), see handoff Results. |

### Phase 7 — PVC Run + Results UI `[CC-S]`

Status: **implemented + P7-REVIEW remediated. Merged to `main` via PR [#14](https://github.com/saqlainmmomin/Rail-PVC/pull/14) (2026-06-11).** 153/153 backend, 99/99 engine, 52/52 vitest, tsc/eslint/next-build clean, route count 43. All HIGH/MEDIUM findings closed (see [REVIEW.md](REVIEW.md)).

| ID | Title | Owner | Status | Notes |
|---|---|---|---|---|
| D-1a | Migration 015 + persist/return run result totals | [CC-S] | complete | `pvc_runs` gains `total_pvc`/`negative_carry_forward`/`quarter_used` (nullable), written at run INSERT from the engine result; `GET /pvc-runs/{id}` returns them + `superseded_by`. Closes a latent audit gap — the **output** carry-forward was previously returned only in the POST body and persisted nowhere. |
| D-1b | `GET /api/contracts/{id}/pvc-runs` run-history list | [CC-S] | complete | Gated by `assert_contract_belongs_to_tenant` (404 foreign contract, empty list for zero runs — mirrors `GET /contracts/{id}/bills`). Newest first. Route count 42→43. |
| D-1c | Backend tests | [CC-S] | complete | `test_d1_pvc_run_results.py` (5): GET-detail totals + components, wrong-tenant 404, list happy/empty/wrong-tenant. Route-count assertion bumped to 43. |
| D-2 | Run results page | [CC-S] | complete | `/contracts/[id]/bills/[billId]/runs/[runId]`. Status badge, result summary, W-derivation panel (named steps; honest `technical_withheld` label per deferred P6-H1-FUP-C), component breakdown, engine-generated bill lines. |
| D-3 | Approve flow + exports | [CC-S] | complete | Approve button (409 `immutable_approved_run` inline) + Excel/PDF buttons gated on `Approved` (mirrors 422 `run_not_approved`). New `apiDownload` helper in `lib/api/client.ts` (auth blob download honoring `Content-Disposition`). Calculate card links to run page via returned `id`. |
| D-4 | Run history + tests | [CC-S] | complete | Run-history list on bill detail filtered to the bill. Pure `lib/pvcWDerivation.ts` + `lib/pvcRunStatus.ts` (statusVariant deduped from bill page) with 7 vitest. |
| D-FUP-1 | Apply migration 015 to Supabase before running PVC on real bills | [CC-S] | complete | Done 2026-06-11 via `alembic upgrade head` (DB now at 016; stamped 013 — `is_admin` pre-existed out-of-band; created `get_tenant_id()` so 014's RLS policies could apply). Existing rows keep NULL totals (acceptable — pre-Phase-7). |
| P7-FUP-L1 | Extract shared `authedFetch` from `apiFetch`/`apiDownload` | [CC-S] | complete | 2026-07-02. `authedFetch` private helper owns auth injection + network-failure logging + toast; `resolveErrorMessage` unifies two-tier error resolution (structured → string `detail` → statusText). `apiDownload` now gets `console.error` logging (was missing) and string-`detail` fallback (was missing) — both were real drift bugs. No caller changes. |
| P7-FUP-L2 | `describeWDerivation` arithmetic guard | [CC-S] | complete | 2026-07-02, landed with P6-H1-FUP-C. `describeWDerivation` now computes `on_account - Σ subtractions - w`; pushes an amber "⚠ Residual (unaccounted)" warning row when `|residual| > 0.01`. 2 new vitest (consistent / inconsistent cases). |

### KU-001 — Rolling-quarter remediation `[CC-S + ChatGPT Codex Sol]`

Status: **complete on `saqlain/fup-backlog` (2026-07-16), merging to `main`.** Domain confirmation (rolling-from-base, anchored to contract `base_month`) closed the design question CC-S opened in `tasks/handoffs/2026-07-15-ccs-quarter-convention.md`; ChatGPT Codex Sol implemented it per `tasks/handoffs/2026-07-16-sol-quarter-rolling-fix.md`.

| ID | Title | Owner | Status | Notes |
|---|---|---|---|---|
| KU-001-FIX | Rewrite `resolve_quarter` for rolling-from-base ordinals; thread `base_month` through engine + backend callers | [Sol] | complete | `quarter.py` rewritten; `calculator.py:318` and `backend/services/pvc_service.py:549` pass `indices.base_month`. Pre-Q1 measurement dates surface a blocking validation error, not an exception. |
| KU-001-FIXTURES | Refresh 14 golden-fixture xfail pins/markers from rolling results | [Sol] | complete | Fixture module: **12 passed, 9 xfailed**. 9 bills flip to genuine PASS; JRH Bills 3–5 + STC Bills 1–4 + `bct_2425_183_bill2_q3` + `bct_2425_252_golden_bill2_q4` remain xfail — verified workbook-internal divergences, not quarter bugs. |
| KU-001-REVIEW | Adversarial review of the quarter-fix diff | [Fable]+[Opus] | complete | 2026-07-16. Formal cycle landed in [REVIEW.md](REVIEW.md) (`KU-001-REVIEW`, per `2026-07-16-opus-ku001-adversarial-review.md`): **no HIGH/MEDIUM defects; 1 LOW deferred** (KU1R-L1 — no DB CHECK that `base_month` is day=01; API-layer-only enforcement). All four scrutiny points verified with traced evidence incl. a 99,696-case brute-force of `resolve_quarter` vs an independent reference (0 mismatches, day-invariant). 2 coverage gaps closed: second-year-boundary window test (`engine/tests/test_quarter.py:39`) + HTTP-level pre-Q1 422 pin (`backend/tests/test_p3_04_zone_snapshot.py`, end). Engine 122 passed / 9 xfailed, backend **167/167**. Uncommitted in working tree pending Saqlain. |
| KU-001-STC-AVG | Rule-set-scoped STC quarter-average precision (Option 2) | [Saqlain] | complete (uncommitted) | Option 2 selected and implemented locally on `codex/ku001-stc-avg-option2`: rule sets may opt into HALF-UP 2dp quarter averages while the default remains full precision; the two STC fixtures now reconcile strictly and existing fixtures remain invariant. Implementation and verification evidence: [tasks/handoffs/2026-07-19-ku001-stc-avg-option2-implementation.md](tasks/handoffs/2026-07-19-ku001-stc-avg-option2-implementation.md). `KU-001-STC-AVG-REVIEW` closed 2026-07-19 (Fable adversarial pass, [REVIEW.md](REVIEW.md)): 1 MEDIUM found+fixed (KU1SA-M1 — PUT omitting the new field silently reset the policy; now COALESCE-preserved), no other HIGH/MEDIUM. Engine 136/7xf, backend 180 green. Uncommitted, pending Saqlain. |

### AUDIT-1 — Usability-audit triage (2026-05-31 PDF, triaged 2026-07-17) `[CC-S]`

Source: `RailPVC Smoke Test & Usability Audit.pdf` (repo root, untracked). Audit predates Phases 5–7: its three BLOCKERs (F1–F3, infinite "Loading…" on contract detail / bills / extra-items) and its two navigation/error-state friction points (F8, F9) were verified fixed on current `main` — every affected page now has `isError` branches with messages and a back-link, and the 2026-07-16 real-stack smoke drove those screens successfully. F4 (logo "RRailPVC") is the intentional R-badge + wordmark, not a doubled string — won't-fix. F6 (Index Manager stub) is superseded by the existing IDX workstream. Accepted findings:

| ID | Audit ref | Title | Disposition | Status | Notes |
|---|---|---|---|---|---|
| AUDIT-1-1 | F10 | Gross-amount field lacks domain guidance | quick win | complete (2026-07-17) | Inline help note on `BillForm` + `BillHeaderForm`: on-account MB total; PVC exclusions deducted at run time (wording from PRODUCT.md W-derivation; GST phrasing avoided — unconfirmed). |
| AUDIT-1-2 | F12 | Contracts list missing contract value column | quick win | complete (2026-07-17) | `contract_value` added to `GET /api/contracts` SELECT + "Value (₹)" column (`formatINR`, right-aligned, "—" when null). |
| AUDIT-1-3 | F5 | Junk draft contracts visible (fake contractor, base month 2501-02) | ticket | complete (2026-07-23) | `DELETE /api/contracts/{id}` added (Draft-only gate, 204; cascade via FK). Trash button on Overview tab (Draft contracts only, browser confirm). Backend: 5 new tests + route count 48→49. **Saqlain: use the Delete button on the junk draft(s) to clear them from the live tenant.** |
| AUDIT-1-4 | F11 | Rebate entered as decimal (0.15 = 15%) invites input errors | ticket | complete (2026-07-23) | `overall_rebate` (ContractForm) and `bid_discount_pct` (ScheduleForm) now accept percent values (type 15 for 15%); backend receives fractions as before. Display in read-only views updated to show `%`. tsc + 92 vitest + next build clean. |
| AUDIT-1-5 | F7 | Document Vault non-functional | implementation | complete (2026-07-22) | Replaced the stale placeholder with contract selection, private upload/list/download, 50 MB client/server validation, DB-failure storage compensation, and live bucket setup. P5-006 was an incorrect reference (Schedules tab); backend P3-BF-4 had already shipped. |
| AUDIT-1-6 | F8 (residual) | No retry button on failed page loads | won't-fix (for now) | closed | Error states + messages exist everywhere now; React Query refetches on focus. Revisit only if real users report it. |

### Phases 8–9 — Forward Plan

| Phase | Owner | Dependency |
|---|---|---|
| Phase 8 — Export UI (E-1, E-2) | [CC-S] | Phase 7 merged + SH-P5-5…6 merged ✅ |
| Phase 9 — E2E + integration (F-1…F-3) | [CC-S]+[CC-SH] | Phase 8 stable |

## Next Review Checkpoints

- `P7-REVIEW` — Codex-S adversarial pass on `saqlain/phase-7` before merge
- `P8-REVIEW` — export format parity review
- `P9-DEBUG` — second-pass debugging and edge-case hunt
