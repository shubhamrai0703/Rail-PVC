# REVIEW.md — Active Review Cycle

Use this file for the current live review state only.

## Canonical Links

- Current project state: [STATUS.md](STATUS.md)
- Coding/review rules: [ENGINEERING_GUIDELINES.md](ENGINEERING_GUIDELINES.md)
- Current task board: [TASKS.md](TASKS.md)
- Historical review pointer: [archive/REVIEW_ARCHIVE.md](archive/REVIEW_ARCHIVE.md)

## Active Cycle

**P6-REVIEW** — opened 2026-06-04. Adversarial pass by **Codex-S** on the merged Phase 6 Bill Entry UI (C-1, C-2, C-2-FIX-A, C-2-FIX-B). This work merged to `main` without a prior adversarial review; this cycle closes that gap before Phase 7.

**Scope (already on `main`):**
- C-1 / C-2 core — PR #10 (`0ccd765`), diff `ba1324e..0ccd765`
- C-2-FIX-A / C-2-FIX-B — folded into `0b96ec5`

**Files in scope:**
- `backend/api/bills.py` (C-1: `ConflictProblem` on `UNIQUE(contract_id, bill_number)`, tenant gate, dropped client `net_amount`)
- `backend/tests/test_c1_bills_create.py`
- `frontend/app/(app)/contracts/[id]/bills/page.tsx` (bills list + create)
- `frontend/app/(app)/contracts/[id]/bills/[billId]/page.tsx` (bill detail + Calculate PVC card)
- `frontend/components/contracts/BillForm.tsx`
- `frontend/components/contracts/RecoveryForm.tsx`
- `frontend/app/(app)/contracts/[id]/page.tsx` (bills link)
- `frontend/components/contracts/ItemsGrid.tsx` (C-2-FIX-A number parser/formatter)

**Out of scope:** C-3 (not yet implemented), IDX-4, SH-P5 exports, P5-IMP (separately reviewed/merged). Demo seed (`seeds/seed_demo_contract.py`) is tracked under DEMO-2, not here.

**Status (2026-06-04):** Codex returned 2 HIGH, 2 MEDIUM, 0 CRITICAL/LOW. All four code-verified by CC-S. **All four closed** — P6-H1 via interim approach A (recoveries → `technical_withheld`), per Saqlain's A-now/C-later decision (see H1 below; C tracked as P6-H1-FUP-C). Suite: **125/125 backend, 45/45 vitest, tsc + eslint clean**, route count 40. Cycle ready to collapse to a closure pointer once changes are committed/merged.

### [HIGH] P6-H1 — `affects_pvc_base` recoveries are ignored by PVC calculation

- **File:** `backend/services/pvc_service.py:429` (`build_bill_payload`)
- **Verified:** `build_bill_payload` sets `on_account_amount` from `running_bills.gross_amount` and hard-codes `technical_withheld=Decimal("0")`. It never queries the `recoveries` table. Meanwhile `backend/api/bills.py:33-35` documents the *intended* behavior: "`affects_pvc_base` … drives whether the recovery is subtracted from the engine's on_account amount during W derivation." So the invariant is documented but unimplemented — a recovery with `affects_pvc_base=TRUE` is silently dropped from W. Confirmed plausible-but-wrong-number per W formula in `PRODUCT.md:60-67` (`W = OnAccount − … − TechnicalWithheld − …`).
- **Proposed fix (pending domain confirmation):** in `build_bill_payload`, sum `recoveries.amount WHERE affects_pvc_base = TRUE` for the bill and feed it into the engine as a **named** W subtraction. Per `PRODUCT.md` rule 1 ("every subtraction is a named, confirmed step"), `TechnicalWithheld` is the only existing W bucket that fits — so route it there rather than silently netting `on_account`. **Open decision for Saqlain:** confirm the bucket + that `affects_pvc_base=TRUE` == "reduces W". **Risk:** changes pinned demo-fixture PVC outputs (`bct_2425_252_*`) if those bills carry such recoveries — must re-reconcile DEMO fixtures.
- **Test that would catch it:** payload-construction test — bill `gross=100000`, one recovery `amount=10000, affects_pvc_base=TRUE` → assert W derives from `90000` (i.e. `technical_withheld=10000`), and a second recovery with `affects_pvc_base=FALSE` does **not** move W.
- **DECISION (Saqlain, 2026-06-04): approach A now, approach C later — and A is explicitly NOT our best long-term bet.** Interim: sum `affects_pvc_base = TRUE` recoveries into the engine's existing `technical_withheld` bucket. Rationale: zero engine/model change, and the deduction stays a *named* W subtraction (PRODUCT.md rule 1) — superior to approach B (netting `on_account`), which was rejected for hiding the subtraction. **Known limitation of A:** it overloads `technical_withheld`, conflating genuine technical withholding with PVC-affecting recoveries; they can't be disaggregated in `w_derivation`. **Agreed end-state is approach C** — a dedicated `RecoveriesAffectingPVC` W bucket distinct from `technical_withheld` — tracked as a follow-up (see TASKS.md P6-H1-FUP-C). Migrate A→C before any context where the two deductions must show separately.
- **CC Response:** **Closed (interim A).** `build_bill_payload` (`backend/services/pvc_service.py`) now runs `SELECT COALESCE(SUM(amount),0) FROM recoveries WHERE bill_id=:bid AND affects_pvc_base = TRUE` and feeds the sum into `technical_withheld`; `on_account_amount` stays at gross (not netted). Comment in `backend/api/bills.py` corrected to match (it previously described approach B). Pinned by `test_p6_h1_recoveries_in_w.py` (2 tests): a TRUE recovery → `technical_withheld=10000` with `on_account` unchanged at `100000`; the filtered-zero case keeps `technical_withheld=0`. 125/125 backend. **Fixture note:** no in-tree fixture/seed currently carries affects_pvc_base recoveries, so no pinned engine output shifted; re-reconcile `bct_2425_252_*` if the demo seed later adds such a recovery.

### [HIGH] P6-H2 — Backend accepts non-positive bill/recovery amounts (frontend-only guard)

- **File:** `backend/api/bills.py:41` (`BillCreate`), `:145` (`RecoveryCreate`)
- **Verified:** `BillCreate` accepts any `bill_number: int` and `gross_amount: Decimal`; `RecoveryCreate` accepts any `amount: Decimal`. Tenant gates are present (`assert_contract_belongs_to_tenant` / `assert_bill_belongs_to_tenant`) — isolation is fine — but the UI's `> 0` checks are the *only* positivity guard. A direct API call can create a zero/negative gross bill, which becomes `on_account_amount` and feeds a plausible-but-wrong PVC run.
- **Proposed fix:** Pydantic boundary constraints — `bill_number` positive, `gross_amount`/recovery `amount` `Decimal > 0` (`condecimal(gt=0)` or field validator). Return structured 422 (`ValidationProblem`), consistent with existing error contract.
- **Test that would catch it:** assert `POST /contracts/{id}/bills` rejects `bill_number=0`, `gross_amount=0`, `gross_amount=-1`; assert recovery rejects `amount=0` and `amount=-1`.
- **CC Response:** **Closed.** `create_bill` now raises `ValidationProblem(field="bill_number")` for `<= 0` and `ValidationProblem(field="gross_amount")` for `<= 0`, both *before* the tenant gate (input shape leaks nothing tenant-specific). `create_recovery` raises `ValidationProblem(field="amount")` for `<= 0` after the existing `recovery_type` check. Matches the inline-`ValidationProblem` convention already used for `recovery_type`. Pinned by parametrized tests in `test_c1_bills_create.py` (gross `0/-1/-100000`, bill_number `0/-1`) and `test_p3_bf_3_recoveries.py` (amount `0/-1/-50.25`), each asserting `session.execute` is never awaited. 123/123 backend.

### [MEDIUM] P6-M3 — Malformed AG Grid numeric edits silently persist as `null`

- **File:** `frontend/components/contracts/ItemsGrid.tsx:71` (`numberValueParser`)
- **Verified:** `numberValueParser` returns `null` for any value `Number()` can't parse — including thousand-separated `"1,23,456"`. `saveAll()` sends that `null` through `itemPayload` (`:85`) and the backend accepts nullable rates/qtys, so a bad paste can silently erase `base_rate`/`agreement_rate`, changing downstream bill/PVC economics.
- **Proposed fix:** on unparseable input, reject the edit (keep old value) and surface a cell/form error instead of coercing to `null`; require finite decimals. Reuse the import parser's reject-with-errors behavior for consistency.
- **Test that would catch it:** parser/save test — malformed numeric input blocks save and does not emit a payload with `agreement_rate: null`.
- **CC Response:** **Closed.** Extracted a pure `lib/parseNumericCell.ts`: blank/null → explicit clear (`null`), strips thousand separators/spaces (`"1,23,456"` → `123456`), and **rejects** any remaining non-decimal input (`{ ok: false }`) — hex/exponent/`Infinity`/garbage included. `ItemsGrid.numberValueParser` now returns the prior `oldValue` and fires a `toast.error` on rejection instead of writing `null`. Pinned by `lib/parseNumericCell.test.ts` (5 cases incl. the null-erasure and non-decimal-notation paths). 45/45 vitest.

### [MEDIUM] P6-M4 — Calculate-PVC inline error drops engine validation detail

- **File:** `frontend/app/(app)/contracts/[id]/bills/[billId]/page.tsx:185`
- **Verified:** the PVC mutation runs `silent: true` then renders only `pvcRun.error.message`. For a structured `engine_validation_error`, that message is the generic header and the actionable `validation_errors` list is dropped — violates "blocking errors must be actionable" (`ENGINEERING_GUIDELINES`).
- **Proposed fix:** when `pvcRun.error instanceof ApiError && detail.code === "engine_validation_error"`, render the `validation_errors` list inline in the PVC card.
- **Test that would catch it:** simulate a 422 `engine_validation_error` with two validation errors → assert both strings render in the card.
- **CC Response:** **Closed.** Extracted pure `lib/pvcRunError.ts::describePvcRunError(error)` returning `{ validationErrors, message }`; for `engine_validation_error` it surfaces the full `validation_errors` list (guarding the array shape since the `ApiProblem` union's catch-all member defeats discriminant narrowing). The PVC card renders the list as `<ul>` under the header. Tested in `lib/pvcRunError.test.ts` (two-error list visible; non-validation ApiError + plain Error + non-Error fallbacks). 45/45 vitest.

## Most Recent Closed Cycle

**P5-REVIEW** — closed 2026-05-20. Adversarial pass by CC-S (Codex-S unavailable) on `saqlain/phase-5` (commits `29352a9` P5-001…P5-008 + `0e3b31f` P5-F1…F5). 14 findings: 1 CRITICAL, 3 HIGH, 6 MEDIUM, 4 LOW. All CRITICAL/HIGH/MEDIUM closed, L-4 closed inline, L-1/L-2/L-3 deferred to TASKS.md (P5-FUP-L1…L3). Pre-existing lint dirt on the branch resolved in the same chain.

Verification on clean Python 3.11 venv built from `backend/pyproject.toml` against the declared dep range floor (`fastapi==0.115.12`, `pytest-asyncio==1.3.0`): **82/82 backend** (up from 67; 15 new regression pins), **99/99 engine**, **16/16 frontend vitest** (new infra: `vitest@2.1.9`), **`next build` clean**, **`npm run lint` clean** (0 errors, 0 warnings).

Headline fixes:
- **C-1**: PEP 563 + `-> None` + 204 → `assert is_body_allowed_for_status_code` at decorator time. Dropped `-> None`; audit confirmed single offender across `backend/api/`.
- **H-1**: `parseTsvImport` extracted to a pure module with strict accept-lists for `is_cement_item` / `steel_subtype`; 12 vitest cases pin behavior.
- **H-2**: `FieldNotNullableProblem` + per-model NOT NULL constants reject explicit-null at the API boundary with structured 422.
- **H-3**: `setError` moved out of render body into `useEffect`.
- **M-3**: `CementSteelConflictProblem` enforced on POST + PUT (PUT uses effective-row merge); client Save All also gates on conflict.
- **M-4**: zod schema emits `null` for cleared nullable optional fields so the Edit form actually clears columns.
- **M-5**: `saveChanges` snapshots `savedKeys` and uses functional `setPending` filter so mid-flight toggles survive.
- **L-4**: UPDATE/DELETE on `contract_items` scoped to `(id, schedule_id)`.

Full per-finding detail (rationale, code references, test pins, audit conclusions) is preserved in git history. Commit chain:

```
3555474 P5-REVIEW lint cleanup: replace set-state-in-effect patterns
259d0cb P5-REVIEW: close findings + sync docs to actual post-remediation state
2a6a05a P5-REVIEW H-3, M-4, M-5: setError as effect + clear-nullable + race-safe save
a74bf1c P5-REVIEW H-2, M-3-backend, M-6, L-4: structured 422s + scoped writes
293b453 P5-REVIEW H-1, M-2, M-3-client: strict TSV parser + Add/Save gates
ab8b29c P5-REVIEW C-1: drop -> None on delete_contract_item
```

To read the full CC Response paragraphs that were appended under each finding, run:

```
git show 259d0cb -- REVIEW.md
```

## Resolution Protocol

1. Open cycles record findings inline with severity (CRITICAL > HIGH > MEDIUM > LOW), file references, and proposed fixes.
2. Each finding closes with a **CC Response** paragraph noting the fix and the test that pins it.
3. CRITICAL and HIGH are blockers per ENGINEERING_GUIDELINES branch hygiene; merge requires zero open in those tiers.
4. MEDIUM and LOW may defer to follow-up tasks in TASKS.md with explicit acceptance criteria.
5. On cycle close, this file collapses to a closure paragraph pointing at the merge SHA + per-finding detail in git history.
