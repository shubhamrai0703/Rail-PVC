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

## Results

**Verdict: NOT READY — 2 HIGH, 4 MEDIUM, 1 LOW.** The ordinary percent round-trips are correct and both delete statements are tenant-scoped, but the delete implementation is not safe to expose as complete: some valid child records prevent deletion with an FK error, successful deletion can orphan uploaded files in Supabase Storage, and the success path can immediately show a stale contract list.

### Findings

#### [HIGH] AUD13-14-H1 — Non-cascading child records make valid Draft deletes fail

- **Files:** `backend/api/contracts.py:203`, `backend/migrations/versions/004_carry_forwards.py:20`, `backend/migrations/versions/007_pvc_runs.py:36-38`, `backend/tests/test_audit1_3_contract_delete.py:47-58`
- **Defect:** The handoff/test premise that all contract children cascade is false. `pvc_runs.contract_id`, `pvc_runs.bill_id`, `carry_forwards.contract_id`, and related references use PostgreSQL's default `NO ACTION`, not `ON DELETE CASCADE`. The application never transitions `contracts.status` away from `Draft`, and a Draft-labelled contract can acquire a PVC run. Clicking Delete then reaches the SQL statement and fails with an FK error/500 instead of the promised 204.
- **Test weakness:** The success test mocks both `session.execute()` calls and asserts only the call count, so it cannot exercise FK behavior. Its non-Draft cases (`Approved`, `Superseded`, `ExceptionFlagged`) are PVC-run statuses, not valid `contract_status` values (`Configured`, `Active`, `Completed`, `Archived`).
- **Required response:** Preserve PVC run/audit history. Reject deletion with a structured 422 when non-deletable children such as `pvc_runs` or `carry_forwards` exist, and pin the behavior with a real-Postgres integration test. No migration is required.

#### [HIGH] AUD13-14-H2 — Contract deletion orphans uploaded Storage objects

- **Files:** `backend/api/contracts.py:203`, `backend/migrations/versions/008_extra_items_documents.py:40-46`, `backend/api/documents.py:96-140`, `backend/services/storage.py:172-182`
- **Defect:** The DB cascade deletes `documents` metadata but does not delete the corresponding private Supabase Storage object. After a successful contract deletion, the bytes remain retained while their only `storage_path` record is gone, creating an unreachable privacy-retention and storage-cost leak.
- **Required response:** Preserve each `storage_path` in a durable retryable cleanup record/workflow and remove the object without losing retryability on Storage failure. Add a test covering metadata plus object cleanup/failure recovery.

#### [MEDIUM] AUD13-14-M1 — Successful delete routes back to a stale contracts list

- **Files:** `frontend/app/(app)/contracts/[id]/page.tsx:234,317`, `frontend/lib/providers.tsx:9-15`, `frontend/app/(app)/contracts/page.tsx:29-33`
- **Defect:** `onDeleted` only calls `router.push("/contracts")`. The `["contracts"]` query remains fresh for 30 seconds and focus refetching is disabled, so the common list -> detail -> delete -> list flow can immediately render the deleted row and link to a 404.
- **Required response:** Invalidate or update `["contracts"]` before routing; optionally remove the deleted detail query too. Add a query-cache navigation test.

#### [MEDIUM] AUD13-14-M2 — Percent conversion narrows the previously accepted rebate domain

- **Files:** `frontend/lib/contracts-schema.ts:55-59`, `frontend/components/contracts/ContractForm.tsx:260-266`, `frontend/app/(app)/contracts/[id]/page.tsx:79-80`
- **Defect:** Before this change, the form and `NUMERIC(5,4)` storage accepted fractions through `9.9999`. The new `max(100)` applies to the percent value, so the largest storable value through the UI is now fraction `1.0`; an existing stored fraction above `1.0` loads as more than `100` and cannot be saved. If rebates above 100% are invalid domain data, that constraint needs to be an explicit compatibility decision rather than an accidental unit-conversion side effect.
- **Required response:** Decide/document the intended `overall_rebate` domain. Either preserve the former range with a `999.99%` UI maximum or add explicit compatibility handling for existing values above fraction `1.0`. Fractional DB storage remains unchanged.

#### [MEDIUM] AUD13-14-M3 — Financial unit conversions have no regression tests

- **Files:** `frontend/components/contracts/ContractForm.tsx:60-66`, `frontend/components/contracts/ScheduleForm.tsx:45-49`, `frontend/lib/contracts-schema.test.ts`
- **Defect:** No frontend test pins either new conversion boundary. A future removal/double-application of `/ 100` can write `15` instead of `0.15` (or `0.0015`) while the existing 92 tests stay green.
- **Required response:** Add focused tests for user `15` -> API `0.15`, API `"0.15"` -> edit `15`, blank, zero, invalid/NaN input, display formatting, and both ContractForm and ScheduleForm payloads.

#### [MEDIUM] AUD13-14-M4 — Generated API schema still says contract DELETE is impossible

- **File:** `frontend/lib/api/schema.ts:37`
- **Defect:** The committed OpenAPI-generated contract still contains `delete?: never` for `/api/contracts/{contract_id}` after the endpoint was added. The current button uses untyped `apiFetch`, so runtime works, but the repository's typed API artifact is stale and future typed consumers cannot use the route.
- **Required response:** Regenerate `frontend/lib/api/schema.ts` from the updated backend OpenAPI document and verify the DELETE operation and 204 response are present.

#### [LOW] AUD13-14-L1 — Schema comments name the wrong conversion layer

- **File:** `frontend/lib/contracts-schema.ts:8-10,64-65`
- **Defect:** Both comments say `setValueAs` divides by 100. It only parses with `Number()`; division happens in the ContractForm/ScheduleForm submit handlers.
- **Required response:** Correct the comments so later refactors do not double-convert.

### Requested scrutiny points

1. **Delete race / transaction:** `get_session` already starts an implicit SQLAlchemy transaction on the first execute and commits on dependency exit. Adding an explicit `BEGIN` alone would not close the check/use gap under PostgreSQL `READ COMMITTED`: each statement receives a new snapshot. There is currently no application route that changes `contracts.status`, so the independent validator did not classify the race as a presently reachable defect. A direct administrative/future lifecycle writer could still change status after the SELECT and before the DELETE because the destructive predicate omits `status = 'Draft'`. Keep this as a hardening requirement: use `SELECT ... FOR UPDATE` before the gate, or make the destructive statement itself tenant-and-status scoped with `RETURNING`.
2. **Tenant boundary:** Confirmed. The SELECT uses `WHERE id = :id AND tenant_id = :tid`, and the DELETE independently repeats both predicates. SQL is parameterized. Wrong-tenant access collapses to 404.
3. **`bid_discount_pct` round-trip:** Correct for normal inputs. `5` -> Zod `5` -> submit `0.05` -> Pydantic `Decimal("0.05")` -> `NUMERIC(5,4)` -> API `0.05` -> display `5.00%`. Blank schedule input intentionally becomes `0`; zero remains zero. `Number()` can create `NaN`, but Zod 4's number schema rejects it before submit.
4. **`overall_rebate` edit round-trip:** Correct within the new 0-100% UI domain. API `"0.15"` -> edit default `15` -> submit `0.15`. With `step=0.01`, percent input has at most two decimal places, so division yields at most four fractional decimal places, matching `NUMERIC(5,4)`. A direct Pydantic JSON probe preserved `0.3333` and `0.15` as exact Decimals.
5. **Blank new-contract rebate:** Correct. Blank -> `undefined`; `undefined != null` is false, so submit retains `undefined`; `JSON.stringify` omits the property; backend `ContractCreate` supplies `Decimal("0")`. On edit, omission preserves the stored value.
6. **`window.confirm`:** Acceptable here. It occurs only after a user clicks the visible Draft-only Delete button; it is not triggered on page load or inside an automated background flow. Chrome automation must explicitly accept the dialog during a delete smoke test.
7. **No explicit transaction:** Not the root issue. The dependency already provides one transaction. Atomic status enforcement requires a row lock or a status predicate on the destructive statement, not merely an explicit transaction wrapper.

### Verification

- `uv run pytest tests/test_audit1_3_contract_delete.py tests/test_p3_08_clean_import.py -q` — **7 passed**
- `npm test` — **92/92 passed**
- `npx tsc --noEmit` — **clean**
- Pydantic Decimal probe — JSON `0.3333` -> `Decimal("0.3333")`; JSON `0.15` -> `Decimal("0.15")`
- Static migration/call-site audit confirmed the non-cascading FKs, Storage cleanup gap, 30-second React Query freshness window, and stale generated API schema.
- Independent validator: **7/8 candidates confirmed**; the status-change race was demoted to residual hardening because no current application status writer exists.
- Cross-model adversarial route: requested Claude `opus` at high effort through the native Claude CLI, but the installed CLI rejected `--effort`; the pass produced no usable artifact (`model_actual=unverified`, `effort_actual=unverified`, `receipt_supported=unavailable`, `independence_verified=unavailable`). Local correctness, standards, testing, maintainability, security, API-contract, and reliability reviews completed.
