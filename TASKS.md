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
- **P3 remediation (P3-R1…P3-R10): complete on `saqlain/phase-3-remediation` (2026-05-17)**

## Current Workstreams

### Phase 3 — Re-review

Status: code + tests landed; awaiting Codex-S re-review against the [P3-REVIEW checklist](archive/REVIEW_ARCHIVE.md)

| ID | Title | Owner | Status | Notes |
|---|---|---|---|---|
| P3-RE-REVIEW | Run adversarial review against `saqlain/phase-3-remediation` | [CODEX-S] | pending | Use the prewritten P3-REVIEW checklist; verify `P3-01…P3-09` resolutions hold under the live API |
| P3-RE-MERGE | Merge `saqlain/phase-3-remediation` → `main` | [CC-S] | blocked | Blocked on `P3-RE-REVIEW` clearance |
| P3-RE-BACKFILL | Add schedules, contract_items, recoveries, documents endpoints | [CC-SH] | pending | Not blocking — add as Phase 5/6 UI needs them |

### Phase 4 — Frontend Shell + Navigation

Status: scaffold complete; live integration unblocks after P3 re-review clears

| ID | Title | Owner | Status | Notes |
|---|---|---|---|---|
| P4-001 | Supabase auth client wiring | [CC-S] | pending | Unblocks after P3 merge |
| P4-002 | Auth pages: login, signup | [CC-SH] | pending | UI task after P4-001 |
| P4-003 | App shell | [CC-S] | complete | Scaffold landed |
| P4-004 | Contract list dashboard | [CC-S] | pending | Unblocks after P3 merge; `GET /api/contracts` contract is stable |
| P4-005 | Error boundaries/global handling | [CC-S] | complete | Backend now ships matching error contract (P3-09); frontend `apiFetch` needs to switch on `detail.code` |
| P4-006 | TanStack Query + typed API integration | [CC-S] | in_progress | Generate types from `/openapi.json` once backend is live |
| P4-007 | Update `frontend/lib/api/client.ts` to surface structured `detail.code` | [CC-S] | pending | Pairs with P3-09 backend contract |

### Phases 5–9 — Forward Plan

Remain planned. Do not advance if they depend on unresolved Phase 3 review findings.

- Phase 5: contract setup UI
- Phase 6: bill entry UI
- Phase 7: PVC run/results UI
- Phase 8: export layer
- Phase 9: integration + testing

## Next Review Checkpoints

- `P3-RE-REVIEW` — Codex-S re-review of the remediation branch
- `P8-REVIEW` — export format parity review
- `P9-DEBUG` — second-pass debugging and edge-case hunt
