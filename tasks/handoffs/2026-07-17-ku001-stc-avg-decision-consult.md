# KU-001-STC-AVG decision consultation handoff

## Goal

Help Saqlain make the `KU-001-STC-AVG` domain decision without implementing it. Explain the two supplied options in plain language, verify the decisive evidence, challenge the provisional recommendation, and guide Saqlain to an explicit choice he understands. Definition of done: Saqlain can state which calculation policy RailPVC should support, why it is appropriate, whether it is universal or rule-set-specific, and what evidence/review conditions must precede implementation.

## Current state

- Investigation is complete. A real STC workbook takes the mean of the three monthly observations, then rounds that mean **half-up to 2 decimal places** before using it. This reproduces two workbook totals to the paisa with zero formula-line mismatches.
- The current engine retains full `Decimal` precision for the quarterly mean and rounds the final aggregate later. Two STC golden fixtures therefore remain strict expected failures: Bill 1 differs by ₹42.12 and Bill 2 by ₹94.77.
- This is a calculation-policy difference, not a source-data error. An earlier attempt to alter monthly observations by ±₹0.01 was reviewed and reverted.
- The canonical product formula currently says `(M-2 + M-1 + M) / 3` and does not specify intermediate rounding.
- `_quarter_avg` is shared by five production paths. Quantizing it unconditionally would change general, cement, and steel calculations for every contract, including immutable audit outputs.
- Workbook practices are not yet proven uniform. At least one JRH fixture records different precision behavior for steel sub-indices, and the SL4 two-stage averaging order remains unresolved.
- External official guidance reviewed by Codex does not impose a universal 2dp quarterly-average rule. Railway GCC describes quarterly averaging and final-certificate rounding; central procurement guidance makes the applicable tender/contract methodology controlling.
- No code has been changed for this decision. The repository has unrelated uncommitted work; preserve it.

### Supplied options

1. **Keep full precision.** No engine change; the two STC fixtures remain strict xfails documenting workbook divergence.
2. **Adopt workbook rounding.** Mean the three monthly values, then apply `ROUND_HALF_UP` at 2dp before formula use. This requires explicit go-ahead and a separate adversarial review.

### Provisional Codex position to challenge

Prefer Option 2 **only as an explicit, versioned rule-set policy**, not as a global one-line change to `_quarter_avg`. Existing rule sets should explicitly retain full precision unless evidence assigns them the workbook policy. If RailPVC cannot represent contract/rule-specific arithmetic safely, keep Option 1 temporarily rather than universalizing the STC observation.

## What Fable should do

1. Read the decision evidence and current engine boundary. Verify the rounding order is **average first, then half-up to 2dp**; do not repeat the misleading phrase “round-then-average.”
2. Explain to Saqlain, without implementation jargon, the difference between mathematical precision, contract correctness, and workbook parity.
3. Compare only the two supplied options. You may refine the scope and conditions of Option 2, but do not invent a third product policy.
4. Test the provisional position skeptically:
   - Is the STC workbook authoritative enough to define policy, or merely a reference calculation?
   - Is a universal rule supported by other JRH/BCT evidence?
   - Would a rule-set-specific policy preserve deterministic replay and immutable audit history?
   - Does matching the total conceal a separate per-formula-line rounding difference?
   - What evidence is required to resolve the SL4 two-stage averaging order?
5. Guide Saqlain interactively. Ask one focused question at a time, explain why it changes the decision, and recommend an answer when the evidence supports one. Do not silently choose on his behalf.
6. Finish with one of these explicit outcomes:
   - `Choose Option 1 now`, with the evidence that would justify revisiting it; or
   - `Choose Option 2`, with a precise statement of its scope and mandatory review conditions; or
   - `Decision blocked`, naming the single missing fact that genuinely prevents a responsible choice.

## Key files

| File | Why it matters |
|---|---|
| `/Users/saqlainmomin/railPVC/tasks/handoffs/2026-07-16-fable-next-open-items.md` | Primary investigation and decision brief; read Results, especially lines 143–158. |
| `/Users/saqlainmomin/railPVC/STATUS.md` | Current branch state and pending-decision summary. |
| `/Users/saqlainmomin/railPVC/TASKS.md` | Canonical `KU-001-STC-AVG` task row. |
| `/Users/saqlainmomin/railPVC/PRODUCT.md` | Canonical rolling-quarter formula and immutable-run requirements. |
| `/Users/saqlainmomin/railPVC/ENGINEERING_GUIDELINES.md` | Explicit domain branching, plausible-wrong-value, and regression-test requirements. |
| `/Users/saqlainmomin/railPVC/engine/engine/components.py` | Current full-precision `_quarter_avg`, five call sites, and SL4 second averaging step. |
| `/Users/saqlainmomin/railPVC/engine/engine/calculator.py` | Current final aggregation and rounding boundary. |
| `/Users/saqlainmomin/railPVC/engine/engine/types.py` | Existing rule-set model; currently exposes final-result rounding only. |
| `/Users/saqlainmomin/railPVC/engine/tests/fixtures/real_tenders/README.md` | Golden-workbook provenance and strict divergence conventions. |
| `/Users/saqlainmomin/railPVC/engine/tests/fixtures/real_tenders/stc_cop_bill1_q3.json` | First exact STC divergence. |
| `/Users/saqlainmomin/railPVC/engine/tests/fixtures/real_tenders/stc_cop_bill2_q4.json` | Second exact STC divergence. |
| `/Users/saqlainmomin/railPVC/engine/tests/fixtures/real_tenders/jrh_bct_2324_48_bill5_q10.json` | Evidence that workbook precision practices may be heterogeneous. |

## Constraints

- This is a read-only consultation. Do not edit engine, backend, frontend, migrations, fixtures, task boards, status files, or review records.
- Do not stage, commit, push, or clean the working tree.
- Do not alter source observations to force reconciliation.
- Treat workbook acceptance, contractual authority, and universal Railway policy as different claims. Cite evidence for each; do not collapse them.
- Do not recommend unconditional quantization of the shared helper unless evidence proves a universal policy across the affected contracts.
- Any eventual Option 2 implementation must define operand set, averaging order, scale, tie behavior, applicability, snapshot/version behavior, and the separate per-line/final rounding boundary.
- Preserve the existing two options. A rule-set-scoped implementation is a safety condition on Option 2, not a new option.

## Verification

Before reporting the consultation complete:

1. Cite the exact evidence for both STC totals and their deltas from the primary brief/fixtures.
2. Confirm from `components.py` that `_quarter_avg` is shared and that SL4 has a second averaging stage.
3. Confirm whether the available JRH/BCT artifacts actually establish their average-rounding convention. If the source workbook is unavailable, state that limitation rather than inferring it from totals.
4. Check that the recommendation distinguishes global behavior from rule-set-specific behavior and separately addresses per-line rounding.
5. Run `git diff -- tasks/handoffs/2026-07-17-ku001-stc-avg-decision-consult.md` and verify that only the `## Results` section was added by this consultation.

## Report back

Append a `## Results` section to this file. Record:

- the questions Saqlain answered;
- the verified facts that determined the choice;
- the selected option, or the exact blocker;
- the agreed policy scope in one unambiguous sentence;
- mandatory implementation and review conditions;
- any remaining assumptions, each labeled as unverified.

Do not implement the decision. End by telling Saqlain the exact next handoff or planning step he can authorize if he wants to proceed.

## Results

Consultation executed by Fable 5, concluded 2026-07-19. Read-only except this section; no engine, fixture, or status files touched.

### Questions Saqlain answered

1. **Workbook authority** — answered indirectly via contractor contact (Ritesh, WhatsApp, 2026-07-19), who responded to the six drafted domain questions: (1) "do not round off index just use upto 2nd decimal point"; (2) source is a "railway circular"; (3) applies to "all" contracts/components; (4) SL4 also 2dp; (5) formula lines also 2dp before adding; (6) Railway would reject full-precision workbooks. He also said "Just use 139.16" — i.e. truncation.
2. **Option 2 scope** — Saqlain chose **rule-set-scoped now** over "universal per Ritesh" and "wait for the circular."

### Verified facts that determined the choice

- STC deltas confirmed from fixtures: Bill 1 workbook −120623.44 vs engine −120665.56 (Δ ₹42.12); Bill 2 −54035.63 vs −54130.40 (Δ ₹94.77). Same monthly observations both sides; pure calculation-policy difference.
- `_quarter_avg` (`engine/engine/components.py:49-56`) is shared by five paths (general, cement, steel sub-components, single-series steel commodity, SL4 loop); SL4 has a second averaging stage over series averages (`components.py:186-189`). Unconditional quantization changes money-math for every contract, including immutable audit outputs.
- **Decisive numeric experiment** (scratchpad monkeypatch of `_quarter_avg`, both STC fixtures):
  - full precision: Δ −42.12 / −94.77
  - **half-up 2dp average: Δ +0.01 / +0.12** — within the fixtures' 0.15 tolerance; both STC fixtures would flip to genuine PASS on average-quantization alone
  - truncate 2dp average: Δ −171.13 / −384.85 — 4–8× worse than full precision.
  The accepted STC workbook therefore used **half-up** (Excel `ROUND()`), not truncation; Ritesh's "just use 139.16" is contradicted by his own side's accepted submission and is treated as loose phrasing.
- JRH Bill 5 fixture notes record heterogeneous practice inside one workbook: steel rows round sub-averages inconsistently (147.7333→147.73 at 2dp, 93.0667→93.1 at 1dp) while general rows use exact averages. This affirmatively contradicts a universal 2dp rule as practiced, so JRH/BCT do **not** establish the STC convention. Limitation: verified from extract-script provenance notes in the fixture, not by reopening the JRH workbook.
- Residual paisa deltas (0.01 / 0.12) are explained by the workbook's separate per-formula-line 2dp rounding, which the engine does not do. Matching totals via average-quantization alone does not conceal a material per-line difference at current tolerances, but per-line rounding remains a distinct policy the implementation spec must address explicitly.

### Selected option

**Option 2, rule-set-scoped.** Policy scope in one sentence: *Rule sets carrying an explicit `quarter_avg_precision = half_up_2dp` policy round each quarterly series average half-up to 2 decimal places before formula use; all existing rule sets explicitly retain full precision, and the shared `_quarter_avg` default is unchanged.*

### Mandatory implementation and review conditions

1. New versioned rule-set field (e.g. `quarter_avg_precision: "full" | "half_up_2dp"`, default `"full"`); snapshotted per run so deterministic replay and immutable audit history are preserved. `engine/engine/types.py` currently exposes final-result rounding only — this is a model extension, not a one-liner in `_quarter_avg`.
2. Spec must define, per the handoff constraints: operand set (each series' 3-month mean), averaging order (**average first, then quantize** — never round monthly observations), scale (2dp), tie behavior (`ROUND_HALF_UP`), applicability (rule-set flag only), snapshot/version behavior, and the separate per-line/final rounding boundary (per-line 2dp rounding is **out of scope** for this change; documented as a follow-up policy candidate).
3. SL4 second-stage order (quantize before or after averaging the three series averages) is unresolved — STC Table 8 cannot discriminate. Implementation must pick one, document it as an explicit assumption in the rule-set spec, and flag it for workbook evidence.
4. The two STC fixtures flip from xfail to strict PASS under the new policy; the 9 currently-passing fixtures must remain byte-identical (their rule sets stay `full`). No re-pinning permitted.
5. Separate adversarial review required before merge, per the original task condition.
6. Universalizing the policy (Ritesh's "yes all") requires the actual railway circular or an approved calculation template as evidence — not WhatsApp confirmation — given the JRH counter-evidence and the truncate/half-up contradiction in the same exchange.

### Remaining assumptions (each unverified)

- **Unverified:** the railway circular Ritesh cites exists and prescribes 2dp intermediate arithmetic; no document has been produced.
- **Unverified:** the STC bills were formally accepted/reconciled by Railway bill-passing staff (as opposed to paid without arithmetic scrutiny).
- **Unverified:** JRH workbook behavior, beyond the extract-script notes; the source workbook was not reopened during this consultation.
- **Unverified:** SL4 two-stage averaging order under the 2dp policy.

### Next step Saqlain can authorize

An implementation handoff for **KU-001-STC-AVG Option 2 (rule-set-scoped)**: extend `PVCRuleSet` with `quarter_avg_precision`, thread it through the five `_quarter_avg` call paths, assign `half_up_2dp` to the STC fixtures' rule sets, flip both STC fixtures to strict PASS, prove the 9 golden fixtures byte-identical, then run the mandated adversarial review. Separately: ask Ritesh for the circular itself (photo/PDF) before any universalization decision.
