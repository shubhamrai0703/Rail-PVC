# STATUS.md — RailPVC Current State

Start here.

This file is the shortest path to current branch state, blockers, and next actions.

## Current Phase

- **Active workstream (Saqlain):** Phase 5 — contract setup UI (B-1…B-5); design review in progress as of 2026-05-19
- **Active workstream (Shubham):** SH-P5 — GET bill endpoints + export backend (parallel to Phase 5 UI)
- TEST-P3P4 complete: TEST-01…07 all merged to `main` (fast-forwarded from `saqlain/test-p3p4`, 2026-05-19)
- Phase 3 backfill + Phase 4 complete: all on `main`

## Current Blockers

- None. No open CRITICAL/HIGH findings.
- Out-of-band: credential hygiene — DB password and JWT secret are in `backend/.env` (git-ignored). Keep `.env` out of version control.

## Active Review Cycle

- No active cycle. TEST-P3P4 merged clean; M-1/M-2 closed, 55/55 backend tests passing, 99/99 engine tests passing.
- Next checkpoint: `P5-REVIEW` — Codex-S pass after Phase 5 UI (B-1…B-5) lands.

## Branch State

- `main` is the active head
- `saqlain/test-p3p4` — completed, can be deleted
- Deleted: `saqlain/phase-3-remediation`, `saqlain/phase-4`, `shubham/phase-3`, `shubham/phase-3-backfill` (all merged)
- Next branches: `saqlain/phase-5` (frontend UI), `shubham/phase-5-backend` (GET bill endpoints + exports)

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

1. [CC-S] Phase 5 UI — branch `saqlain/phase-5`; implement B-1 (creation form) → B-2 (detail) → B-3 (edit) → B-4 (schedules) → B-5 (items grid) in order.
2. [CC-SH] SH-P5 backend — branch `shubham/phase-5-backend`; add missing GET bill endpoints + export routes (see TASKS.md).
3. Credential hygiene — DB password + JWT secret are in `backend/.env` only (git-ignored). Document in onboarding.

## File Classification

- Startup/status: [STATUS.md](STATUS.md)
- Stable truth: [PRODUCT.md](PRODUCT.md), [ARCHITECTURE.md](ARCHITECTURE.md), [ENGINEERING_GUIDELINES.md](ENGINEERING_GUIDELINES.md)
- Active state: [TASKS.md](TASKS.md), [REVIEW.md](REVIEW.md), [SESSION_LOG.md](SESSION_LOG.md)
- Instructions: [CLAUDE.md](CLAUDE.md), [CODEX.md](CODEX.md)
- Archive pointers: [archive/REVIEW_ARCHIVE.md](archive/REVIEW_ARCHIVE.md), [archive/SESSION_LOG_ARCHIVE.md](archive/SESSION_LOG_ARCHIVE.md)
