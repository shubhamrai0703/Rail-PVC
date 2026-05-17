# STATUS.md — RailPVC Current State

Start here.

This file is the shortest path to current branch state, blockers, and next actions.

## Current Phase

- Active workstream: Phase 3 backfill endpoints (CC-SH) + Phase 5 contract setup UI (CC-S)
- Phase 4 complete: all P4-001…P4-007 merged to `main` (2026-05-17)
- Current branch in repo: `main` is the active head — no active feature branch

## Current Blockers

- None for frontend. Phase 5 contract creation UI needs `POST /api/contracts` (already live).
- Out-of-band: credential hygiene still pending — old `Ghost028301@` password was rotated; new `Vihandatad00` DB password and JWT secret are in `backend/.env` (git-ignored). Keep `.env` out of version control.
- `backend/tests/` use HS256 test tokens and will fail against the live ES256 JWKS — test suite needs updating before the next review cycle.

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

1. [CC-SH] Phase 3 backfill endpoints — schedules, contract_items, recoveries, documents — branch off `main`.
2. [CC-S] Phase 5 — contract creation form (`POST /api/contracts`); backend endpoint already live.
3. Fix backend test suite — `services/auth.py` now uses JWKS/ES256; test tokens in `tests/` are minted with HS256 and will fail. Update before next review cycle.
4. Credential hygiene — new DB password + JWT secret are in `backend/.env` only (git-ignored). Document in onboarding.

## File Classification

- Startup/status: [STATUS.md](STATUS.md)
- Stable truth: [PRODUCT.md](PRODUCT.md), [ARCHITECTURE.md](ARCHITECTURE.md), [ENGINEERING_GUIDELINES.md](ENGINEERING_GUIDELINES.md)
- Active state: [TASKS.md](TASKS.md), [REVIEW.md](REVIEW.md), [SESSION_LOG.md](SESSION_LOG.md)
- Instructions: [CLAUDE.md](CLAUDE.md), [CODEX.md](CODEX.md)
- Archive pointers: [archive/REVIEW_ARCHIVE.md](archive/REVIEW_ARCHIVE.md), [archive/SESSION_LOG_ARCHIVE.md](archive/SESSION_LOG_ARCHIVE.md)
