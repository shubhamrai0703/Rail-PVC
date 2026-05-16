## P2-01: Quarter Mode Is Silently Ignored
Severity: CRITICAL
File: engine/calculator.py (line 83), engine/types.py (line 45)
Issue: `PVCRuleSet.quarter_mode` accepts both `"measurement_date"` and `"bill_date"`, but `calculate_pvc()` always calls `resolve_quarter(bill.measurement_date)` and never branches on `rules.quarter_mode`. A run with `quarter_mode="bill_date"` returns `validation_errors=[]` and still computes using `measurement_date`.
Risk: The engine can persist a rule set that appears to support a different quarter anchor while silently producing measurement-date numbers. That is exactly the kind of plausible-but-wrong output this review is supposed to stop before Phase 3.
Suggested fix: Either remove `"bill_date"` from the schema/UI entirely, or add the missing input and branching logic. If only measurement-date mode is supported, reject any other mode with a validation error instead of ignoring it.

## P2-02: Missing General Weights Are Treated As Zero Instead Of Blocking
Severity: HIGH
File: engine/components.py (line 72), engine/types.py (line 46)
Issue: `compute_general_w_components()` uses `rules.component_weights.get(cat)` and skips the component when the key is missing or falsy. That means an incomplete or misspelled rules payload silently under-calculates PVC with `validation_errors=[]`. In a direct run, full standard weights produced `85.00`, while `{"labour": 0.20}` produced `20.00` with no error.
Risk: Any malformed persisted rule set or partial API payload can drop plant/fuel/materials from the calculation without any visible failure. This is a silent wrong-number path in the core formula engine.
Suggested fix: Validate `component_weights` strictly in the Pydantic model. Require the expected keys for general works, reject unknown keys, and distinguish an explicit `0` weight from a missing key. The engine should block if a required configured component is absent.

## P2-03: Carry-Forward Payload Invariants Are Unenforced
Severity: HIGH
File: engine/types.py (lines 16-23), engine/w_derivation.py (lines 27-31)
Issue: `CarryForwardPayload` has no guardrails for `paid_ratio`, `recorded_qty`, `paid_qty_source`, or `carry_qty`, and `prorate_carry_forwards()` blindly applies `cf.amount * cf.paid_ratio`. A payload with `paid_ratio=1.2`, `paid_qty_source > recorded_qty`, and `carry_qty=-2` returns `validation_errors=[]` and increases the steel deduction anyway.
Risk: The engine accepts impossible carry-forward states and converts them into deterministic but incorrect W deductions. This is especially dangerous because Phase 3 plans to call the engine synchronously and trust its result.
Suggested fix: Add model validation for `0 <= paid_ratio <= 1`, `recorded_qty >= 0`, `paid_qty_source >= 0`, `paid_qty_source <= recorded_qty`, and `carry_qty >= 0`. Also reject duplicate carry-forward entries for the same source item/target bill combination instead of summing them blindly.

## P2-04: `carry_qty` Is Ignored Completely During Proration
Severity: HIGH
File: engine/types.py (line 21), engine/w_derivation.py (lines 18-31)
Issue: The engine stores `carry_qty` on the payload but never uses it in the math. A carry-forward with `carry_qty=0` still contributes `cf.amount * cf.paid_ratio` to the steel bucket. In a direct run, a bill with `steel_angles_amount=100` and a carry-forward of `amount=500`, `paid_ratio=1.0`, `carry_qty=0` produced `steel_angles=600` and `W=400`.
Risk: The carry-forward boundary case explicitly called out in the brief is currently wrong: a record that says there is no carried quantity can still reduce W. That can distort both the current bill and every downstream negative-carry recovery.
Suggested fix: Tie the monetary proration to the carried quantity invariant instead of ignoring it. At minimum, reject any carry-forward with `carry_qty <= 0` before using it. Prefer deriving the carry amount from `recorded_qty`, `paid_qty_source`, and `carry_qty` so the numbers cannot diverge.

## P2-05: Required Real-Workbook Regression Coverage Is Missing
Severity: HIGH
File: engine/tests/test_real_tender_fixtures.py (lines 20-38), engine/tests/fixtures/real_tenders/README.md (line 1)
Issue: The “real tender fixture” test is effectively disabled because there are no JSON fixtures in `engine/tests/fixtures/real_tenders/`. The directory test just skips when empty, so there is no automated Bill-1/Bill-2 regression against BCT-24-25-252 despite Phase 2 acceptance requiring real workbook values and despite the known Bill-2 workbook divergence needing explicit documentation.
Risk: The engine currently has no pinned end-to-end regression proving that current outputs match the trusted workbook inputs for the real tender case. Phase 3 could build on top of a numerically drifting engine without any red test.
Suggested fix: Add at least the confirmed BCT-24-25-252 Bill-1 and Bill-2 fixtures now, including the intentional Q4-vs-Q2 divergence note for Bill-2, and make the regression test fail when the fixture directory is empty.

## CC Response

### P2-01 — Fixed
`PVCRuleSet.quarter_mode` narrowed to `Literal["measurement_date"]` in `engine/types.py`. Any persisted rule set carrying `"bill_date"` now fails Pydantic deserialization with a clear schema error instead of silently flowing through and using measurement-date numbers. Rationale: only one mode is domain-valid, so the type system should refuse to represent the other.
Tests: `TestPVCRuleSetSchema::test_bill_date_quarter_mode_rejected` in `engine/tests/test_w_derivation.py`.

### P2-02 — Fixed
`PVCRuleSet.component_weights` now requires exactly `{labour, plant, fuel, materials}` via a `field_validator`. Missing keys block at model construction; unknown keys are rejected; an explicit `0` is allowed (distinguishing "weighted to zero" from "accidentally omitted"). `compute_general_w_components` now reads with `[cat]` instead of `.get()` — since the validator guarantees completeness, a missing key would be an internal bug rather than user-input fallthrough.
Tests: `TestPVCRuleSetSchema::test_missing_component_weight_rejected`, `test_unknown_component_weight_rejected`, `test_explicit_zero_weight_is_allowed`.

### P2-03 / P2-04 — Fixed (combined)
`CarryForwardPayload` was over-specified — `recorded_qty`, `paid_qty_source`, `paid_ratio`, `carry_qty`, and `amount` could disagree. The model is now minimal: inputs are `recorded_qty` (>0), `paid_qty_source` (0 ≤ x ≤ recorded_qty), `amount` (≥0). `paid_ratio` and `carry_qty` are `@computed_field` properties derived from quantities — they can no longer drift from each other or take impossible values. This makes the P2-04 case (`carry_qty=0` with positive proration) impossible by construction: zero `carry_qty` now requires `paid_qty_source == recorded_qty`, which is the genuine "fully-paid carry-forward" case where attributing the full amount is correct.
Tests: `TestCarryForwardInvariants` covering rejection of paid > recorded, negative paid, zero recorded, negative amount, plus positive cases for fully-paid and zero-paid records.

### P2-05 — Fixed
Two regression fixtures added under `engine/tests/fixtures/real_tenders/`:
- `bct_2425_252_bill1_q2.json` — Q2-FY2025-26, typical on-account bill with cement, steel buckets, excluded NS extra item.
- `bct_2425_252_bill2_q4.json` — Q4-FY2025-26 with a steel carry-forward; `notes.workbook_divergence` explicitly documents that the physical workbook used Q2 indices for this Q4 measurement and that the expected `total_pvc` pins the **engine's correct Q4 result**, not the workbook's wrong number.
`test_real_tender_fixtures.py` now **fails** when the fixture directory is empty (previously skipped). A second test asserts that any fixture flagging a workbook divergence must populate `notes.workbook_divergence`, so the divergence documentation can't silently disappear.
Coverage after changes: 99% (engine package), 88 tests passing.

## P2-06: Trace Output Does Not Meet The Accepted Provenance Contract
Severity: MEDIUM
File: engine/calculator.py (lines 25-67)
Issue: Phase 2 acceptance says every trace field should point to `{input_field, formula, index_ref, bill_line_ref}`. The current trace only stores rendered values plus quarter/base-month metadata. It does not identify which input field populated a component, which formula variant was used, or which source line/item produced the deduction.
Risk: Phase 3/7 cannot reliably expose cell-level provenance from the engine result even though the interface claims it exists. That weakens auditability and increases the chance that the frontend or export layer will re-derive explanations on its own.
Suggested fix: Expand the trace schema now to include formula identifiers, index series/month references, and source field/item references for W deductions and each component. If that structure is intentionally deferred, lower the acceptance claim in `TASKS.md` instead of returning a misleading trace shape.

### P2-06 — Fixed (CC-S, 2026-05-16)

Resolved by **expanding** the trace contract, not by downgrading acceptance. Decided ahead of Phase 3's P3-009 so the persisted shape is final on first write.

**Approach:**
1. `PVCRunResult.trace` is now a typed `TraceContract` Pydantic model (not `dict`). Static type-checking; locked shape; `schema_version="1.0"` for future evolution.
2. Added opaque `source_ref: str | None` to `ExtraItemDecision` and `CarryForwardPayload`. Engine never interprets it — Phase 3 fills with `bill_lines.id` and the engine echoes it into trace as `bill_line_ref`. Resolves the engine-doesn't-know-DB-IDs constraint without coupling.
3. `index_ref` echoes **full values** (base month/value + quarter months/values/avg), not just keys. Trace is self-contained — the `revision_snapshots` audit is the truth even if `index_observations` later mutates.
4. W derivation gets both surfaces: numeric `result.w_derivation` (already there) plus an annotated `trace.w_derivation` that names the input field per line and lists carry-forward contributions per steel bucket.
5. Steel buckets distinguish `steel_bucket_pvc` (single commodity series, SL1/SL2/SL3) from `steel_bucket_pvc_derived_avg` (SL4, GCC 46A.9 average across three series). Each steel bucket trace enumerates its four sub-component index_refs (labour/plant/fuel/materials).

**Files changed:**
- `engine/types.py` — `source_ref` on `ExtraItemDecision`/`CarryForwardPayload`; new models: `IndexBaseValue`, `IndexQuarterValues`, `IndexRef`, `DerivedAvgIndexRef` (discriminated union), `SteelSubComponentTrace`, `ComponentTrace`, `CarryForwardContribution`, `WDerivationLine`, `WDerivationTrace`, `CarryForwardTrace`, `ExtraItemTrace`, `TraceContract`. `PVCRunResult.trace: TraceContract`.
- `engine/calculator.py` — `_build_index_ref`, `_build_derived_avg_ref`, `_build_component_trace`, `_build_w_derivation_trace`, `_build_carry_forward_traces`, `_build_extra_item_traces`. Refactored `_build_trace` to compose these and accept `rules` + `w_derivation` (may be None on pre-W block).
- `engine/tests/test_calculator.py` — switched existing trace tests to attribute access; added 8 new tests covering schema_version, W provenance, blocked-run W=None, single vs derived-avg commodity refs, source_ref echo to both trace.carry_forwards and trace.w_derivation contributions, eligible-True vs eligible-False applied flag.

**Verification:**
- 99 tests passing (was 91), 0 failing.
- Coverage: 99% on `engine/` package — held.
- BCT-24-25-252 Bill-1/Bill-2 fixtures still pass; expected totals unchanged.

**Phase 3 contract implications:**
- P3-009 must persist `trace` as a JSONB column on `pvc_components` (or `pvc_runs` if denormalized). Recommend `pvc_runs.trace JSONB` since trace is one document per run.
- `revision_snapshots` should snapshot the full trace, since it now contains all input values needed to re-render the audit.
- P3-002/P3-007 (contracts/extra items) and P3-005 (carry-forwards) should plumb `bill_lines.id` through as `source_ref` when constructing the engine payload — required for cell-level provenance in Phase 7.

P2-06 closed.

## P3-PRE-REVIEW — 2026-05-16

Verified against `REFERENCES/GCC_April-2022ACS14.07.2022-PVCClause.pdf`: GCC 46A.9(1) clearly makes TMT/rebar its own SL1 category, GCC 46A.9(1) SL4 clearly defines “other sections” as the average of SL1/SL2/SL3, and GCC 46A.9(2) matches the 16-zone mapping used in migration 010. The Bill-2 fixture arithmetic also checks out: `avg(56700, 56800, 56500) = 56666.67`, which yields `expected.total_pvc = 76959.55`; the old direct `56900` path reproduces the prior `77565.84`. I could not independently verify the physical workbook itself because it is not present in the repo.

### P3-PRE-01
Severity: CRITICAL
File: `engine/types.py` (lines 49-55), `README.md` (line 84)
Issue: `BillPayload.steel_tmt_amount` was introduced to represent GCC 46A.9(1) SL1 (“Reinforcement bars and other rounds”), but it defaults silently to `Decimal("0")`. That means any Phase 3 mapper that forgets to populate the new field will still produce a valid engine payload and a plausible PVC number, while omitting a mandatory steel bucket entirely. This directly contradicts the project rule “Missing input → run blocked. No silent defaults.”
Suggested fix: Make `steel_tmt_amount` required. If backward compatibility is temporarily necessary, add an explicit compatibility gate that rejects payloads missing `steel_tmt_amount` whenever the source contract contains any `contract_items.steel_subtype = 'tmt'`.

### P3-PRE-02
Severity: CRITICAL
File: `backend/migrations/versions/009_rls_policies.py` (lines 226-245)
Issue: The migration comment says `index_series` / `index_observations` are shared global data and that writes are “restricted to the service role only”, but the actual policies grant `INSERT` and `UPDATE` on `index_observations` to any authenticated user via `auth.uid() IS NOT NULL`. Because these tables are global, not tenant-scoped, one tenant can alter the price index history used for every other tenant’s PVC calculations. This is a cross-tenant data integrity break and can silently change approved or future PVC numbers.
Suggested fix: Remove authenticated `INSERT`/`UPDATE` policies from `index_observations`. If Phase 3 needs manual observation entry, route it through a trusted backend/service-role path or introduce an explicit admin role policy; do not leave shared index data writable by ordinary authenticated users.

### P3-PRE-03
Severity: HIGH
File: `backend/migrations/versions/009_rls_policies.py` (lines 264-278), `README.md` (lines 90-92)
Issue: `pvc_runs` has a broad tenant-wide `UPDATE` policy even though the product contract says “Once a PVC run is approved it cannot be modified.” API-layer immutability in Phase 3 is not an adequate backstop here: with Supabase, any client path that can issue updates under the caller’s JWT can still mutate tenant-owned `pvc_runs` rows directly at the database layer, including approved runs, unless the database itself blocks it.
Suggested fix: Enforce immutability in the database. Either remove the general `UPDATE` policy and perform approval through a controlled function, or add a trigger/check that rejects updates once `status = 'Approved'` (and ideally restricts post-creation mutations more narrowly than “any update by tenant”).

### P3-PRE-04
Severity: HIGH
File: `backend/migrations/versions/010_railway_zone.py` (lines 38-40), `TASKS.md` (lines 47, 82, 89)
Issue: `contracts.railway_zone` is added as nullable, with no backfill and no corresponding requirement in the current P3-002 contract-create acceptance. But P1-011 and P3-009 explicitly make zone selection part of JPC snapshot selection. That leaves a straight-line failure mode for Phase 3: create a contract without `railway_zone`, then fail later when building the zone-specific JPC snapshot for a PVC run.
Suggested fix: Make `railway_zone` mandatory before Phase 3 contract APIs ship. Backfill existing contracts, add API validation in P3-002 returning `422` when `railway_zone` is omitted, and then tighten the column to `NOT NULL` once the backfill is complete.

### P3-PRE-05
Severity: LOW
File: `engine/components.py` (lines 171-187)
Issue: `_steel_bucket_pvc()` now accepts `str | list[str]` for the commodity series and correctly blocks when one required series is missing, but it does not defend against an empty list. A future caller passing `[]` will hit a division-by-zero path at `len(commodity_series)` instead of returning a normal validation error.
Suggested fix: Guard `if not commodity_series:` and return an explicit error such as `empty commodity series list for steel bucket` before attempting the average.

---

## P3-PRE-REVIEW — CC-S Responses (2026-05-16)

### P3-PRE-01 — Fixed

`BillPayload.steel_tmt_amount` default removed; field is now required. Any caller that omits it will get a Pydantic `ValidationError` (field required) at payload construction, consistent with the project rule "Missing input → run blocked. No silent defaults." All test helpers (`test_calculator.py::_bill`, `test_import.py`) updated to pass `steel_tmt_amount` explicitly. Real-tender fixture JSONs already included the field.

Tests: existing 91 tests still pass; no regression.

### P3-PRE-02 — Fixed

`index_observations_insert` and `index_observations_update` RLS policies dropped in migration `011`. Only `SELECT` remains for authenticated users. The service role (used by seed scripts and backend admin paths) bypasses RLS entirely, so write access is preserved for authorised infrastructure without creating a policy that any JWT-bearing client can exploit.

Migration: `backend/migrations/versions/011_security_hardening.py`.

### P3-PRE-03 — Fixed

A `BEFORE UPDATE` trigger (`trg_pvc_runs_immutable_approved` / `prevent_approved_run_update()`) added in migration `011`. It raises `check_violation` if `OLD.status = 'Approved'`, blocking mutations at the DB layer regardless of the calling path. The existing tenant-scoped `UPDATE` RLS policy is retained for pre-approval state transitions (Draft → Calculated → Approved); the trigger is the backstop once the run is locked.

Migration: `backend/migrations/versions/011_security_hardening.py`.

### P3-PRE-04 — Fixed

Migration `011` backfills `contracts.railway_zone = 'NR'` for any NULL rows, then sets the column `NOT NULL`. The backfill is a placeholder — prod deployments must correct values before running PVC calculations. The CLAUDE.md KU-006 section already documents the zone→city mapping. API validation (`railway_zone` required in the P3-002 contract-create endpoint) is recorded as a Phase 3 acceptance criterion in TASKS.md.

Migration: `backend/migrations/versions/011_security_hardening.py`.

### P3-PRE-05 — Fixed

Guard `if not commodity_series: return None, None, None, ["empty commodity series list for steel bucket"]` added at the top of the list branch in `_steel_bucket_pvc()` (`engine/components.py`). New test: `TestSteelComponents::test_empty_commodity_series_list_returns_error`.

Tests: 91 passing (includes new test).

---

## P3-REVIEW Checklist (pre-flight, awaiting CC-SH submission)

**Status:** Stub. Codex-S runs this against `shubham/phase-3` once all P3-001…P3-011 land. CC-SH may use it as a self-review before requesting review to cut a cycle.

**Scope:** API correctness, security, contract fidelity to engine. Does NOT re-review engine code (covered by P2-REVIEW).

### CRITICAL — fail merge

1. **Tenant isolation on every protected endpoint.** Every read/write filters by `tenant_id` from the JWT; no endpoint returns or accepts rows belonging to another tenant. Verify by issuing requests with two distinct JWTs against the same resource IDs and confirming 404/403.
2. **`railway_zone` required on contract create (P3-002).** POST `/api/contracts` without `railway_zone` returns 422; ENUM validation rejects non-listed zones (16 valid values per migration 010). Without this, P3-009 fails downstream when selecting JPC city.
3. **Approved `pvc_runs` immutability (P3-010).** PUT/PATCH on an Approved run returns 409 Conflict. Verify the DB trigger (`trg_pvc_runs_immutable_approved`, migration 011) fires even for service-role direct writes. The API-layer check is belt; the trigger is suspenders.
4. **No engine fallback path.** P3-009 must NEVER swallow `validation_errors` from `calculate_pvc()`. Non-empty errors → 422 with the full list, no persisted run row. Verify: pass a payload with `eligible=None` extra item → 422, zero rows inserted in `pvc_runs`.
5. **`index_observations` writes blocked for authenticated users.** Confirm RLS policy state matches migration 011: `SELECT` only for `authenticated`; no `INSERT`/`UPDATE` policies. Service role bypasses RLS — that path is acceptable.
6. **W derivation parity.** Snapshot the engine payload P3-009 constructs and assert it matches a hand-built BillPayload for BCT-24-25-252 Bill-1: same on_account, same per-bucket steel amounts (incl. carry-forward proration), same extra_item_decisions with eligibility populated. Field name drift between API and engine = silent miscalculation.

### HIGH — must fix before merge

7. **`source_ref` plumbing (P2-06 contract).** P3-007 (extra items) and P3-005 (carry-forwards) must pass `bill_lines.id` as `source_ref` when constructing engine payloads. Without this, Phase 7 audit UI cannot link a deduction back to its source row.
8. **Trace persistence.** P3-009 must persist the engine's `TraceContract` (now `schema_version="1.0"`) into `pvc_runs.trace` JSONB. The `revision_snapshot` must capture the trace too — that's the audit truth. Verify shape with `result.trace.model_dump(mode='json')`.
9. **Idempotency on POST /pvc-runs.** Duplicate POSTs (same bill, same rule_set, no upstream changes) should not create N runs. Either: (a) require an `Idempotency-Key` header, or (b) check for an existing Draft run and 409 with the existing run_id.
10. **Numeric precision.** All Decimal fields preserve precision through the API boundary (request → engine → DB → response). No float coercion. Spot-check: round-trip `steel_other_amount = "57727.5023"` and confirm bit-identity.
11. **`paid_ratio` server-derived (P3-005 acceptance).** PUT carry-forward MUST recompute `paid_ratio` from `paid_qty / recorded_qty`; reject any client-supplied ratio. The model's @computed_field is enforcement; the API should not even accept the field in input.
12. **PVCRuleSet validation parity.** `component_weights` API validation must mirror the engine's `_weights_complete_and_known` validator: reject missing keys, reject unknown keys, allow explicit zero. Verify: `{"labour": 0.20}` → 422 (not silently accepted).
13. **JPC zone-specific snapshot construction (P3-009).** Building the `IndexSnapshot` for a run must select index_series filtered by `contracts.railway_zone` → city mapping (CLAUDE.md KU-006). Two contracts in different zones submitting on the same day should produce different snapshots.

### MEDIUM — log, don't block

14. **OpenAPI schema coverage.** Every endpoint has request/response schemas; no `Any` returns. Required for P4-006 `openapi-typescript` codegen.
15. **Error response shape consistency.** 422 returns Pydantic-style `{detail: [{loc, msg, type}]}`; 4xx errors include a `correlation_id` for log tracing.
16. **`approved_by` field.** Still TEXT (post-MVP debt); confirm endpoint passes the JWT user's email or display name, not the raw `auth.uid()`.
17. **Audit trail on PVC rule changes.** PUT `/api/contracts/{id}/pvc-rule-set` should not silently overwrite a rule set referenced by an Approved run. Suggested: copy-on-write or hard-link via rule_set_id.

### LOW — nice to have

18. **Rate limiting** on POST `/pvc-runs` (engine call is synchronous in MVP; one tenant DoS-ing themselves is fine, but worth a guard).
19. **CORS** locked to known origins, not `*`.
20. **OpenAPI examples** for at least the three trickiest endpoints (POST /pvc-runs, PUT /carry-forwards, POST /contracts with railway_zone).

### Domain-correctness regression set

Codex must rerun these against the live API (not just engine fixtures):

- BCT-24-25-252 Bill-1 (Q2-FY2025-26): full payload → POST /pvc-runs → response `total_pvc=0.00`, `negative_carry_forward=635.38`.
- BCT-24-25-252 Bill-2 (Q4-FY2025-26): with steel carry-forward → response `total_pvc=76959.55`.
- Bill with `eligible=None` extra item → 422, no persisted run.
- Bill with `steel_tmt_amount` omitted from request → 422 (Pydantic field required).
- Contract POST without `railway_zone` → 422.
- Approved run, attempt PUT → 409.

