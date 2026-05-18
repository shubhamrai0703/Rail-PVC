# STATUS.md — RailPVC Current State

Start here.

This file is the shortest path to current branch state, blockers, and next actions.

## Current Phase

- Active workstream: TEST-P3P4 — TEST-01…07 complete on `saqlain/test-p3p4`, awaiting review
- Phase 3 backfill complete: P3-BF-1…P3-BF-4 merged to `main` via PR #4 (2026-05-18)
- Phase 4 complete: all P4-001…P4-007 merged to `main` (2026-05-17)
- Current branch in repo: `saqlain/test-p3p4` — open PR pending

## Current Blockers

- Backend tests verified: no HS256 token-minting existed in tests/; protected routes are exercised via `app.dependency_overrides[get_current_user]`. TEST-04 closed without churn.
- Out-of-band: credential hygiene — DB password and JWT secret are in `backend/.env` (git-ignored). Keep `.env` out of version control.

## Active Review Cycle

- No active cycle. PR #4 reviewed by CC-S (2026-05-18): no CRITICAL/HIGH. Two medium findings (M-1: missing BF-3 recovery_type test; M-2: untyped 500 on Supabase storage error) tracked in TASKS.md as TEST-01 / TEST-02.
- Next checkpoint: `TEST-P3P4-REVIEW` — Codex-S pass after TEST-01…TEST-04 land.

## Branch State

- `main` is the active head
- Deleted: `saqlain/phase-3-remediation`, `saqlain/phase-4`, `shubham/phase-3`, `shubham/phase-3-backfill` (all merged)
- Next feature branch: `saqlain/test-p3p4` — branch from `main` for TEST-P3P4 fixes

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

1. [CC-S] TEST-P3P4 — branch `saqlain/test-p3p4` from `main`; complete TEST-01 through TEST-07 in order.
2. [CC-S] After TEST-P3P4 merges: Phase 5 contract creation form (`POST /api/contracts`); backend endpoint already live.
3. Credential hygiene — DB password + JWT secret are in `backend/.env` only (git-ignored). Document in onboarding.

## File Classification

- Startup/status: [STATUS.md](STATUS.md)
- Stable truth: [PRODUCT.md](PRODUCT.md), [ARCHITECTURE.md](ARCHITECTURE.md), [ENGINEERING_GUIDELINES.md](ENGINEERING_GUIDELINES.md)
- Active state: [TASKS.md](TASKS.md), [REVIEW.md](REVIEW.md), [SESSION_LOG.md](SESSION_LOG.md)
- Instructions: [CLAUDE.md](CLAUDE.md), [CODEX.md](CODEX.md)
- Archive pointers: [archive/REVIEW_ARCHIVE.md](archive/REVIEW_ARCHIVE.md), [archive/SESSION_LOG_ARCHIVE.md](archive/SESSION_LOG_ARCHIVE.md)
