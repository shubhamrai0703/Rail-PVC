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

Status: open. Fixes the two medium findings from PR #4 review and runs the full regression suite.

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

### Phases 5–9 — Forward Plan

Remain planned. Do not advance if they depend on unresolved Phase 3 review findings.

- Phase 5: contract setup UI
- Phase 6: bill entry UI
- Phase 7: PVC run/results UI
- Phase 8: export layer
- Phase 9: integration + testing

## Next Review Checkpoints

- `TEST-P3P4-REVIEW` — Codex-S adversarial pass after TEST-01…TEST-04 land (verify M-1/M-2 closed, suite green)
- `P8-REVIEW` — export format parity review
- `P9-DEBUG` — second-pass debugging and edge-case hunt
