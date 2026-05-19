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

Status: **in progress** — design review as of 2026-05-19. Branch: `saqlain/phase-5`.

| ID | Title | Owner | Status | Notes |
|---|---|---|---|---|
| B-1 | Contract creation form (`/contracts/new`) | [CC-S] | pending | `POST /api/contracts`; full field validation |
| B-2 | Contract detail page (`/contracts/[id]`) | [CC-S] | pending | TanStack Query; tab scaffold for schedules/bills |
| B-3 | Contract edit (inline or modal) | [CC-S] | pending | `PUT /api/contracts/{id}`; reuse B-1 form |
| B-4 | Schedule management on detail | [CC-S] | pending | Dep: B-2 + A-1 (merged) |
| B-5 | Contract items grid (AG Grid) | [CC-S] | pending | Dep: B-4 + A-2 (merged); OQ-2 open |

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
