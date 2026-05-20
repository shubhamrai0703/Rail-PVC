# STATUS.md — RailPVC Current State

Start here.

This file is the shortest path to current branch state, blockers, and next actions.

## Current Phase

- **Active workstream (Saqlain):** Phase 5 — UX polish fixes **P5-F1…F5 + P5-REVIEW remediation complete** on `saqlain/phase-5` (2026-05-20). **82/82 backend tests passing** on the declared dep floor (`fastapi==0.115.12`), **99/99 engine tests**, **16/16 frontend vitest**, `next build` clean. All CRITICAL/HIGH/MEDIUM closed; L-1/L-2/L-3 deferred to follow-up tasks (L-4 fixed inline). Awaiting human push + merge decision.
- **Active workstream (Shubham):** SH-P5 — GET bill endpoints + export backend (parallel to Phase 5 UI).
- TEST-P3P4 complete: TEST-01…07 all merged to `main` (fast-forwarded from `saqlain/test-p3p4`, 2026-05-19).
- Phase 3 backfill + Phase 4 complete: all on `main`.

## Current Blockers

- None blocking. No open CRITICAL/HIGH findings.
- Out-of-band: credential hygiene — DB password and JWT secret are in `backend/.env` (git-ignored). Keep `.env` out of version control.

## Active Review Cycle

- `P5-REVIEW` **closed** (2026-05-20). CC-S reviewed (Codex-S unavailable), all 14 findings resolved: 1 CRITICAL + 3 HIGH + 6 MEDIUM + 1 LOW closed inline; L-1/L-2/L-3 deferred to TASKS.md.
- Suite state on branch: **82/82 backend tests** on declared dep floor `fastapi==0.115.12` (67 prior + 15 new regression pins), **99/99 engine tests**, **16/16 frontend vitest** (new), `next build` clean. Route count 31 unchanged.

## Branch State

- `main` — last commit `22ba97c` (docs sync 2026-05-19).
- `saqlain/phase-5` — Phase 5 implementation + P5-F1…F5 + P5-REVIEW remediation complete (PR #6). Smoke test passed 2026-05-20. BUG-1 fixed (`CAST(:stype AS schedule_type)`). `base_month` edit-mode fix included. P5-REVIEW resolved 2026-05-20 (C-1/H-1/H-2/H-3/M-1…M-6/L-4 closed; L-1/L-2/L-3 deferred). Awaiting human push + merge.
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

1. [human] Push `saqlain/phase-5` to origin; merge to `main` once review responses are accepted.
2. [CC-S] Address the deferred L-1/L-2/L-3 + lint-dirty follow-up tasks post-merge.
3. [CC-SH] Continue SH-P5 backend (G-1 → G-2 → G-3); request `SH-P5-REVIEW` before merge.

## File Classification

- Startup/status: [STATUS.md](STATUS.md)
- Stable truth: [PRODUCT.md](PRODUCT.md), [ARCHITECTURE.md](ARCHITECTURE.md), [ENGINEERING_GUIDELINES.md](ENGINEERING_GUIDELINES.md)
- Active state: [TASKS.md](TASKS.md), [REVIEW.md](REVIEW.md), [SESSION_LOG.md](SESSION_LOG.md)
- Instructions: [CLAUDE.md](CLAUDE.md), [CODEX.md](CODEX.md)
- Archive pointers: [archive/REVIEW_ARCHIVE.md](archive/REVIEW_ARCHIVE.md), [archive/SESSION_LOG_ARCHIVE.md](archive/SESSION_LOG_ARCHIVE.md)
