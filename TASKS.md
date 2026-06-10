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
| P6-H1-FUP-C | Replace interim A with a dedicated `RecoveriesAffectingPVC` W bucket | [CC-S] | pending | **Agreed end-state — A is not the best shape.** Add a named W bucket in the engine `BillPayload` + formula + `w_derivation`, distinct from `technical_withheld`, so genuine technical withholding and PVC-affecting recoveries disaggregate. Touches engine + 99 engine tests + ARCHITECTURE.md W invariant + run-detail UI/export. Do before any flow that must show both deductions separately. |

### DEMO — Seed Test Dataset for PVC Cycle Walk-Through `[CODEX-S → CC-S]`

Status: **Codex generating the seed script.** Purpose: a realistic, idempotent demo dataset so the team can visualise the Phase 5–6 UI end-to-end and (via scripts) reconcile against pinned engine outputs. The PVC-run UI itself is Phase 7 — until then, PVC numbers are visible only through `scripts/run_engine_fixture.py`.

| ID | Title | Owner | Status | Notes |
|---|---|---|---|---|
| DEMO-1 | `seeds/seed_demo_contract.py` — Banjara/COLABA BP 252 (BCT-24-25-252) | [CODEX-S] | in progress | Idempotent asyncpg seed (mirror `seeds/seed_indices.py` connection + `ON CONFLICT DO NOTHING` pattern). Target tenant `bd589426-93ba-4847-b5f3-1f69b020b4c0`, zone WR, `base_month` 2024-12-01. Seeds contract + `pvc_rule_set` + schedules + BOQ `contract_items` (cement/steel subtypes + ExtraNS NS-1 + carry-forward item 10.2) + two `running_bills` (8 903 877.99 / 7 250 000.00) + `bill_lines` rolling to fixture buckets + recoveries + `extra_item_decisions`. Anchored to engine fixtures `bct_2425_252_bill1_q2.json` / `bill2_q4.json` (Bill-1 total_pvc 0.00, Bill-2 76 959.55). |
| DEMO-2 | CC-S review of Codex's `seed_demo_contract.py` before first run | [CC-S] | pending | Verify: tenant/zone/base_month constants, idempotency, FK ordering, decimal precision, and that seeded amounts reconcile to the pinned fixture outputs. **Do not run against Supabase until reviewed.** Decision: the team works with the script Codex produces in its session (not a parallel CC-S implementation). |

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
| P5-IMP-FUP-1 | Wire backend (router include, anthropic dep, env, route-count bump, pytest) | [CC-S] | pending | Separate branch off `main` once P5-IMP frontend merges |
| P5-IMP-FUP-2 | Templates apply/save UI in `ImportRowsModal` | [CC-S] | pending | Blocked on FUP-1 |

### Phase 7 — PVC Run + Results UI `[CC-S]`

Status: **implemented on `saqlain/phase-7` (2026-06-10).** 145/145 backend, 99/99 engine, 52/52 vitest, tsc/eslint/next-build clean, route count 43. Awaiting commit + `P7-REVIEW`.

| ID | Title | Owner | Status | Notes |
|---|---|---|---|---|
| D-1a | Migration 015 + persist/return run result totals | [CC-S] | complete | `pvc_runs` gains `total_pvc`/`negative_carry_forward`/`quarter_used` (nullable), written at run INSERT from the engine result; `GET /pvc-runs/{id}` returns them + `superseded_by`. Closes a latent audit gap — the **output** carry-forward was previously returned only in the POST body and persisted nowhere. |
| D-1b | `GET /api/contracts/{id}/pvc-runs` run-history list | [CC-S] | complete | Gated by `assert_contract_belongs_to_tenant` (404 foreign contract, empty list for zero runs — mirrors `GET /contracts/{id}/bills`). Newest first. Route count 42→43. |
| D-1c | Backend tests | [CC-S] | complete | `test_d1_pvc_run_results.py` (5): GET-detail totals + components, wrong-tenant 404, list happy/empty/wrong-tenant. Route-count assertion bumped to 43. |
| D-2 | Run results page | [CC-S] | complete | `/contracts/[id]/bills/[billId]/runs/[runId]`. Status badge, result summary, W-derivation panel (named steps; honest `technical_withheld` label per deferred P6-H1-FUP-C), component breakdown, engine-generated bill lines. |
| D-3 | Approve flow + exports | [CC-S] | complete | Approve button (409 `immutable_approved_run` inline) + Excel/PDF buttons gated on `Approved` (mirrors 422 `run_not_approved`). New `apiDownload` helper in `lib/api/client.ts` (auth blob download honoring `Content-Disposition`). Calculate card links to run page via returned `id`. |
| D-4 | Run history + tests | [CC-S] | complete | Run-history list on bill detail filtered to the bill. Pure `lib/pvcWDerivation.ts` + `lib/pvcRunStatus.ts` (statusVariant deduped from bill page) with 7 vitest. |
| D-FUP-1 | Apply migration 015 to Supabase before running PVC on real bills | [CC-S] | pending | Dev DB needs `alembic upgrade head`; existing rows keep NULL totals (acceptable — pre-Phase-7). |

### Phases 8–9 — Forward Plan

| Phase | Owner | Dependency |
|---|---|---|
| Phase 8 — Export UI (E-1, E-2) | [CC-S] | Phase 7 merged + SH-P5-5…6 merged ✅ |
| Phase 9 — E2E + integration (F-1…F-3) | [CC-S]+[CC-SH] | Phase 8 stable |

## Next Review Checkpoints

- `P7-REVIEW` — Codex-S adversarial pass on `saqlain/phase-7` before merge
- `P8-REVIEW` — export format parity review
- `P9-DEBUG` — second-pass debugging and edge-case hunt
