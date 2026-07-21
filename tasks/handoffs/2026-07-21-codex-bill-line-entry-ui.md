# Handoff — Bill-line entry UI

## Goal

Add a frontend form to create bill lines. The backend endpoint
(`POST /api/bills/{bill_id}/lines`) has existed and worked since bills were
built, but no frontend caller was ever written — the bill detail page shows
lines **read-only**. Result: a bill's cement/steel deductions and ExtraNS
amounts (which the PVC engine derives from `bill_lines` via
`build_bill_payload`) silently compute as zero unless someone pre-enters
lines via raw `curl`. See `tasks/walkthrough-first-user.md` Appendix 1 for
the current curl workaround.

**Definition of done:** from the bill detail page, a user can add a bill
line (pick a contract item, enter the qty/amount fields) without leaving the
page or touching the API directly. The new line appears in the existing
lines table immediately after submit.

## Current state

- Backend: `POST /api/bills/{bill_id}/lines` already exists, is tenant-gated,
  and validates the item belongs to the bill's contract. **No backend
  changes should be needed.** See `BillLineCreate` schema and the route at
  `backend/api/bills.py:238-287`.
- Frontend: the bill detail page
  (`frontend/app/(app)/contracts/[id]/bills/[billId]/page.tsx`) fetches
  lines read-only via `linesQuery` (`useQuery` on `["bill-lines", billId]`,
  calling `GET /api/bills/{billId}/lines`) and renders them starting around
  line 386 ("Bill lines — read-only in the current interface"). The copy at
  ~line 390-414 explicitly tells the user lines must be prepared "outside
  this screen" — that copy should be replaced/updated once the form exists.
- There is an existing, working pattern to copy almost verbatim:
  `frontend/components/contracts/RecoveryForm.tsx`. It's a small
  react-hook-form + zod form that POSTs to `/api/bills/{billId}/recoveries`
  and calls `onCreated()` on success; the bill page passes it a callback
  that invalidates `["bill", billId]` — check how the page wires
  `RecoveryForm`'s `onCreated` prop and mirror it for the new form so
  `["bill-lines", billId]` gets invalidated too (that key is also
  invalidated by the "Calculate PVC" mutation, so reuse it exactly, don't
  invent a new key).

## Key files

- `backend/api/bills.py:238-287` — `BillLineCreate` schema + `POST
  /api/bills/{bill_id}/lines` route. Read this to get field names/types
  right; don't change it unless you find an actual bug.
- `frontend/components/contracts/RecoveryForm.tsx` — the pattern to mirror
  (react-hook-form + zod, `apiFetch` POST, reset-on-success, inline field
  errors).
- `frontend/app/(app)/contracts/[id]/bills/[billId]/page.tsx` — where
  `RecoveryForm` is already wired in (find that usage first — mirror it for
  the new form) and where the read-only lines table lives (~line 386-420).
- `frontend/components/contracts/ItemsGrid.tsx` — shows how contract items
  are fetched and rendered (`useQuery(["schedule-items", scheduleId], ...
  GET /api/schedules/{scheduleId}/items)`), including the `ContractItem`
  type shape (item_code, description, unit, is_cement_item, steel_subtype,
  etc.) you'll want for the item picker's label.
- `backend/api/schedules.py:82` — `GET /api/contracts/{contract_id}/schedules`.
- `backend/api/contract_items.py:305` — `GET /api/schedules/{schedule_id}/items`.

## The one real design decision: which items to offer

Items live under `schedule_id`, not directly under `contract_id` — a
contract can have multiple schedules (see `frontend/app/(app)/contracts/[id]/page.tsx`,
which lets a user pick a schedule tab and only then renders `ItemsGrid`).
The bill detail page currently only has `contract_id` (from the route) and
`billId` in scope — it does not know a schedule_id.

You need to decide how the item dropdown sources its options. Reasonable
approach, in order of preference:
1. Fetch `GET /api/contracts/{contract_id}/schedules`, then fetch items for
   each schedule and flatten into one list (most contracts have one
   schedule in practice, but don't assume — code the general case).
2. If that's awkward, fetch schedules first and if there's exactly one,
   fetch its items directly; if there's more than one, group the dropdown
   by schedule (optgroup) so the user can still tell items apart.

Don't guess silently — if it's not obvious from the data which items should
be selectable for a bill line, that's worth a one-line comment explaining
the choice, not a assumption baked in silently.

## Constraints

- Match existing style: Tailwind classes already used in `RecoveryForm.tsx`
  and the surrounding bill page (`labelCls`/`inputCls`/`errCls` constants,
  same button component from `@/components/ui/Button`).
- Decimal fields (`qty_up_to_last`, `qty_since_last`, `qty_up_to_date`,
  `amount_up_to_last`, `amount_since_last`, `amount_up_to_date`,
  `special_condition_amount`) must be sent as **strings** to the API to
  preserve decimal precision — `RecoveryForm.tsx` does this for `amount`
  (`String(values.amount)`); do the same for all seven fields here.
- Do not touch `backend/api/bills.py` unless you find the existing route is
  actually broken — it isn't known to be; this is a frontend-only gap.
- Don't remove the existing read-only table — extend the section with a
  form above/below it, and update the explanatory copy that currently says
  lines must be prepared "outside this screen" since that will no longer be
  true.
- No test infra changes needed beyond what's normal for a new component —
  add vitest coverage for the new form the same way `RecoveryForm` (or
  similar existing forms) are tested, if such tests exist; check
  `frontend/lib/*.test.ts` and any existing component tests for the
  pattern.

## Verification

- `cd frontend && npm run build` (or the project's usual typecheck/lint
  command) must pass clean.
- Run the existing vitest suite; add tests for any new pure logic
  (e.g. payload construction) rather than only relying on manual UI checks.
- Smoke-test manually: start the dev server, open a bill detail page for a
  bill with a real contract/schedule/items, submit a new line through the
  new form, and confirm (a) the POST succeeds, (b) the line appears in the
  read-only table without a manual page refresh (query invalidation
  working), (c) submitting with a missing/invalid item shows an inline
  error rather than a silent failure.
- Report exact commands run and their pass/fail output in Results, not just
  "tests pass."

## Report back

Append a `## Results` section to this file with: what you built, which
files changed, the verification commands + output, and anything you had to
decide (especially the schedule/item-sourcing question above) with your
reasoning.

## Results

### What was built

- Added `BillLineForm`, a `react-hook-form` + Zod client form on the bill
  detail page. It exposes the contract item plus all three quantity fields,
  all three amount fields, and `special_condition_amount`; successful creates
  reset to zero defaults while API failures render inline.
- The item picker fetches every schedule for the bill's actual
  `bill.contract_id`, issues the per-schedule item queries concurrently using
  the existing React Query keys, flattens the results, and retains schedule
  name/type in every option label. Existing bill-line item IDs are excluded.
- The existing lines query is now an explicit prerequisite for the form. A
  loading or failed line list cannot be mistaken for an authoritative empty
  bill. After POST, the page cancels stale line reads, inserts the returned row
  into `['bill-lines', billId]` immediately, then invalidates and awaits that
  exact key for server reconciliation. The existing read-only table remains.
- All seven decimal values stay as strings through the form and request body.
  Validation also matches the database's `NUMERIC(15,4)` storage boundary (at
  most 11 significant integral digits and 4 fractional digits), preventing
  silent database rounding and avoidable overflow errors.
- Review exposed an actual backend defect permitted by the handoff's exception:
  concurrent duplicate `(bill_id, item_id)` inserts leaked an unstructured 500.
  The route now translates only PostgreSQL `23505` on
  `bill_lines_bill_id_item_id_key` to a structured 409; unrelated integrity
  violations are re-raised. Focused tests distinguish both paths.

### Decisions

- **Schedule/item source:** used the preferred general solution—all contract
  schedules, then all of their items—because a bill has no `schedule_id` and
  assuming one schedule would silently hide valid items. Labels include
  schedule context because item codes and schedule names are not unique.
- **Contract identity:** used `bill.contract_id`, not the nested route's `id`.
  The bill response is independently tenant-gated; using it prevents a
  mismatched URL from offering items that the backend correctly rejects.
- **Duplicate handling:** frontend filtering is advisory only. Query gating and
  optimistic cache insertion cover the normal UI flow; the backend 409 remains
  the authoritative protection for cross-tab races or lost responses.
- **Tests:** the repo has no jsdom/happy-dom or Testing Library setup and no
  interactive form-test precedent. Added pure Vitest coverage for validation,
  exact string preservation, trimming, leading zeros, and database precision
  boundaries without changing test infrastructure.

### Files changed

- `frontend/components/contracts/BillLineForm.tsx` (new)
- `frontend/lib/billLine.ts` (new)
- `frontend/lib/billLine.test.ts` (new)
- `frontend/app/(app)/contracts/[id]/bills/[billId]/page.tsx`
- `backend/api/bills.py`
- `backend/tests/test_p3_06_bill_line_integrity.py`
- `tasks/todo.md`
- `tasks/handoffs/2026-07-21-codex-bill-line-entry-ui.md`

### Verification evidence

1. Proof-first frontend test:
   - `cd frontend && npm test -- --run lib/billLine.test.ts`
   - Before implementation: **FAIL** as expected—Vitest could not load the
     missing `./billLine` module (1 failed suite, 0 tests).
   - Final focused result: **PASS**, 1 file / **11 tests**.
2. Proof-first backend duplicate contract:
   - `cd backend && uv run pytest tests/test_p3_06_bill_line_integrity.py -q`
   - Before the 409 fix: **FAIL**, 1 failed / 3 passed; raw
     `sqlalchemy.exc.IntegrityError` escaped.
   - The follow-up non-unique case initially **FAIL**ed, 1 failed / 4 passed,
     proving the first catch was over-broad.
   - Final focused result: **PASS**, **5 passed**; exact unique constraint maps
     to 409 and foreign-key `23503` remains an `IntegrityError`.
3. `cd frontend && npm test`
   - **PASS**, 13 files / **87 tests**.
4. `cd frontend && npx tsc --noEmit`
   - **PASS**, exit 0 with no diagnostics.
5. `cd frontend && npm run lint`
   - **PASS**, exit 0 with no warnings or errors.
6. `cd frontend && npm run build`
   - First sandboxed attempt: **FAIL** only because Next could not fetch Geist
     and Geist Mono from Google Fonts.
   - Retried with network access: **PASS**. Next.js 16.2.6 compiled, completed
     TypeScript, generated 11/11 static pages, and emitted the bill-detail
     dynamic route. The final post-review build also passed with the same route
     set.
7. `cd backend && uv run pytest -q`
   - **PASS**, **196 passed**.
8. Simplification + scoped review:
   - Reuse/quality/efficiency pass applied four behavior-preserving cleanups.
   - Correctness/adversarial review found two frontend P2s plus the duplicate
     API race; all were fixed. Final correctness re-review: **no remaining
     concrete defect**. Project-standards review found no applicable code
     violation. Interactive form/network branches remain a documented testing
     gap because the repo has no client-DOM test harness.

### Manual smoke-test status

Both local services were already listening (`127.0.0.1:3000` frontend and
`127.0.0.1:8000` backend), but the in-app browser runtime reported
`No browser is available` and its available-browser list was empty. Therefore
the authenticated desktop/mobile click-through, real POST, table-refetch
observation, and missing/invalid-item visual check were **not run** in this
session. This is the only incomplete verification item; it remains unchecked
in `tasks/todo.md` and must be run when a browser session is available.
