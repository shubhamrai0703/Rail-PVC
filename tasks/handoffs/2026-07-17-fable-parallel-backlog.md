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

## Results

Executed by Fable 5 (orchestrator) on 2026-07-17, branch `saqlain/parallel-backlog` off `main` at `900de63`. Mechanical work ran on three parallel Sonnet 5 subagents (PDF extraction, workbook/export inventory, AG Grid migration); triage, gap analysis, parity implementation, and the migration stayed on Fable. Four scoped commits: `38f399c` (WS-D), `bcc3228` (WS-A), `e2ce3d5` (WS-B), `0ec890c` (WS-C), plus a docs commit.

### WS-A — Usability-audit triage: **done** (with one verification caveat)

The audit PDF is dated **2026-05-31** — it predates Phases 5–7. Judgment outcome, recorded as the new `### AUDIT-1` section in TASKS.md:

- **F1/F2/F3 (all three BLOCKERs — infinite "Loading…" on contract detail / bills / extra-items): already fixed.** Every affected page now has an `isError` branch with a message and back-link (`contracts/[id]/page.tsx:123`, `bills/page.tsx:83`, `extra-items/page.tsx:43`), and the 2026-07-16 real-stack smoke drove those screens successfully. Same for **F8** (no error states) and **F9** (no breadcrumb) — the detail page has a "← Contracts" link since Phase 5.
- **F4 ("RRailPVC" logo): won't-fix** — it's the amber "R" icon badge + "RailPVC" wordmark with a 10px gap (`Sidebar.tsx:34-42`), not a doubled string; the auditor's screenshot flattened it.
- **F6 (Index Manager stub): superseded** — `/indices` + `/indices/[series]` are functional since IDX-4; data landed via IDX-1.
- **Quick wins shipped:** **AUDIT-1-1** (F10) — inline help under "Gross amount" in `BillForm` + `BillHeaderForm`: "On-account bill total from the Measurement Book…" (wording derived from PRODUCT.md's W-derivation; the audit's "before GST" phrasing was deliberately NOT used — GST treatment is unconfirmed). **AUDIT-1-2** (F12) — `contract_value` added to the `GET /api/contracts` list SELECT (it was already in the detail SELECT and the DB) and rendered as a right-aligned "Value (₹)" column via `formatINR`, "—" when null.
- **Tickets for Saqlain:** AUDIT-1-3 (junk draft contracts in the live tenant — data hygiene, not code) and AUDIT-1-4 (rebate-as-decimal input — needs a UX convention call before changing form semantics).

Full verbatim extraction: scratchpad `ws-a-audit-extraction.md` (session-local; the PDF stays untracked as instructed).

**Smoke caveat (applies to WS-A quick wins + WS-D console check):** the authenticated browser click-through could not be completed autonomously. The session's permission classifier blocked injecting the magic-link session into the controlled browser (twice, deliberately — not retried further), and the Claude-in-Chrome extension didn't respond (likely a pending permission prompt with nobody at the keyboard). What was verified instead: full `tsc`/`eslint`/`vitest`/`next build` clean after the edits, the backend column addition exercised against the live DB, and repo-wide greps proving zero deprecated AG Grid options remain. **Saqlain: one manual look at `/contracts` (Value column), the new-bill form (help note), and the Items grid console (no AG Grid deprecation warnings) closes this caveat.** Both servers were left running on the standard ports (backend :8000, frontend :3000, freshly built).

**Closed 2026-07-18:** Codex completed the authenticated `/contracts`, bill-form, and Items-grid console checks; all passed. Evidence: `tasks/handoffs/2026-07-18-codex-browser-smoke-caveat.md` Results.

### WS-B — Export submission-format parity: **done** (first parity pass + gap report)

**Implemented (uncontroversial, backend-only, commit `e2ce3d5`):**
- Component table now follows the submission Bill-sheet order and vocabulary: `Category | Eligible amount "W" | Average index of quarter | Base index | Component weight | PVC amount` (was: eligible → base → current-avg → weight → value with app-internal names).
- Numeric cells are native numbers with submission-style formats — `#,##0.00` money, `0.00` indices, `0%` weights (weight is stored as a fraction; verified 0.10 renders 10%). Previously every cell was a plain string.
- The Excel "Total PVC" is now a live `=SUM(F..:F..)` formula (accounting-format), matching the workbook's live-formula character; static 0 when a run has no components.
- Summary block gains a **Quarter** row (`quarter_used` added to the export route SELECT) — the submission Front Page is organized around "Quarter No.".
- PDF mirrors the same order/headers with matching text formatting.
- Tests: 4 new pins (column order incl. quarter row, native values + number formats, live SUM, empty-components total) — `test_sh_p5_exports.py` 13 passed.

**Smoke (real stack):** generated Excel + PDF from approved run `8bfc1f40` (TEST-A-WR-252) against live Supabase data — 8 components rendered with correct order, native numerics, quarter `Q2-FY2025-26` in the summary, and `=SUM(F12:F19)` total. Files at scratchpad `smoke_export.xlsx/.pdf`.

**Gap report — column-by-column and structural parity vs the real submission workbook** (structure only; reference: `PVC/BCT-24-25-252` GCC workbook + `IRL PVC calculation sample`):

| Submission element | App export today | Gap class |
|---|---|---|
| Bill-sheet component columns: W amount → avg index → base index → weight → PVC | **Matches after this pass** (single base-index column; workbook repeats base index twice because it renders the algebra cell-by-cell) | closed |
| Money/index/weight number formats; live totals | **Matches after this pass** | closed |
| Quarter identity on the output | Quarter row in summary block | closed (placement differs — see Q1 below) |
| 8-sheet workbook: Front Page (cover/reference block/quarter summary), Index (monthly obs + AVG rows per quarter), Second Page (W decomposition per bill), Cement, Steel (bifurcation + carry-forward), 10.2 (MB item detail), Bill-N per quarter | Single "PVC Run" sheet | **open — the substantive P8 feature** |
| Steel decomposed into up to 4 cost-driver sub-lines per section type (Labour/Plant/Fuel/Other/main-material, own weights, clause codes 9A/9C/9D in labels) | One flat row per engine category (`steel_angles`, `steel_tmt`, `steel_other`) | **open — needs engine-output granularity discussion (engine boundary — not touched; Codex owns engine this cycle)** |
| Cross-sheet formula linkage (auditor can trace every number to source) | Static values + one SUM | open (depends on multi-sheet) |
| Cover-page reference block: work description, reference letter, LOA no./date, contractor line, per-quarter PVC summary with remarks | Run ID/Status/Tender/Contractor/Approved-by | open |
| Formula legend rendered as a readable equation across the header | Not rendered | open (cosmetic-ish) |

**P8-REVIEW open questions for Saqlain:**
1. Is the single-sheet export acceptable as an interim deliverable with the quarter in the summary, or does P8 target the full 8-sheet submission workbook? (The multi-sheet build is a real project — Index/W-decomposition/Cement/Steel sheets each need data the export route doesn't currently fetch.)
2. Steel sub-lines: the workbook's 4-cost-driver decomposition per steel section doesn't exist in `pvc_components` — is that decomposition wanted in the export (and does the engine already compute it internally), or do the 3 aggregate steel rows suffice for submission?
3. Should component labels carry the clause codes ("Labour for Classificate (9A)" etc.) verbatim?
4. Header vocabulary now says `Eligible amount "W"` — per the Second Page, W excludes cement/steel/extra items, but cement/steel component rows carry their own eligible amounts; confirm the header wording isn't domain-misleading for those rows.

### WS-C — `base_month` DB CHECK (KU1R-L1): **done**

Gate check: nothing landed on `origin/main` past `900de63`; Codex's blast radius (engine + KU-001 doc sections, investigation task) excludes migrations — proceeded as sequenced. Migration `017_base_month_first_day_check.py`: `ADD CONSTRAINT contracts_base_month_first_day CHECK (EXTRACT(DAY FROM base_month) = 1)` with matching downgrade. Verified against the live DB per REVIEW.md's prescription: 0 pre-existing day≠1 rows, `alembic upgrade head` applied cleanly (**DB now at head 017**), and a manual `INSERT ... base_month='2025-01-15'` was rejected with `CheckViolationError` (transaction discarded). Postgres-only, so no aiosqlite test — verification documented in the migration docstring. REVIEW.md's KU1R-L1 entry was **not** edited (Codex owns KU-001 sections this cycle); closure is recorded here and in STATUS.md.

### WS-D — AG Grid deprecation cleanup: **done** (console evidence pending — see WS-A caveat)

`frontend/components/contracts/ItemsGrid.tsx` was the only file in `frontend/` using deprecated selection options (repo-wide grep). Migrated to the v35 object API preserving behavior: `rowSelection="multiple"` + `suppressRowClickSelection` + column-level `checkboxSelection`/`headerCheckboxSelection` → `rowSelection={{ mode: "multiRow", checkboxes: true, headerCheckbox: true, enableClickSelection: false }}`. One documented v35 rendering difference: checkboxes move from inside the "Code" cell to AG Grid's dedicated leading selection column (no legacy equivalent without a custom renderer); multi-select/delete-selected flows unaffected. All four logged warnings map to the removed options, so the console should be clean — visual confirmation is the one item pending Saqlain (blocked browser auth, above).

### Session-end verification

- Backend: **171 passed** (167 baseline + 4 new export pins).
- Frontend: `npx tsc --noEmit` clean, `npx eslint .` clean, `npx vitest run` **65 passed**, `npm run build` clean (production).
- Engine: untouched (hard boundary respected — no `engine/` or KU-001 REVIEW.md/STATUS.md edits).
- `git status`: only pre-existing untracked items (audit PDF — intentionally untracked; `.codex-stage/`; `REFERENCES/…numbers`) plus `tasks/handoffs/2026-07-17-ku001-stc-avg-decision-consult.md`, which **appeared mid-session from the concurrent Codex session — left strictly alone, not committed**.

### Environment notes for Saqlain

1. **Port 3000 squatter:** a `hermes-agent` WhatsApp bridge (`~/.hermes/hermes-agent/scripts/whatsapp-bridge/bridge.js --port 3000 --mode self-chat`) grabbed port 3000 within seconds of the old frontend process being stopped — something supervises and respawns it. The frontend was re-bound to :3000 afterwards, but if that bridge isn't something you knowingly run, it's worth a look; if it is, consider moving it off the app's port.
2. Both dev servers were restarted on the new build and left running: uvicorn :8000, `next start` :3000.
3. Supabase auth allowlist only permits `localhost:3000` redirects — relevant to any future automated smoke that needs a login.

### Branch / PR state

`saqlain/parallel-backlog` pushed with 5 commits (4 workstream + 1 docs); PR opened against `main` — see the PR link in the session transcript. Rebased/fast-forward check against `origin/main` done pre-push (`900de63`, unchanged all session). Merge note: **migration 017 is already applied to the live DB**, so merging the branch is doc/code-only risk; reverting would require `alembic downgrade`.
