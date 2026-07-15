# Handoff: Fix `quarter.py` — rolling quarters from contract base month (KU-001)

Target agent: ChatGPT Codex Sol 5.6, high effort. Assume zero context beyond this file and the files it links.

## Goal

Replace the engine's calendar-quarter resolver with the confirmed rolling-from-base convention: Quarter N = months (3N−2 .. 3N) counted from the month immediately after the contract's base month, labelled with plain ordinals ("Q3"), no financial-year alignment. Definition of done: `cd engine && uv run pytest` green with the KU-001 xfail fixtures in `tests/test_real_tender_fixtures.py` flipped to genuinely passing (exact expected split below), the full backend suite green, and the frontend type/lint/build checks clean.

## Domain decision (already made — do not relitigate)

Confirmed 2026-07-15 by Saqlain's railway contact and by five decoded real Western Railway workbooks (all GCC April 2022, contractor Banjara): **"rolling quarter, start date will be input by contractor."**

- Rolling-from-base is the ONLY convention under Apr-2022 GCC. Do **not** add a `quarter_convention` flag to `PVCRuleSet` — there is no second convention to configure.
- Anchor = the contract's existing `base_month` (already a contract column and already on `IndexSnapshot.base_month`). No schema change, no new payload field.
- Quarter 1 = the three months **immediately after** the base month. Example: base Jul-23 → Q1 = Aug–Oct-23, Q2 = Nov-23–Jan-24, … The day-of-month is irrelevant (base_month is stored day=01).
- A bill maps to the quarter containing its `measurement_date` (the measurement period "To" date — this part of the old KU-001 still holds).
- Labels are plain ordinals: `"Q3"`, `"Q10"`, … unbounded N (contracts with extensions run past Q4). The old `"Q2-FY2025-26"` format disappears from new output.
- Evidence + full design discussion: `tasks/handoffs/2026-07-15-ccs-quarter-convention.md` (read its "Domain confirmation" section; the rest is background).

## Current state

- Branch: work on `saqlain/fup-backlog`. Its working tree contains the uncommitted golden fixtures (16 workbook-derived JSONs in `engine/tests/fixtures/real_tenders/`, the extractor at `engine/scripts/extract_pvc_fixtures.py`, and the xfail-aware test). Do not commit or push; leave everything in the working tree.
- `engine/engine/quarter.py::resolve_quarter(measurement_date)` currently returns calendar quarters (`Q1=Jan–Mar`) with FY labels. This is the sole known engine defect. All component math (W-derivation, general components, cement, steel buckets) is verified correct to the paisa against a real workbook — do not touch it.
- The fixture suite currently reports `7 passed, 14 xfailed`. Each xfail **pins the exact current engine total (or exact validation-error list)**, so your resolver change will make the xfail pins mismatch — refreshing those pinned outcomes deliberately is part of this task (see Verification for the target end-state per fixture).

## The change

1. **`engine/engine/quarter.py`** — `resolve_quarter(measurement_date: date, base_month: date) -> tuple[str, list[str]]`. Compute months-since-base = (12·Δyears + Δmonths) using month arithmetic on first-of-month dates; quarter ordinal `n = ((months_since_base − 1) // 3) + 1`; label `f"Q{n}"`; window = the 3 months of that quarter as `"YYYY-MM"` strings. Rewrite the module docstring — it documents the falsified convention.
2. **`engine/engine/calculator.py:318`** — pass `indices.base_month` as the second argument.
3. **`backend/services/pvc_service.py:549`** — same; `contract_row["base_month"]` is already in scope (it's passed to `build_index_snapshot` on line 553). Note the call currently happens before/independent of the snapshot — keep the resolver import pattern (comment there explains it keeps backend and engine in lock-step).
4. **Edge case — measurement date on or before the end of the base month** (months_since_base ≤ 0): the bill predates Quarter 1. Return no window; surface it through the existing engine validation-error path (a clear message like `"measurement_date 2023-07-15 falls in or before the contract base month 2023-07 — no PVC quarter exists yet"`), not an exception. Add a unit test.
5. **`pvc_runs.quarter_used` label migration: none.** It's nullable TEXT with dev-only data; old FY-style rows stay as-is, new runs write ordinals. The frontend treats it as an opaque string — no frontend change expected (verify with a grep for `FY` in `frontend/`).
6. **Tests to update:** `engine/tests/test_quarter.py` (rewrite for rolling semantics — keep/port boundary cases: quarter boundaries, December wrap, multi-year contracts, Q>4), `engine/tests/test_calculator.py` (FY-label assertions), the two synthetic fixtures `bct_2425_252_bill1_q2.json` / `bill2_q4.json` if they pin FY-style `quarter_used`, backend `tests/test_p7_review_h1_h2.py` and `tests/test_d1_pvc_run_results.py` (grep for `FY` / hardcoded labels), and the pinned xfail outcomes in the golden fixtures.

## Key files

- `/Users/saqlainmomin/railPVC/engine/engine/quarter.py` — the resolver (34 lines, whole file changes).
- `/Users/saqlainmomin/railPVC/engine/engine/calculator.py` — caller at line 318; `_build_trace` just threads the label through.
- `/Users/saqlainmomin/railPVC/engine/engine/types.py` — `IndexSnapshot.base_month` (line 70) is the anchor source. `PVCRuleSet.quarter_mode` stays `Literal["measurement_date"]` — it describes the anchor date, which is unchanged.
- `/Users/saqlainmomin/railPVC/backend/services/pvc_service.py` — backend caller at line 549.
- `/Users/saqlainmomin/railPVC/engine/tests/test_real_tender_fixtures.py` + `engine/tests/fixtures/real_tenders/*.json` — acceptance harness; per-fixture `notes.xfail_reason` + pinned outcomes.
- `/Users/saqlainmomin/railPVC/engine/scripts/run_engine_fixture.py` — single-fixture runner for spot checks.
- `/Users/saqlainmomin/railPVC/tasks/handoffs/2026-07-15-ccs-quarter-convention.md` — evidence and design rationale.
- `/Users/saqlainmomin/railPVC/tasks/handoffs/2026-07-15-pvc-golden-fixtures.md` — fixture provenance; its Results section lists every fixture's workbook value and which divergences are workbook-internal (NOT quarter bugs).
- `/Users/saqlainmomin/railPVC/ENGINEERING_GUIDELINES.md` — coding/review rules; follow them.

## Constraints

- Allowed surface: `engine/engine/quarter.py`, the two caller lines (calculator + pvc_service), tests, fixture JSON metadata (pinned outcomes / `quarter_used` expectations / xfail markers), and docs listed in Report back. Nothing else — in particular do NOT touch `w_derivation.py`, `components.py`, the money math in `calculator.py`, migrations, or the frontend.
- Do not add config for a calendar convention (decision above).
- `PVC/` source workbooks are read-only and never committed; you should not need them — the fixtures carry every month from base through measurement, so rolling windows resolve from existing fixture data.
- Fixture expected values (`expected.total_pvc`) are workbook ground truth — never adjust them to make tests pass. If a fixture that should pass doesn't, the resolver (or the fixture's month coverage) is wrong; investigate, don't paper over.
- Do not commit or push; leave changes in the working tree.

## Verification (required before reporting done)

Expected end-state per golden fixture after the fix:

| Must flip to PASS | Must REMAIN xfail (workbook-internal divergence, not a quarter bug) |
|---|---|
| `stc_cop_bill1_q3`, `stc_cop_bill2_q4` (tolerance 0.15 for workbook per-line rounding) | `stc_cop_bill3_q7` (TMT double-count), `stc_cop_bill4_q9` (steel-other hybrid) |
| `bct_2324_296_bill1_q3`, `bill2_q4`, `bill3_q4` | `bct_2425_183_bill2_q3` (cement double-treatment) |
| `jrh_bct_2324_48_bill1_q4`, `bill2_q6`, `bill3_q7`, `bill4_q9` | `bct_2425_252_golden_bill2_q4` (workbook links Q2 rows for a Q4 bill) |
| `jrh_bct_2324_48_bill5_q10` — probably: it xfailed on a missing calendar Oct–Dec-2025 horizon that rolling windows shouldn't request. If its rolling window resolves and the total matches, flip it; if a genuine workbook divergence emerges, document and keep xfail. | |

Already passing and must stay passing: `bct_2425_183_bill1_q2`, `bct_2425_252_golden_bill1_q2`, and the two synthetic 252 fixtures (Dec-24 base coincides with calendar, so their windows are unchanged; only their `quarter_used` label expectations change). **If any fixture in the right-hand column starts passing, treat it as a bug in your change.**

```bash
cd /Users/saqlainmomin/railPVC/engine
uv run pytest tests/test_real_tender_fixtures.py -v   # split exactly as above
uv run pytest                                          # full engine suite green
uv run python scripts/run_engine_fixture.py tests/fixtures/real_tenders/stc_cop_bill1_q3.json --fail-on-mismatch   # newly-passing spot check
cd /Users/saqlainmomin/railPVC/backend
uv run pytest                                          # full backend suite green (was 164/164)
cd /Users/saqlainmomin/railPVC/frontend
npx tsc --noEmit && npm run lint                       # no frontend change expected; prove it
```

Paste the pytest summary lines and the spot-check JSON into Results.

## Report back

Append a `## Results` section to THIS file with: the final pass/xfail table (calling out any fixture that didn't land where predicted, especially JRH bill 5), the edge-case behaviour you implemented for measurement-in-base-month, every file touched, the verification output, and anything the reviewer (CC-S will review this change) should scrutinize. Also update: `STATUS.md` (quarter defect fixed on `saqlain/fup-backlog`), the `## Results` section of `tasks/handoffs/2026-07-15-ccs-quarter-convention.md` (one paragraph: decision executed, pointer here), and the KU-001 note in `engine/engine/types.py` if its comment references calendar quarters.
