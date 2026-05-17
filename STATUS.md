# STATUS.md — RailPVC Current State

Start here.

This file is the shortest path to current branch state, blockers, and next actions.

## Current Phase

- Active workstream: Phase 3 backfill endpoints (CC-SH) + Phase 4 frontend integration (CC-S)
- Review state: Phase 3 remediation merged to `main` via PR #3 (2026-05-17)
- Current branch in repo: `main` is the active head — no active feature branch

## Current Blockers

- None.
- Out-of-band action still required: rotate the previously-exposed Supabase project keys + Postgres password. Regex test in `backend/tests/test_p3_01_env_example.py` blocks re-introduction in code.

## Active Review Cycle

- No active cycle. P3-01…P3-09 closed; PR #3 merged.
- Post-merge regression check on `main` by [CODEX-S] on 2026-05-17 — **no findings**. Engine 99/99 + backend 31/31 passing; clean `import engine` and `from main import app` (21 routes); tenant scoping, no global index writes, typed error contract, idempotency logic all still match review intent.
- Next checkpoint: review of Phase 3 backfill endpoints (schedules / contract_items / recoveries / documents) when CC-SH opens that PR.

## Branch State

- `main` is the active head
- Deleted: `saqlain/phase-3-remediation` (merged via PR #3), `saqlain/phase-4` (superseded by remediation), `shubham/phase-3` (quarantined)
- Next feature branches: `shubham/phase-3-backfill` (CC-SH) and `saqlain/phase-4-integration` (CC-S, frontend `apiFetch` for typed error contract + auth wiring) — branch from `main`

## What To Read

### If you are implementing fixes

1. [PRODUCT.md](PRODUCT.md)
2. [ARCHITECTURE.md](ARCHITECTURE.md)
3. [ENGINEERING_GUIDELINES.md](ENGINEERING_GUIDELINES.md)
4. [TASKS.md](TASKS.md)
5. [REVIEW.md](REVIEW.md)
6. [SESSION_LOG.md](SESSION_LOG.md)

### If you are doing adversarial review

1. [PRODUCT.md](PRODUCT.md)
2. [ARCHITECTURE.md](ARCHITECTURE.md)
3. [TASKS.md](TASKS.md)
4. [REVIEW.md](REVIEW.md)
5. [ENGINEERING_GUIDELINES.md](ENGINEERING_GUIDELINES.md)

## Current Priorities

1. [CC-SH] Phase 3 backfill endpoints — schedules, contract_items, recoveries, documents — branch off `main`. Patterns and boundaries documented in PR #3 description.
2. [CC-S] Frontend `apiFetch` switches on `detail.code` for the typed error contract (P4-007); wire Supabase auth client (P4-001) and contract list (P4-004) once backend is live in a deployed env.
3. Rotate exposed Supabase credentials (out-of-band).

## File Classification

- Startup/status: [STATUS.md](STATUS.md)
- Stable truth: [PRODUCT.md](PRODUCT.md), [ARCHITECTURE.md](ARCHITECTURE.md), [ENGINEERING_GUIDELINES.md](ENGINEERING_GUIDELINES.md)
- Active state: [TASKS.md](TASKS.md), [REVIEW.md](REVIEW.md), [SESSION_LOG.md](SESSION_LOG.md)
- Instructions: [CLAUDE.md](CLAUDE.md), [CODEX.md](CODEX.md)
- Archive pointers: [archive/REVIEW_ARCHIVE.md](archive/REVIEW_ARCHIVE.md), [archive/SESSION_LOG_ARCHIVE.md](archive/SESSION_LOG_ARCHIVE.md)
