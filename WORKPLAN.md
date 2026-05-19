# WORKPLAN.md — Saqlain + Shubham Session Reference

**Last updated:** 2026-05-19  
**Status snapshot:** Phases 0–4 + TEST-P3P4 all merged to `main`. Phase 5 UI starting (Saqlain); GET bill endpoints + export backend starting (Shubham, parallel).

This document is the single place to see what we are building, in what order, who owns each step, and what "done" looks like for each task. TASKS.md stays the canonical board; this document adds the detail that was missing.

---

## How to Read This Document

- **Owner tags:** `[S]` = Saqlain · `[SH]` = Shubham
- **Status tags:** `pending` · `in-progress` · `complete` · `BLOCKED`
- Each task has: goal → exact deliverables → acceptance criteria → dependencies
- Do not start a task if its dependency row isn't `complete`

---

## Parallel Tracks Right Now

Two branches should be open simultaneously:

| Branch | Owner | Work |
|---|---|---|
| `saqlain/phase-5` | [S] | Frontend-only: contract setup UI (B-1…B-5) |
| `shubham/phase-5-backend` | [SH] | Backend-only: GET bill endpoints + export routes (SH-P5-1…7) |

These are independent — Shubham's branch touches `backend/api/` only; Saqlain's branch touches `frontend/` only.

---

## TRACK A — Phase 3 Backfill Endpoints `[SH]`

### Context

The main API routers (`contracts.py`, `bills.py`) were written and reviewed in Phase 3. Four endpoint groups were deferred. The patterns are already established — copy them, don't invent new ones.

**Reference files to read before writing any code:**
- `backend/api/contracts.py` — tenant check pattern, Pydantic response schema pattern
- `backend/api/bills.py` — `create_bill_line` for the recoveries pattern
- `backend/models/` — all SQLAlchemy model definitions
- PR #3 description — explicit copy guidance

---

### A-1: `POST /api/contracts/{id}/schedules` + `GET /api/contracts/{id}/schedules`

**Goal:** Allow creating and listing schedules under a contract.

**Deliverables:**
- New router file `backend/api/schedules.py` (or add to `contracts.py` — match existing pattern)
- Pydantic request schema: `ScheduleCreate { name: str, schedule_type: Literal["DSR","NS","ExtraNS"], bid_discount_pct: Decimal }`
- Pydantic response schema: `ScheduleOut { id, contract_id, name, schedule_type, bid_discount_pct, created_at }`
- `POST` — creates row, returns `201 + ScheduleOut`
- `GET` — returns `list[ScheduleOut]` filtered to contract
- Tenant check: verify `contract.tenant_id == jwt_tenant_id` before any write/read (copy from `contracts.py`)
- Registered in `main.py`

**Acceptance criteria:**
- `pytest backend/tests/` green
- `GET /api/contracts/{id}/schedules` returns `[]` for a new contract, correct rows after POST
- A request with a contract belonging to a different tenant returns `403`

**Dependency:** None — patterns already on `main`

---

### A-2: `POST /api/schedules/{id}/items` + `GET /api/contracts/{id}/items`

**Goal:** Allow adding contract line items to a schedule and listing all items on a contract.

**Deliverables:**
- Router (in `schedules.py` or `contract_items.py`)
- Pydantic request schema: `ContractItemCreate { item_code, description, unit, original_qty, revised_qty, base_rate, agreement_rate, is_cement_item: bool, steel_subtype: Optional[Literal["angles","plates","other_sections","tmt"]] }`
- Pydantic response schema: `ContractItemOut { id, contract_id, schedule_id, ...all fields..., created_at }`
- `POST /api/schedules/{id}/items` — parent check: `schedule.contract.tenant_id == jwt_tenant_id`; use `assert_schedule_belongs_to_tenant` helper (create if not exists, following `assert_*` pattern from existing code)
- `GET /api/contracts/{id}/items` — return all items across all schedules for contract, tenant-checked
- Registered in `main.py`

**Acceptance criteria:**
- Parent-child tenant isolation: posting to a schedule owned by another tenant returns `403`
- `steel_subtype` accepts only the four valid enum values or `null`
- `pytest` green

**Dependency:** A-1 complete (schedules must exist for items to attach to)

---

### A-3: `POST /api/bills/{id}/recoveries`

**Goal:** Allow recording recoveries (deductions) against a bill.

**Deliverables:**
- Add route to `backend/api/bills.py` (it already has bill endpoints — add here)
- Pydantic request schema: `RecoveryCreate { recovery_type: Literal["security_deposit","income_tax","labour_cess","water","other"], amount: Decimal, affects_pvc_base: bool = False }`
- Pydantic response schema: `RecoveryOut { id, bill_id, recovery_type, amount, affects_pvc_base, created_at }`
- `POST` — tenant check via bill → contract; returns `201 + RecoveryOut`
- Optional: `GET /api/bills/{id}/recoveries` — return list (needed by Phase 6 bill entry UI)

**Acceptance criteria:**
- Wrong-tenant attempt → `403`
- `pytest` green

**Dependency:** None — `bills.py` already exists

---

### A-4: `POST /api/contracts/{id}/documents` + `GET /api/contracts/{id}/documents`

**Goal:** Allow uploading and listing documents (PDF/Excel) attached to a contract.

**Deliverables:**
- New router file `backend/api/documents.py`
- `POST` — multipart upload; save to Supabase Storage bucket `contract-documents/{tenant_id}/{contract_id}/{uuid}_{original_filename}`; insert row into `documents` table; return `DocumentOut`
- `GET` — list rows from `documents` filtered to contract, return `list[DocumentOut]`
- Pydantic response schema: `DocumentOut { id, contract_id, file_type, storage_path, original_filename, uploaded_at }`
- File size limit: 50 MB (enforce at upload handler, not client)
- No parsing — store only
- Registered in `main.py`

**Acceptance criteria:**
- File > 50 MB → `413` response
- Wrong-tenant contract → `403`
- Uploaded file is retrievable at the storage path returned
- `pytest` green (can mock Supabase Storage client in tests)

**Dependency:** None

---

### A-REVIEW: PR Checkpoint

Once A-1 through A-4 are complete:
1. Open PR `shubham/phase-3-backfill` → `main`
2. Codex-S runs adversarial review (`P3-BF-REVIEW` in TASKS.md)
3. No merge until review passes

---

## TRACK B — Phase 5: Contract Setup UI `[S]`

### Context

The backend `POST /api/contracts` and `GET /api/contracts` are already live on `main`. Phase 4 built the contract list page (`/contracts`). Phase 5 builds the creation form and the contract detail/configuration view.

---

### B-1: Contract Creation Form

**Goal:** Let a user create a new contract from the UI.

**Deliverables:**
- New page: `frontend/app/(app)/contracts/new/page.tsx`
- Form fields (all required unless noted):
  - `tender_number` (text)
  - `agreement_number` (text)
  - `loa_number` (text)
  - `loa_date` (date picker)
  - `contractor_name` (text)
  - `work_description` (textarea)
  - `contract_value` (number)
  - `bid_amount` (number)
  - `start_date` (date picker)
  - `completion_date` (date picker)
  - `base_month` (month picker — format `YYYY-MM`)
  - `gst_mode` (select: `inclusive` / `exclusive`)
  - `pvc_applicable` (checkbox, default true)
  - `overall_rebate` (number, optional, default 0)
- On submit: `POST /api/contracts` via `apiFetch` (existing typed client in `lib/api/client.ts`)
- On success: redirect to `/contracts/{id}` (detail page, created in B-2)
- On error: display inline error using the `ApiError` pattern from P4-007

**Acceptance criteria:**
- Form validation before submit (required fields, number format, date order: start < completion)
- `base_month` must be before `start_date` (warn user if not)
- Successful POST → user lands on the new contract's detail page
- API error codes mapped to human-readable messages (reuse toast/error logic from `lib/api/client.ts`)

**Dependency:** Phase 4 complete (already is)

---

### B-2: Contract Detail Page (Read View)

**Goal:** Show all contract metadata after creation or when navigating from the list.

**Deliverables:**
- New page: `frontend/app/(app)/contracts/[id]/page.tsx`
- Fetches `GET /api/contracts/{id}` via TanStack Query
- Displays all fields in a structured read layout (not a form — display view first)
- Tab or section structure for later expansion (Phase 5 will add Schedules tab; Phase 6 will add Bills tab)
- "Edit" button (can be a stub that opens inline edit — or defer editing to B-3)
- "Add Schedule" button (stub for B-4)

**Acceptance criteria:**
- Navigation from contract list row → detail page works
- Redirect after B-1 creation lands here correctly
- 404 or wrong-tenant contract → show error state, not a crash

**Dependency:** B-1

---

### B-3: Contract Edit (inline or modal)

**Goal:** Allow updating contract metadata.

**Deliverables:**
- Reuse the form from B-1 (same fields, pre-populated)
- `PUT /api/contracts/{id}` on submit
- Can be inline on the detail page or a modal — pick the simpler option

**Dependency:** B-2

---

### B-4: Schedule Management on Contract Detail

**Goal:** Let the user add and view schedules within the contract detail page.

**Deliverables:**
- Section on `contracts/[id]/page.tsx` (or a sub-page `contracts/[id]/schedules/`)
- "Add Schedule" form: `name`, `schedule_type` (DSR/NS/ExtraNS), `bid_discount_pct`
- POST to `POST /api/contracts/{id}/schedules` (will be live once A-1 merges)
- List existing schedules with row-level "Add Items" navigation

**Dependency:** B-2 complete; A-1 merged to `main`

---

### B-5: Contract Items Grid on Schedule

**Goal:** Let the user add line items to a schedule.

**Deliverables:**
- Sub-page or panel: `contracts/[id]/schedules/[schedule_id]/items` (or inline in detail)
- AG Grid editable table for bulk item entry
- Columns: `item_code`, `description`, `unit`, `original_qty`, `revised_qty`, `base_rate`, `agreement_rate`, `is_cement_item` (checkbox), `steel_subtype` (dropdown)
- On save: POST each row to `POST /api/schedules/{id}/items`
- Consider batch: POST rows one at a time in sequence (no bulk endpoint in v1)

**Dependency:** B-4 complete; A-2 merged to `main`

---

## TRACK C — Phase 6: Bill Entry UI `[S]`

> Start only after B-2 is stable. B-5 and A-3 should be complete before C-3.

### C-1: Bill List on Contract Detail

**Deliverables:**
- Bills section on `contracts/[id]/page.tsx`
- Fetches `GET /api/contracts/{id}/bills`
- List with bill number, date, status, gross amount
- "Create Bill" button

**Dependency:** B-2

---

### C-2: New Bill Form

**Deliverables:**
- Page: `contracts/[id]/bills/new/page.tsx`
- Fields: `bill_number`, `bill_date`, `measurement_date`, `gross_amount`, `net_amount`
- POST to `POST /api/contracts/{id}/bills`
- Redirect to bill detail page on success

**Dependency:** C-1

---

### C-3: Bill Lines Entry (AG Grid)

**Goal:** AG Grid spreadsheet-style entry for bill lines — quantities by item.

**Deliverables:**
- Page: `contracts/[id]/bills/[bill_id]/page.tsx`
- AG Grid table: rows = contract items; columns = `qty_up_to_last`, `qty_since_last`, `qty_up_to_date`, computed amounts (read-only derived columns)
- Save: POST each modified row to `POST /api/bills/{id}/lines`
- Recoveries section below the grid (uses A-3 endpoint)

**Dependency:** C-2; A-2 + A-3 merged to `main`

---

## TRACK D — Phase 7: PVC Run + Results UI `[S]`

> Start only after C-3 is stable.

### D-1: PVC Rule Configuration

**Deliverables:**
- Section on contract detail: component weights, quarter mode, negative PVC policy, rounding mode
- `GET /api/contracts/{id}/pvc-rule-set` to load
- `PUT /api/contracts/{id}/pvc-rule-set` to save
- Weight inputs must sum to 1.0 — validate client-side and show running total

---

### D-2: Extra-Item Eligibility Decisions

**Deliverables:**
- Section on contract detail: list of extra-item contract items (where `schedule_type = 'ExtraNS'`)
- For each item: `eligible` toggle (Yes / No / Undecided)
- Undecided items show a warning: "PVC run will be blocked until all extra items are decided"
- POST/PUT to `extra-item-decisions` endpoints

---

### D-3: Trigger PVC Run

**Deliverables:**
- "Run PVC" button on bill detail page
- `POST /api/contracts/{id}/pvc-runs` with `bill_id`
- Handle validation errors from engine (display `validation_errors` list from `PVCRunResult`)
- Show run results: W derivation breakdown, per-component table, total PVC

---

### D-4: Approve Run

**Deliverables:**
- "Approve" button on PVC run result view (only visible in `Calculated` status)
- `POST /api/pvc-runs/{id}/approve`
- After approval: run becomes read-only; show immutability indicator

---

## TRACK E — Phase 8: Export `[S]`

> Start only after D-4 is complete.

### E-1: Excel Export

- "Export Excel" button on approved PVC run
- `GET /api/pvc-runs/{id}/export/excel` → download file
- Format must match contractor submission workbook layout (defined in `engine/` export module)

### E-2: PDF Print Pack

- "Print PDF" button on approved PVC run
- `GET /api/pvc-runs/{id}/export/pdf`
- HTML → PDF via WeasyPrint on the backend

---

## TRACK F — Phase 9: Integration + Testing `[S]` + `[SH]`

### F-1: Backend Test Suite Fix `[S]`

> This is a blocker for the next review cycle regardless of other tracks.

**Problem:** `services/auth.py` now validates Supabase JWKS/ES256 tokens. The existing `backend/tests/` mint HS256 test tokens and will fail against the live auth middleware.

**Deliverables:**
- Update test fixtures to generate or mock ES256 tokens correctly
- OR introduce a `TEST_MODE` bypass that validates a static test header (discuss with Saqlain before implementing — security implication)
- All 31 existing backend tests green with real auth path

---

### F-2: E2E Smoke Tests `[SH]`

- Playwright tests for the critical path: signup → create contract → add schedule → add items → create bill → enter lines → run PVC → approve → export Excel
- Run against local dev stack

---

### F-3: Index Seed Verification `[S]`

- Confirm RBI/JPC historical index values (2022–present) are correctly seeded
- Spot-check: one known quarter calculation vs. manual computation

---

## TRACK G — SH-P5: GET Bill Endpoints + Export Backend `[SH]`

> Parallel to Track B (Phase 5 UI). Branch: `shubham/phase-5-backend`. All routes go in `backend/api/bills.py` (GET endpoints) or `backend/api/pvc_runs.py` (exports). Follow the tenant-check pattern in existing POST routes.

---

### G-1: GET Bill List + Detail

**Goal:** Expose read endpoints for bills so Phase 6 UI can list and view bills.

**Deliverables:**
- `GET /api/contracts/{contract_id}/bills` — list bills; returns `list[BillOut]`; tenant-checked via contract
- `GET /api/bills/{bill_id}` — single bill; returns `BillOut`; tenant-checked via bill→contract
- Add to `backend/api/bills.py` (existing file)
- `BillOut` schema if not already defined: `{ id, contract_id, bill_number, bill_date, measurement_date, gross_amount, net_amount, status, created_at }`

**Acceptance criteria:**
- Empty list (not 404) when no bills exist for a contract
- Wrong-tenant contract → `NotFoundProblem(404)` (not 403 — don't leak existence)
- `pytest backend/tests/` green including new tests for these routes

---

### G-2: GET Bill Lines + Recoveries

**Goal:** Expose line items and recoveries for the bill detail / AG Grid view in Phase 6.

**Deliverables:**
- `GET /api/bills/{bill_id}/lines` — returns `list[BillLineOut]`; tenant-checked via line→bill→contract
- `GET /api/bills/{bill_id}/recoveries` — returns `list[RecoveryOut]`; tenant-checked
- Add to `backend/api/bills.py`

**Acceptance criteria:**
- Same tenant-isolation rules as G-1
- `pytest` green; include wrong-tenant test for each route

**Dependency:** G-1

---

### G-3: Export Endpoints (Excel + PDF)

**Goal:** Allow downloading approved PVC run results.

**Context:** Check `engine/engine/` for existing export logic before writing routes. The engine may already have `export_excel` / `export_pdf` functions — wire them, don't rewrite.

**Deliverables:**
- `GET /api/pvc-runs/{run_id}/export/excel` — calls engine export; returns `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` download
- `GET /api/pvc-runs/{run_id}/export/pdf` — HTML→PDF via WeasyPrint; returns `application/pdf`
- Both routes: tenant-check via run→contract; must be `status = "Approved"` or return `422` with `detail.code = "run_not_approved"`
- Add to `backend/api/pvc_runs.py`

**Acceptance criteria:**
- Unapproved run → `422 run_not_approved`
- Wrong-tenant run → `404`
- Response headers: `Content-Disposition: attachment; filename="pvc_run_{id}.xlsx"` (and `.pdf`)
- `pytest` green

**Dependency:** G-1 + G-2

---

## Ordering Summary

```
Right now (parallel):
  Track B  →  B-1, B-2, B-3, B-4, B-5  (Saqlain, frontend only)
  Track G  →  G-1, G-2, G-3             (Shubham, backend only)

Note: A-1 and A-2 are already merged (POST schedules + POST items).
B-4 and B-5 are already unblocked.

After G-1 merges:
  C-1 (bill list) unblocked

After G-1 + G-2 merge + C-2 done:
  C-3 (bill lines AG Grid) unblocked

After B-2 done:
  C-1 unblocked (frontend side)

After C-3 done:
  D-1, D-2 unblocked (can be parallel)

After D-1 + D-2 done:
  D-3 unblocked

After D-3 done:
  D-4 unblocked

After D-4 done:
  E-1, E-2 unblocked (can be parallel)

After all tracks:
  F-1, F-2, F-3 (integration + cleanup)
```

---

## Open Questions / Decisions Needed

| # | Question | Who decides | Urgency |
|---|---|---|---|
| OQ-1 | Backend test suite: proper ES256 mock vs. TEST_MODE bypass? | Saqlain | **Closed** — TEST-04 confirmed all tests use dep overrides, no token minting needed |
| OQ-2 | B-5 items grid: save on cell-edit (per row) or explicit "Save all" button? | Saqlain | Medium — before B-5 starts |
| OQ-3 | D-2 extra-item UI: inline on contract detail or separate page? | Saqlain | Low — before D-2 starts |
| OQ-4 | Credential hygiene: new DB password + JWT secret in `.env` only — is onboarding doc needed for Shubham? | Saqlain | Medium |
