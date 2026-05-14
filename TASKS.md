# TASKS.md — RailPVC MVP Build Plan

**Owner:** Claude Code (CC) maintains this file.
**Codex:** reads this file, acts on `[CODEX]` and `[CODEX-REVIEW]` tagged tasks, writes critique to `REVIEW.md`.
**Blocker protocol:** prepend `BLOCKED: <reason>` to the task and stop. Do not work around it.

**Stack:** Next.js 14 + TypeScript · FastAPI (Python) · Supabase (Postgres + Auth + Storage) · engine/ pure Python package

---

## Phase 0 — Scaffolding

| ID | Title | Owner | Deps | Acceptance Criteria | Domain Notes |
|---|---|---|---|---|---|
| P0-001 | Initialize Next.js 14 app (App Router, TypeScript, Tailwind) | [CC] | — | `npm run dev` starts without errors; app router structure confirmed | Use `create-next-app` with TypeScript + Tailwind |
| P0-002 | Initialize FastAPI project structure | [CC] | — | `uvicorn main:app` starts; `/health` returns 200; OpenAPI docs at `/docs` | Python 3.11+, poetry or uv for deps |
| P0-003 | Set up Supabase project (DB + Auth + Storage) | [CC] | — | Supabase project created; local `.env` has `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_KEY`; Storage bucket `documents` created | Use Supabase CLI for local dev (`supabase start`) |
| P0-004 | Initialize engine/ Python package skeleton | [CC] | — | `pip install -e ./engine` works; `from engine import calculate_pvc` importable; pytest discovers tests/ | No FastAPI deps in engine. Pure stdlib + pydantic. |
| P0-005 | Configure environment variables (.env.local, .env) | [CC] | P0-003 | All services connect to Supabase; no secrets in code | Never commit .env files |
| P0-006 | Set up local dev scripts | [CC] | P0-001–P0-005 | Single command starts frontend + backend + Supabase local emulator | Makefile or package.json script |

---

## Phase 1 — Data Model + Migrations

| ID | Title | Owner | Deps | Acceptance Criteria | Domain Notes |
|---|---|---|---|---|---|
| P1-001 | Migration: tenants, users | [CC] | P0-003 | `alembic upgrade head` applies cleanly; tables exist in Supabase | users.supabase_auth_id links to Supabase Auth uuid |
| P1-002 | Migration: contracts, schedules, contract_items | [CC] | P1-001 | Tables created with all fields from ARCHITECTURE.md data model | base_month stored as DATE (first day of month); overall_rebate as NUMERIC(5,4) |
| P1-003 | Migration: running_bills, bill_lines, recoveries | [CC] | P1-002 | Tables created; bill_lines.item_id FK to contract_items | All qty/amount fields NUMERIC(15,4) — Railway amounts up to crores |
| P1-004 | Migration: carry_forwards | [CC] | P1-003 | Table created with source/target bill FKs; paid_ratio NUMERIC(10,8) | paid_ratio = paid_qty_source / recorded_qty; constraint: 0 ≤ paid_ratio ≤ 1 |
| P1-005 | Migration: index_series, index_observations | [CC] | P1-001 | Tables created; (series_id, month) UNIQUE constraint on observations | Seed data goes in next task |
| P1-006 | Migration: pvc_rule_sets | [CC] | P1-002 | Table created; component_weights stored as JSONB | Default weights: {"labour":0.20,"plant":0.30,"fuel":0.15,"materials":0.20} for general works |
| P1-007 | Migration: pvc_runs, pvc_components, revision_snapshots | [CC] | P1-006 | Tables created; revision_snapshots has no UPDATE trigger (append-only enforced at API layer) | pvc_runs.superseded_by self-FK; NULL = active run |
| P1-008 | Migration: extra_item_decisions, documents | [CC] | P1-002 | Tables created; extra_item_decisions.(contract_id, item_id) UNIQUE | eligible NULL = undecided. This field blocks PVC runs. |
| P1-009 | Seed historical RBI/JPC index data (Jan 2022 – present) | [CC] | P1-005 | All 9 index series populated; at least 36 months of values per series; seed script is idempotent | Source: RBI WPI index publications + JPC Steel Price Index. BCT-24-25-252 base month Dec-24 must be seeded. |
| P1-010 | Supabase RLS policies (tenant isolation) — dashboard | [CC] | P1-007 | Policies written in Supabase SQL editor; SELECT/INSERT/UPDATE/DELETE on all tables filtered by tenant_id; revision_snapshots has no UPDATE policy | Apply via dashboard to learn RLS interactively before codifying |
| P1-010-ALEMBIC | Capture RLS as Alembic migration 009 | [CC] | P1-010, P3-001 | All dashboard RLS SQL transcribed into migrations/versions/009_rls_policies.py; `alembic upgrade head` applies cleanly on fresh DB | **Trigger:** immediately before Phase 3 starts (auth middleware build). Not deferred past P3-001. |

---

## Phase 2 — Calculation Engine

| ID | Title | Owner | Deps | Acceptance Criteria | Domain Notes |
|---|---|---|---|---|---|
| P2-001 | Define Pydantic types: BillPayload, IndexSnapshot, PVCRuleSet, PVCRunResult | [CC] | P0-004 | All types importable; serialization round-trips without loss; type stubs pass mypy | See ARCHITECTURE.md engine interface section |
| P2-002 | Implement W derivation: cement bucket subtraction | [CC] | P2-001 | Unit tests: W reduces by exact cement amount; zero cement = no change | Cement amount comes from bill lines tagged is_cement_item — rate build-up (DSR → schedule escalation → discount → rebate) is pre-calculated before reaching engine |
| P2-003 | Implement W derivation: steel bucket subtraction (angles, plates, other) | [CC] | P2-002 | Unit tests: W reduces by sum of three buckets independently; subtype breakdown preserved | Each steel subtype maps to its own JPC index series — keep them separate through the whole pipeline |
| P2-004 | Implement W derivation: extra-item exclusion | [CC] | P2-003 | If any ExtraItemDecision.eligible is None in payload → validation_error returned, no W computed | This is the most common silent error in the domain. Never default to included or excluded. |
| P2-005 | Implement carry-forward proration (paid_ratio, per-bill allocation) | [CC] | P2-003 | Unit test: item 10.2 BCT-24-25-252 case — recorded 6172.57, paid 5600, ratio 0.9072. First bill bucket = total × ratio; carry = total × (1 − ratio) | ProRation must be applied before the steel bucket is subtracted from W |
| P2-006 | Implement quarter resolver (measurement_date → quarter → 3-month average) | [CC] | P2-001 | Unit tests: measurement_date 2025-05-15 → Q1 FY2025-26 → avg(Apr-25, May-25, Jun-25); base_month Dec-24 → base = Dec-24 value | **DOMAIN RISK**: quarter interpretation (measurement_date vs execution_period) must be confirmed with Saqlain before this ships. Default: measurement_date. |
| P2-007 | Implement component formula: general W components | [CC] | P2-006 | Unit tests: PVC_component = W × weight × (Qavg − base) / base for labour(0.20), plant(0.30), fuel(0.15), materials(0.20) | Weights must come from rules input, not hardcoded |
| P2-008 | Implement component formula: cement sub-formula | [CC] | P2-007 | Unit test: PVC_cement = cement_amount × 0.85 × (Qavg_cement − base_cement) / base_cement | Weight for cement is 0.85 (85% adjustable, 15% fixed) |
| P2-009 | Implement component formula: steel bucket sub-formulas | [CC] | P2-008 | Unit tests per subtype: each bucket gets labour(0.10) + steel_commodity(0.50) + plant(0.10) + fuel(0.10) + materials(0.05) = 0.85 adjustable | Steel commodity index is subtype-specific: angles → JPC angles index, plates → JPC plates index |
| P2-010 | Implement run validation: block on missing indices or undecided extra items | [CC] | P2-009 | Test: missing index for any required month → validation_error; undecided extra_item → validation_error; all present → no error | Validation runs before any calculation. Return errors list; if non-empty, return early with no computed values |
| P2-011 | Implement trace tree generation | [CC] | P2-010 | Every field in PVCRunResult.trace points to its source: {input_field, formula, index_ref, bill_line_ref} | Required for cell-level provenance in Phase 2+. Build the structure now even if UI doesn't use it yet |
| P2-012 | pytest unit tests: all engine functions, 80%+ coverage | [CC] | P2-011 | `pytest engine/tests/ --cov=engine --cov-report=term` shows ≥80% | Fixtures: BCT-24-25-252 real values from workbook. Every edge case (zero cement, all-steel bill, carry-forward, negative PVC) must have a test |
| P2-013 | Hypothesis property tests: W derivation invariants | [CC] | P2-012 | Properties: W ≤ on_account_amount; W ≥ 0 if no negative inputs; sum of subtractions + W == on_account_amount | Use hypothesis to generate random BillPayload values |
| **P2-REVIEW** | **Adversarial engine review** | **[CODEX-REVIEW]** | P2-001–P2-013 | REVIEW.md updated with numbered critique. Check: silent defaults in W derivation, missing error states, formula invariants, carry-forward edge cases, quarter boundary ambiguity, negative PVC handling | **This checkpoint blocks Phase 3 start.** CC must respond to all CRITICAL/HIGH issues before proceeding. |

---

## Phase 3 — API Layer

| ID | Title | Owner | Deps | Acceptance Criteria | Domain Notes |
|---|---|---|---|---|---|
| P3-001 | Auth middleware: Supabase JWT validation + tenant context | [CC] | P0-002, P1-010 | All protected routes return 401 without valid token; tenant_id extracted from JWT and injected into request context | Use Supabase's `auth.users` table; tenant_id must be on every DB query |
| P3-002 | Contracts CRUD endpoints | [CC] | P3-001 | POST/GET/PUT /api/contracts work; validation errors return 422; tenant isolation confirmed | base_month stored as first-of-month date |
| P3-003 | Schedules + ContractItems endpoints | [CC] | P3-002 | CRUD for schedules and items under a contract; item classification fields (is_cement_item, steel_subtype) validated | steel_subtype must be one of: NULL, angles, plates, other_sections, tmt |
| P3-004 | Bills + BillLines + Recoveries endpoints | [CC] | P3-002 | Bill creation validates contract exists and belongs to tenant; bill_lines have correct cumulative/incremental split | Quantities stored as NUMERIC(15,4); never round on ingestion |
| P3-005 | CarryForward endpoints | [CC] | P3-004 | GET returns carry-forwards for a contract; PUT updates paid_qty and recalculates paid_ratio; invalid ratio rejected | paid_ratio recomputed server-side from paid_qty/recorded_qty — never accepted from client |
| P3-006 | IndexSeries + IndexObservation endpoints | [CC] | P1-005 | GET index-observations supports ?series_id=&from=&to= query; POST validates month format; duplicate (series_id, month) rejected | Include revision_flag and revised_at in responses |
| P3-007 | ExtraItemDecision endpoints | [CC] | P3-003 | POST/PUT per item; NULL eligible is valid (undecided); GET returns all decisions for a contract with item details | Undecided items must be surfaced clearly — they block PVC runs |
| P3-008 | PVCRuleSet endpoints | [CC] | P3-002 | GET/PUT for a contract's rule set; component_weights must sum to ≤ 1.0 per classification group; validated | Default weights auto-created on contract creation |
| P3-009 | POST /pvc-runs: validate, call engine, persist result + snapshot | [CC] | P3-001–P3-008, P2-013 | Collects bill payload + index snapshot from DB; calls engine.calculate_pvc(); if validation_errors → 422; if success → persists run + components; creates revision_snapshot | Engine call is synchronous in MVP. If too slow, move to background job in Phase 2. |
| P3-010 | POST /pvc-runs/{id}/approve: immutability enforcement | [CC] | P3-009 | Approved run: status set to Approved, approved_by/at recorded; subsequent PUT attempts return 409 Conflict; revision_snapshot confirmed written | Test: attempt to modify approved run → must fail with 409 |
| P3-011 | Document upload endpoint (Supabase Storage) | [CC] | P0-003, P3-001 | POST /api/contracts/{id}/documents accepts multipart; stores to Supabase Storage under tenant/{contract_id}/; returns storage_path | Max 50MB per file. No parsing in v1 — store only. |
| **P3-REVIEW** | **Adversarial API review** | **[CODEX-REVIEW]** | P3-001–P3-011 | REVIEW.md updated. Check: auth gaps, missing tenant validation, API shapes that force awkward frontend patterns, missing error states, immutability enforcement correctness | **This checkpoint blocks Phase 4 start.** |

---

## Phase 4 — Frontend Shell + Navigation

| ID | Title | Owner | Deps | Acceptance Criteria | Domain Notes |
|---|---|---|---|---|---|
| P4-001 | Next.js App Router setup with Supabase Auth client | [CC] | P0-001, P3-001 | `createClient` from `@supabase/ssr` configured; session refresh works; protected routes redirect to login | Use `@supabase/ssr` not deprecated `@supabase/auth-helpers-nextjs` |
| P4-002 | Auth pages: login, signup | [CODEX] | P4-001 | Email/password login and signup work against Supabase Auth; session cookie set; redirects to dashboard on success | Simple form components — Codex generation task |
| P4-003 | App shell: sidebar navigation, header, layout | [CC] | P4-001 | Navigation renders with: Contracts, Index Manager, Document Vault links; active route highlighted; layout wraps all protected pages | — |
| P4-004 | Contract list dashboard page | [CC] | P4-003, P3-002 | Fetches and displays contract list; loading/empty/error states; link to contract detail | Show: contract name, status, base_month, bill count |
| P4-005 | Error boundary and global error handling | [CC] | P4-001 | Unhandled errors show user-friendly message, not stack trace; API errors surfaced as toast notifications | — |
| P4-006 | TanStack Query setup + typed API client | [CC] | P4-001 | `QueryClientProvider` wrapped at root; typed fetch functions for all API endpoints; invalidation patterns defined | Generate types from FastAPI OpenAPI schema (`openapi-typescript`) |

---

## Phase 5 — Contract Setup UI

| ID | Title | Owner | Deps | Acceptance Criteria | Domain Notes |
|---|---|---|---|---|---|
| P5-001 | Contract creation form | [CODEX] | P4-006, P3-002 | Form with all contract fields; validation; submits and redirects to contract detail; error states shown | Fields: tender_number, agreement_number, loa_number, loa_date, base_month, completion_date, overall_rebate, gst_mode, pvc_applicable |
| P5-002 | Schedule configuration UI | [CODEX] | P5-001 | Add/edit/delete schedules A/B/C; type (DSR/NS/ExtraNS) and discount fields; changes persist | — |
| P5-003 | ContractItem table (AG Grid, editable) | [CODEX] | P5-002 | AG Grid table with inline editing; is_cement_item toggle; steel_subtype dropdown; import from CSV stub (no parsing) | Columns: item_code, description, unit, original_qty, base_rate, agreement_rate, schedule, is_cement_item, steel_subtype |
| P5-004 | PVC rule configuration form | [CC] | P5-001 | Component weights form with validation (must sum correctly per group); quarter_mode selection; negative_pvc_policy | This is correctness-critical — CC owns it, not Codex |
| P5-005 | Extra-item eligibility decision UI | [CC] | P5-003 | For each item marked as extra (Schedule C/ExtraNS): show Eligible/Not Eligible/Undecided toggle; undecided items highlighted in red; count shown on contract header | Undecided items must be impossible to miss — they block PVC runs |
| P5-006 | Document vault upload UI | [CODEX] | P4-006, P3-011 | Drag-and-drop or file picker; upload to Supabase Storage; show upload list with file_type selector; no parsing in v1 | File types: agreement, mb, bill, recovery, workbook, other |

---

## Phase 6 — Bill Entry UI

| ID | Title | Owner | Deps | Acceptance Criteria | Domain Notes |
|---|---|---|---|---|---|
| P6-001 | Bill creation form + bill list | [CODEX] | P4-006, P3-004 | Form: bill_number, bill_date, measurement_date, gross_amount, net_amount; list shows all bills for contract | measurement_date is the date used for quarter resolution — must be labeled clearly |
| P6-002 | BillLine entry table (AG Grid) | [CC] | P6-001 | AG Grid with inline editing; qty_up_to_last (read-only if prior bill exists), qty_since_last (editable), qty_up_to_date (computed); amount fields | This table is the core data entry screen — CC owns it. Spreadsheet-feel is non-negotiable. |
| P6-003 | Recovery entry table | [CODEX] | P6-001 | Tabular entry: recovery_type, amount, affects_pvc_base toggle; totals row | — |
| P6-004 | CarryForward management UI | [CC] | P6-002 | Show items with recorded_qty > paid_qty; edit paid_qty; paid_ratio auto-computed; carry_qty displayed; shows which bill the carry resolves in | This screen must make carry-forward visible and explicit — it's the #1 source of silent errors in Excel |
| P6-005 | W derivation preview panel | [CC] | P6-003, P6-004 | Live preview: shows W = OnAccount - Cement - SteelAngles - ... for current bill state; highlights missing decisions (undecided extra items, unresolved carry-forwards) | Drives user confidence before triggering PVC run |

---

## Phase 7 — PVC Run + Results UI

| ID | Title | Owner | Deps | Acceptance Criteria | Domain Notes |
|---|---|---|---|---|---|
| P7-001 | Index management screen | [CC] | P4-006, P3-006 | Table of index observations per series; monthly view; edit existing values; add new month; revision_flag indicator | Pre-seeded values display correctly; user can add current month |
| P7-002 | PVC run builder | [CC] | P5-004, P5-005, P7-001, P3-009 | Shows precondition checklist (all extra items decided, all required indices present, bill reconciled); triggers run; shows validation errors clearly if blocked | Never let user click "Calculate" and get a silent wrong number. Block with explicit list of what's missing. |
| P7-003 | PVC results view | [CC] | P7-002 | Component-wise breakdown table: category, eligible_amount, base_index, current_avg, weight, pvc_value; W derivation breakdown; total PVC; quarter used | This is the primary trust-building screen. Must match the layout operators recognize from their Excel workbooks. |
| P7-004 | Approval flow | [CC] | P7-003, P3-010 | "Approve & Lock" button; confirmation dialog; run status updates to Approved; all edit buttons disabled; supersede button available | Immutability must be visually obvious after approval |
| P7-005 | PVC run history + superseding chain | [CC] | P7-004 | List of all runs for a bill; active run highlighted; superseded runs shown with link to superseding run; status badges | — |

---

## Phase 8 — Export Layer

| ID | Title | Owner | Deps | Acceptance Criteria | Domain Notes |
|---|---|---|---|---|---|
| P8-001 | Excel export: bill-style PVC sheet (openpyxl) | [CC] | P3-009 | Generated Excel matches BCT-24-25-252 workbook layout: Front Page, Index, Second Page, Cement, Steel, Bill-N sheets; values match engine output exactly | Test against known values from sample workbook. This is the adoption gate — field accounts must recognize the format. |
| P8-002 | PDF export: print pack (WeasyPrint) | [CC] | P8-001 | PDF generated from approved run; covers summary + component breakdown + W derivation; printable A4 | — |
| P8-003 | Export download in frontend | [CC] | P8-001, P8-002 | Download buttons on results view; triggers API; download starts immediately; loading state shown | — |
| **P8-REVIEW** | **Export format parity review** | **[CODEX-REVIEW]** | P8-001–P8-003 | REVIEW.md updated. Review Excel output against BCT-24-25-252 workbook: column headers, sheet structure, formula trace, numerical precision | Codex should verify sample values match manually. |

---

## Phase 9 — Integration + Testing

| ID | Title | Owner | Deps | Acceptance Criteria | Domain Notes |
|---|---|---|---|---|---|
| P9-001 | E2E test: contract setup → bill entry → PVC run → export | [CC] | Phase 8 complete | Full flow with BCT-24-25-252 sample data produces correct PVC output; export downloads successfully | Use Playwright |
| P9-002 | Engine regression tests: BCT-24-25-252 sample values | [CC] | P2-012 | engine.calculate_pvc() with real workbook inputs produces exact values from the PVC sheet (Bill-1 and Bill-2) | Pin expected values from workbook. These must never change silently. |
| P9-003 | Snapshot immutability tests | [CC] | P7-004 | Approved run: PUT attempt on run returns 409; revision_snapshot row count = 1 after approval; second approval creates new superseding run | — |
| **P9-DEBUG** | **Second-pass debugging** | **[CODEX]** | P9-001–P9-003 | Run full test suite; identify calculation edge cases not covered (zero-bill, all-extra-items, negative PVC, carry-forward across 3 bills); write failing tests for each; report in REVIEW.md | Codex should specifically look for cases where the engine produces a plausible-but-wrong number rather than an error |

---

## Known Unknowns (Block Before Engine Ships)

These require Saqlain's domain confirmation before the relevant task can be completed:

| ID | Question | Blocks | Status |
|---|---|---|---|
| KU-001 | Quarter mapping: is measurement_date correct, or does it vary by Railway zone? | P2-006 | **CONFIRMED 2026-05-14**: Use "To" date of MB period. Calendar Qs (Q1=Jan-Mar, Q2=Apr-Jun, Q3=Jul-Sep, Q4=Oct-Dec), FY label Apr-Mar. Format: Q2-FY2025-26. |
| KU-002 | Schedule C extra NS items in 2nd bill of BCT-24-25-252 — intentionally included or spreadsheet error? | P2-004 | **CONFIRMED 2026-05-14**: Extra NS items included in on-account amount, then explicitly subtracted from W. ~16L yellow-highlighted items are eligible=False. Engine blocks on eligible=None. |
| KU-003 | Treatment of negative PVC: recover from next bill, or immediate offset? | P2-007 | **CONFIRMED 2026-05-14**: Zero-floor this bill; carry negative_carry_forward forward for recovery from next bill's PVC total. |

---

## Legend

- `[CC]` — Claude Code owns this task
- `[CODEX]` — Codex generation task (UI components, test boilerplate)
- `[CODEX-REVIEW]` — Adversarial review checkpoint by Codex; outputs go to `REVIEW.md`
- `BLOCKED: <reason>` — Task is blocked; do not proceed until resolved
