# Handoff — Parallel backlog orchestration (audit triage · export parity · KU1R-L1 · AG Grid cleanup)

**Date:** 2026-07-17
**From:** Claude (Fable) session
**To:** A fresh Claude Fable session acting as **orchestrator** — dispatch workstreams to subagents, keep judgment calls on Fable
**Repo:** `/Users/saqlainmomin/railPVC` (branch `main` — pull first; this handoff is pushed with the latest docs sync)

## Goal

Clear the four parallel-safe backlog items below while Codex (a separate agent, running concurrently) owns the KU-001-STC-AVG domain decision inside `engine/`. Definition of done: each workstream either lands as a reviewed, tested change on a feature branch (or `main` per repo convention) or produces its specified deliverable (tickets/report), every code change has a smoke check run and reported, and the Results section of this file records per-workstream outcomes.

## Current state

- `main` head includes: KU-001 rolling-quarter fix, FUP backlog (PR #17), P5-IMP-FUP-2 import templates, and a docs sync closing the Supabase blocker — the real-stack smoke test PASSED with no defects (`tasks/handoffs/2026-07-16-codex-supabase-smoke-test.md` Results).
- Supabase project is live again; DB at migration head `016`. Backend `.venv` + frontend build all work; suites green (167 backend / 122+9 xfail engine / 65 frontend vitest).
- **Codex is concurrently working on KU-001-STC-AVG** (whether the engine should adopt the workbook's avg-then-round-half-up-2dp quarter averages — decision brief in `tasks/handoffs/2026-07-16-fable-next-open-items.md` Results). Codex's blast radius: `engine/`, engine tests, REVIEW.md/STATUS.md KU-001 entries.

## Workstreams and model routing

Run A, B, D in parallel via the Agent tool; C is sequenced (see its row). Route mechanical work to **Sonnet 5** subagents; keep domain judgment and final review on **Fable** (the orchestrator — you). Nothing here needs Opus.

### WS-A — Usability-audit triage (extraction: Sonnet 5 · judgment: Fable)

`/Users/saqlainmomin/railPVC/RailPVC Smoke Test & Usability Audit.pdf` sits untracked in the repo root and no task tracks it. Steps:
1. Sonnet 5 subagent: read the PDF, extract every finding verbatim-faithfully into a structured list (area, severity as stated, repro/observation, suggested fix if given).
2. Fable (you): triage each finding — duplicate of a closed item, quick win, ticket, or won't-fix — and add a new `### AUDIT-1` table to `TASKS.md` with one row per accepted finding.
3. Quick wins that are frontend-only and low-risk may be fixed in this session (Sonnet 5 for mechanical edits, you review); everything else stays a ticket.
Deliverable: TASKS.md section + any quick-win fixes, each with a smoke check.

### WS-B — Export submission-format parity, P8-REVIEW prep (Fable judgment; Sonnet 5 for mechanical diffs)

Phase 8's named checkpoint is `P8-REVIEW`: Excel export column order/format vs the real Railway submission format (WORKPLAN.md "Next Review Checkpoints"). The current Excel/PDF exports (`backend/services/exports.py`, endpoints `GET /api/pvc-runs/{id}/export/{excel,pdf}`) were built from run + `pvc_components` rows without a submission-format reference. The reference material is the local, git-ignored `PVC/` golden workbooks and the `IRL PVC calculation sample` folder (real Banjara cases — never commit or quote client-identifying content into tracked files).
1. Sonnet 5 subagent: inventory the submission-side sheet layout (sheet names, column order, headers, totals rows) from the local workbooks; inventory the current export layout from `services/exports.py` + its tests.
2. Fable (you): produce a gap report — column-by-column parity table, what's missing, what's ordered differently, what needs domain confirmation from Saqlain.
3. Implement the uncontroversial parity fixes (backend-only, `services/exports.py` + `backend/tests/test_sh_p5_exports.py`); list the rest as `P8-REVIEW` open questions in the gap report.
Deliverable: gap report appended to Results + parity fixes with passing export tests + a real export smoke check (generate an Excel from an approved run, open/inspect it).

### WS-C — KU1R-L1: `base_month` DB CHECK constraint (Sonnet 5, sequenced LAST)

The one deferred LOW from `KU-001-REVIEW` (REVIEW.md): add a DB CHECK constraint on `contracts.base_month` (migration `017`) plus a test. **Do not start until you've checked whether Codex's STC-AVG work has landed anything touching migrations or contract schema** (`git log --oneline main..` and the Codex handoff Results); if Codex is still in flight at the end of the session, leave WS-C undone and say so in Results — a stale-head migration conflict is not worth the race.

### WS-D — AG Grid deprecation cleanup (Sonnet 5)

The 2026-07-16 smoke test logged four AG Grid deprecation warnings about legacy row-selection options. Repo uses AG Grid 35.x (AllCommunityModule + themeQuartz — see the AG Grid v35 notes in auto-memory if loaded). Migrate the deprecated `rowSelection` string/option usage in `frontend/components/` (start with `ItemsGrid`) to the v35 object API. Deliverable: zero AG Grid deprecation warnings in the browser console on the Items grid and any other grid pages, vitest + tsc + lint + build clean, before/after console evidence.

## Key files

- `/Users/saqlainmomin/railPVC/STATUS.md`, `TASKS.md`, `REVIEW.md`, `WORKPLAN.md` — state, backlog, review history, phase map.
- `/Users/saqlainmomin/railPVC/RailPVC Smoke Test & Usability Audit.pdf` — WS-A input (untracked; leave untracked).
- `/Users/saqlainmomin/railPVC/backend/services/exports.py`, `backend/api/exports.py`, `backend/tests/test_sh_p5_exports.py` — WS-B surface.
- `/Users/saqlainmomin/railPVC/PVC/`, `/Users/saqlainmomin/railPVC/IRL PVC calculation sample/` — WS-B reference (git-ignored client data; keep it that way).
- `/Users/saqlainmomin/railPVC/backend/migrations/versions/` — WS-C surface (head `016`).
- `/Users/saqlainmomin/railPVC/frontend/components/ItemsGrid.tsx` and sibling grid components — WS-D surface.
- `/Users/saqlainmomin/railPVC/tasks/handoffs/2026-07-16-fable-next-open-items.md` — STC-AVG brief (context for what Codex owns).

## Constraints

- **Hard boundary: do not touch `engine/`, engine tests, or the KU-001 sections of REVIEW.md/STATUS.md** — Codex owns them this cycle. If a workstream seems to need an engine change, stop and record it as an open question instead.
- Work on a feature branch (e.g. `saqlain/parallel-backlog`); one branch is fine for all workstreams, commits scoped per workstream. Pull/rebase on `main` before pushing — Codex may land first.
- 8 GB machine: never `next dev`; use `npm run build && npm run start`. Prefer running one heavy build at a time even with parallel subagents.
- Smoke-test default: no workstream is "done" on green units alone — drive the actual surface (browser for WS-A/WS-D, generated file for WS-B, applied migration for WS-C) and report what you observed.
- Never copy client names, contract parties, or workbook contents into tracked files; the parity gap report must describe structure (columns/sheets), not client data.
- Don't relitigate settled decisions: rolling quarters from `base_month` (KU-001), fpdf2 over WeasyPrint, tenant isolation in API not RLS, exports built from run+component rows.

## Verification

Per workstream, as specified above; plus at session end: full backend pytest, frontend `tsc`/`eslint`/`vitest`/`next build` all clean on the branch, and `git status` free of stray files.

## Report back

Append a `## Results` section to this file: per-workstream outcome (done/partial/skipped + why), evidence (test counts, smoke narratives, console before/after), the WS-B gap report (or a pointer if long), open questions for Saqlain, and branch/PR state. Update STATUS.md/TASKS.md per repo convention — except KU-001 sections, which Codex owns.
