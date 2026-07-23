# Handoff — Adversarial Review: AUDIT-1-3 (Contract Delete) + AUDIT-1-4 (Percent Inputs)

**Date:** 2026-07-23
**From:** Claude Sonnet 4.6 session
**To:** ChatGPT — adversarial code review pass
**Repo:** `/Users/saqlainmomin/railPVC` (branch `main`)

## What was built today

Two AUDIT items from the usability-audit triage (TASKS.md `### AUDIT-1` section):

### AUDIT-1-3 — Draft contract delete affordance

**Backend (`backend/api/contracts.py`):**
- Added `DELETE /api/contracts/{contract_id}` endpoint
- Tenant gate: `SELECT status FROM contracts WHERE id = :id AND tenant_id = :tid` → 404 if not found
- Status gate: reject with `ValidationProblem(422)` if `status != 'Draft'`
- Delete: `DELETE FROM contracts WHERE id = :id AND tenant_id = :tid` — all child records cascade via FK `ON DELETE CASCADE` (schedules, items, bills, pvc_runs, documents all have cascade FKs in migrations 002–008)
- Returns `Response(status_code=204)`
- Route count bumped 48 → 49 in `test_p3_08_clean_import.py`

**Frontend (`frontend/app/(app)/contracts/[id]/page.tsx`):**
- `OverviewTab` gains an `onDeleted: () => void` prop (wired to `router.push("/contracts")`)
- Trash button visible only when `contract.status === "Draft"`, guarded by `window.confirm`
- `useMutation` calls `apiFetch("/api/contracts/{id}", { method: "DELETE" })`

**Tests (`backend/tests/test_audit1_3_contract_delete.py` — new file):**
- 5 tests: Draft success (204, 2 execute calls), Approved/Superseded/ExceptionFlagged each get 422, wrong-tenant gets 404

### AUDIT-1-4 — Percent inputs for rebate fields

**Problem:** `bid_discount_pct` (schedules) and `overall_rebate` (contracts) are stored as fractions (0.15 = 15%) but the UI previously accepted raw decimals with "(0.05 = 5%)" hints. Users were entering the wrong values.

**ScheduleForm (`frontend/components/contracts/ScheduleForm.tsx`):**
- Schema changed from `max(1, "must be ≤ 1 (as fraction)")` to `max(100, "must be ≤ 100%")`
- Label changed to "Bid discount (%)"
- `setValueAs` still just `Number(v)` (no division) — percent value stays in form state
- Submit body: `{ ...values, bid_discount_pct: values.bid_discount_pct / 100 }` — division happens at POST time
- Hint paragraph removed (% label makes it self-explanatory)

**ContractForm (`frontend/components/contracts/ContractForm.tsx`):**
- Label changed to "Overall rebate (%)"
- `setValueAs` unchanged: `Number(v)` (no division)
- `submit` handler: divides `overall_rebate / 100` before calling `onSubmit(payload)` — this is where the fraction goes to the API
- Hint paragraph removed; `step` changed from 0.0001 to 0.01

**Schema (`frontend/lib/contracts-schema.ts`):**
- `overall_rebate`: `max(9.9999)` → `max(100, "must be ≤ 100%")`, comment updated

**Display (`frontend/app/(app)/contracts/[id]/page.tsx`):**
- `toFormDefaults`: `overall_rebate * 100` when loading for edit (API returns fraction, form expects percent)
- Overview tab read-only: `${(Number(contract.overall_rebate) * 100).toFixed(2)}%`
- Schedules table column header: "Bid discount (%)", value: `${(Number(s.bid_discount_pct) * 100).toFixed(2)}%`

## Verification already done

- `backend/pytest`: 199 pass (5 new delete tests); 3 pre-existing alembic-env failures unrelated to this work
- `frontend/tsc --noEmit`: clean
- `frontend/vitest run`: 92/92 pass
- `next build`: clean

## What to review

Adversarially check the following:

1. **Delete cascade safety** — can a non-Draft contract ever reach the delete endpoint with a race condition? The SELECT and DELETE are separate SQL statements with no transaction wrapper. What happens if status changes between them?

2. **Tenant boundary on delete** — does the tenant gate in the SELECT (`AND tenant_id = :tid`) also apply to the DELETE statement? Confirm both SQL statements gate on tenant, not just the first.

3. **Percent input round-trip** — trace the full round-trip for `bid_discount_pct`: user types "5" → schema sees 5 → `max(100)` passes → submit divides by 100 → API receives 0.05 → DB stores 0.05 → API returns 0.05 → display multiplies by 100 → shows "5.00%". Any place where a 0 vs undefined vs NaN could leak?

4. **`overall_rebate` edit round-trip** — when editing an existing contract: API returns `overall_rebate: "0.15"` (string from Postgres) → `toFormDefaults` does `Number("0.15") * 100 = 15` → form shows "15" → user saves → `setValueAs` returns `Number("15") = 15` → Zod validates 15 ≤ 100 ✓ → submit handler: `15 / 100 = 0.15` → API receives 0.15. Confirm no precision drift at double precision vs DB NUMERIC(5,4).

5. **New contract without rebate** — `overall_rebate` is optional in the schema. If user leaves it blank: `setValueAs` → `undefined` → Zod `.optional()` → submit handler: `undefined != null` is false → `undefined / 100` = `NaN`? Check the condition: `values.overall_rebate != null ? values.overall_rebate / 100 : values.overall_rebate`. `undefined != null` is false (since `undefined == null` in loose comparison) → returns `values.overall_rebate` (undefined) → API body omits the field → backend uses DB default 0. Confirm.

6. **`window.confirm` on delete** — this triggers a browser dialog. The codebase has a pattern note about not triggering browser dialogs in the Claude-in-Chrome test environment. Confirm this is acceptable in this context (it's a user-initiated action, not an automated flow).

7. **No transaction on delete** — FastAPI's `get_session` provides a session but the delete runs two separate `execute()` calls (SELECT for status check, then DELETE) without an explicit BEGIN/COMMIT. Is this safe, or should both be wrapped in a transaction to prevent a status-change race?

## Key files to read

```
backend/api/contracts.py                          # DELETE endpoint (new)
backend/tests/test_audit1_3_contract_delete.py    # new tests
backend/tests/test_p3_08_clean_import.py          # route count updated 48→49
frontend/app/(app)/contracts/[id]/page.tsx        # delete button + display changes
frontend/components/contracts/ContractForm.tsx    # overall_rebate percent input
frontend/components/contracts/ScheduleForm.tsx    # bid_discount_pct percent input
frontend/lib/contracts-schema.ts                  # schema max updated
```

## Constraints

- Do not change the backend DB schema or add migrations
- Do not change how `overall_rebate` is stored in the DB (fraction stays)
- If you find a defect, document it in REVIEW.md under a new `AUDIT13-14-REVIEW` cycle following the existing format (CRITICAL/HIGH/MEDIUM/LOW)
- Backend suite must stay green (excluding the 3 pre-existing alembic-env failures)
