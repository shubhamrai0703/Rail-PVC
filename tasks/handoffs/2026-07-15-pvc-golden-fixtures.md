# Handoff: Extract golden PVC fixtures from 5 real Banjara workbooks + parametrized xfail reconciliation tests

Target agent: ChatGPT Codex Sol 5.6, high effort. Assume zero context beyond this file.

## Goal

Turn the five real-contract PVC workbooks under `/Users/saqlainmomin/railPVC/PVC/` into permanent regression fixtures for the PVC engine: one JSON fixture per bill (~14 bills total across 5 contracts) in `engine/tests/fixtures/real_tenders/`, plus test support so bills whose quarter windows the engine cannot yet resolve correctly are marked `xfail` instead of failing. Definition of done: `cd engine && uv run pytest tests/test_real_tender_fixtures.py -v` runs green — every new fixture either passes (engine output == workbook's PVC value) or xfails with reason `KU-001` — and each fixture documents its provenance in `notes`.

## Current state

- The engine (`engine/engine/`) is a pure-function PVC calculator, fully merged and tested. Entry point: `calculate_pvc(bill: BillPayload, indices: IndexSnapshot, rules: PVCRuleSet)` from `engine/__init__.py`. Pydantic models in `engine/types.py`.
- **Known engine defect (do NOT fix it):** `engine/engine/quarter.py` resolves quarters as calendar quarters (Q1=Jan–Mar…) anchored to `measurement_date`. All five workbooks instead use **rolling quarters counted from the contract's base month** (Quarter 1 = the 3 months immediately after base month). This was confirmed on 2026-07-15 by decoding all five workbooks. The fix is owned by another agent (CC-S) and is pending a domain confirmation. Your fixtures must encode the **workbook's** expected PVC values as ground truth; where the engine's calendar windows differ from the workbook's rolling windows, the test must `xfail`.
- Two coincidences matter: contracts with base month Dec-24 (BCT-24-25-252) and Sep-24 (BCT-24-25-183) have rolling windows that happen to equal calendar quarters, so their fixtures should PASS today. Contracts with base Jul-23 (COP/STC), Feb-24 (BCT-23-24-296), May-23 (JRH) will NOT reconcile until quarter.py is fixed → xfail.
- Two 252 fixtures already exist (`bct_2425_252_bill1_q2.json`, `bct_2425_252_bill2_q4.json`) with partially synthetic index values. Leave them in place unless your freshly-extracted 252 fixtures supersede them exactly — if so, replace them and say so in Results.

## Source data (read-only — never modify or commit these)

All under `/Users/saqlainmomin/railPVC/PVC/`. The `.xlsx` workbooks are the golden references; PDFs are underlying evidence (ignore them unless a workbook cell is ambiguous).

| Contract | Workbook (relative to PVC/) | Base month | Bills | Calendar-aligned? |
|---|---|---|---|---|
| STC COP & Seating | `COP & Seating/Banjara - STC COP - Apr 2022 GCC.xlsx` | Jul-23 | 4 (Q3, Q4, Q7, Q9) | No → xfail |
| BCT-24-25-252 | `BCT-24-25-252/Banjara - COLABA BP 252 - Apr 2022 GCC.xlsx` | Dec-24 | 2 (Q2, Q4) | Yes → should pass |
| BCT-24-25-183 | `BCT-24-25-183/Banjara - COLABA BP  183 - Apr 2022 GCC.xlsx` | Sep-24 | 2 (Q2, Q3) | Yes → should pass (verify) |
| BCT-23-24-296 | `BCT-23-24-296/Banjara - COLABA BP  296 - Apr 2022 GCC.xlsx` | Feb-24 | 3 | No → xfail |
| JRH (BCT-23-24-48) | `JRH/New folder/Banjara - JRH - Apr 2022 GCC (4) (1).xlsx` | May-23 | 5 | No → xfail |

Workbook anatomy (COP uses sheets `Table 1`–`Table 11`; the others use named sheets like `Front Page `, `Index`, `Cement`, `Steel`, per-bill sheets):
- **Front/summary sheet**: quarter-wise PVC amounts per bill — these are your `expected.total_pvc` values. COP ground truth: Bill 1 → −120623.44, Bill 2 → −54035.63, Bill 3 → +8588.242160840233, Bill 4 → −130259.32482108506 (cumulative previously paid −166070.82783915979).
- **Index sheet(s)**: base index row + per-month index values grouped into rolling quarters with an `Average` row, 9 series: Labour, Plant Machinery & Spares, Fuel & Lubricants, Other Materials, Cement (RBI, ~90–160 range) and TMT Bars, Angles, Plates, Other Sections (JPC Mumbai, ~52000–72000 range). Bill-to-quarter mapping is annotated in the rightmost column (e.g. "1st Bill 18/06/2025").
- **W-derivation / bill sheets**: on-account amount minus cement, steel (bifurcated angles/plates/TMT/other), technical withheld, extra items → W. Map to `BillPayload` fields.
- ⚠️ Known data quirks: the 252 workbook's Plant series sits at ~160–163 while the other four use ~88–93 (different index base — use each workbook's own values verbatim, do not normalize). The JRH Index sheet is messy (duplicated Base rows, a stray Apr-23 row). Some cells hold datetime objects for months (e.g. `2025-05-01 00:00:00` = May-25).

## Key files

- `/Users/saqlainmomin/railPVC/engine/tests/test_real_tender_fixtures.py` — existing parametrized test; extend it to honor a per-fixture xfail marker.
- `/Users/saqlainmomin/railPVC/engine/tests/fixtures/real_tenders/` — fixture JSONs live here; `README.md` documents the shape; the two existing 252 fixtures are your shape reference.
- `/Users/saqlainmomin/railPVC/engine/engine/types.py` — `BillPayload`, `IndexSnapshot`, `PVCRuleSet`, `ExtraItemDecision` (authoritative field names/validation).
- `/Users/saqlainmomin/railPVC/engine/engine/calculator.py`, `w_derivation.py`, `components.py`, `quarter.py` — read to understand exact semantics; do not modify.
- `/Users/saqlainmomin/railPVC/engine/scripts/run_engine_fixture.py` — single-fixture runner (`--fail-on-mismatch`).
- `/Users/saqlainmomin/railPVC/ENGINEERING_GUIDELINES.md` — coding/review rules; follow them.

## Approach notes

1. Write a reusable extraction script at `engine/scripts/extract_pvc_fixtures.py` (openpyxl, `data_only=True`) rather than hand-copying cells — it is the provenance record. openpyxl is NOT in the engine venv; add it as a dev dependency via `uv add --dev openpyxl` in `engine/` (that's acceptable) or run the script with a separate venv — your call, state it in Results.
2. In each fixture's `indices.series`, include **every month from base month through the bill's measurement month** (the index sheets contain them all). This way the fixture stays valid regardless of which months the quarter resolver picks, now and after the KU-001 fix. Missing months cause engine validation errors, not wrong numbers.
3. Per-fixture xfail: add an optional field, e.g. `"notes": {"xfail_reason": "KU-001: workbook uses rolling-from-base quarters (base Jul-23); engine resolves calendar quarters"}`, and in the test apply `pytest.xfail(reason)` (non-strict is fine) when present and the assert would run. Fixtures for 252/183 must NOT carry the marker — they must genuinely pass.
4. Rules: extract each workbook's component weights, adjustable fraction (0.85), and fixed-steel split from its own formula cells — do not assume they're identical across contracts. Set `negative_pvc_policy: "allow"` — the workbooks carry raw negative PVC across bills with no zero-flooring.
5. Cross-check every extracted `expected.total_pvc` against the workbook summary sheet value verbatim (full float precision as shown in the cell, e.g. `-130259.32482108506`).

## Constraints

- Decisions already made — do not relitigate: workbook FINAL indices (not provisional); quarter.py stays untouched; xfail (not skip, not fixing the engine) for non-aligned contracts; `PVC/` source data never gets committed (it's untracked and will be gitignored separately).
- Do not touch anything outside `engine/tests/`, `engine/scripts/`, and (if you choose the dev-dep route) `engine/pyproject.toml` + `uv.lock`.
- Match existing fixture JSON style (string-encoded decimals, same key names).
- If a workbook cell is genuinely ambiguous, extract your best reading, note it in the fixture's `notes.workbook_divergence`, and list it in Results — do not silently guess.
- Do not commit or push anything; leave changes in the working tree.

## Verification (required before reporting done)

```bash
cd /Users/saqlainmomin/railPVC/engine
uv run pytest tests/test_real_tender_fixtures.py -v   # all new fixtures: pass or xfail-with-KU-001-reason
uv run pytest                                          # full engine suite still green
```

Paste the pytest summary lines into Results. For at least one passing fixture (252 or 183), also run `uv run python scripts/run_engine_fixture.py tests/fixtures/real_tenders/<file>.json --fail-on-mismatch` and show the output.

## Report back

Append a `## Results` section to THIS file (`tasks/handoffs/2026-07-15-pvc-golden-fixtures.md`) with: fixtures created (path + expected value + pass/xfail), whether 183 actually passed (its calendar alignment is predicted but unverified), any workbook ambiguities encountered, the pytest summaries, and anything CC-S should know for the quarter.py fix.

## Addendum — CC reconciliation findings (2026-07-15, read before extracting COP fixtures)

CC ran the engine against the COP & Seating workbook using the workbook's own quarter averages (bypassing the quarter resolver). Findings that change fixture expectations:

1. **COP Bills 1 & 2 reconcile to ₹0.01 / ₹0.12** — engine math is correct; residual is the workbook rounding each formula line to 2dp. For these two fixtures set `expected.total_pvc` to the workbook values (−120623.44, −54035.63) and expect the test to need a small tolerance OR document the paise-level residual in notes. Recommended: assert equality to the ENGINE's reproduced value only if exact; otherwise add an optional `expected.tolerance` field (e.g. "0.15") honored by the test.
2. **COP Bill 3 workbook is internally inconsistent (double-counts TMT):** Table 4 W = 6773975.905 subtracts TMT 320238.765, but Table 10 runs general components on 7094214.67 (W + TMT) while ALSO computing the TMT steel bucket. Engine-consistent total = +5325.76 vs workbook +8588.24. Fixture: keep workbook value as `expected.total_pvc`, add `notes.workbook_divergence` explaining the double-count, and xfail with the KU-001 reason PLUS the divergence note — this fixture will NOT pass even after the quarter fix.
3. **COP Bill 4 same problem, different line:** W subtracts steel-other 665094.334275 but the steel-other bucket runs on 1978547.683065 (adds items 10.28 SS-plate 405809.35 + 10.16.1 MS-tubes 907644.00). Workbook total −130259.32 is the hybrid. Engine-consistent totals: −60034.59 (other=665094 everywhere) or −156249.28 (other=1978547 everywhere). Same fixture treatment as Bill 3; use steel_other_amount=1978547.683065 in the payload and document the hybrid.
4. **Index-sheet inconsistencies inside COP:** Table 10 (Q7) uses angles avg 59820 (implies Apr-25 angles 61133.33, matching the 252 workbook) while COP's own Table 3 says 59806.22 (Apr-25 = 61092). When quarter-calc sheets and index sheets disagree, extract BOTH into notes and use the quarter-calc value for expected reproduction.
5. Watch for the same double-count patterns in the other four workbooks — check every bill: does the general-components base amount equal the W column in the W-derivation sheet, and does each steel bucket amount equal the amount subtracted from W? Flag mismatches in `notes.workbook_divergence`.
