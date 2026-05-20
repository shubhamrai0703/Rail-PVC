# STATUS.md — RailPVC Current State

Start here.

This file is the shortest path to current branch state, blockers, and next actions.

## Current Phase

- **Phase 5 merged to `main` (2026-05-20).** P5-001…P5-008 + P5-F1…F5 + P5-REVIEW remediation all on `main`. **82/82 backend** on declared dep floor (`fastapi==0.115.12`), **99/99 engine**, **16/16 frontend vitest**, `next build` clean, `npm run lint` clean (0/0). Local merge only — not pushed.
- **Active workstream (Saqlain):** WORKPLAN smoke verification on the merged `main` tomorrow, then push to origin.
- **Active workstream (Shubham):** SH-P5 — GET bill endpoints + export backend (parallel to Phase 5 UI).
- TEST-P3P4 complete: TEST-01…07 all merged to `main` (fast-forwarded from `saqlain/test-p3p4`, 2026-05-19).
- Phase 3 backfill + Phase 4 complete: all on `main`.

## Current Blockers

- None blocking. No open CRITICAL/HIGH findings.
- Out-of-band: credential hygiene — DB password and JWT secret are in `backend/.env` (git-ignored). Keep `.env` out of version control.

## Active Review Cycle

- **None open.** `P5-REVIEW` closed and merged 2026-05-20 (see [REVIEW.md](REVIEW.md) for the closure pointer + commit chain; per-finding CC Responses preserved in commit `259d0cb`).
- Suite state on `main`: **82/82 backend tests** on declared dep floor `fastapi==0.115.12` (67 prior + 15 new regression pins), **99/99 engine tests**, **16/16 frontend vitest**, `next build` clean, `npm run lint` clean. Route count 31.

## Branch State

- `main` — Phase 5 + P5-REVIEW remediation merged via fast-forward 2026-05-20. **Not yet pushed to origin** (awaiting Saqlain's smoke pass + manual push).
- `saqlain/phase-5` — fully merged into `main`. Deletable after origin push.
- `shubham/phase-5-backend` — Shubham's parallel track (GET bills + exports), in progress.
- Deletable: `saqlain/test-p3p4` (already merged).

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

1. [Saqlain] Run WORKPLAN smoke table against merged `main` tomorrow; push `main` to origin if clean.
2. [CC-S] Address `P5-FUP-L1/L2/L3` (deferred LOW findings) post-push.
3. [CC-SH] Continue SH-P5 backend (G-1 → G-2 → G-3); request `SH-P5-REVIEW` before merge.

## File Classification

- Startup/status: [STATUS.md](STATUS.md)
- Stable truth: [PRODUCT.md](PRODUCT.md), [ARCHITECTURE.md](ARCHITECTURE.md), [ENGINEERING_GUIDELINES.md](ENGINEERING_GUIDELINES.md)
- Active state: [TASKS.md](TASKS.md), [REVIEW.md](REVIEW.md), [SESSION_LOG.md](SESSION_LOG.md)
- Instructions: [CLAUDE.md](CLAUDE.md), [CODEX.md](CODEX.md)
- Archive pointers: [archive/REVIEW_ARCHIVE.md](archive/REVIEW_ARCHIVE.md), [archive/SESSION_LOG_ARCHIVE.md](archive/SESSION_LOG_ARCHIVE.md)
