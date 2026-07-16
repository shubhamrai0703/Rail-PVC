# Brief for CC-S: KU-001 quarter convention is wrong — evidence + design question

Audience: CC-S (engine-semantics owner). Assume zero context from other sessions. Status: **UNBLOCKED (2026-07-15)** — Saqlain's railway contact confirmed: quarters are **rolling** (not calendar), anchored to the contract's start date, which is **input by the contractor**. See "Domain confirmation" below. Implementation may proceed.

## The claim

`engine/engine/quarter.py` resolves fixed calendar quarters (Q1=Jan–Mar, FY-labelled) anchored to the measurement date, per KU-001 (confirmed 2026-05-14 on contract BCT-24-25-252). Five real Western Railway PVC workbooks (contractor: Banjara, all GCC April 2022) decoded on 2026-07-15 show this is not how PVC quarters work: **quarters roll from the contract's base month** — Quarter 1 = the three months immediately after the base month, Quarter N = months (3N−2..3N) after base, no calendar or FY alignment, quarters numbered 1..N for the life of the contract (plus extensions).

## The evidence

Source: `/Users/saqlainmomin/railPVC/PVC/` (untracked local folder, five contract subfolders, each with a fully-worked golden workbook).

| Contract | Base month | Workbook Quarter 1 | Rolling == calendar? |
|---|---|---|---|
| STC COP & Seating (WR/BCT/Civil/2023/0202) | Jul-23 | Aug–Oct-23 | No |
| BCT-24-25-252 | Dec-24 | Jan–Mar-25 | **Yes — coincidence** |
| BCT-24-25-183 | Sep-24 | Oct–Dec-24 | **Yes — coincidence** |
| BCT-23-24-296 | Feb-24 | Mar–May-24 | No |
| JRH (BCT-23-24-48) | May-23 | Jun–Aug-23 | No |

Why KU-001 got confirmed wrong: 252's base month is December, so rolling-from-base and calendar quarters produce identical windows — the conventions were indistinguishable on the confirming contract. 296 (Q1 = Mar–May) and COP (Q3 = Feb–Apr) disambiguate.

Also note: the workbook quarter label is plain ordinal ("Quarter No. 3"), not `Q3-FY2025-26`. Bills map to the quarter containing the measurement "To" date (that part of KU-001 holds). Quarters with no bill are skipped rows, not renumbered.

## Independent verification that ONLY the quarter resolver is wrong

CC reconciled the engine against the COP workbook by injecting the workbook's own quarter-average indices into the calendar months the engine picks (bypassing resolution):

- Bill 1: engine −120623.43 vs workbook −120623.44 (Δ ₹0.01, workbook rounds per-line)
- Bill 2: engine −54035.51 vs workbook −54035.63 (Δ ₹0.12, same cause)
- Bills 3–4 diverge only because the workbook itself double-counts (Bill 3 runs general components on W+TMT while also computing the TMT bucket; Bill 4 subtracts steel-other 665094.33 from W but runs the bucket on 1978547.68). The engine's refusal to double-count is correct behaviour; divergences are fully quantified in `tasks/handoffs/2026-07-15-pvc-golden-fixtures.md` (addendum).

So W-derivation, general components, cement, steel buckets incl. derived SL4 are all verified correct. The quarter resolver is the single remaining defect.

## Design question for CC-S (after Saqlain's confirmation)

1. Does any real WR contract use true calendar quarters, or is rolling-from-base the only convention under Apr-2022 GCC? (Saqlain is asking his contact. Working hypothesis: rolling-only; calendar was a misread of the 252 coincidence.)
2. If rolling-only: `resolve_quarter(measurement_date)` becomes `resolve_quarter(measurement_date, base_month)` returning ordinal labels ("Q3") and rolling windows. This changes the engine signature and every caller (API layer passes the contract's base month — it already stores `IndexSnapshot.base_month`). FY-labelled quarter strings disappear from traces; DB rows/exports referencing `Q2-FY2025-26` style labels need a migration story.
3. If both conventions exist: `PVCRuleSet.quarter_convention: "rolling_from_base" | "calendar"` with rolling as the Apr-2022-GCC default.
4. Edge cases to spec: measurement date inside the base month itself; contract extensions (COP has one: 2024-11-04 → 2025-10-30, "with PVC YES"); bills whose date falls in a quarter with no index data yet.
5. Regression harness is being built in parallel (see fixtures handoff above): 5 contracts / ~14 bills with per-fixture xfail markers carrying reason `KU-001` — they flip to passing when the fix lands, which is the acceptance test.

## Domain confirmation (2026-07-15, railway contact via Saqlain)

Verbatim answer to "rolling from contract start vs fixed calendar quarters under Apr-2022 GCC": **"rolling quarter, start date will be input by contractor."**

Consequences for the design questions above:

1. **Q1 answered: rolling-only.** No real Apr-2022-GCC contract uses calendar quarters — 252/183 were coincidences. Therefore take the Q2 path, NOT the Q3 path: change `resolve_quarter` to `resolve_quarter(measurement_date, base_month)` with ordinal labels ("Q3") and rolling windows. Do **not** add a `quarter_convention` rule-set flag — there is no second convention to configure (YAGNI).
2. **Anchor source:** "start date input by contractor" maps to the existing contract-level `base_month` field (migration 002; entered on the contract form, already carried on `IndexSnapshot.base_month`). No schema change needed. Per all five workbooks, Quarter 1 = the three months **immediately after** the base month (base Jul-23 → Q1 = Aug–Oct-23); the day-of-month of the start date is irrelevant to window boundaries.
3. **Label migration story:** `pvc_runs.quarter_used` is nullable TEXT with dev-only data — leave old `Q2-FY2025-26`-style rows as-is; new runs write ordinal labels. Exports render whatever the run row carries.
4. **Acceptance test:** the 14 KU-001 xfails in `engine/tests/test_real_tender_fixtures.py` (see fixtures handoff Results). Note the pinned-outcome mechanism: each xfail pins the current engine total, so the resolver change requires deliberately refreshing those pins. Post-fix expectations: ordinary COP/296/JRH bills flip to passing; COP Bills 3–4, 183 Bill 2, 252 Bill 2 remain xfail (workbook-internal divergences, not quarter bugs); COP Bill 4 + JRH Bill 5 previously requested a calendar Oct–Dec-2025 horizon the fixtures lack — rolling windows should eliminate that, verify.
5. **Edge cases still to spec during implementation** (contact answer doesn't cover them): measurement date falling inside the base month itself (before Q1 starts); contract extensions (COP: extended 2024-11-04 → 2025-10-30 "with PVC YES" — quarters keep counting past the original completion date); quarters with missing index months (existing validation-error path should stand).

## Results

Executed on `saqlain/fup-backlog` on 2026-07-16: `resolve_quarter` now uses the contract's existing `base_month`, numbers unbounded rolling three-month windows with plain ordinal labels, and rejects measurement dates in or before the base month through the existing validation-error path. No convention flag, schema migration, payload field, component-math change, or frontend change was introduced. The complete implementation notes, fixture reconciliation (including newly verified JRH workbook divergences), file list, and verification evidence are in `tasks/handoffs/2026-07-16-sol-quarter-rolling-fix.md`.
