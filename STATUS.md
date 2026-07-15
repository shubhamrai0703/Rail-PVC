# STATUS.md — RailPVC Current State

Start here.

This file is the shortest path to current branch state, blockers, and next actions.

## Current Phase

- **PVC golden data + KU-001 falsified (2026-07-15).** Five real Banjara Apr-2022-GCC contracts (~14 bills) in `PVC/` (local-only, gitignored). All five use **rolling quarters from base month** — KU-001's calendar quarters were misconfirmed on 252 (its Dec-24 base makes the two conventions coincide). Engine reconciled against COP workbook: Bill 1 Δ₹0.01, Bill 2 Δ₹0.12 — component math verified correct; Bill 3–4 gaps are workbook double-counts, fully quantified. `quarter.py` is the sole open engine defect — CC-S brief at `tasks/handoffs/2026-07-15-ccs-quarter-convention.md`, **blocked on railway-contact confirmation**. Fixture extraction (all 5 contracts, xfail tests) delegated to Codex Sol via `tasks/handoffs/2026-07-15-pvc-golden-fixtures.md`.
- **FUP backlog — `saqlain/fup-backlog` (2026-07-02, 3 commits). All three tickets complete; PR ready to open against `main`.** P6-H1-FUP-C + P7-FUP-L2 (dedicated `recoveries_affecting_pvc` W bucket + arithmetic guard), P7-FUP-L1 (shared `authedFetch` + `resolveErrorMessage` in `client.ts`), P5-IMP-FUP-1 (imports router wired, `anthropic` dep, 11 new backend tests). Suite: **103/103 engine, 164/164 backend, 54/54 vitest**.
- **Phase 7 (PVC run + results UI) — D-1…D-4 + P7-REVIEW remediation on `saqlain/phase-7` (2026-06-11). PR [#14](https://github.com/saqlainmmomin/Rail-PVC/pull/14) OPEN — all HIGH/MEDIUM closed, merge unblocked.** Dedicated run page `/contracts/[id]/bills/[billId]/runs/[runId]` (status, result totals, W-derivation, component breakdown, approve flow, export buttons, run-history list). **Migration 015** persists run result totals; **migration 016** persists `lines_snapshot` (per-run bill lines, P7-H2). Supersede-at-INSERT: recalculating marks prior Calculated runs `Superseded` (P7-H1). Route count 42→43.
- **IDX-1 RBI backfill — PR [#15](https://github.com/saqlainmmomin/Rail-PVC/pull/15) merged to `main` (2026-06-11) [CC-SH].** 5 non-steel series sourced from official publications (CPI-IW/WPI/PPAC derived CSVs) Apr-2022 onward; corrects the workbook's systematic +70 error on `plant_machinery`/`fuel` via `ON CONFLICT DO UPDATE`. Data already applied to Supabase (246 rows verified). Workbook loop now seeds JPC steel only.
- **Phase 6 COMPLETE — PR [#13](https://github.com/saqlainmmomin/Rail-PVC/pull/13) (P6-REVIEW + C-3) merged to `main` (2026-06-09).** `main` at `a88b85e`.
- **Phase 5 + SH-P5-1..4 + P5-FUP + IDX-2..3 all on `main` (2026-05-30).** PRs #7/#8/#9 merged.
- **Phase 6 C-1 + C-2 + demo seed + P5-IMP frontend + two demo smoke-test fixes merged to `main` (2026-06-02).**
- **IDX-4 (PR #11) + SH-P5-5/6 export (PR #12) merged to `main` via merge-commits (2026-06-02).** Route count 38→40 (2 export routes; IDX-4 is frontend-only).
- **IDX-4 — Index Manager UI:** `/indices` series list + `/indices/[series]` detail (observations table + `IndexMonthForm`). Optimistic UI; backend `require_admin` stays sole enforcement, 403/409 surfaced inline. Follow-up fix on merge: encode series name in the detail link.
- **SH-P5-5/6 — Export endpoints:** `GET /api/pvc-runs/{id}/export/{excel,pdf}`. Tenant-gate (404) → status-gate (422 `run_not_approved`) → attachment. Pure generators in `services/exports.py`; Excel via `openpyxl`, PDF via **fpdf2** (not WeasyPrint — GTK native stack isn't pip-installable on Windows dev/test). Submission-format parity deferred to P8-REVIEW.
- **P5-IMP — Smart items import (frontend) merged.** File upload + paste + fuzzy column mapper, exceljs lazy-loaded. Backend code for templates + Anthropic Haiku 4.5 mapper is on disk but not wired — follow-up branch.
- TEST-P3P4 complete: TEST-01…07 all merged to `main` (fast-forwarded from `saqlain/test-p3p4`, 2026-05-19).
- Phase 3 backfill + Phase 4 complete: all on `main`.

## Current Blockers

- None for PR [#14](https://github.com/saqlainmmomin/Rail-PVC/pull/14) — P7-REVIEW HIGH/MEDIUM all closed (2026-06-11); awaiting merge.
- None for `saqlain/fup-backlog` — all 3 tickets green; ready to open PR.
- Out-of-band: credential hygiene — DB password and JWT secret are in `backend/.env` (git-ignored). Keep `.env` out of version control.

## Active Review Cycle

- **`P7-REVIEW` REMEDIATED (2026-06-11) — PR [#14](https://github.com/saqlainmmomin/Rail-PVC/pull/14) merge unblocked.** H1 (approve gate both layers + supersede-at-INSERT), H2 (migration 016 `lines_snapshot` — `bill_snapshot` never contained lines; reviewer premise corrected), M1 (migrations 013-stamped/014/015/016 applied to Supabase, DB at head), M2 (apiDownload blob/URIError paths toast), M3 (closed by H2 — no live lines fetch), M4 (case-insensitive UUID filter). L1/L2 → `P7-FUP-L1`/`P7-FUP-L2` in [TASKS.md](TASKS.md). CC Responses in [REVIEW.md](REVIEW.md).
- Suite state (on `saqlain/phase-7`): **153/153 backend** (+8 P7-REVIEW pins), **99/99 engine**, **52/52 frontend vitest**, `tsc` + `eslint` + `next build` clean. Route count **43**.
- Suite state (on `saqlain/fup-backlog`): **164/164 backend** (+11 P5-IMP imports), **103/103 engine**, **54/54 frontend vitest**, `tsc` + `eslint` clean. Route count **47**.

## Branch State

- `main` — PR #15 (IDX-1 RBI backfill) merged 2026-06-11. Local `main` checkout may lag origin.
- `saqlain/fup-backlog` — **FUP backlog: P6-H1-FUP-C + P7-FUP-L2 + P7-FUP-L1 + P5-IMP-FUP-1. All 3 commits done, suite green, PR not yet opened.**
- `saqlain/phase-7` — **Phase 7 D-1…D-4 + P7-REVIEW remediation. PR [#14](https://github.com/saqlainmmomin/Rail-PVC/pull/14) open, merge unblocked.** 153/99/52 green, route count 43.
- All prior feature branches deleted after merge (`saqlain/p6-review`, `saqlain/phase-6`, `saqlain/p5-imp`, `shubham/idx-flag`, and earlier phase/test branches).

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

1. [Saqlain] **Open PR for `saqlain/fup-backlog`** — 3 commits, all green (164/164 backend, 103/103 engine, 54/54 vitest).
2. [Saqlain] **Merge PR [#14](https://github.com/saqlainmmomin/Rail-PVC/pull/14)** — P7-REVIEW fully remediated; smoke the run page (calculate → supersede badge → approve → export) first if desired.
3. [CC-S] When a real submission is available, validate `C-3-FUP-NET` (net_amount formula).
4. [CC-SH] Next task TBD. Export submission-format parity deferred to P8-REVIEW.

## File Classification

- Startup/status: [STATUS.md](STATUS.md)
- Stable truth: [PRODUCT.md](PRODUCT.md), [ARCHITECTURE.md](ARCHITECTURE.md), [ENGINEERING_GUIDELINES.md](ENGINEERING_GUIDELINES.md)
- Active state: [TASKS.md](TASKS.md), [REVIEW.md](REVIEW.md), [SESSION_LOG.md](SESSION_LOG.md)
- Instructions: [CLAUDE.md](CLAUDE.md), [CODEX.md](CODEX.md)
- Archive pointers: [archive/REVIEW_ARCHIVE.md](archive/REVIEW_ARCHIVE.md), [archive/SESSION_LOG_ARCHIVE.md](archive/SESSION_LOG_ARCHIVE.md)
