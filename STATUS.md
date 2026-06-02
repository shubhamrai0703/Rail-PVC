# STATUS.md — RailPVC Current State

Start here.

This file is the shortest path to current branch state, blockers, and next actions.

## Current Phase

- **Phase 5 + SH-P5-1..4 + P5-FUP + IDX-2..3 all on `main` (2026-05-30).** PRs #7/#8/#9 merged. Route count 38.
- **Phase 6 C-1 + C-2 + demo seed + P5-IMP frontend + two demo smoke-test fixes merged to `main` (2026-06-02).** C-3 (bill/recovery edit + computed net) pending.
- **Demo smoke-test fixes (this merge):** Items grid "Invalid Number" fixed (AG Grid `cellDataType: false` + custom number parser/formatter); "Calculate PVC" trigger card added to the bill detail page (wires the existing `POST /pvc-runs` endpoint).
- **P5-IMP — Smart items import (frontend) merged.** File upload + paste + fuzzy column mapper, exceljs lazy-loaded. Backend code for templates + Anthropic Haiku 4.5 mapper is on disk but not wired — follow-up branch.
- **Active workstream (Shubham):** SH-P5-5..6 — Excel/PDF export endpoints (pending).
- TEST-P3P4 complete: TEST-01…07 all merged to `main` (fast-forwarded from `saqlain/test-p3p4`, 2026-05-19).
- Phase 3 backfill + Phase 4 complete: all on `main`.

## Current Blockers

- **None blocking Phase 6.** IDX-2..3 (index write endpoints) are on `main`; seed Jan–May 2026 index months before running PVC on 2026 bills (Phase 7 concern).
- Out-of-band: credential hygiene — DB password and JWT secret are in `backend/.env` (git-ignored). Keep `.env` out of version control.

## Active Review Cycle

- **None open.** `P5-REVIEW` closed and merged 2026-05-20; all deferred L-findings closed by 2026-05-30 (PR #9). SH-P5-REVIEW completed (PR #7 merged clean).
- Suite state: **106/106 backend**, **99/99 engine**, **33/33 frontend vitest**, `next build` clean, `npm run lint` clean. Route count 38.

## Branch State

- `main` — **fully up to date with origin (2026-06-02).** Phase 6 C-1/C-2 + demo seed + P5-IMP frontend + demo smoke-test fixes merged (fast-forward from `saqlain/phase-6`).
- `saqlain/phase-6` — merged to `main`; deletable.
- `saqlain/p5-imp` — backend WIP stashed; P5-IMP backend wiring lands here in a follow-up branch.
- `saqlain/phase-5` — deletable (merged).
- `saqlain/test-p3p4` — deletable (merged).
- `shubham/phase-5-backend` — deletable (merged via PR #7).
- `shubham/idx-flag` — deletable (merged via PR #8).
- `shubham/p5-fup-l2` — deletable (merged via PR #9).

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

1. [CC-S] Proceed to C-3 (bill/recovery edit + computed net_amount). Then P5-IMP backend wiring (LLM mapper + template CRUD + migration 014) on a follow-up branch off `saqlain/p5-imp`.
2. [CC-SH] SH-P5-5..6 — Excel/PDF export endpoints (request `SH-P5-REVIEW` before merge).

## File Classification

- Startup/status: [STATUS.md](STATUS.md)
- Stable truth: [PRODUCT.md](PRODUCT.md), [ARCHITECTURE.md](ARCHITECTURE.md), [ENGINEERING_GUIDELINES.md](ENGINEERING_GUIDELINES.md)
- Active state: [TASKS.md](TASKS.md), [REVIEW.md](REVIEW.md), [SESSION_LOG.md](SESSION_LOG.md)
- Instructions: [CLAUDE.md](CLAUDE.md), [CODEX.md](CODEX.md)
- Archive pointers: [archive/REVIEW_ARCHIVE.md](archive/REVIEW_ARCHIVE.md), [archive/SESSION_LOG_ARCHIVE.md](archive/SESSION_LOG_ARCHIVE.md)
