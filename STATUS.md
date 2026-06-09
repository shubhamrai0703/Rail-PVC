# STATUS.md — RailPVC Current State

Start here.

This file is the shortest path to current branch state, blockers, and next actions.

## Current Phase

- **Phase 5 + SH-P5-1..4 + P5-FUP + IDX-2..3 all on `main` (2026-05-30).** PRs #7/#8/#9 merged.
- **Phase 6 C-1 + C-2 + demo seed + P5-IMP frontend + two demo smoke-test fixes merged to `main` (2026-06-02).** C-3 (bill/recovery edit + computed net) pending.
- **IDX-4 (PR #11) + SH-P5-5/6 export (PR #12) merged to `main` via merge-commits (2026-06-02).** Route count 38→40 (2 export routes; IDX-4 is frontend-only).
- **IDX-4 — Index Manager UI:** `/indices` series list + `/indices/[series]` detail (observations table + `IndexMonthForm`). Optimistic UI; backend `require_admin` stays sole enforcement, 403/409 surfaced inline. Follow-up fix on merge: encode series name in the detail link.
- **SH-P5-5/6 — Export endpoints:** `GET /api/pvc-runs/{id}/export/{excel,pdf}`. Tenant-gate (404) → status-gate (422 `run_not_approved`) → attachment. Pure generators in `services/exports.py`; Excel via `openpyxl`, PDF via **fpdf2** (not WeasyPrint — GTK native stack isn't pip-installable on Windows dev/test). Submission-format parity deferred to P8-REVIEW.
- **P5-IMP — Smart items import (frontend) merged.** File upload + paste + fuzzy column mapper, exceljs lazy-loaded. Backend code for templates + Anthropic Haiku 4.5 mapper is on disk but not wired — follow-up branch.
- TEST-P3P4 complete: TEST-01…07 all merged to `main` (fast-forwarded from `saqlain/test-p3p4`, 2026-05-19).
- Phase 3 backfill + Phase 4 complete: all on `main`.

## Current Blockers

- **None blocking Phase 6 C-3.** P6-REVIEW findings all closed. IDX-2..3 (index write endpoints) are on `main`; seed Jan–May 2026 index months before running PVC on 2026 bills (Phase 7 concern).
- **Tech-debt (non-blocking):** `P6-H1-FUP-C` — interim approach A overloads `technical_withheld` with PVC-affecting recoveries; migrate to a dedicated W bucket (approach C) before any flow that must show both deductions separately.
- Out-of-band: credential hygiene — DB password and JWT secret are in `backend/.env` (git-ignored). Keep `.env` out of version control.

## Active Review Cycle

- **`P6-REVIEW` closed (2026-06-04)** — Codex-S pass, 2 HIGH + 2 MEDIUM all fixed; P6-H1 via interim approach A (`P6-H1-FUP-C` tracks the C end-state). On `saqlain/p6-review`.
- **Phase 6 C-3 complete (2026-06-08) on `saqlain/p6-review`.** `PUT /api/bills/{id}` + `DELETE /api/bills/{id}/recoveries/{rid}` + computed `net_amount` (gross − Σ non-PVC recoveries; **formula flagged for field validation — `C-3-FUP-NET`**). FE: inline bill-header edit + recovery delete. Route count 40→42.
- `P5-REVIEW` closed and merged 2026-05-20; PRs #11/#12 merged clean (2026-06-02).
- Suite state: **140/140 backend** (+15: C-3 PUT/DELETE + net formula), **99/99 engine**, **45/45 frontend vitest**, `tsc` + `eslint` clean. Route count **42**.

## Branch State

- `main` — up to date with origin (2026-06-02); Phase 6 C-1/C-2 etc. merged.
- `saqlain/p6-review` — **P6-REVIEW fixes + Phase 6 C-3. PR [#13](https://github.com/saqlainmmomin/Rail-PVC/pull/13) OPEN → `main`.** Commits `73bd306` (P6-REVIEW) + `3786ec1` (C-3). 140/99/45 green, route count 42. No open CRITICAL/HIGH — clear to merge.
- `saqlain/phase-6` — merged to `main`; deletable.
- `saqlain/p5-imp` — backend WIP stashed; P5-IMP backend wiring lands here in a follow-up branch.
- `saqlain/phase-5` — deletable (merged).
- `saqlain/test-p3p4` — deletable (merged).
- `shubham/phase-5-backend` — deletable (merged via PR #7).
- `shubham/idx-flag` — deletable (merged via PR #8).
- `shubham/p5-fup-l2` — deletable (merged via PR #9).
- `shubham/idx-4` — deletable (merged via PR #11).
- `shubham/sh-p5-exports` — deletable (merged via PR #12).

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

1. [CC-S] Push `saqlain/p6-review` + open PR (P6-REVIEW + C-3). Then **Phase 7 (PVC run + results UI)** now that C-3 is stable, or P5-IMP backend wiring (LLM mapper + template CRUD + migration 014) off `saqlain/p5-imp`.
2. [CC-S] When a real submission is available, validate `C-3-FUP-NET` (net_amount formula) and revisit `P6-H1-FUP-C` (dedicated W bucket).
3. [CC-SH] Next task TBD. Export submission-format parity deferred to P8-REVIEW.

## File Classification

- Startup/status: [STATUS.md](STATUS.md)
- Stable truth: [PRODUCT.md](PRODUCT.md), [ARCHITECTURE.md](ARCHITECTURE.md), [ENGINEERING_GUIDELINES.md](ENGINEERING_GUIDELINES.md)
- Active state: [TASKS.md](TASKS.md), [REVIEW.md](REVIEW.md), [SESSION_LOG.md](SESSION_LOG.md)
- Instructions: [CLAUDE.md](CLAUDE.md), [CODEX.md](CODEX.md)
- Archive pointers: [archive/REVIEW_ARCHIVE.md](archive/REVIEW_ARCHIVE.md), [archive/SESSION_LOG_ARCHIVE.md](archive/SESSION_LOG_ARCHIVE.md)
