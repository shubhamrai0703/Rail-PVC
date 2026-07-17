# STATUS.md — RailPVC Current State

Start here.

This file is the shortest path to current branch state, blockers, and next actions.

## Current Phase

- **Post-merge follow-ups in working tree (2026-07-16, uncommitted).** PR #17 merged; a Fable session then executed `tasks/handoffs/2026-07-16-fable-next-open-items.md`: (a) **KU-001 review pass — no defects found** in the flagged areas (month-delta boundary, Nov/Dec rollover + new boundary tests, unbounded `Q10+` labels, pre-Q1 422 path); a parallel Opus session owns the formal REVIEW.md entry. (b) **KU-001-STC-AVG investigation complete** — workbook hard-codes avg-then-round-half-up-2dp quarter averages, reproduces both STC totals to the paisa; decision brief in the handoff, awaiting Saqlain's call. (c) **P5-IMP-FUP-2 templates apply/save UI implemented** — `ImportTemplateControls` in `ImportRowsModal`, `lib/importTemplates.ts` + 11 vitest (65 total), schema.ts regenerated; tsc/lint/build/vitest clean; browser smoke test done against a mock API because Supabase is unreachable (below).
- **FUP backlog + KU-001 quarter fix — `saqlain/fup-backlog`, pushed and merging to `main` (2026-07-16).** Branch now bundles: the 3 original FUP tickets (P6-H1-FUP-C + P7-FUP-L2 dedicated `recoveries_affecting_pvc` W bucket + arithmetic guard; P7-FUP-L1 shared `authedFetch`/`resolveErrorMessage`; P5-IMP-FUP-1 imports router wired) plus the KU-001 rolling-quarter remediation. The engine now resolves plain ordinal quarters (`Q1`…`Q10`…) from the contract `base_month`, Quarter 1 starting the following month; measurement dates in or before the base month fail through the normal validation path. Workbook reconciliation: **12 passed / 9 xfailed** in the fixture module (JRH Bills 3–5 have verified workbook-input divergences; STC Bills 1–2 resolve the correct rolling windows but remain xfail — their calculation sheets hard-code rounded quarter averages, a separate unresolved domain question). Full suites: **119 passed / 9 xfailed engine**, **166 passed backend**; frontend typecheck, lint, and production build clean. Evidence: `tasks/handoffs/2026-07-15-ccs-quarter-convention.md`, `tasks/handoffs/2026-07-16-sol-quarter-rolling-fix.md`.
- **Phase 7 (PVC run + results UI) — D-1…D-4 + P7-REVIEW remediation. PR [#14](https://github.com/saqlainmmomin/Rail-PVC/pull/14) MERGED to `main` (2026-06-11).** Dedicated run page `/contracts/[id]/bills/[billId]/runs/[runId]` (status, result totals, W-derivation, component breakdown, approve flow, export buttons, run-history list). **Migration 015** persists run result totals; **migration 016** persists `lines_snapshot` (per-run bill lines, P7-H2). Supersede-at-INSERT: recalculating marks prior Calculated runs `Superseded` (P7-H1). Route count 42→43.
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

- ~~Supabase project `ivselmhloegjmqrjekcy` unreachable~~ — **CLOSED 2026-07-16**: Saqlain restored the paused project; Codex re-ran the P5-IMP-FUP-2 smoke test against the real stack (real auth, DB at head `016`, full template save/apply/409/delete flow) — **PASSED, no defects**. Evidence: `tasks/handoffs/2026-07-16-codex-supabase-smoke-test.md` Results.
- None for `saqlain/fup-backlog` — 3 FUP tickets + KU-001 quarter fix, all green; pushed and merging to `main`.
- STC hard-coded quarter-average rule (2 remaining STC xfails) needs a separate domain decision before it can close — not a blocker for this merge.
- Out-of-band: credential hygiene — DB password and JWT secret are in `backend/.env` (git-ignored). Keep `.env` out of version control.

## Active Review Cycle

- **`P7-REVIEW` REMEDIATED (2026-06-11) — PR [#14](https://github.com/saqlainmmomin/Rail-PVC/pull/14) merged to `main`.** H1 (approve gate both layers + supersede-at-INSERT), H2 (migration 016 `lines_snapshot` — `bill_snapshot` never contained lines; reviewer premise corrected), M1 (migrations 013-stamped/014/015/016 applied to Supabase, DB at head), M2 (apiDownload blob/URIError paths toast), M3 (closed by H2 — no live lines fetch), M4 (case-insensitive UUID filter). L1/L2 → `P7-FUP-L1`/`P7-FUP-L2` in [TASKS.md](TASKS.md). CC Responses in [REVIEW.md](REVIEW.md).
- No open review cycle on `saqlain/fup-backlog` yet — KU-001 quarter fix has not had an adversarial pass; CC-S flagged (in the Sol handoff) that the month-delta boundary, December/year rollover, and unbounded `Q10+` labels should get scrutiny.
- Suite state (on `saqlain/fup-backlog`, includes quarter fix): **166/166 backend**, **119/119 passed + 9 xfailed engine**, **54/54 frontend vitest**, `tsc` + `eslint` + `next build` clean. Route count **47**.

## Branch State

- `main` — PR #14 (Phase 7) and PR #15 (IDX-1 RBI backfill) merged. `saqlain/fup-backlog` merges next.
- `saqlain/fup-backlog` — **FUP backlog (P6-H1-FUP-C + P7-FUP-L2 + P7-FUP-L1 + P5-IMP-FUP-1) + KU-001 rolling-quarter fix. All green, pushed, merging to `main`.**
- All prior feature branches deleted after merge (`saqlain/phase-7`, `saqlain/p6-review`, `saqlain/phase-6`, `saqlain/p5-imp`, `shubham/idx-flag`, and earlier phase/test branches).

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

1. ~~[Saqlain] Restore Supabase + re-run P5-IMP-FUP-2 smoke test~~ — **done 2026-07-16**: project restored, Codex real-stack smoke test PASSED (`tasks/handoffs/2026-07-16-codex-supabase-smoke-test.md`).
2. [Saqlain] **KU-001-STC-AVG domain decision** — investigation complete (workbook = avg-then-round-half-up-2dp, verified to the paisa); decision brief in `tasks/handoffs/2026-07-16-fable-next-open-items.md` Results. Option 1 (keep full precision, xfails stay) vs Option 2 (adopt workbook rounding — scoped, needs go-ahead + its own review).
3. ~~[Opus] Land the formal KU-001-REVIEW entry~~ — **done 2026-07-16**: REVIEW.md `KU-001-REVIEW` cycle landed (no HIGH/MEDIUM; 1 LOW deferred — KU1R-L1 base_month DB CHECK); Fable's independent pass agreed. Backend 167/167, engine 122 + 9 xfailed.
4. [CC-S] When a real submission is available, validate `C-3-FUP-NET` (net_amount formula).
5. [CC-SH] Next task TBD. Export submission-format parity deferred to P8-REVIEW.

## File Classification

- Startup/status: [STATUS.md](STATUS.md)
- Stable truth: [PRODUCT.md](PRODUCT.md), [ARCHITECTURE.md](ARCHITECTURE.md), [ENGINEERING_GUIDELINES.md](ENGINEERING_GUIDELINES.md)
- Active state: [TASKS.md](TASKS.md), [REVIEW.md](REVIEW.md), [SESSION_LOG.md](SESSION_LOG.md)
- Instructions: [CLAUDE.md](CLAUDE.md), [CODEX.md](CODEX.md)
- Archive pointers: [archive/REVIEW_ARCHIVE.md](archive/REVIEW_ARCHIVE.md), [archive/SESSION_LOG_ARCHIVE.md](archive/SESSION_LOG_ARCHIVE.md)
