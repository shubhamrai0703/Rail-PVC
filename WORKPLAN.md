# WORKPLAN.md — RailPVC Implementation Plan

**Last updated:** 2026-05-30 (Session 21 — PR catch-up + IDX-2..3)
**Status snapshot:** Phases 0–5 + SH-P5 G-1/G-2 + all P5-FUP findings + IDX-2..3 on `main`. **Phase 6 C-1 + C-2 on `saqlain/phase-6` (2026-05-31)** — awaiting smoke + P6-REVIEW; C-3 pending. Suite: **106/106 backend**, 99/99 engine, 16/16 frontend vitest, `next build` + lint clean. Route count 38. Migration head: 013.

---

## Resolved Bugs

| # | Bug | Resolution |
|---|-----|------------|
| BUG-1 | `POST /api/contracts/{id}/schedules` → 500 Internal Server Error. Root cause: `VALUES (:stype::schedule_type …)` — SQLAlchemy asyncpg dialect left `:stype` unsubstituted because `::schedule_type` breaks named-param parsing. | Fixed 2026-05-20: `CAST(:stype AS schedule_type)` in `api/schedules.py`. |
| BUG-2 | Input sanitisation (text/number fields accept injection patterns). | Superseded by P5-F1…F5 scope; zod client-side validation already present. Backend hardening deferred post-MVP. |

## Open UX Fixes (P5-F1…F5, blocking P5-REVIEW)

| # | Issue | Decision | Status |
|---|-------|----------|--------|
| P5-F1 | Items grid column headers have no definitions — confusing fields (original_qty, revised_qty, base_rate, agreement_rate, is_cement_item, steel_subtype) | Custom AG Grid `headerComponent` with ⓘ icon + tooltip | ✅ complete |
| P5-F2 | No Excel paste support — multi-row copy collapses to single cell | Option B: "Import rows" button → modal with `<textarea>` → TSV parse → preview → append as new rows. Column order documented in modal. (Option C file import = post-MVP) | ✅ complete |
| P5-F3 | Items Save All always creates new rows; no update or delete | Option B: checkbox-select rows → "Delete selected" + confirm; Save All distinguishes new/dirty/persisted; backend needs `PUT` + `DELETE` for items + tests | ✅ complete |
| P5-F4 | Mutual-exclusion warning uses engine jargon | Replace with: "One or more items are marked as both a cement item and a steel item. Each item can only belong to one — please correct before saving." | ✅ complete |
| P5-F5 | Extra-items auto-save feels unsafe | Option B: staged local state + explicit "Save changes" button; batch POST on save; per-row unsaved indicator | ✅ complete |

---

## Next Steps (in order)

### Saqlain [CC-S]
1. **Run migration 013** on Supabase (`ALTER TABLE users ADD COLUMN is_admin ...`).
2. **Seed Jan–May 2026 index months** via `POST /api/indices/{series}/months` with your admin user (set `is_admin = TRUE` in DB first).
3. **Phase 6 — Bill entry UI (C-1…C-3)** — see Phase 6 section below.

### Shubham [CC-SH]
1. **G-3 — Export endpoints** — check `engine/engine/` for existing export logic first; wire `GET /api/pvc-runs/{id}/export/excel` + `.../export/pdf`. Request `SH-P5-REVIEW` before merge.
2. **IDX-4 — Index Manager UI** — replace `/indices` stub with series list + monthly entry form. Backend is live (IDX-2..3 on `main`).

### Both
- No open CRITICAL/HIGH findings. No merge gates active.

---

## P5-F Implementation Prompt

> Paste this verbatim into a fresh Claude Code chat to implement P5-F1…F5.

---

```
You are implementing five UX polish fixes (P5-F1…F5) on the RailPVC project, branch `saqlain/phase-5`.

Start by reading these files in order:
1. STATUS.md
2. ENGINEERING_GUIDELINES.md
3. TASKS.md (find the P5-F1…F5 rows for acceptance criteria)
4. backend/api/contract_items.py  (tenant gate pattern for items)
5. backend/api/schedules.py       (existing items POST + schedule_type CAST pattern)
6. frontend/components/contracts/ItemsGrid.tsx
7. frontend/components/contracts/ExtraItemDecisionList.tsx
8. frontend/app/(app)/contracts/[id]/extra-items/page.tsx

Then implement the five fixes below in a single working session. Commit everything in one or two logical commits on `saqlain/phase-5` when done. Run the backend test suite (`cd backend && python -m pytest -x -q`) before committing — it must stay green.

---

## P5-F1 — Items grid column-header tooltips

**Files:** `frontend/components/contracts/ItemsGrid.tsx`

Create a `TooltipHeader` component (can be inline in the same file) that renders the column header label + a small ⓘ character. On mouse hover over the ⓘ, show a tooltip with the field definition. Use a `title` attribute on a `<span>` wrapping the ⓘ — no external tooltip library needed.

Register it as `headerComponent: TooltipHeader` on the following columns only, passing `headerName` + a `tooltipText` via `headerComponentParams`:

| Column | Tooltip text |
|--------|-------------|
| `original_qty` | Quantity as specified in the original LOA/agreement |
| `revised_qty` | Quantity after amendment or deviation order; used for billing when set |
| `base_rate` | Schedule rate before bid discount (DSR/NS published rate) |
| `agreement_rate` | Rate after applying the bid discount; this is the rate used in bills |
| `is_cement_item` | Mark if this item falls under the cement PVC bucket (affects which price index series is applied) |
| `steel_subtype` | Mark if this item falls under the steel PVC bucket; the subtype maps to a specific steel index series |

**Acceptance criteria:** All six columns show the ⓘ in the header; hovering ⓘ shows the definition text. Other columns are unchanged.

---

## P5-F2 — Excel paste import dialog

**Files:** `frontend/components/contracts/ItemsGrid.tsx`

Add an "Import rows" button in the toolbar above the AG Grid (next to the existing "+ Add row" button). Clicking it opens a modal (can be a simple absolutely-positioned overlay — no external modal library). The modal contains:

1. A one-line instruction: "Copy a range from Excel, then paste it here. Columns must be in this order:"
2. A code block or `<pre>` listing the expected column order:
   `item_code | description | unit | original_qty | revised_qty | base_rate | agreement_rate | is_cement_item (TRUE/FALSE) | steel_subtype (blank, angles, plates, other_sections, tmt)`
3. A `<textarea>` (tall, monospace font) where the user pastes.
4. A "Preview" button that parses the textarea content as TSV (tab-separated, newline per row) and renders a small preview table of the parsed rows below the textarea. Show a parse error if the column count doesn't match.
5. An "Add N rows" button that appends the parsed rows to the grid as new rows (same `_rowState: "new"` as "+ Add row"). Closes the modal on click.
6. A "Cancel" button.

**Parsing logic:**
- Split on `\n`; skip blank lines
- Split each line on `\t`
- Map positionally to: item_code (str), description (str), unit (str), original_qty (number), revised_qty (number or null if blank), base_rate (number), agreement_rate (number), is_cement_item (boolean: "TRUE"/"true"/"1" → true, else false), steel_subtype (blank/"" → null, else use value as-is)
- If a row has fewer than 8 columns, mark it as a parse error and don't include it in the preview

**Acceptance criteria:** Button visible above grid; modal opens; pasting 3 rows from Excel and clicking "Add 3 rows" appends those rows to the grid; modal closes; rows appear with `_rowState: "new"` (behave like manually added rows for Save All).

---

## P5-F3 — Items CRUD (update + delete)

### Backend

**File:** `backend/api/contract_items.py`

Read this file carefully before writing anything. Follow the existing tenant gate pattern exactly.

Add two endpoints:

**`PUT /api/schedules/{schedule_id}/items/{item_id}`**
- Tenant gate: verify item belongs to schedule AND schedule belongs to a contract owned by the request's `tenant_id`. Do this in two queries: (1) fetch the item's `schedule_id` and verify it matches the URL param, (2) call `assert_contract_belongs_to_tenant` via the schedule's `contract_id`.
- Body: same updatable fields as the existing POST (item_code, description, unit, original_qty, revised_qty, base_rate, agreement_rate, is_cement_item, steel_subtype). Use a `ContractItemUpdate` Pydantic model with all fields Optional; use `model_fields_set` to build the SET clause so unset fields don't overwrite existing values.
- Returns the updated row (same shape as POST response).
- Wrong schedule_id → 404 NotFoundProblem. Wrong tenant → 404 NotFoundProblem.

**`DELETE /api/schedules/{schedule_id}/items/{item_id}`**
- Same tenant gate as PUT.
- Hard delete.
- Returns 204 No Content.
- Wrong schedule_id or wrong tenant → 404 NotFoundProblem.

**Tests:** Add `backend/tests/test_p5_f3_items_crud.py` with:
- PUT: valid update returns updated fields
- PUT: wrong schedule_id → 404
- PUT: wrong tenant → 404
- DELETE: valid delete → 204; subsequent GET returns empty list
- DELETE: wrong schedule_id → 404
- DELETE: wrong tenant → 404

Also bump the route count assertion in `backend/tests/test_p3_08.py` by 2 (29 → 31).

### Frontend

**File:** `frontend/components/contracts/ItemsGrid.tsx`

**Row state tracking:** Add a `_rowState: "new" | "dirty" | "persisted"` field to each row object. This field is never sent to the backend.
- Rows loaded from `GET /api/schedules/{id}/items` → `_rowState: "persisted"`, include their real `id`
- Rows added via "+ Add row" or "Import rows" → `_rowState: "new"`, `id: undefined`
- When the user edits a cell in a `"persisted"` row → `_rowState: "dirty"` (use AG Grid's `onCellValueChanged` callback)

**Save All update:**
- `"new"` rows → POST (existing logic); on success set `_rowState: "persisted"` and store the returned `id`
- `"dirty"` rows → `PUT /api/schedules/{scheduleId}/items/{row.id}`; on success set `_rowState: "persisted"`
- `"persisted"` rows with no edits → skip

**Delete:**
- Add a checkbox selection column to the grid (`checkboxSelection: true` on the first column; `headerCheckboxSelection: true`)
- Show a "Delete selected (N)" button in the toolbar when ≥1 row is selected
- On click:
  - For rows where `_rowState === "new"`: remove from grid immediately (no API call)
  - For rows where `_rowState === "dirty"` or `"persisted"`: show `window.confirm("Delete N item(s)? This cannot be undone.")` — if confirmed, call `DELETE /api/schedules/{scheduleId}/items/{row.id}` for each, then remove from grid
  - Deselect all after deletion

**Acceptance criteria:**
- Loading existing items shows them in the grid; editing a cell and clicking Save All calls PUT (not POST) for that row
- Adding a new row and clicking Save All calls POST for that row only
- Checkbox-selecting 2 saved rows and clicking Delete → confirm → both rows removed from grid and from DB
- Selecting 1 unsaved row and clicking Delete → removed immediately, no confirm, no API call

---

## P5-F4 — Mutual-exclusion warning copy

**File:** `frontend/components/contracts/ItemsGrid.tsx`

Find the amber warning banner that fires when a row has `is_cement_item === true` AND `steel_subtype !== null`. Replace the message text with:

"One or more items are marked as both a cement item and a steel item. Each item can only belong to one — please correct before saving."

**Acceptance criteria:** Old engine-jargon text is gone. New text is user-facing. Banner still appears under the same condition.

---

## P5-F5 — Extra-items manual save (staged changes)

**Files:**
- `frontend/components/contracts/ExtraItemDecisionList.tsx`
- `frontend/app/(app)/contracts/[id]/extra-items/page.tsx`

Replace the current auto-save-on-toggle pattern with explicit staged saves.

**New behaviour:**
1. On mount, load decisions from the API as before. Store them in component state as the "server state".
2. Also maintain a `pendingChanges: Record<string, "Yes" | "No" | "Undecided">` map in state. This starts empty.
3. When the user clicks a Yes/No/Undecided button: update `pendingChanges[itemId]` — do NOT call the API yet. The displayed value for a row is `pendingChanges[itemId] ?? serverState[itemId]`.
4. Rows with a pending change show a small amber dot or "(unsaved)" label next to the toggle buttons.
5. A "Save changes" button appears (or activates) when `Object.keys(pendingChanges).length > 0`. Show how many changes are pending in the button label: "Save changes (3)".
6. On "Save changes" click:
   - Disable the button, show "Saving…"
   - Call `POST /api/contracts/{id}/extra-item-decisions` for each entry in `pendingChanges` (can be in parallel via Promise.all)
   - On full success: merge `pendingChanges` into `serverState`, clear `pendingChanges`, update the banner (undecided count), show a success toast "Saved N decision(s)"
   - On any failure: show error toast, keep `pendingChanges` intact so the user can retry
7. The existing undecided-count banner logic should read from the merged view (server + pending) so it reflects what will be saved.

**Acceptance criteria:**
- Toggling a decision does NOT make an API call
- Amber dot appears on rows with pending changes
- "Save changes (N)" button is active only when N > 0
- Clicking Save makes exactly one POST per changed item; on success the pending indicators clear
- On API failure the pending changes are preserved and the error toast appears

---

## After all five fixes

1. Run `cd backend && python -m pytest -x -q` — must be green (≥63 tests passing: 61 existing + 6 new from P5-F3).
2. Run `cd frontend && npm run build` — must be clean with 0 type errors.
3. Commit to `saqlain/phase-5` with message: "P5-F1…F5: items grid UX + CRUD + extra-items staged save"
4. Update WORKPLAN.md: mark P5-F1…F5 as complete in the Open UX Fixes table.
5. Do NOT kick off P5-REVIEW — that is a separate step done by the human.
```

### Manual Smoke Plan (before P5-REVIEW)

| Flow | Steps | Expected |
|---|---|---|
| Create | `/contracts` → "New contract" → fill required fields → submit | Redirects to `/contracts/{id}` with new tender_number in header, status badge "Draft" |
| Edit | Overview → Edit → change `contractor_name` → Save | Returns to read view with new name; query invalidated |
| Validation | Submit with `completion_date < start_date` | Inline error, no API call |
| Schedules | Schedules tab → Add ExtraNS schedule | Row appears; "Manage extra-item decisions →" link appears in header |
| Items | Items tab → select schedule → +Add row → fill → Save All | "Saved N row(s)"; rows persist on tab reload |
| Mutual-exclusion warning | Items grid: set `is_cement_item=true` + `steel_subtype=tmt` | Amber warning banner visible above grid |
| Extra-items | Click header link → toggle one item Undecided → Yes | Banner updates; row persists across reload |

---

---

## Phase 5 — Contract Setup UI

### Goals

A user starts with an empty tenant and, by the end of Phase 5, can produce a contract that is fully configured for bill entry (Phase 6) and PVC calculation (Phase 7). That means: a contract row with all required metadata, at least one schedule, contract items under each schedule (with `is_cement_item` and `steel_subtype` correctly classified), and — when the contract has ExtraNS items — explicit eligibility decisions that prevent the engine from blocking at run time. The user navigates from the contract list, clicks "New contract", fills a form, is redirected to a persistent detail page with tabs for schedules and items, and can link out to a dedicated extra-items page. No session continuity is required: the contract row is created as `Draft` on first submit, so the user can always return.

---

### Out of Scope

- Bills, bill_lines, recoveries (Phase 6)
- PVC runs, approvals, run results (Phase 7)
- Carry-forwards (Phase 6/7)
- Document upload UI — page stub exists; stays empty
- Index ingestion — ops-side; read-only in this app
- PVC rule set editing — auto-created by P3-07 on contract creation; edit surface is Phase 7 prep
- multi-user RBAC (post-MVP)

---

### Resolved Decisions

| # | Question | Choice | Reason |
|---|---|---|---|
| Q1 | Creation flow shape | Shallow create at `/contracts/new` → redirect to `/contracts/[id]` with tabs (Overview \| Schedules \| Items) | Matches the DB structure; each step is atomic and recoverable; no in-memory draft state required |
| Q2 | Items entry UX | AG Grid inline-editable table + Save All button | BOQ entries are bulk; row-by-row form doesn't scale to 50+ items; AG Grid already in ARCHITECTURE.md |
| Q3 | Form library | `react-hook-form` + `zod` | Already decided; zod mirrors Pydantic ContractCreate; `@hookform/resolvers/zod` bridges them |
| Q4 | Railway zone picker | Typed dropdown, all 16 VALID_ZONES, no escape hatch | Wrong zone = wrong JPC city = wrong steel series; enum is exhaustive; new zones require a migration so the dropdown can be updated at the same time |
| Q5 | Save-and-resume | Backend draft rows — `POST /api/contracts` creates `status='Draft'` immediately; user can return via contract list | Matches existing status enum; no localStorage second-source-of-truth |
| Q6 | Validation split | Client validates dates + numerics; server owns cross-row constraints | Client catches date ordering + `bid_amount ≤ contract_value` instantly via zod `.refine()`. (Note: `agreement_number` is not UNIQUE in migration 002 — no server-side conflict check exists. P5-FUP-L3 removed the dead inline-409 affordance; add a UNIQUE migration + `ConflictProblem` raise if uniqueness becomes a product requirement.) |
| Q7 | Extra-item decisions | Separate page `/contracts/[id]/extra-items`, linked from contract detail when ExtraNS schedule exists | Keeps the detail page tabs uncluttered; decisions are a distinct workflow, not part of setup navigation |
| Q8 | Out-of-scope confirmation | All confirmed out of scope | See list above |

---

### Route Map

```
frontend/app/(app)/
└── contracts/
    ├── page.tsx                      [P4 — done] Contract list
    │   Modify: enable "New contract" button (→ /contracts/new)
    │   Modify: enable "View" row links (→ /contracts/[id])
    │
    ├── new/
    │   └── page.tsx                  [P5-003] Creation form
    │       Auth: inherited from (app) layout
    │       API: POST /api/contracts → 201 → redirect /contracts/[id]
    │
    └── [id]/
        ├── page.tsx                  [P5-004, P5-005, P5-006, P5-007]
        │   Auth: inherited from (app) layout
        │   API (mount): GET /api/contracts/{id}
        │   Tabs (via ?tab= searchParam, default=overview):
        │   ├── overview              GET /api/contracts/{id} (read) 
        │   │                         PUT /api/contracts/{id} (edit mode)
        │   ├── schedules             GET /api/contracts/{id}/schedules
        │   │                         POST /api/contracts/{id}/schedules
        │   └── items                 GET /api/contracts/{id}/schedules (schedule selector)
        │                             GET /api/schedules/{id}/items (per selected schedule)
        │                             POST /api/schedules/{id}/items (Save All)
        │
        └── extra-items/
            └── page.tsx              [P5-008] Eligibility decisions
                Auth: inherited from (app) layout
                Shown: link visible on /contracts/[id] only when ≥1 ExtraNS schedule exists
                API: GET /api/contracts/{id}/extra-item-decisions
                     POST /api/contracts/{id}/extra-item-decisions (upsert per item)
```

**Backend gap — must land before B-3 can ship:**

`PUT /api/contracts/{id}` is in `ARCHITECTURE.md` but **does not exist** in `backend/api/contracts.py`. Task P5-001 adds it.

---

### Component Inventory

| New component | Location | Props summary | Reuses |
|---|---|---|---|
| `ContractForm` | `components/contracts/ContractForm.tsx` | `defaultValues?: Partial<ContractDraft>`, `onSubmit(data): Promise<void>`, `isSubmitting: bool` | `Button` (submit), native inputs |
| `ZoneSelect` | `components/contracts/ZoneSelect.tsx` | `value: string`, `onChange(zone: string): void`, `error?: string` | Tailwind select; VALID_ZONES constant from `lib/zones.ts` |
| `ContractOverviewTab` | inline in `[id]/page.tsx` | `contract: ContractDetail`, `onEdit(): void` | `Badge` (status), `Button` (Edit) |
| `ScheduleForm` | `components/contracts/ScheduleForm.tsx` | `contractId: string`, `onCreated(schedule): void` | `Button` (submit) |
| `ScheduleList` | inline in `[id]/page.tsx` schedules tab | `schedules: Schedule[]`, `selectedId: string \| null`, `onSelect(id): void` | `Badge` (schedule_type) |
| `ItemsGrid` | `components/contracts/ItemsGrid.tsx` | `scheduleId: string`, `onSaved(): void` | AG Grid Community; `Button` (Save All) |
| `ExtraItemDecisionList` | `components/contracts/ExtraItemDecisionList.tsx` | `contractId: string` | `Button` (per decision toggle) |

**AG Grid is not yet installed** — P5-002 adds it. `ItemsGrid` cannot be built before P5-002 completes.

---

### Task Status (post-implementation, 2026-05-19)

| ID | Task | Status |
|---|---|---|
| P5-001 | Backend: PUT `/api/contracts/{id}` + expanded GET | ✅ complete |
| P5-002 | Frontend deps + `lib/zones.ts` + `lib/contracts-schema.ts` | ✅ complete |
| P5-003 / B-1 | `/contracts/new` creation form | ✅ complete |
| P5-004 / B-2 | `/contracts/[id]` detail page + tab shell | ✅ complete |
| P5-005 / B-3 | Overview tab inline edit | ✅ complete |
| P5-006 / B-4 | Schedules tab + `ScheduleForm` | ✅ complete |
| P5-007 / B-5 | Items tab — AG Grid `ItemsGrid` | ✅ complete |
| P5-008 | `/contracts/[id]/extra-items` decision page | ✅ complete |

**Implementation notes captured during the session:**

- AG Grid 35.x API uses `AllCommunityModule` registration and `themeQuartz.withParams({…})` (legacy module imports are gone).
- `react-hook-form` `setValueAs` is the cleanest way to append `-01` to a `<input type="month">` value — keeps validation pure inside zod and avoids a separate submit transform.
- Postgres `::text` casts in the GET SELECT make the route handler impossible to fully exercise under aiosqlite; the P5-001 test split is: tenant-gate + validation paths run end-to-end, the SELECT-back path is documented as Postgres-only.
- `model_fields_set` is the canonical way to express "patch semantics" in Pydantic v2 — no need for a custom `exclude_unset` dance.

---

### Task Breakdown

#### P5-001 — Backend: `PUT /api/contracts/{id}`

**Scope:** Add the missing update endpoint so B-3 (edit) has something to call.

**Files touched:**
- `backend/api/contracts.py` — add `ContractUpdate` Pydantic model + `@router.put("/{contract_id}")` handler
- `backend/tests/test_contracts_put.py` — new test file

**Acceptance criteria:**
- `PUT /api/contracts/{id}` with valid body → `200 + updated fields`
- Wrong-tenant contract → `404 NotFoundProblem`
- Invalid `railway_zone` → `422 ValidationProblem`
- `base_month.day != 1` → `422 ValidationProblem`
- `agreement_number` conflict (if unique constraint exists) → `409 ConflictProblem`
- Existing backend suite (55 tests) still green

**Test plan:**
- Unit: valid update, wrong-tenant → 404, bad zone → 422, bad base_month → 422
- `ContractUpdate` should use `model_fields_set` so unset optional fields do not overwrite existing values (partial update semantics)

**LOC estimate:** ~60 backend + ~40 test ≈ 100 total

---

#### P5-002 — Frontend: Install deps + shared constants

**Scope:** Add missing packages and the frontend VALID_ZONES constant. Unblocks all other P5 tasks.

**Files touched:**
- `frontend/package.json` — add `react-hook-form`, `@hookform/resolvers`, `zod`, `ag-grid-community`, `@ag-grid-community/react`
- `frontend/lib/zones.ts` — new; exports `VALID_ZONES` as a typed tuple of 16 zone codes with display names
- `frontend/lib/contracts-schema.ts` — new; exports `contractCreateSchema` (zod) mirroring `ContractCreate`

**Acceptance criteria:**
- `next build` clean after install
- `VALID_ZONES` list matches `backend/services/zone_mapping.py:VALID_ZONES` exactly (manually verified at task time)
- `contractCreateSchema` validates: `tender_number` non-empty, `contractor_name` non-empty, `railway_zone` in VALID_ZONES, `base_month` matches `/^\d{4}-\d{2}-01$/`, `start_date ≤ completion_date` (if both supplied), `base_month ≤ start_date` (if both supplied), `contract_value > 0` (if supplied), `bid_amount ≤ contract_value` (if both supplied)

**Test plan:**
- Unit (Vitest): zod schema — valid input passes, each `.refine()` rejects correctly
- No browser test needed for constants

**LOC estimate:** ~80 (schema + zones + lockfile excluded)

---

#### P5-003 — B-1: Contract creation form `/contracts/new`

**Scope:** Creation form; on submit creates a Draft contract and redirects to the detail page.

**Files touched:**
- `frontend/app/(app)/contracts/new/page.tsx` — new page
- `frontend/components/contracts/ContractForm.tsx` — new; driven by react-hook-form + `contractCreateSchema`
- `frontend/components/contracts/ZoneSelect.tsx` — new; renders 16-option `<select>` from VALID_ZONES
- `frontend/app/(app)/contracts/page.tsx` — change "New contract" button from `disabled` to `<Link href="/contracts/new">`

**Field list (from `ContractCreate` Pydantic model):**

| Field | Type | Required | Client rule |
|---|---|---|---|
| `tender_number` | text | yes | non-empty |
| `agreement_number` | text | no | — |
| `loa_number` | text | no | — |
| `loa_date` | date | no | — |
| `contractor_name` | text | yes | non-empty |
| `work_description` | textarea | no | — |
| `railway_zone` | dropdown | yes | must be in VALID_ZONES |
| `base_month` | month input → `YYYY-MM-01` | yes | must be first of month |
| `start_date` | date | no | ≤ completion_date, ≥ base_month |
| `completion_date` | date | no | ≥ start_date |
| `contract_value` | decimal | no | > 0 if supplied |
| `bid_amount` | decimal | no | ≤ contract_value if both supplied |
| `gst_mode` | select | yes | `inclusive` / `exclusive` |
| `pvc_applicable` | checkbox | yes | default true |
| `overall_rebate` | decimal | no | stored as fraction (0.15 = 15%); label must say "e.g. 0.15 for 15%" |

**Acceptance criteria:**
- Zod errors shown inline per field before submit
- `base_month` `<input type="month">` → appends `-01` before sending to API
- On `POST /api/contracts` success → `router.push("/contracts/" + id)`
- On 422 `conflict` (agreement_number) → inline error on that field, not just toast
- On network error → toast (existing apiFetch behavior)

**Test plan:**
- Unit: `ContractForm` renders; zod validation fires; submit calls `apiFetch` with correct body
- Browser: fill all required fields → submit → land on `/contracts/{id}` with correct tender_number in heading
- Browser: submit with completion_date before start_date → inline error, no API call

**LOC estimate:** ~240 (form + zone select + page)

---

#### P5-004 — B-2: Contract detail page (read view + tab shell)

**Scope:** Detail page fetches the contract and renders an Overview tab (read-only) plus empty tab placeholders for Schedules and Items.

**Files touched:**
- `frontend/app/(app)/contracts/[id]/page.tsx` — new
- `frontend/app/(app)/contracts/page.tsx` — change row "View" button from `disabled` to `<Link href="/contracts/{id}">`

**Acceptance criteria:**
- `GET /api/contracts/{id}` fetched via TanStack Query on mount
- All ContractOut fields displayed in Overview tab (tender_number, contractor_name, base_month, railway_zone, status, and any additional fields returned by the GET endpoint)
- 404 or wrong-tenant → error state with "Contract not found" message, no crash
- Tab bar shows Overview (active), Schedules, Items; tab switching changes `?tab=` in URL without page reload
- Link "Manage extra-item decisions" is present but hidden (rendered when ExtraNS schedule exists — wired in P5-006)

**Test plan:**
- Unit: loading state renders spinner; error state renders error message; data renders contract fields
- Browser: navigate from contract list → detail page → correct fields appear; click Schedules tab → URL changes to `?tab=schedules`

**LOC estimate:** ~180

---

#### P5-005 — B-3: Contract inline edit (Overview tab)

**Scope:** Adds an Edit mode to the Overview tab; reuses `ContractForm`; calls `PUT /api/contracts/{id}`.

**Dependency:** P5-001 (PUT endpoint) + P5-004 (detail page)

**Files touched:**
- `frontend/app/(app)/contracts/[id]/page.tsx` — add edit mode toggle + PUT call
- `frontend/components/contracts/ContractForm.tsx` — accept `defaultValues` prop (already in component interface)

**Acceptance criteria:**
- "Edit" button switches Overview from read view to `ContractForm` pre-populated with current values
- On submit: `PUT /api/contracts/{id}` → success → invalidate `["contract", id]` query → return to read view
- On 422 conflict (agreement_number) → inline error on field
- "Cancel" discards edits, returns to read view with no API call

**Test plan:**
- Unit: edit mode renders form with correct defaultValues; cancel restores read view
- Browser: edit contractor_name → save → read view shows new value; edit with bad completion_date → inline error, no API call

**LOC estimate:** ~120

---

#### P5-006 — B-4: Schedules tab

**Scope:** Schedules tab lists existing schedules and provides a form to add new ones.

**Files touched:**
- `frontend/components/contracts/ScheduleForm.tsx` — new; fields: `name` (text), `schedule_type` (select: DSR / NS / ExtraNS), `bid_discount_pct` (decimal, default 0)
- `frontend/app/(app)/contracts/[id]/page.tsx` — add Schedules tab content; add ExtraNS detection logic for extra-items link visibility

**Acceptance criteria:**
- TanStack Query: `GET /api/contracts/{id}/schedules` on tab mount (not on page load — defer with `enabled: activeTab === "schedules"`)
- Schedule list shows name, type badge, bid_discount_pct
- Add Schedule form submits to `POST /api/contracts/{id}/schedules` → on success invalidates schedules query
- After any ExtraNS schedule is created, the "Manage extra-item decisions" link becomes visible in the page header
- Invalid `schedule_type` never reaches the API — select only allows DSR/NS/ExtraNS

**Test plan:**
- Unit: form renders; submit calls POST with correct body; ExtraNS detection flips link visibility
- Browser: add DSR schedule → appears in list; add ExtraNS schedule → extra-items link appears

**LOC estimate:** ~180

---

#### P5-007 — B-5: Items tab (AG Grid)

**Scope:** Items tab shows a schedule selector; when a schedule is selected, its items load in an AG Grid inline-editable table. "Save All" POSTs new/modified rows sequentially.

**Dependency:** P5-006 (schedules must exist)

**Files touched:**
- `frontend/components/contracts/ItemsGrid.tsx` — new; wraps AG Grid Community
- `frontend/app/(app)/contracts/[id]/page.tsx` — add Items tab content

**AG Grid column config:**

| Column | Type | Editable | Cell renderer/editor |
|---|---|---|---|
| `item_code` | text | yes | plain text |
| `description` | text | yes | plain text |
| `unit` | text | yes | plain text |
| `original_qty` | numeric | yes | numeric editor |
| `revised_qty` | numeric | yes | numeric editor |
| `base_rate` | numeric | yes | numeric editor |
| `agreement_rate` | numeric | yes | numeric editor |
| `is_cement_item` | boolean | yes | checkbox cell renderer |
| `steel_subtype` | enum | yes | select cell editor: `—` / `angles` / `plates` / `other_sections` / `tmt` |

**Acceptance criteria:**
- Schedule selector (dropdown) drives which schedule's items load
- `GET /api/schedules/{id}/items` fetched when schedule selected
- "+ Add row" appends a blank row to the grid (client-side only until Save All)
- "Save All" POSTs each new/modified row to `POST /api/schedules/{id}/items` sequentially; shows progress count ("Saving 3 of 12…"); on any failure, stops and shows which row failed
- Rows with `is_cement_item=true` and `steel_subtype` both set → client-side warning (a cement item cannot also be a steel item; the engine treats them as mutually exclusive buckets)
- `steel_subtype = null` is sent when the dropdown shows `—`

**Test plan:**
- Unit: AG Grid renders with correct columns; Save All iterates rows and calls POST per row; cement+steel mutual exclusion warning appears
- Browser: add 3 items → Save All → reload tab → items reappear; set `is_cement_item=true` + `steel_subtype=tmt` → warning indicator appears

**LOC estimate:** ~260

---

#### P5-008 — Extra-items page `/contracts/[id]/extra-items`

**Scope:** Dedicated page listing all ExtraNS items for a contract with their current eligibility decision; user can flip decisions inline.

**Dependency:** P5-006 (ExtraNS schedule + items must exist before this page is useful)

**Files touched:**
- `frontend/app/(app)/contracts/[id]/extra-items/page.tsx` — new
- `frontend/components/contracts/ExtraItemDecisionList.tsx` — new

**Acceptance criteria:**
- Fetches `GET /api/contracts/{id}/extra-item-decisions` + cross-references with items from `GET /api/contracts/{id}/schedules` + `GET /api/schedules/{id}/items` for ExtraNS schedules to build the full item list
- Each row shows: item_code, description, schedule name, eligible status (Yes / No / Undecided ⚠)
- Clicking Yes/No/Undecided calls `POST /api/contracts/{id}/extra-item-decisions` (upsert); updates optimistically; reverts on error
- If all items are decided (none undecided), shows green confirmation: "All extra items are decided — PVC run can proceed"
- If any undecided, shows warning banner: "N item(s) undecided — PVC run will be blocked until all are decided"
- Back link to `/contracts/[id]`

**Test plan:**
- Unit: undecided badge renders; toggle triggers POST with correct body; optimistic update + revert on error
- Browser: flip item from Undecided → Yes → row updates immediately; banner clears when last undecided item is decided

**LOC estimate:** ~200

---

### Risk Register

- **VALID_ZONES drift.** Frontend `lib/zones.ts` must match `backend/services/zone_mapping.py:VALID_ZONES` exactly. If the backend ENUM is extended (new zone added via migration), the frontend dropdown must be updated in the same PR. Prevention: cross-check at P5-002 task time; add a comment in `zones.ts` linking to the migration file.

- **`base_month` format mismatch.** `<input type="month">` returns `"YYYY-MM"` not `"YYYY-MM-01"`. The backend rejects anything where `day != 1`. Prevention: `ContractForm` must append `-01` in the zod transform or submit handler before calling `apiFetch`. Zod schema `.transform()` on that field.

- **PUT /api/contracts/{id} missing.** B-3 (edit) is blocked until P5-001 ships. If P5-001 is skipped, the Overview edit mode has no endpoint to call. Prevention: P5-001 is a hard dependency of P5-005 and must ship first.

- **AG Grid not installed.** B-5 is blocked until P5-002 ships. Prevention: P5-002 is the first frontend task; no other task depends on AG Grid until P5-007.

- **`is_cement_item` + `steel_subtype` mutual exclusion.** The engine treats cement and steel as separate subtraction buckets in W derivation. An item marked as both confuses the calculation. The backend does not currently block this combination. Prevention: client-side warning in ItemsGrid (P5-007 AC); flag as a future backend hardening item.

- **ExtraNS items blocking PVC run silently.** If a user creates ExtraNS items but never visits `/contracts/[id]/extra-items`, the engine will block at run time (Phase 7) with an undecided-items error. Prevention: the "Manage extra-item decisions" link on the detail page becomes visible as soon as an ExtraNS schedule exists (P5-006 AC), with an ⚠ indicator if any items are undecided. This makes the blocking condition visible before Phase 7.

- **`bid_amount > contract_value` not backend-validated.** `ContractCreate` Pydantic model does not check `bid_amount ≤ contract_value`. The client-side zod check (Q6 decision) catches this before the API call, but the server will accept violating values if the API is called directly. Prevention: noted; backend hardening is a future task outside Phase 5 scope.

- **`GET /api/contracts/{id}` returns a slim ContractOut.** The existing `GET /api/contracts/{id}` in `contracts.py` returns only: `id, tender_number, contractor_name, base_month, railway_zone, status`. Fields like `contract_value`, `bid_amount`, `loa_number`, etc. are not in the current response. The Overview tab will be missing these fields until the GET endpoint is expanded. Prevention: P5-004 must verify what the live endpoint actually returns and either display only available fields or flag the gap for a backend fix.

---

### Open Questions Still Requiring Product Input

| # | Question | Blocked task | What's needed |
|---|---|---|---|
| OQ-5 | `overall_rebate` storage format: migration says `NUMERIC(5,4)` (max 9.9999). Is this stored as a fraction (0.15 = 15%) or a percentage (15 = 15%)? The label on the form must be accurate. | P5-003 | Confirm before ContractForm ships |
| OQ-6 | `GET /api/contracts/{id}` currently returns only 6 fields (see contracts.py:97-116). Should all `ContractCreate` fields be returned for the Overview edit view, or is a separate `GET /api/contracts/{id}/detail` endpoint needed? | P5-004 | Decide before P5-004 starts; if yes, backend must be expanded (small change to contracts.py SELECT) |

---

## Track G — SH-P5: GET Bill Endpoints + Export Backend `[SH]`

> Branch: `shubham/phase-5-backend` (merged PR #7 for G-1/G-2 on 2026-05-30). G-3 pending.

### G-1: GET Bill List + Detail — ✅ COMPLETE (PR #7, 2026-05-30)

`GET /api/contracts/{contract_id}/bills` + `GET /api/bills/{bill_id}` in `backend/api/bills.py`. Tenant-gated via `assert_contract_belongs_to_tenant` / `assert_bill_belongs_to_tenant`. Empty list (not 404) for zero rows. SH-P5-REVIEW passed (CC-S, 2026-05-30). Route count 31→35.

---

### G-2: GET Bill Lines + Recoveries — ✅ COMPLETE (PR #7, 2026-05-30)

`GET /api/bills/{bill_id}/lines` + `GET /api/bills/{bill_id}/recoveries`. Same tenant pattern as G-1. 12 tests in `test_sh_p5_bills_get.py`.

---

### G-3: Export Endpoints (Excel + PDF) — ✅ COMPLETE (`shubham/sh-p5-exports`, 2026-06-02)

**Goal:** Allow downloading approved PVC run results.

**Context:** Check `engine/engine/` for existing export logic before writing routes. Wire it, don't rewrite. **Outcome:** no export module existed in `engine/engine/`, so the routes build the report directly from the run + `pvc_components` rows (`services/exports.py`). Excel via `openpyxl`, PDF via `fpdf2` (both pure-Python — WeasyPrint's native GTK stack isn't pip-installable on the Windows test env). Awaiting `SH-P5-REVIEW`.

**Deliverables:**
- `GET /api/pvc-runs/{run_id}/export/excel` → `application/vnd.openxmlformats...` download
- `GET /api/pvc-runs/{run_id}/export/pdf` → `application/pdf` download
- Both: tenant-check via run→contract; status must be `Approved` or return `422` with `detail.code = "run_not_approved"`
- `Content-Disposition: attachment; filename="pvc_run_{id}.xlsx"` (and `.pdf`)

**Acceptance criteria:** Unapproved run → 422; wrong-tenant → 404; tests for both cases.

**Dependency:** G-1 + G-2

---

## Parallel Track Summary

```
As of 2026-05-31:
  main                    Phases 0–5 + SH-P5 G-1/G-2 + IDX-2..3 all merged
  saqlain/phase-6         Phase 6 C-1 ✅ + C-2 ✅ (awaiting P6-REVIEW); C-3 next
  shubham (next)          G-3 (export), then IDX-4 (index UI)

Phase 6 unblocked: ✅ (SH-P5 G-1/G-2 merged + IDX-2..3 done 2026-05-30)
Phase 7 unblocked when: Phase 6 (C-3) complete
Phase 8 unblocked when: Phase 7 + G-3 merged
```

---

## Next Review Checkpoints

- `SH-P5-REVIEW` (G-3) — CC-S adversarial pass on Shubham's export endpoints before merge
- `P6-REVIEW` — adversarial pass after Phase 6 bill entry UI lands
- `P8-REVIEW` — export format parity review (Excel column order vs submission format)

---

## Phase 6 — Bill Entry UI `[CC-S]`

**Status (2026-05-31):** C-1 ✅ + C-2 ✅ on `saqlain/phase-6`. C-3 pending. 106/106 backend, 16/16 vitest, `next build` + lint clean.

**Dependency:** SH-P5 G-1/G-2 merged ✅ + IDX-2..3 on `main` ✅ → **fully unblocked**

**Goal:** A Billing Engineer opens a contract, creates a running bill (header metadata), enters the line items and recoveries, and the bill is stored ready for a Phase 7 PVC run.

### Goals

By end of Phase 6, a user can:
- Navigate to `/contracts/[id]/bills` and see a list of bills for the contract
- Create a new bill with: `bill_number`, `bill_date`, `measurement_date`, `gross_amount`
- View a bill's detail page with its `bill_lines` (from the schedule items) and `recoveries`
- Add/edit recoveries manually (`recovery_type`, `amount`, `affects_pvc_base`)
- Bill `status` starts as `Draft`; no status transitions in Phase 6 (Phase 7 owns the run flow)

### Out of Scope for Phase 6

- Bill lines are engine-generated on PVC run — Phase 6 only *views* them (they may be empty at bill creation)
- Status transitions (Draft → Calculated → Approved) — Phase 7
- Bill deletion — post-MVP

### Route Map

| Route | Backend status | Frontend task |
|---|---|---|
| `GET /api/contracts/{id}/bills` | ✅ SH-P5-1 (PR #7) | C-1: list view |
| `GET /api/bills/{id}` | ✅ SH-P5-2 (PR #7) | C-2: detail view |
| `GET /api/bills/{id}/lines` | ✅ SH-P5-3 (PR #7) | C-2: lines table |
| `GET /api/bills/{id}/recoveries` | ✅ SH-P5-4 (PR #7) | C-2: recoveries table |
| `POST /api/contracts/{id}/bills` | ❌ needs implementation | C-1: create form |
| `POST /api/bills/{id}/recoveries` | ✅ P3-BF-3 | C-2: add recovery |

### Task Breakdown

#### C-1 — Bill list + create (`/contracts/[id]/bills`) — ✅ COMPLETE

**Backend:** `POST /api/contracts/{id}/bills` **already existed** (Phase 3 remediation). C-1 hardened it: gate via `assert_contract_belongs_to_tenant`; catch `UNIQUE(contract_id, bill_number)` `IntegrityError` → `ConflictProblem` (409); tightened `BillCreate` to `{ bill_number, bill_date, measurement_date, gross_amount }` and **removed client-supplied `net_amount`** (derived value the backend owns). 3 tests in `test_c1_bills_create.py` (valid 201 / wrong-tenant 404 / duplicate 409). No new route — count stays 38.

**Frontend:** **Separate page** `/contracts/[id]/bills` (decision below), not a tab. `BillForm` zod-validated; duplicate `bill_number` renders inline via `detail.code === "conflict"`. On create → invalidate list (no redirect — the `[billId]` detail page is C-2). "Bills →" entry link added to the contract detail header.

#### C-2 — Bill detail (`/contracts/[id]/bills/[billId]`) — ✅ COMPLETE

**Frontend only** (all backend routes exist). Shows:
- Bill header fields (number, dates, gross/net amount, status badge)
- Bill lines table — **plain read-only table** (not AG Grid: data is read-only and empty until a Phase 7 PVC run generates lines; a plain table is simpler and matches the app's list styling)
- Recoveries table + `RecoveryForm` (type select + amount + affects_pvc_base toggle → `POST /api/bills/{id}/recoveries`; invalidates the recoveries query)

net_amount is shown as stored (currently `—` at create); the **computed** net is C-3.

#### C-3 — Bill edit + recovery management

**Frontend:** Inline edit for bill header fields (same PUT pattern as Overview tab). Recovery add/delete. Bill `net_amount` is computed: `gross_amount − sum(recovery amounts where affects_pvc_base=FALSE)` — display only, not user-editable.

### Open Questions — RESOLVED (2026-05-31)

- **`bill_number` uniqueness:** already `UNIQUE(contract_id, bill_number)` in migration 003 → **per-contract**. No migration needed; C-1 translates the constraint violation into a 409.
- **Tab vs page:** **separate `/contracts/[id]/bills` page.** Contract detail already carries Overview/Schedules/Items + the ExtraNS link, and the bill `[billId]` sub-route needs a natural parent.
