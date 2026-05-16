# RailPVC — Session Log & Decision Record

This document is a running record of major decisions, confirmed domain rules, architectural choices, and phase-by-phase work completed. Maintained by Claude Saqlain (CC-S). Append new entries at the bottom under the relevant phase or date.

---

## Project Initiation — 2026-05-13

### What was built
- Initial project planning scaffolding: `PRODUCT.md`, `ARCHITECTURE.md`, `TASKS.md`, `CODEX.md`, `CLAUDE.md`
- Defined the MVP as a billing OS for Indian Railway contractors under GCC Clause 46A
- Established the three non-negotiables (from `PRODUCT.md`): deterministic output, Excel-parity export, full W derivation auditability

### Key decisions
- **Stack chosen:** Next.js 14 (App Router) + TypeScript frontend; FastAPI (Python 3.11+) backend; Supabase (Postgres + Auth + Storage); pure Python `engine/` package with no DB or HTTP dependencies
- **Engine isolation:** `engine/` is a pure function package — `calculate_pvc(bill, indices, rules) → PVCRunResult`. It never calls the DB, never calls HTTP. FastAPI imports it; the engine knows nothing about FastAPI.
- **AG Grid for all tabular data entry** — spreadsheet-feel is a product requirement, not a preference. Field operators recognize grid-based input from their Excel workflows.
- **openpyxl for Excel export** — must match BCT-24-25-252 workbook layout exactly (sheet names, column headers, formula structure). This is the adoption gate.
- **Single-user per org for MVP** — multi-user RBAC (3 roles: AE/JE/Contractor) is immediate post-MVP, but not in scope for v1.

---

## Phase 0 — Scaffolding — 2026-05-14 (commit `0bc20a5`)

### What was built
- Next.js 14 app with App Router, TypeScript, Tailwind — `npm run dev` runs
- FastAPI project with `/health` endpoint and OpenAPI docs at `/docs`
- Supabase project wired: `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_KEY` in `.env`
- `engine/` Python package skeleton — `pip install -e ./engine` works; `from engine import calculate_pvc` importable
- `Makefile` for local dev startup
- `.gitignore` set; no secrets in repo

### Gaps noted (from Phase 0/1 review)
- README was overstating maturity — listed `backend/api/`, `backend/models/`, `backend/services/` directories that did not exist yet
- Engine was a stub returning `"Engine not yet implemented — Phase 2"`

---

## Phase 1 — Data Model + Migrations — 2026-05-14 (commit `cc0de0c`)

### What was built
- Alembic migration sequence `001` through `008`:
  - `001`: tenants, users (supabase_auth_id FK to Supabase Auth)
  - `002`: contracts, schedules, contract_items
  - `003`: running_bills, bill_lines, recoveries
  - `004`: carry_forwards (paid_ratio NUMERIC(10,8), constraint 0 ≤ ratio ≤ 1)
  - `005`: index_series, index_observations ((series_id, month) UNIQUE)
  - `006`: pvc_rule_sets (component_weights as JSONB)
  - `007`: pvc_runs, pvc_components, revision_snapshots
  - `008`: extra_item_decisions, documents
- RLS policies applied via Supabase dashboard; documented in `backend/RLS_POLICIES.md`
- Seed script `seeds/seed_indices.py` — idempotent; seeds RBI + JPC index data

### Key schema decisions
- All qty/amount fields: `NUMERIC(15,4)` — Railway contract amounts run to crores; float is not acceptable
- `base_month` stored as `DATE` (first day of month), never as string
- `extra_item_decisions.eligible` is nullable — `NULL` = undecided. This field blocks PVC runs at engine level.
- `pvc_runs.superseded_by` is a self-FK; `NULL` = active run. Revisions create new rows, never modify old ones.
- `revision_snapshots` has `SELECT` + `INSERT` RLS only — no `UPDATE` policy. Append-only enforced at both DB and API layer.
- `approved_by` is `TEXT` in v1 (not a user FK) — acceptable for MVP, flagged for post-MVP hardening

### Open items from Phase 1 review (REVIEW_PHASE0_PHASE1.md)
- RLS not yet captured as Alembic migration `009` — environment is not reproducible from git alone until this is done. Trigger: immediately before P3-001 (auth middleware) starts.
- Seeded index history is Dec-2024 to Dec-2025 (13 months), not Jan-2022 to present as originally planned. Accepted for MVP; full backfill is post-MVP.
- `pvc_runs.approved_by` should become a user FK post-MVP.

---

## Phase 2 — Calculation Engine — 2026-05-14 (commit `99c416d`)

### What was built
- Full engine implementation: P2-001 through P2-013
- Pydantic types: `BillPayload`, `IndexSnapshot`, `PVCRuleSet`, `PVCRunResult`
- W derivation pipeline:
  - Cement bucket subtraction
  - Steel bucket subtraction (angles, plates, other — kept separate through the whole pipeline because each maps to a different JPC index series)
  - Extra-item exclusion (blocks on `eligible=None` — never defaults)
  - Carry-forward proration (`paid_ratio = paid_qty / recorded_qty`; prorated before steel subtraction)
- Quarter resolver: `measurement_date` → calendar quarter → 3-month average of index observations
- Component formulas:
  - General W: `PVC = W × weight × (Qavg − base) / base` per component
  - Cement: `PVC_cement = cement_amount × 0.85 × (Qavg_cement − base_cement) / base_cement`
  - Steel: per-subtype formula with `labour(0.10) + steel_commodity(0.50) + plant(0.10) + fuel(0.10) + materials(0.05) = 0.85`
- Run validation: blocks if any required index month is missing OR any extra item is `eligible=None`
- Trace tree: every field in `PVCRunResult.trace` points to its source `{input_field, formula, index_ref, bill_line_ref}`
- Negative PVC: zero-floor on this bill; `negative_carry_forward` stored for recovery from next bill's PVC total
- pytest unit tests (≥80% coverage) + Hypothesis property tests on W derivation invariants

### Confirmed domain rules (KU series)
- **KU-001 ✓** (confirmed 2026-05-14): Quarter anchor = "To" date of MB period (`measurement_date`). Calendar quarters: Q1=Jan-Mar, Q2=Apr-Jun, Q3=Jul-Sep, Q4=Oct-Dec. FY label follows Indian FY (Apr-Mar). Format: `Q2-FY2025-26`. Stored as immutable field on every PVC run — never re-derived.
- **KU-002 ✓** (confirmed 2026-05-14): Schedule C extra NS items in BCT-24-25-252 bill 2 are intentional. ~16L worth of yellow-highlighted items are `eligible=False` (included in `on_account_amount`, explicitly subtracted from W). Engine blocks on `eligible=None`.
- **KU-003 ✓** (confirmed 2026-05-14): Negative PVC treatment = zero-floor this bill + store `negative_carry_forward`. Recovered from next bill's PVC total. Not an immediate offset.

### Additional work in this cycle (uncommitted as of 2026-05-16)
- **JPC PDF extraction pipeline:** `seeds/extract_jpc_pdf.py` — extracts fortnightly JPC steel price bulletins from PDF; outputs `REFERENCES/jpc_raw_extracted.csv`
- **JPC monthly averaging:** `seeds/compute_jpc_monthly.py` — computes monthly averages from fortnightly data; method: average fortnightly readings per city, then avg_4city = mean of 4 city averages; flags outliers (>30% deviation from median of other 3 cities)
- **REFERENCES/ directory:** source documents added — JPC bulletins (PDF), All India Index CSV, WPI metadata, Steel Index xlsx, CPIW labour index, extraction error logs and warnings
- **Real tender fixtures framework:** `engine/tests/test_real_tender_fixtures.py` + `engine/tests/fixtures/real_tenders/` — parametric pytest tests that run the engine against JSON fixtures from real tenders; fixture dir currently has a README placeholder awaiting BCT-24-25-252 JSON fixture
- **`scripts/run_engine_fixture.py`:** CLI tool to run the engine against a fixture file and compare output to expected PVC value — useful for manual verification without a full test run
- **PDF sample pages:** `REFERENCES/pdf_samples/` — 5 sample pages extracted from the JPC bulletin PDF for OCR quality review

---

## Collaboration Structure — 2026-05-16

### Decision: Three-agent model
Moved from a two-party model (CC + Codex) to a three-agent model:

| Agent | Label | Role |
|---|---|---|
| Claude Saqlain | `[CC-S]` | Engine, auth, business logic, critical UI (W derivation preview, BillLine grid, carry-forward, eligibility UI), review responses |
| Claude Shubham | `[CC-SH]` | Phase 3 API layer; UI generation tasks (forms, simple tables, upload UI) |
| Codex Saqlain | `[CODEX-S]` | Adversarial review checkpoints only — P2-REVIEW, P3-REVIEW, P8-REVIEW, P9-DEBUG. Writes to `REVIEW.md`, never touches code. |

### Rationale
- Codex is better at adversarial critique and finding silent calculation defaults than at UI generation; restrict it to that strength
- Shubham's Claude handles Phase 3 API (which is largely CRUD + tenant isolation) and can generate UI scaffolding without risk to engine correctness
- Saqlain owns all correctness-critical paths end to end

### Branch strategy
- `shubham/phase-3` — Shubham's Phase 3 work; does not merge to main until P2-REVIEW CRITICAL/HIGH issues resolved and CC-S signs off
- `saqlain/engine-fixes` — engine fixes from P2-REVIEW findings
- `saqlain/phase-4` — Phase 4 frontend shell; starts after Shubham's P3-001 merges

### Hard boundary for CC-SH
Shubham's Claude must never touch: `engine/`, `backend/migrations/`, auth middleware, snapshot/immutability logic (`pvc_runs` approve endpoint, `revision_snapshots`). These are all `[CC-S]` territory.

### Merge gate
`REVIEW.md` is the async handoff document. Codex writes numbered critique there. CC-S responds under each issue. Both sides write to `REVIEW.md` — it is the single source of truth for review state. Phase 3 does not merge to main until all CRITICAL and HIGH issues from P2-REVIEW are cleared.

---

## Current State — 2026-05-16

### What is complete and on main
- Phase 0: Full scaffolding
- Phase 1: All migrations (001–008), RLS policies (dashboard), seed script
- Phase 2: Full engine implementation + tests (P2-001 through P2-013)

### What is ready to push (this commit)
- Collaboration model updates: TASKS.md, CODEX.md, CLAUDE.md
- README improvements
- JPC extraction and averaging pipeline (`seeds/extract_jpc_pdf.py`, `seeds/compute_jpc_monthly.py`)
- Updated seed script (`seeds/seed_indices.py`)
- REFERENCES source documents
- Real tender fixture test framework (`engine/tests/test_real_tender_fixtures.py`, `engine/tests/fixtures/`)
- Engine fixture runner script (`scripts/run_engine_fixture.py`)

### Immediate next steps
1. **CC-S + Codex-S:** Run P2-REVIEW — adversarial engine review; output to `REVIEW.md`
2. **CC-SH:** Clone repo, create `shubham/phase-3` branch, begin Phase 3 API (start with P3-001 auth middleware, read ARCHITECTURE.md and CODEX.md first)
3. **CC-S:** Address CRITICAL/HIGH findings from P2-REVIEW on `saqlain/engine-fixes` branch
4. **CC-S:** Begin Phase 4 scaffolding (P4-001, P4-003, P4-005) after P3-001 merges

### Open items / known debt
- RLS migration `009` not yet in git (P1-010-ALEMBIC) — must be captured before Phase 3 merges
- BCT-24-25-252 real tender JSON fixture not yet created — needed for P9-002 engine regression tests
- JPC seed coverage: Dec-2024 to present only; full backfill (Jan-2022 onward) is post-MVP
- `pvc_runs.approved_by` is TEXT, not a user FK — post-MVP hardening item

---

## Workflow Confirmation — 2026-05-16

### This is the permanent collaboration model going forward

The three-agent split described above is now locked in. All future work proceeds under this model — no exceptions without explicit agreement from Saqlain.

**Day-to-day flow:**

1. **Codex-S runs first** at each review checkpoint (P2-REVIEW, P3-REVIEW, P8-REVIEW, P9-DEBUG). Saqlain triggers it manually against the completed phase. Output lands in `REVIEW.md` as numbered, severity-tagged issues.

2. **CC-S responds to CRITICAL and HIGH issues** in `REVIEW.md` under each finding before the phase branch merges. MEDIUM and below are tracked but do not block the merge.

3. **CC-SH works phase branches independently.** Shubham's Claude reads `TASKS.md`, `ARCHITECTURE.md`, and `CODEX.md` at the start of each session. It never modifies engine code, migrations, auth middleware, or snapshot logic — those are hard boundaries regardless of context.

4. **`REVIEW.md` is the only async handoff document.** Neither agent pings the other directly. The review file is the contract: if a finding has a CC-S response and is marked resolved, it is closed. If it has no response, it is open and blocks the merge.

5. **`SESSION_LOG.md` gets a new dated entry** for any significant decision, domain confirmation, or workflow change. Append at the bottom. This file is the audit trail for the project — not the git log, not chat history.

**Branch lifecycle:**
- Shubham opens `shubham/phase-N` → builds → CC-S + Codex-S review → CRITICAL/HIGH cleared → CC-S approves merge → merged to main → Shubham deletes branch and opens `shubham/phase-N+1`
- CC-S works `saqlain/phase-N` in parallel where dependencies allow → merges after Shubham's prerequisites land

**What CC-SH must read before starting Phase 3:**
- `ARCHITECTURE.md` — full data model and API surface
- `CODEX.md` — boundaries, review format, what never to touch
- `TASKS.md` — Phase 3 task list, acceptance criteria, domain notes
- `engine/` source — understand the types and output shape before building P3-009

---

## P2-REVIEW Response — 2026-05-16 (CC-S, evening session)

### What was done

CC-S responded to all CRITICAL/HIGH findings in `REVIEW.md`. P2-06 (MEDIUM) was deferred per the session brief.

| ID | Severity | Status |
|---|---|---|
| P2-01 | CRITICAL | ✅ Fixed |
| P2-02 | HIGH | ✅ Fixed |
| P2-03 | HIGH | ✅ Fixed (combined with P2-04) |
| P2-04 | HIGH | ✅ Fixed |
| P2-05 | HIGH | ✅ Fixed |
| P2-06 | MEDIUM | Deferred — trace provenance contract |

### Files changed

- `engine/types.py` — type-level invariants. `quarter_mode` narrowed to `Literal["measurement_date"]`; `PVCRuleSet.component_weights` validator requires the exact four general-works keys (`labour`, `plant`, `fuel`, `materials`) with explicit `0` distinguished from missing; `CarryForwardPayload` redesigned to minimal inputs (`recorded_qty`, `paid_qty_source`, `amount`) with `paid_ratio` and `carry_qty` as `@computed_field` properties so the model cannot represent contradictory state.
- `engine/components.py` — `.get(cat)` → `[cat]` since the schema validator now guarantees completeness.
- `engine/tests/test_w_derivation.py` — `_cf` helper updated; new `TestCarryForwardInvariants` and `TestPVCRuleSetSchema` test classes covering invariant rejection and required-key enforcement.
- `engine/tests/test_components.py` — `_rules` helper backfills missing keys with `0`.
- `engine/tests/test_calculator.py` — `CarryForwardPayload` constructor calls drop removed fields.
- `engine/tests/test_import.py` — full weight dict in test rule set.
- `engine/tests/test_real_tender_fixtures.py` — empty fixture directory now **fails** instead of skipping; new assertion that any fixture flagging workbook divergence must populate `notes.workbook_divergence`.
- `engine/tests/fixtures/real_tenders/bct_2425_252_bill1_q2.json` — new. Q2-FY2025-26, measurement 2025-06-18, cement + steel + excluded NS extra item. Expected `total_pvc = 0.00`, `negative_carry_forward = 635.38`.
- `engine/tests/fixtures/real_tenders/bct_2425_252_bill2_q4.json` — new. Q4-FY2025-26, measurement 2025-11-04, steel carry-forward. Expected `total_pvc = 77565.84`. Notes explicitly document the physical workbook's Q2→Q4 silent index error and pin the engine's CORRECT Q4 output.
- `REVIEW.md` — `## CC Response` section added with per-finding write-ups.

### Design decisions (reasoning recorded for future review)

1. **P2-01 — narrow the type, don't add runtime validation.** `quarter_mode` accepting `"bill_date"` as a Literal variant was the schema lying about reality. Removing the variant means Pydantic rejects bad input at deserialization with a clear error, instead of producing plausible-but-wrong numbers downstream. Cleanest representation of an invariant we already know to be true (KU-001).

2. **P2-02 — distinguish "zero" from "missing" at the model layer.** The reviewer flagged that `.get(cat)` silently under-computed PVC. The fix lives at the schema, not at the engine: validator enforces exactly the four required keys, with explicit `0` allowed. The engine then reads with `[cat]` knowing completeness is guaranteed.

3. **P2-03 + P2-04 — make invalid states unrepresentable.** The `CarryForwardPayload` was over-specified — five fields where three sufficed, with no guard against contradiction. Rebuilt around the source-of-truth inputs (`recorded_qty`, `paid_qty_source`, `amount`); `paid_ratio = paid_qty_source / recorded_qty` and `carry_qty = recorded_qty − paid_qty_source` become `@computed_field` properties. By construction, ratio is in `[0, 1]`, carry_qty is non-negative, and `carry_qty=0` now means "fully paid" (which correctly attributes full amount). The P2-04 contradiction (`carry_qty=0` while still deducting) becomes impossible.

4. **P2-05 — pin behaviour with documented intent.** Two fixtures cover Bill-1 (Q2) and Bill-2 (Q4). Bill-2's `notes.workbook_divergence` field is the audit trail for the known Q2→Q4 silent error in the physical workbook — the fixture asserts the engine's CORRECT Q4 result, not the workbook's wrong number. The skip-on-empty behaviour was inverted to fail-on-empty so this regression coverage cannot quietly disappear.

### Verification

- All existing tests still pass.
- New tests added: `TestCarryForwardInvariants` (7), `TestPVCRuleSetSchema` (4), 2 real-tender fixture tests + parametrized over fixture files.
- Coverage: **99% on `engine/` package** (≥80% gate cleared). 88 passing, 0 failing.

### What this unblocks

- All P2-REVIEW CRITICAL + HIGH cleared. `shubham/phase-3` merge gate is now open from CC-S's side once P2-06 (MEDIUM, deferred) is either addressed or formally accepted.
- BCT-24-25-252 regression coverage now exists for both Bill-1 and Bill-2 — closes the P9-002 fixture gap surfaced in REVIEW.md.

### Carrying forward

- **P2-06 (trace provenance contract)** — deferred this session per brief. Decision: either expand trace schema to include `{input_field, formula, index_ref, bill_line_ref}` per field, or downgrade the acceptance claim in `TASKS.md`. Pick one before Phase 7 (results UI) starts; Phase 3 doesn't strictly need richer trace.
- **RLS migration 009** — still not in git (P1-010-ALEMBIC). Must land before `shubham/phase-3` merges.
- **TMT bucket confirmation** — still pending Saqlain's domain input. Does not block engine merge, but determines whether `steel_tmt`/`steel_other_sections` split matters for the workbook.

---

## Session 3 — 2026-05-16 (GCC analysis + engine fixes + migrations)

### Context

GCC PDF analysis before Shubham begins Phase 3. Two items highlighted from the plan: P2-06 trace decision and P1-010-ALEMBIC RLS migration. Expanded to four items after GCC PDF confirmed domain gaps in the engine.

### GCC 46A.9 — new domain confirmations

Analyzed `REFERENCES/GCC_April-2022ACS14.07.2022-PVCClause.pdf`:

- **KU-004 ✓**: TMT/rebar is SL1 — its own JPC series (`steel_tmt`), separate W subtraction bucket. Was previously incorrectly routed to the `steel_other` bucket.
- **KU-005 ✓**: Other sections is SL4 — commodity index = `avg(JPC_tmt, JPC_angles, JPC_plates)` per GCC 46A.9. No standalone series. Engine was looking up a non-existent `steel_other_sections` series — fixed.
- **KU-006 ✓**: GCC 46A.9(2) — JPC city by Railway zone: NR/NCR/NWR/NER → Delhi; ER/ECR/ECOR/NFR/SER/SECR → Kolkata; CR/WR/WCR → Mumbai; SR/SCR/SWR → Chennai. Added `railway_zone` ENUM to contracts.

### What was built

**Migration 009 (RLS policies)** — `backend/migrations/versions/009_rls_policies.py`
- RLS for all 17 tables; `get_tenant_id()` SECURITY DEFINER function
- Three subquery patterns: `_VIA_CONTRACTS`, `_VIA_BILLS`, `_VIA_RUNS`
- `revision_snapshots`: INSERT + SELECT only — DB-enforced append-only
- Closes P1-010-ALEMBIC ✅

**Migration 010 (railway_zone)** — `backend/migrations/versions/010_railway_zone.py`
- `railway_zone` PostgreSQL ENUM with 16 zone codes
- Nullable column on `contracts` — existing rows unaffected
- P3-009 (pvc-run endpoint) must use zone to select the correct JPC city observations

**Engine: steel_tmt bucket** — `engine/types.py`, `engine/w_derivation.py`
- `BillPayload.steel_tmt_amount` added (default `Decimal("0")` for backward compat)
- `WDerivation.steel_tmt` added
- `_SUBTYPE_TO_BUCKET["tmt"]` → `"steel_tmt"` (was `"steel_other"`)
- Carry-forward additions dict and W formula both include `steel_tmt` separately

**Engine: steel_other SL4 derived formula** — `engine/components.py`
- `_STEEL_BUCKET_COMMODITY_SERIES["steel_other"]` = `["steel_tmt", "steel_angles", "steel_plates"]`
- `_steel_bucket_pvc` extended to accept `str | list[str]` — list case averages all named series for base and quarter

**Tests** — 90 passing (was 88)
- New: `test_tmt_maps_to_steel_tmt_bucket`, `test_all_four_steel_buckets`, `test_tmt_bucket_uses_steel_tmt_series`, `test_steel_other_uses_derived_avg_of_three_series`
- `test_hypothesis.py` sum identity updated to include `d.steel_tmt`

**BCT-24-25-252 bill-2 fixture** — `expected.total_pvc` corrected from `77565.84` → `76959.55`
- Q4 SL4 avg: `(56700+56800+56500)/3 = 56666.67` (GCC-correct) vs old `56900` (wrong standalone series value)
- `notes.workbook_divergence` updated to document both divergences from physical workbook

### Design decisions

1. **`steel_tmt_amount` defaults to `Decimal("0")`** — backward compat for existing API calls not yet passing TMT amounts. Engine will produce a valid result; the zero default means no TMT W subtraction until the UI passes real values.

2. **`_steel_bucket_pvc` list branch averages before computing ΔI/I₀** — the GCC formula says SL4's SB/SQ = average of SL1+SL2+SL3, not a weighted sum. The averaging is on the index values themselves, not on the PVC component results.

3. **Migration 010 is nullable** — Railway zone is not known at contract creation time in all cases (some contractors work across zones). Engine zone-awareness deferred to P3-009.

### Open items carried forward

- P2-06 (trace provenance) — still deferred, decide before Phase 7
- JPC zone-specific queries — P3-009 must use `contracts.railway_zone` to filter `index_series` by city
- RBI historical seed — Apr-2022 to Nov-2024 still missing

---

## P3-PRE-REVIEW Response — 2026-05-16 (CC-S)

### What was done

CC-S addressed all 5 P3-PRE-REVIEW findings. All CRITICAL and HIGH issues resolved before Phase 3 API starts.

| ID | Severity | Status |
|---|---|---|
| P3-PRE-01 | CRITICAL | ✅ Fixed |
| P3-PRE-02 | CRITICAL | ✅ Fixed |
| P3-PRE-03 | HIGH | ✅ Fixed |
| P3-PRE-04 | HIGH | ✅ Fixed |
| P3-PRE-05 | LOW | ✅ Fixed |

### Files changed

- `engine/types.py` — `BillPayload.steel_tmt_amount` default removed; field is now required. Omitting it raises a Pydantic `ValidationError`.
- `engine/components.py` — `_steel_bucket_pvc()` now returns an explicit error for an empty commodity-series list instead of dividing by zero.
- `engine/tests/test_calculator.py` — `_bill()` helper updated to include explicit `tmt` parameter.
- `engine/tests/test_import.py` — `BillPayload` constructor updated to include `steel_tmt_amount`.
- `engine/tests/test_components.py` — new test `test_empty_commodity_series_list_returns_error`.
- `backend/migrations/versions/011_security_hardening.py` — new migration covering:
  - P3-PRE-02: drops INSERT/UPDATE policies on `index_observations` (SELECT-only for auth users)
  - P3-PRE-03: BEFORE UPDATE trigger `trg_pvc_runs_immutable_approved` blocks mutations on Approved runs at DB layer
  - P3-PRE-04: backfills `contracts.railway_zone` NULLs → 'NR', then sets NOT NULL
- `TASKS.md` — P1-012 task added (migration 011); P3-002 updated to require `railway_zone` field in contract create API.
- `REVIEW.md` — CC-S response section added under P3-PRE-REVIEW.

### Verification

- 91 engine tests passing (90 existing + 1 new), 0 failing.
- GCC behavior preserved: TMT is SL1 (separate bucket), steel_other is SL4 (avg of SL1+SL2+SL3), Bill-2 fixture arithmetic unchanged.

### Design decisions

1. **P3-PRE-01 — remove default, don't add compatibility shim.** Phase 3 API hasn't shipped yet. Making the field required now is cleaner than a gate that would need to be removed later. All test helpers updated to pass it explicitly.

2. **P3-PRE-02 — drop policies, don't narrow them.** There is no legitimate reason for an ordinary authenticated user to write shared index history. The service role bypasses RLS, so infrastructure (seed scripts, admin ops) is unaffected.

3. **P3-PRE-03 — trigger, not policy narrowing.** The existing tenant-scoped UPDATE policy is still needed for pre-approval transitions. The trigger fires after that gate and blocks only the `Approved` case. This is belt-and-suspenders: even a service-role or direct connection cannot mutate an approved run without the trigger firing.

4. **P3-PRE-04 — backfill 'NR' as placeholder + NOT NULL.** No real contracts exist yet in dev. The 'NR' backfill is documented as a placeholder; prod deployments must correct values before running PVC calculations. The NOT NULL constraint now enforces this for all new contracts.

5. **P3-PRE-05 — minimal guard before the division.** The list branch already handles missing series; adding an empty-list check at the very top is the minimal change that prevents a silent div-by-zero.

### Open items carried forward

- P2-06 (trace provenance) — deferred, decide before Phase 7
- P3-002 `railway_zone` API validation — Phase 3 (CC-SH) must enforce 422 on missing zone
- RBI historical seed — Apr-2022 to Nov-2024 still missing

---

## Session 4 — 2026-05-16 (Parallel-track session: P2-06 trace contract + P3-REVIEW pre-flight)

### Context

Shubham working on `shubham/phase-3`. CC-S running parallel tracks that don't conflict with that branch. Two tracks landed; Phase 4 scaffolding queued for a fresh window.

### Track A — P2-06 trace provenance (CLOSED)

The only remaining MEDIUM from P2-REVIEW. Decided to **expand** rather than downgrade, ahead of P3-009 so the persisted shape is final on first write (avoids a Phase 7 schema migration).

**Design decisions (user-confirmed via AskUserQuestion):**

1. **Typed Pydantic `TraceContract`** model — not free dict. `PVCRunResult.trace: TraceContract`. Static type-checking, locked shape, `schema_version: Literal["1.0"]` for evolution.
2. **Opaque `source_ref: str | None`** added to `ExtraItemDecision` and `CarryForwardPayload`. Engine never interprets — Phase 3 fills with `bill_lines.id`, engine echoes into trace as `bill_line_ref`. Solves the engine-doesn't-know-DB-IDs constraint without coupling.
3. **Full index value echo** in `index_ref`: base month/value + quarter months/values/avg. Trace is self-contained — `revision_snapshots` is audit truth even if `index_observations` later mutates.
4. **Both top-level + annotated trace** for W: numeric `result.w_derivation` plus `trace.w_derivation` with per-line `input_field` and per-bucket carry-forward contributions.

**Files changed:**

- `engine/types.py` — added `IndexBaseValue`, `IndexQuarterValues`, `IndexRef`, `DerivedAvgIndexRef` (discriminated union via `kind`), `SteelSubComponentTrace`, `ComponentTrace`, `CarryForwardContribution`, `WDerivationLine`, `WDerivationTrace`, `CarryForwardTrace`, `ExtraItemTrace`, `TraceContract`. `source_ref` on `ExtraItemDecision` + `CarryForwardPayload`. `PVCRunResult.trace: TraceContract`.
- `engine/calculator.py` — new helpers `_build_index_ref`, `_build_derived_avg_ref`, `_build_component_trace`, `_build_w_derivation_trace`, `_build_carry_forward_traces`, `_build_extra_item_traces`. `_build_trace` now takes `rules` + `w_derivation` (may be None on pre-W block).
- `engine/tests/test_calculator.py` — 4 existing trace tests converted to attribute access; 8 new tests covering schema_version, W provenance, blocked-run W=None, single vs derived-avg commodity refs, `source_ref` echo to both `trace.carry_forwards` and `trace.w_derivation.inputs[bucket].carry_forward_contributions`, eligible-True vs eligible-False `applied_to_w_subtraction` flag.
- `REVIEW.md` — full CC-S response added under P2-06 with Phase 3 contract implications.
- `TASKS.md` — P2-06 marked closed in P2-REVIEW table, P2-011 marked done, branch-strategy header updated (P2-REVIEW gate fully cleared).

**Verification:**

- **99 tests passing (was 91), 0 failing**
- **Coverage held at 99% on `engine/` package**
- BCT-24-25-252 Bill-1/Bill-2 fixture totals unchanged (0.00 / 76959.55)
- `result.trace.model_dump(mode="json")` produces clean nested JSON — ready for `pvc_runs.trace JSONB` persistence in P3-009

**Steel bucket trace shapes:**

- `steel_tmt`, `steel_angles`, `steel_plates`: `formula="steel_bucket_pvc"`, `commodity_index_ref.kind="single"`, references the bucket's own JPC series
- `steel_other` (GCC 46A.9 SL4): `formula="steel_bucket_pvc_derived_avg"`, `commodity_index_ref.kind="derived_avg"`, `series_list=["steel_tmt","steel_angles","steel_plates"]`, with per-series `IndexRef` echoes

### Track D — P3-REVIEW checklist (PRE-FLIGHT)

Pre-wrote the adversarial checklist for Codex to run against `shubham/phase-3` once P3-001…P3-011 land. Doubles as a CC-SH self-review prompt before requesting Codex — saves one review cycle.

**Section coverage:**

- **CRITICAL (6):** tenant isolation, `railway_zone` 422, Approved pvc_runs 409 + DB trigger, no engine fallback path on validation errors, `index_observations` write-blocked, W derivation parity between API and engine
- **HIGH (7):** `source_ref` plumbing for P2-06, trace persistence to `pvc_runs.trace` JSONB + snapshot, POST /pvc-runs idempotency, decimal precision through API boundary, `paid_ratio` server-derived only, `component_weights` validation parity, JPC zone-specific snapshot construction
- **MEDIUM (4):** OpenAPI schema coverage, error response shape, `approved_by` field, rule set copy-on-write
- **LOW (3):** rate limiting, CORS, OpenAPI examples
- **Domain-correctness regression set:** BCT-24-25-252 Bill-1 + Bill-2 via the live API, `eligible=None` 422, `steel_tmt_amount` 422, `railway_zone` 422, Approved 409

Lives at the bottom of `REVIEW.md` as a stub awaiting Codex-S to fill per-finding once the branch is ready.

### Phase 3 contract implications recorded for CC-SH

- **P3-009 must persist `trace` as JSONB.** Recommend `pvc_runs.trace JSONB`; `revision_snapshots` should snapshot the full trace document.
- **P3-002/P3-007/P3-005 must plumb `bill_lines.id` as `source_ref`** when building engine payloads. Without this, Phase 7 cell-level provenance fails silently (renders without bill_line links).
- These are noted in REVIEW.md P2-06 response so Shubham sees them when reading review state.

### Open items carried forward

- **Phase 4 scaffolding (P4-003, P4-005, P4-006)** — queued for fresh window; design-quality requirement: not dated/boring, Excel-style formula bar + numeric cells where useful, polished and trustworthy
- **RBI historical seed (Apr 2022 – Nov 2024)** — Saqlain sourcing in parallel
- **JPC seed Apr 2022 – Nov 2024** — same window
- **P3-002 `railway_zone` API validation** — Phase 3 (CC-SH)

### Notes for the next CC-S window

The vault `top-of-mind.md`, `01-projects/RailPVC.md`, and `04-logs/sessions/2026-05-16.md` updated to reflect: Phase 3 gate fully clear, P2-06 closed, design philosophy locked in, Phase 4 fresh-window prompt prepared.

---

## Session 5 — 2026-05-16 (Phase 4 Track B scaffolding)

### Context

Fresh window, per the Track B brief (`tasks/track-b-phase4-scaffolding.md`). Branch: `saqlain/phase-4`. CC-SH continues `shubham/phase-3` in parallel — no overlap.

Mid-session, the 13" M2 / 8 GB box hard-froze twice from memory pressure while bringing up `next dev` + Turbopack with concurrent route probes against a heavy Electron AI IDE. No kernel panics — pure jetsam / WindowServer deadlock. Recovery + memory diagnosis written up in `tasks/lessons.md` (2026-05-16 entry). New rules for this hardware: prefer `next build && next start` over `next dev`; probe one route at a time; don't run dev concurrently with Electron AI IDEs. **This session followed those rules end-to-end.**

### What landed (P4-003 + P4-005 + P4-006 base)

**App shell — `frontend/components/shell/`:**

- `AppShell.tsx` — sidebar / header / scrollable main grid; owns `ShellStateProvider` and the `CommandPalette` portal.
- `Sidebar.tsx` — slate-900 rail, amber-600 brand, three nav items with active-state amber rail. Collapsed 52 px / expanded 220 px.
- `Header.tsx` — section breadcrumb + `#header-context-slot` (slot for per-route contract/bill/quarter chips later) + ⌘K search-palette opener with `kbd` hint.
- `CommandPalette.tsx` — `cmdk` dialog. Navigate group only in Phase 4; "Recent runs" stub for Phase 5. `g`-prefix Vim-style jumps (`g c` / `g i` / `g d`), suppressed when typing.
- `ShellState.tsx` — sidebar `auto | manual` mode (auto-collapse < 1280 px via `matchMedia`); `⌘\` toggles + pins manual; `⌘K` opens palette. Single hook surface for the shell.
- `nav.ts` — single source of truth for nav items (href, label, lucide icon, jump key).

**UI primitives — `frontend/components/ui/`:** `Button`, `Badge` (`draft|approved|superseded|blocked` variants), `EmptyState`. Small, restrained, slate-first, amber-only-as-accent.

**Routes — `frontend/app/(app)/`:**

- `(app)/layout.tsx` — wraps every authenticated page in `<AppShell>`. Note left for P4-001 auth guard.
- `(app)/contracts/page.tsx` — empty-state + a "Visual smoke-test" panel that previews badges, a tabular grid (mono right-aligned amounts, lakh-grouped INR), an Excel-style `fx` formula bar, plus throw/toast buttons exercising the error and toast plumbing. This is the AG Grid placeholder (decision below).
- `(app)/indices/page.tsx` — empty state.
- `(app)/documents/page.tsx` — empty state.
- `app/page.tsx` — redirects `/` → `/contracts`.

**Error / 404 surface:**

- `app/error.tsx` — route-level. Branded card. Next 16's reset prop is now `unstable_retry`, so the signature matches.
- `app/global-error.tsx` — last-resort root boundary.
- `app/not-found.tsx` — branded 404.

**Data layer — `frontend/lib/`:**

- `providers.tsx` — TanStack `QueryClientProvider` + `ReactQueryDevtools` (dev-only, bottom-left). `staleTime` 30s; no retry on 401/403/404/409/422.
- `api/client.ts` — typed `apiFetch<T>()`. Throws `ApiError`. Default: surface failures as Sonner toasts; `silent: true` opts a caller out for inline UI handling. Network errors → toast + `ApiError(status=0)`.
- `api/schema.ts` — empty placeholder for openapi-typescript output. `npm run gen:api` is wired to `${NEXT_PUBLIC_API_URL:-http://localhost:8000}/openapi.json` — runs the moment Shubham's FastAPI exposes the schema.
- `format.ts` — `formatINR` / `formatINRWithSymbol` using `Intl en-IN` (lakh/crore grouping).
- `cn.ts` — `clsx + tailwind-merge` helper.

**Root files modified:**

- `app/layout.tsx` — Geist Sans + Geist Mono via `next/font/google`; `Providers` wrapping; `Toaster` (Sonner, bottom-right, closeButton, richColors off).
- `app/globals.css` — `@theme inline` tokens (slate neutrals + amber-600 accent), tabular-nums on body, `.num-mono` / `.num-sans` helpers, focus-visible ring, Sonner palette overrides.
- `next.config.ts` — back to an empty config; the stray `~/package-lock.json` workaround was removed in Session 4 diagnosis.

**Dependencies added:** `@tanstack/react-query`, `@tanstack/react-query-devtools`, `sonner`, `cmdk`, `lucide-react`, `openapi-typescript` (dev), `clsx`, `tailwind-merge`.

### Verification (rails respected)

- **Type check:** `npx tsc --noEmit` — clean, 0 errors.
- **Build:** `next build` — compiled in 1.5 s, TypeScript clean, all 5 routes prerendered as static.
- **SSR markup probe:** `next start` on :3000, then `curl` one route at a time with pauses (≈6 s between requests) per the lessons-doc rules.
  - `/contracts` → `<nav class="flex-1 py-2">`, `RailPVC` brand, `Visual smoke-test` panel all present in SSR HTML.
  - `/indices` → shell nav + `Index Manager` + `Index data not loaded` empty state.
  - `/documents` → shell nav + `Document Vault` + `No documents yet` empty state.
- Server killed cleanly between probes. Memory held steady (`Pages free` 29 402 mid-run on the 8 GB box).
- **No `next dev` was run.** No concurrent route probes.

### AG Grid decision

Confirmed via `AskUserQuestion`: **defer to Phase 5.** The contracts smoke-test panel already proves the design language on tabular data (header row, mono right-aligned numbers, lakh-grouped INR, formula bar). Pulling in `ag-grid-*` (~250 KB) for a placeholder doesn't earn its weight before P5/P6 know the column shape. AG Grid theming against our CSS variables happens when the first real `ContractItem` grid is built.

### Design decisions log

Captured retrospectively in `tasks/track-b-design-decisions.md` (the original brief asked for an `AskUserQuestion` log up front; this session locked decisions inline and the live log wasn't captured). Ten sections: typeface, palette, sidebar shape, command palette, toast lib, density / numeric typography, AG Grid placeholder, error handling, TanStack Query setup, OpenAPI codegen. **Appendix added (post-commit) cross-references each option in `tasks/phase-4-design-options.html` (the four-question mockup) against the file:line where it landed — every Phase 4 decision is now traceable; deferred items (5c approve, 5d pill content, AG Grid) map to phases with the prerequisite data.**

### Open items carried forward

- **P4-001 auth client** — still blocked on P3-001 merging from `shubham/phase-3`. `(app)/layout.tsx` carries the TODO marker for where the auth guard goes.
- **P4-002 auth pages** — CC-SH task per `TASKS.md`. Not started.
- **P4-004 contract list** — needs `GET /api/contracts` live.
- **AG Grid theme tokens** — Phase 5 cost.
- **RBI / JPC seed backfill** — Apr 2022 – Nov 2024 still missing.

### Notes for the next CC-S window

Hardware rails still apply: 8 GB box + Electron AI IDE + `next dev` = deadlock. Prefer `next build && next start` for any future SSR / route verification. Don't probe routes back-to-back. See `tasks/lessons.md` (2026-05-16 entry) before opening a parallel session.
