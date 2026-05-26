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
| P5-FUP-L2 | Delete-selected confirm wording overclaims for mixed selection | [CC-SH] | pending | REVIEW.md L-2. "This cannot be undone" applies to persisted rows only, but the count shown is `persisted + new`. Accept criteria: confirm only counts persisted/dirty rows; new-only deletions skip the modal entirely. |
| P5-FUP-L3 | Remove unreachable 409 → inline-error path on `agreement_number` | [CC-S] | complete | Session 20 (2026-05-21). Removed `serverFieldError` prop + `useEffect` from `ContractForm.tsx`; removed try/catch + `useState` from `contracts/new/page.tsx`; removed `onError` 409 branch + state from `OverviewTab`. WORKPLAN Q6 updated to drop false "server owns uniqueness" claim. |

### SH-P5 — GET Bill Endpoints + Export Backend `[CC-SH]`

Status: **ready to start**. Branch: `shubham/phase-5-backend`. These run in parallel with Phase 5 UI and unblock Phase 6.

Missing backend routes that Phase 6 UI needs:

| ID | Title | Owner | Status | Notes |
|---|---|---|---|---|
| SH-P5-1 | `GET /api/contracts/{id}/bills` | [CC-SH] | pending | List bills for a contract; tenant-checked; add to `bills.py` |
| SH-P5-2 | `GET /api/bills/{id}` | [CC-SH] | pending | Bill detail; tenant-checked via bill→contract |
| SH-P5-3 | `GET /api/bills/{id}/lines` | [CC-SH] | pending | List bill lines; add to `bills.py` |
| SH-P5-4 | `GET /api/bills/{id}/recoveries` | [CC-SH] | pending | List recoveries; add to `bills.py` |
| SH-P5-5 | `GET /api/pvc-runs/{id}/export/excel` | [CC-SH] | pending | Calls engine export; returns `.xlsx` download; see `engine/` export module |
| SH-P5-6 | `GET /api/pvc-runs/{id}/export/pdf` | [CC-SH] | pending | HTML→PDF via WeasyPrint; `GET /api/pvc-runs/{id}/export/pdf` |
| SH-P5-7 | Tests for SH-P5-1…4 | [CC-SH] | pending | Follow TEST-01 pattern: valid list, wrong-tenant → 404 |

**Acceptance criteria for SH-P5-1…4:** same tenant-check pattern as existing POST routes; empty list (not 404) for zero rows.

**Acceptance criteria for SH-P5-5…6:** approved run → file download; unapproved run → 422 with `run_not_approved` code.

**Dependency for SH-P5-5…6:** verify `engine/` has export logic before writing route (check `engine/engine/` for export module).

### IDX — Index Data & Manager UI (WPI / JPC) `[unassigned]` — flagged 2026-05-26

Status: **flagged, not started.** Captures the open gap around RBI WPI + JPC index data input. Tracking only — no implementation planned in this entry. Owner to be assigned by CC-S.

Gap surface:

| ID | Title | Owner | Status | Notes |
|---|---|---|---|---|
| IDX-1 | Source RBI WPI All-Commodities + series values for Apr-2022 → Nov-2024 | unassigned | pending | `seeds/seed_indices.py` docstring flags this period as "RBI not available for this period — must be sourced separately". Data sourcing task, not code |
| IDX-2 | Backend: `POST /api/indices/{series}/months` for manual monthly entry | unassigned | pending | Per `PRODUCT.md`: "Index master with seeded historical RBI/JPC values (2022–present) + manual monthly entry for new months". No route exists yet |
| IDX-3 | Backend: `GET /api/indices` + `GET /api/indices/{series}` for list/detail | unassigned | pending | Needed before IDX-4 can show data |
| IDX-4 | Frontend: replace `/indices` page stub with series list + monthly entry form | unassigned | pending | Currently just an `EmptyState` at `frontend/app/(app)/indices/page.tsx:17`; copy promises "Once API is live, this page will list series and let you add the current month" |
| IDX-5 | Retroactive index revision alerting (Phase 2 deferred per `PRODUCT.md`) | unassigned | pending | When a published index value is revised after a bill has used it, surface the affected runs |

**Why this is flagged now:** the Index Manager is a v1 product requirement (`PRODUCT.md`) but has no task ID anywhere in the workplan. Phase 7 (PVC Run UI) will exercise these series, and Phase 8 (Export UI) bills will reference them — without monthly entry, the system can't ingest new months as they're published.

**Out of scope here:** docs-only flag — no code, no engine/migration changes. This row exists to make the gap visible so CC-S can scope and assign before Phase 7 begins.

### Phases 6–9 — Forward Plan

| Phase | Owner | Dependency |
|---|---|---|
| Phase 6 — Bill entry UI (C-1…C-3) | [CC-S] | B-2 stable + SH-P5-1…4 merged |
| Phase 7 — PVC run + results UI (D-1…D-4) | [CC-S] | C-3 stable |
| Phase 8 — Export UI (E-1, E-2) | [CC-S] | D-4 + SH-P5-5…6 merged |
| Phase 9 — E2E + integration (F-1…F-3) | [CC-S]+[CC-SH] | Phase 8 stable |

## Next Review Checkpoints

- `P5-REVIEW` — Codex-S adversarial pass after Phase 5 UI (B-1…B-5) lands
- `SH-P5-REVIEW` — CC-S review of Shubham's GET endpoints + exports before merge
- `P8-REVIEW` — export format parity review
- `P9-DEBUG` — second-pass debugging and edge-case hunt
