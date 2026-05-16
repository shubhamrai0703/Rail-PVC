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
