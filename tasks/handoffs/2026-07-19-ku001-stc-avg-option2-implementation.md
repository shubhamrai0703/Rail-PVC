# KU-001-STC-AVG Option 2 implementation — rule-set-scoped quarter-average precision

## Goal

Implement the decided calculation policy for `KU-001-STC-AVG`: a **versioned, rule-set-scoped** quarter-average precision option. Rule sets carrying `quarter_avg_precision = "half_up_2dp"` round each quarterly series average **half-up to 2 decimal places after averaging, before formula use**; all existing rule sets explicitly retain full precision and the engine default is unchanged.

Definition of done: the two STC golden fixtures pass **strictly** (no xfail) under the new policy; the 9 currently-passing real-tender fixtures produce byte-identical results with no re-pinning; the policy is snapshotted per PVC run end-to-end (DB → API → engine); all engine + backend suites pass; results are appended to this file.

This decision is final — do not relitigate it. Full decision record with evidence: `/Users/saqlainmomin/railPVC/tasks/handoffs/2026-07-17-ku001-stc-avg-decision-consult.md` (Results section).

## Current state

- Investigation and decision are complete (2026-07-19, Saqlain + contractor contact). Verified numerically: half-up 2dp quarter averages reproduce both accepted STC workbook totals within tolerance (Δ +0.01 / +0.12 vs the fixtures' 0.15); truncation was empirically ruled out (Δ −171 / −385); full precision diverges by ₹42.12 / ₹94.77.
- No implementation code exists yet. The engine's `_quarter_avg` (`engine/engine/components.py:49-56`) returns a full-precision `Decimal` mean and is shared by five call paths: general components (`:85`), cement (`:121`), steel sub-components (`:164`), the SL4 commodity list loop (`:178`), and single-series steel commodity (`:192`). SL4 additionally averages the three series averages (`:186-189`).
- `PVCRuleSet` (`engine/engine/types.py`) exposes final-result `rounding_mode` only; there is no intermediate-precision field.
- Backend: `pvc_rule_sets` DB table stores rule-set columns (insert at `backend/services/pvc_service.py:273-297`, default payload `~:130-142`); `PVCRuleSet` is constructed from the stored row at `pvc_service.py:558-566`; the rules API is `backend/api/pvc_rules.py`. DB is at migration head 017.
- The two STC fixtures (`stc_cop_bill1_q3.json`, `stc_cop_bill2_q4.json`) are non-strict xfails via `notes.xfail_reason` + `notes.current_engine_total` pins; the harness is `engine/tests/test_real_tender_fixtures.py`.
- The repository has unrelated uncommitted work — preserve it; do not clean the tree.

## What to implement

### Phase A — engine

1. Add `quarter_avg_precision: Literal["full", "half_up_2dp"] = "full"` to `PVCRuleSet` in `engine/engine/types.py`. Default `"full"` so every existing caller and fixture is behavior-identical.
2. Thread the policy into `engine/engine/components.py` so that when `half_up_2dp` is active, `_quarter_avg`'s result is quantized `Decimal("0.01"), ROUND_HALF_UP` on **all five** call paths. Note `compute_cement_component` and the steel helpers do not currently receive `rules` — extend their signatures (or pass the policy explicitly from `calculator.py`); pick the cleanest option consistent with existing style.
3. SL4 second stage (`components.py:186-189`, average of the three series averages): under `half_up_2dp`, quantize the three inputs (they already are, via `_quarter_avg`) and **also quantize the derived average** half-up to 2dp. This ordering is a documented assumption — record it in a code comment referencing KU-001-STC-AVG and in the Results section; STC evidence cannot discriminate the order and no workbook evidence exists yet.
4. `base` values are used as-published — never round monthly observations, never touch `_base_value`.
5. **Out of scope, do not implement:** per-formula-line 2dp rounding (separate policy candidate), any change to final `rounding_mode` semantics, any universal/default flip of the new field.

### Phase B — fixtures and tests

1. Set `"quarter_avg_precision": "half_up_2dp"` in the `rules` of `stc_cop_bill1_q3.json` and `stc_cop_bill2_q4.json` only. Remove their `xfail_reason` / `current_engine_total` pins, set `notes.reconciliation_status` to `reconciles`, and update `notes` to record the policy decision (cite the consult handoff). Both must then pass strictly within their existing `expected.total_pvc` and `tolerance: 0.15` — do not change expected totals or observations.
2. The other 9 fixtures must not gain the field (implicit `"full"`); assert byte-identical engine totals (see Verification).
3. Unit tests: quantization applied per series average (e.g. 139.1666… → 139.17); half-up tie behavior (x.xx5 rounds away from zero); `"full"` default unchanged; SL4 derived-average quantization order; property/hypothesis coverage if it fits the existing `test_hypothesis.py` style.

### Phase C — backend threading (policy must be snapshotted per run)

1. Migration `018`: add `quarter_avg_precision TEXT NOT NULL DEFAULT 'full'` with a CHECK constraint (`IN ('full','half_up_2dp')`) to `pvc_rule_sets`. Follow the style of existing migrations in `backend/migrations/versions/`.
2. Include the column in: the default payload and INSERT in `pvc_service.py`, the rule-set row selects (`backend/api/pvc_rules.py`, `backend/api/pvc_runs.py`), the rules PATCH endpoint, and the `PVCRuleSet(...)` construction at `pvc_service.py:558-566`. Existing per-run rule-set snapshotting must capture it so replay is deterministic.
3. Backend tests per existing patterns (aiosqlite limits apply — no `Decimal` binds, no `::text` casts; see `ENGINEERING_GUIDELINES.md`).

## Key files

| File | Why it matters |
|---|---|
| `/Users/saqlainmomin/railPVC/tasks/handoffs/2026-07-17-ku001-stc-avg-decision-consult.md` | The decision record: scope, mode, evidence, mandatory conditions. Read its Results section first. |
| `/Users/saqlainmomin/railPVC/engine/engine/types.py` | `PVCRuleSet` — add the new field here. |
| `/Users/saqlainmomin/railPVC/engine/engine/components.py` | `_quarter_avg` + five call paths + SL4 second averaging stage. |
| `/Users/saqlainmomin/railPVC/engine/engine/calculator.py` | Where rules flow into component computation; final rounding boundary (unchanged). |
| `/Users/saqlainmomin/railPVC/engine/tests/test_real_tender_fixtures.py` | Golden-fixture harness (strict-pass vs xfail semantics). |
| `/Users/saqlainmomin/railPVC/engine/tests/fixtures/real_tenders/stc_cop_bill1_q3.json` | Flip to strict PASS with the new rule field. |
| `/Users/saqlainmomin/railPVC/engine/tests/fixtures/real_tenders/stc_cop_bill2_q4.json` | Flip to strict PASS with the new rule field. |
| `/Users/saqlainmomin/railPVC/backend/services/pvc_service.py` | Rule-set default payload, INSERT, and engine `PVCRuleSet` construction. |
| `/Users/saqlainmomin/railPVC/backend/api/pvc_rules.py` | Rules read/PATCH API — expose the new field. |
| `/Users/saqlainmomin/railPVC/backend/migrations/versions/` | Add migration 018 here, matching existing style. |
| `/Users/saqlainmomin/railPVC/ENGINEERING_GUIDELINES.md` | Domain-branching, plausible-wrong-value, and regression-test requirements. |

## Constraints

- Decisions already made — do not reopen: rule-set-scoped (not universal); `ROUND_HALF_UP` (not truncation, despite the contact's "139.16" phrasing — empirically disproven); average-first-then-quantize; default `"full"`; per-line rounding out of scope.
- The 9 currently-passing fixtures must remain byte-identical in inputs and produce identical engine totals. **No re-pinning of any fixture is permitted.**
- Never alter monthly source observations.
- Do not universalize: no code path may apply `half_up_2dp` unless the rule set explicitly carries it.
- Preserve unrelated uncommitted work in the tree. Do not commit or push without checking with Saqlain first.
- A separate adversarial review is mandatory before this merges — implementing here does not close the task; note it as pending in Results.
- Supabase project may still be paused — all verification must run against local test suites, not the live stack.

## Verification

Before reporting done, run and record:

1. `cd engine && uv run pytest` — full suite green; the two STC fixtures pass **strictly** (confirm they no longer appear as xfail; expected xfail count drops accordingly).
2. `uv run python scripts/run_engine_fixture.py tests/fixtures/real_tenders/stc_cop_bill1_q3.json --fail-on-mismatch` and same for `stc_cop_bill2_q4.json` — both exit 0.
3. Nine-fixture invariance: capture `run_engine_fixture.py` output for the other 9 fixtures before and after the change and diff — totals must be identical to the last digit.
4. Regression guard: a test proving a rule set **without** the field (default `"full"`) reproduces the pre-change engine totals for at least one golden fixture.
5. `cd backend && uv run pytest` — full backend suite green, including new migration/API coverage.
6. Confirm `git status` shows only files this handoff required.

## Report back

Append a `## Results` section to this file: files changed, test counts before/after, the 9-fixture invariance evidence, the SL4 ordering assumption as documented, any deviations from this spec with reasons, and an explicit note that the adversarial review (KU-001-STC-AVG-REVIEW) is still pending.

## Results

Implemented on `codex/ku001-stc-avg-option2` on 2026-07-19. No commit or push was made.

### Outcome

- Added `quarter_avg_precision: "full" | "half_up_2dp"` to `PVCRuleSet`, defaulting to `full`.
- Under `half_up_2dp`, every three-month series mean is calculated from the unmodified monthly observations and then quantized with `ROUND_HALF_UP` to `0.01` before formula use. Base values and final `rounding_mode` semantics are unchanged.
- Applied the policy to all five engine paths: general components, cement, steel common sub-components, single-series steel commodity, and the SL4 commodity list.
- Kept trace/audit averages identical to the averages used by the calculation.
- Added migration 018 and threaded the policy through default rule creation, rules GET/PUT, latest-rule selection, and stored-row-to-engine construction. Existing DB rows receive explicit `full` through the migration default; legacy engine payloads without the field also remain `full`.
- Updated only the two STC fixtures to opt into `half_up_2dp`; their expected totals and monthly observations were not changed, and both now pass strictly.

### Files changed

- Engine: `engine/engine/types.py`, `engine/engine/components.py`, `engine/engine/calculator.py`
- Engine tests/fixtures: `engine/tests/test_components.py`, `engine/tests/test_calculator.py`, `engine/tests/test_w_derivation.py`, `engine/tests/test_real_tender_fixtures.py`, and the two STC JSON fixtures
- Backend: `backend/migrations/versions/018_quarter_avg_precision.py`, `backend/services/pvc_service.py`, `backend/api/pvc_rules.py`, `backend/api/pvc_runs.py`
- Backend tests: `backend/tests/test_ku001_stc_avg_rule_threading.py`, `backend/tests/test_p3_04_zone_snapshot.py`, `backend/tests/test_p3_07_default_rule_set.py`
- Contract/docs: `frontend/lib/api/schema.ts`, `ARCHITECTURE.md`, `TASKS.md`, `tasks/todo.md`, and this handoff

### Verification evidence

Test-first proof:

- Engine focused tests before production edits: `11 failed, 99 passed, 9 xfailed`; failures covered the missing rule field, all precision paths, SL4 ordering, and trace parity.
- Backend focused tests before production edits: `8 failed`; failures covered migration, default/INSERT, rules API, run selection, and engine construction.

Final checks:

- Engine full suite: **136 passed, 7 xfailed** (before: **122 passed, 9 xfailed**). The two STC cases moved from xfail to strict pass; 12 new regression cases were added.
- Backend full suite: **180 passed** (before: **171 passed**).
- `uv run mypy engine`: clean.
- `uv run alembic heads`: `018 (head)`.
- Frontend `npx tsc --noEmit` and `npm run lint`: clean after regenerating the checked-in rule-update contract.
- `git diff --check`: clean.

Required fixture smoke results (`--fail-on-mismatch`, all exit 0):

| Fixture | Actual | Expected | Absolute difference | Tolerance |
|---|---:|---:|---:|---:|
| `stc_cop_bill1_q3.json` | -120623.31 | -120623.44 | 0.13 | 0.15 |
| `stc_cop_bill2_q4.json` | -54035.51 | -54035.63 | 0.12 | 0.15 |

Nine-fixture invariance (pre-change -> final, exact displayed total):

| Fixture | Before | Final |
|---|---:|---:|
| `bct_2324_296_bill1_q3.json` | 82102.85 | 82102.85 |
| `bct_2324_296_bill2_q4.json` | 94049.85 | 94049.85 |
| `bct_2324_296_bill3_q4.json` | 314.12 | 314.12 |
| `bct_2425_183_bill1_q2.json` | 76077.19 | 76077.19 |
| `bct_2425_252_bill1_q2.json` | 0.00 | 0.00 |
| `bct_2425_252_bill2_q4.json` | 76959.55 | 76959.55 |
| `bct_2425_252_golden_bill1_q2.json` | 34616.03 | 34616.03 |
| `jrh_bct_2324_48_bill1_q4.json` | -23233.54 | -23233.54 |
| `jrh_bct_2324_48_bill2_q6.json` | 166826.18 | 166826.18 |

The other nine fixture inputs remained byte-identical: the fixture-directory diff contains only the two STC files.

### SL4 ordering assumption

For `half_up_2dp`, the engine first quantizes each of the three SL1/SL2/SL3 quarterly series means, averages those three quantized values, then quantizes the derived SL4 mean to 2dp. The code comment references `KU-001-STC-AVG`; tests discriminate this order from quantizing only the raw derived mean. Base observations, including a derived SL4 base with more than 2dp, remain unrounded. This ordering still requires workbook/circular evidence because the current STC workbooks cannot distinguish it.

### Review and deviations

- The repository exposes rule updates as PUT, although the handoff calls it PATCH; the implemented route was updated without adding a duplicate endpoint.
- The new PUT field defaults to `full` so pre-change clients remain valid; the checked-in frontend API schema was updated accordingly.
- A quality review found that the existing PUT lock prevents a contract with any Approved run from adopting a later rule-set version. Converting that guard to version-on-write would change the established MVP update/immutability model and was not enumerated in this handoff, so it was not folded into this implementation. It is explicitly carried into `KU-001-STC-AVG-REVIEW`; until resolved, opt-in through the current API is limited to rule sets not locked by Approved history.
- A detached Claude adversarial pass was attempted as an internal quality check but produced no usable artifact because the local Claude CLI is not logged in. This does **not** satisfy the mandated separate review.
- `git status` also contains unrelated pre-existing/concurrent work (`STATUS.md`, `.codex-stage/`, the audit PDF/Numbers reference, and the consultation handoff). Those files were preserved and excluded; no cleanup was performed.

### Pending gate

**`KU-001-STC-AVG-REVIEW` is still pending and must complete before merge.** This implementation does not close that adversarial-review requirement.

## Adversarial review (KU-001-STC-AVG-REVIEW) — Claude Fable 5, 2026-07-19

**Closed. 1 MEDIUM defect found and fixed in the review pass; no other HIGH/MEDIUM defects.** Full record in [REVIEW.md](../../REVIEW.md).

- **KU1SA-M1 (fixed):** `RuleSetUpdate.quarter_avg_precision` defaulted to `"full"` and the PUT always wrote it, so a client unaware of the field would silently reset a `half_up_2dp` rule set to full precision. Fixed to `QuarterAvgPrecision | None = None` + `COALESCE(:qap, quarter_avg_precision)` — omitted preserves, explicit persists. Test `test_rule_update_omitted_precision_defaults_to_full_and_persists` renamed/repinned to `..._preserves_stored_policy`; `frontend/lib/api/schema.ts` regenerated from the live OpenAPI spec.
- Independently re-verified: nine-fixture invariance, both STC strict passes, no-universalization grep, trace parity, SL4 ordering discrimination, migration default/CHECK, and `PVCRuleSet.model_validate` coercion against production-shaped rows.
- Post-review suites: engine **136 passed, 7 xfailed**; backend **180 passed**; `mypy engine`, frontend `tsc --noEmit`, and `eslint` all clean.
- Deferred as pre-existing: rule-set version-on-write vs the Approved-run PUT lock (already noted above); API-layer `str` typing of `rounding_mode`/`negative_pvc_policy`.
