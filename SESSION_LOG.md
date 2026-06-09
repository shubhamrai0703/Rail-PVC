# SESSION_LOG.md — Current Operational Log

Keep this file small.

Use it for current milestone decisions and recent sessions only.

## Canonical Links

- Current state: [STATUS.md](STATUS.md)
- Active task board: [TASKS.md](TASKS.md)
- Active review cycle: [REVIEW.md](REVIEW.md)
- Historical archive pointer: [archive/SESSION_LOG_ARCHIVE.md](archive/SESSION_LOG_ARCHIVE.md)

## Current Project State

- Phases 0–5 + all P5-FUP findings + SH-P5-1..4 + IDX-2..3 all on `main` (2026-05-30).
- **Phase 6 C-1 + C-2 merged to `main` (2026-06-02).**
- **IDX-4 (PR #11) + SH-P5-5/6 export (PR #12) merged via merge-commits (2026-06-02).** Both Shubham tasks done.
- **P6-REVIEW (Codex-S) closed + Phase 6 C-3 done — PR [#13](https://github.com/saqlainmmomin/Rail-PVC/pull/13) OPEN (`saqlain/p6-review` → `main`).** P6: 2 HIGH + 2 MEDIUM fixed (H1 interim approach A → `P6-H1-FUP-C`). C-3: `PUT /api/bills/{id}` + `DELETE .../recoveries/{rid}` + computed `net_amount` (formula flagged → `C-3-FUP-NET`). No open CRITICAL/HIGH — clear to merge.
- **Shubham's next task:** TBD.
- Test suite: **140/140 backend**, 99/99 engine, **45/45 frontend vitest**, `tsc` + `eslint` clean. Route count **42**.
- DB migrations at head (013 — `users.is_admin`). Run `013_admin_flag.py` on Supabase before entering new index months.
- Local backend: `cd backend && source .venv/bin/activate && uvicorn main:app --reload --port 8000`
- Local frontend: `cd frontend && npm run build && npm start` (port 3000) — always rebuild after code changes
- DB: Supabase at `ivselmhloegjmqrjekcy.supabase.co`.
- Tenant provisioned for `saqlainmmomin@gmail.com` — tenant_id `bd589426-93ba-4847-b5f3-1f69b020b4c0`.

## Recent Sessions

### Session 26 — 2026-06-08 (Phase 6 C-3 — bill edit + recovery delete + net_amount)

Implemented Phase 6 C-3 on `saqlain/p6-review` (continuing from the P6-REVIEW work). TDD throughout.

- **`PUT /api/bills/{id}`** — partial header edit via `model_fields_set` (mirrors `update_contract`). Rejects explicit-null on NOT NULL columns (`bill_number`, `measurement_date`) with `FieldNotNullableProblem`; P6-H2-parity positivity guards on `bill_number`/`gross_amount`; 409 `ConflictProblem` on `UNIQUE(contract_id, bill_number)`; empty body → current row. Returns the row with computed `net_amount`.
- **`DELETE /api/bills/{id}/recoveries/{rid}`** — new `_assert_recovery_under_bill_for_tenant` two-step gate (bill→tenant, recovery→bill; both failures collapse to 404 per P3-06); 204, no `-> None` annotation (fastapi 0.115 PEP-563 gotcha); DELETE scoped to `(id, bill_id)`.
- **`net_amount` computed on read** — extracted `_NET_AMOUNT_EXPR` SQL constant, used in GET list, GET detail (now via shared `_select_bill`), and the PUT re-projection. Backend owns the derived value; never persisted, so it can't drift.
- **DECISION (Saqlain) — net_amount = gross − Σ(recoveries WHERE `affects_pvc_base=FALSE`), FLAGGED.** PVC-affecting recoveries are treated as notional (they reduce W via H1, not net payable). Explicitly not certain to be the right model — `C-3-FUP-NET` tracks validating it against a real Railway submission; flip the filter if net payable should net ALL recoveries. (Same "ship a documented interim, name the revisit" pattern as H1.)
- **Frontend** — `BillHeaderForm` inline edit (react-hook-form + zod; 409 surfaced inline since `bill_number` uniqueness is server-owned, unlike the P5-FUP-L3 agreement_number case); per-row recovery delete (confirm → DELETE → invalidates recoveries + bill so net refreshes); net-amount label clarified to "net of non-PVC recoveries".
- **Route count 40→42**; `test_p3_08` assertion bumped. **140/140 backend** (+15: PUT/DELETE mock tests + the net formula run against real `_NET_AMOUNT_EXPR` via aiosqlite), 99/99 engine, 45/45 vitest, tsc+eslint clean. Did not run `next build` (8 GB box); tsc covers types.
- **Env reminder:** the repo has both a miniconda 3.13 env and `backend/.venv`; pytest + the session-installed `aiosqlite` live in miniconda — use `~/miniconda/bin/python -m pytest`.
- **Shipped:** pushed `saqlain/p6-review` and opened **PR [#13](https://github.com/saqlainmmomin/Rail-PVC/pull/13)** (P6-REVIEW + C-3) → `main`. Clear to merge (no open CRITICAL/HIGH).

### Session 25 — 2026-06-04 (P6-REVIEW — Codex-S adversarial pass + remediation)

Opened the first adversarial review of the merged Phase 6 Bill Entry UI (C-1/C-2/fixes), which had landed without one. Drove Codex-S via the `codex` CLI; prompt archived at `REVIEW_P6_PROMPT.md`. Codex returned **2 HIGH, 2 MEDIUM, 0 CRITICAL/LOW**; CC-S code-verified all four against `main` before remediating one at a time (failing test → fix → green). Branch `saqlain/p6-review`.

- **P6-H1 (HIGH) — `affects_pvc_base=TRUE` recoveries silently ignored by W derivation.** `build_bill_payload` hard-coded `technical_withheld=Decimal("0")` and never queried `recoveries`, so a recovery flagged to reduce the PVC base did nothing — a plausible-but-wrong number. **Saqlain's decision: interim approach A now, approach C later, and A is explicitly not the best shape.** A = sum `affects_pvc_base=TRUE` recoveries into the engine's existing `technical_withheld` bucket (named W subtraction per PRODUCT.md rule 1, zero engine-model change); `on_account` stays at gross (not netted — that was the rejected approach B). Known limitation: A overloads `technical_withheld`, conflating genuine technical withholding with PVC-affecting recoveries. End-state C (a dedicated `RecoveriesAffectingPVC` W bucket) is tracked as `P6-H1-FUP-C`. Fix in `pvc_service.py` + corrected the stale `bills.py` comment that described approach B. 2 tests (`test_p6_h1_recoveries_in_w.py`).
- **P6-H2 (HIGH) — backend accepted non-positive bill/recovery amounts.** UI `>0` guard was the only one; direct API calls could create zero/negative `gross_amount` (→ `on_account`) / `bill_number` / recovery `amount`. Added `ValidationProblem` checks at the handler boundary (before the tenant gate; input shape leaks nothing). +8 parametrized tests across `test_c1_bills_create.py` + `test_p3_bf_3_recoveries.py`.
- **P6-M3 (MEDIUM) — malformed AG Grid numeric edits silently became `null`.** Old parser coerced `"1,23,456"`/garbage → `null`, erasing rates on save. Extracted pure `lib/parseNumericCell.ts` (strips thousand separators, rejects non-decimal incl. hex/exponent/`Infinity`); the grid parser now keeps `oldValue` + `toast.error` on reject. +5 vitest.
- **P6-M4 (MEDIUM) — Calculate-PVC card dropped the engine `validation_errors` list.** It rendered only the generic header. Extracted pure `lib/pvcRunError.ts::describePvcRunError` (guards the array shape since the `ApiProblem` union's catch-all defeats discriminant narrowing); card now lists every validation error. +4 vitest.
- **Env note.** `aiosqlite` (declared dep, `pyproject.toml:25`) was missing from this venv — silently erroring 35 tests until installed. Reconfirms `feedback_aiosqlite_test_limits`.
- **Verification.** 125/125 backend, 99/99 engine, 45/45 frontend vitest, `tsc` + `eslint` clean, route count unchanged at 40. UI changes (M3 toast / M4 list) covered by pure-fn tests + types/lint; not browser-clicked (8 GB box, `next dev` avoided).

### Session 24 — 2026-06-02 (Review + merge of Shubham PRs #11 and #12)

Reviewed and merged Shubham's two open PRs into `main` via merge-commits, with one follow-up fix folded in.

- **PR #11 — IDX-4 Index Manager UI (`shubham/idx-4`, frontend-only).** `/indices` series list + `/indices/[series]` detail (observations table + `IndexMonthForm`, react-hook-form + zod). `<input type="month">` is coerced to a first-of-month date for the backend validator; `value` sent as a string to preserve `Decimal` precision. Optimistic-UI admin gate — the form renders for everyone, the backend `require_admin` stays the sole enforcement point (per P3-03), and typed 403 `forbidden` / 409 `conflict` map to inline messages. `lib/indices.ts` (`humanizeSeries`) + 3 vitest. Route count unchanged.
- **Follow-up fix on merge.** The list page linked with a raw `s.name` while the detail page + month form used `encodeURIComponent`. Aligned them (commit `65519d3`) so non-trivial series names route correctly.
- **PR #12 — SH-P5-5/6 export endpoints (`shubham/sh-p5-exports`).** `GET /api/pvc-runs/{id}/export/{excel,pdf}`. Shared gate: tenant-check via run→contract (404, indistinguishable per P3-06) → status must be `Approved` (else 422 `RunNotApprovedProblem`, `code=run_not_approved`) → `Content-Disposition: attachment`. `api/exports.py` is thin (gating + wiring); `services/exports.py` holds pure byte-generators built directly from the run + `pvc_components` rows — **no engine export module existed** (`engine/engine/` has none), so "wire it" had nothing to wire. Route count 38→40; `test_p3_08_clean_import.py` assertion bumped in the same diff.
- **Library deviation accepted — fpdf2 over WeasyPrint.** WeasyPrint needs GTK/Pango/Cairo native libs that aren't pip-installable on the Windows dev/test env, which would violate "clean checkout boots from declared deps" (the export router wouldn't even import). Both `fpdf2` and `openpyxl` are pure-Python. WORKPLAN G-3 only requires an `application/pdf` download; submission-format / column-order parity is explicitly **deferred to P8-REVIEW**, so this is styling-only, not a contract change.
- **Verification before push.** Test-merged each PR against `main` (both clean; main was still at route count 38, the P5-IMP commit was frontend-only), then verified the combined merge had no conflict despite both touching `TASKS.md`. Integrated `main`: **115/115 backend pytest**, **36/36 frontend vitest**, `tsc` + `eslint` clean. Both PRs auto-closed as MERGED after push (`0b96ec5..3158257`).

### Session 23 — 2026-06-02 (P5-IMP smart items-import — frontend on `saqlain/p5-imp`)

Built a smart Excel/paste items-import flow to replace the rigid positional TSV modal. Branch `saqlain/p5-imp` off `main`. **Frontend-only for this PR**; backend pieces (LLM mapper, template CRUD, migration 014) are committed on disk as untracked-then-staged additions but not wired into `main.py` / `pyproject` / `test_p3_08`. Backend integration ships in a follow-up branch.

- **What was the pain.** Session 15's positional-paste modal required the user to pre-format their xlsx into 9 columns in a fixed order with fixed tokens (TRUE/FALSE, tmt/angles/...). Real BOQs vary by zone and contractor; users were hand-massaging Excel before paste.

- **New flow (`components/contracts/ImportRowsModal.tsx`).** One modal, progressive disclosure: (1) tabbed source — drop `.xlsx` or paste TSV; (2) for xlsx, pick sheet + header-row; (3) column-mapping table auto-filled by a deterministic header fuzzy matcher (Option A); (4) preview + commit. AI button ("Auto-map with AI", Option B) is rendered disabled with a tooltip — backend ships in follow-up. Template save/apply UI omitted from this PR. Existing M-2 invariant preserved: any row parse error blocks the import; no silent partial commit.

- **xlsx library.** `xlsx` (SheetJS) on npm is unmaintained with known CVEs (Prototype Pollution + ReDoS). Used **`exceljs`** instead. Lazy-imported via dynamic `import()` in `lib/parseXlsx.ts` so non-import pages don't pay the bundle cost.

- **Pure modules + tests.** `lib/fuzzyHeaderMap.ts` (synonym tables + token-set scoring + collision resolution + required-field detection); `lib/normalizeImportRows.ts` (mapping + raw rows → ParsedRow[], preserving the H-1 no-silent-coercion rule for `is_cement_item` / `steel_subtype`, plus value-normalization hooks for the future AI mapper). 17 new vitest cases covering railway-zone vocabulary (BOQ Item, UOM, SOR Rate, Quoted Rate, etc.), tie-breaking, thousand-separator stripping, and the H-1 invariant. **33/33 frontend vitest, `next build` + `npm run lint` clean.**

- **In-render state-adjust pattern.** When source headers change, `mappingOverrides` resets to the fuzzy-matched defaults. Used React 19's "adjust state during render" with a `lastHeadersKey` guard (per the P5-FUP-L cleanup precedent) — `useEffect`+`setState` would have tripped the `react-hooks/set-state-in-effect` rule.

- **Backend code on disk (not wired).** `backend/migrations/versions/014_import_templates.py` (jsonb mapping + value_normalizations, `UNIQUE(tenant_id, name)`, RLS), `backend/api/imports.py` (templates CRUD + `POST /api/imports/suggest-mapping`), `backend/services/llm.py` (Anthropic Haiku 4.5 with prompt-cached system prompt + structured-output schema). Follow-up branch lands router include, anthropic dep, `.env.example` entry, route-count bump 38→42, and backend pytest.

- **Demo smoke-test fixes (folded into this merge, originated on `saqlain/phase-6`).** Two bugs surfaced in manual demo testing of the Phase 5–6 UI:
  - **Items grid showed "Invalid Number" in every numeric column.** Root cause was AG Grid v35's `cellDataType: "number"` machinery: its built-in valueFormatter prints the literal string `Invalid Number` whenever `typeof value !== "number"`, and grid type-inference re-applies the number type even after the explicit declaration is dropped. The data path itself was clean end-to-end (Postgres `NUMERIC` → FastAPI `jsonable_encoder` serializes `Decimal`→`float` → `JSON.parse` yields JS numbers). Fix in `frontend/components/contracts/ItemsGrid.tsx`: set `cellDataType: false` on the four numeric columns (original_qty, revised_qty, base_rate, agreement_rate) and supply module-scope `numberValueParser` / `numberValueFormatter` that null-coerce blanks and tolerate string/number input. Boolean column keeps `cellDataType: "boolean"`.
  - **No "Calculate PVC" trigger anywhere on the bill flow.** The engine endpoint (`POST /api/contracts/{id}/pvc-runs`, body `{bill_id}`) was fully built but had no caller. Added a "Price Variation (PVC)" card to `frontend/app/(app)/contracts/[id]/bills/[billId]/page.tsx`: a `useMutation` that POSTs with a fresh `crypto.randomUUID()` Idempotency-Key, renders Total PVC / negative carry-forward / quarter-used on success, shows inline errors (`silent: true`), and invalidates the `bill` + `bill-lines` queries so generated lines + recomputed amounts refresh.
  - Verified before merge: **33/33 frontend vitest, 106/106 backend pytest, `next build` clean.**

### Session 22 — 2026-05-31 (Phase 6 C-1 + C-2)

Implemented Phase 6 bill-entry UI through C-2 on `saqlain/phase-6`.

- **Stale kickoff premise caught.** The kickoff said `POST /api/contracts/{id}/bills` didn't exist; it has been on `main` since Phase 3 remediation (commit `739bc4f`). And the WORKPLAN's "no UNIQUE constraint" open question was wrong — migration 003 already declares `UNIQUE(contract_id, bill_number)`. So C-1 backend was a **hardening pass**, not greenfield, and **no migration was needed**.

- **C-1 backend (`backend/api/bills.py`):** swapped the inline ownership SELECT for `assert_contract_belongs_to_tenant`; wrapped the INSERT to catch the unique-violation `IntegrityError` → `ConflictProblem(409)` carrying `bill_number`; tightened `BillCreate` to `{ bill_number, bill_date, measurement_date, gross_amount }` and **dropped client-supplied `net_amount`** (ENGINEERING_GUIDELINES: backend owns derived financial values). Test-first: `test_c1_bills_create.py` (valid 201 / wrong-tenant 404 / duplicate 409), boundary-mocked like the SH-P5 suite. **106/106 backend.** No new route — count stays 38.

- **C-1 frontend:** separate `/contracts/[id]/bills` page (not a tab) + `BillForm`. Duplicate `bill_number` renders inline via `detail.code === "conflict"` (toast suppressed for that case); `gross_amount` sent as string to preserve decimal precision. On create → invalidate list (no redirect — detail page is C-2). "Bills →" link added to the contract detail header.

- **C-2 frontend:** `/contracts/[id]/bills/[billId]` — header fields, read-only **plain** lines table (empty until a Phase 7 PVC run; plain table chosen over AG Grid since data is read-only), recoveries table + `RecoveryForm` (`POST /api/bills/{id}/recoveries`).

- **Decisions logged in WORKPLAN/TASKS:** bill_number unique per-contract; bills as a separate page; net_amount computation deferred to C-3.

- **Not done:** live browser smoke (8 GB dev-box constraint — verified type-check, lint, vitest instead). C-3 (needs new `PUT /api/bills/{id}` + recovery DELETE) deferred — will ask before starting per kickoff rules.

### Session 21 — 2026-05-30 (PR catch-up + IDX-2..3)

Returned after a gap. Reviewed and merged all three open PRs, then implemented IDX-2..3.

- **PR #9 (P5-FUP-L2, `shubham/p5-fup-l2`)** — Merged clean. `ItemsGrid.deleteSelected` now shows separate saved vs unsaved counts; new-only selections skip the confirm modal entirely. 1 file, no logic change.

- **PR #7 (SH-P5-1..4, `shubham/phase-5-backend`)** — Full adversarial review (SH-P5-REVIEW). Tenant isolation correct (`assert_contract_belongs_to_tenant` / `assert_bill_belongs_to_tenant`); empty-list contract correct; 12 tests following the boundary-mock pattern; route count 31→35 pinned. No findings. Merged.

- **PR #8 (IDX docs, `shubham/idx-flag`)** — Docs-only gap flag for WPI/JPC Index Manager. Caught sequencing error in PR: it claimed IDX-2..3 block Phase 7, but seed data ends Dec-2025 and we're already May 2026 → **IDX-2..3 actually block Phase 6**. Corrected TASKS.md in a commit before merging.

- **IDX-2..3 (CC-S, 2026-05-30)** — Implemented the index write backend:
  - Migration 013: `users.is_admin BOOLEAN NOT NULL DEFAULT FALSE`
  - `ForbiddenProblem` (403) added to `services/errors.py`
  - `require_admin` dependency in `services/auth.py` (403 for any non-admin user)
  - `GET /api/indices` — list all series
  - `GET /api/indices/{series_name}` — series + full observation history
  - `POST /api/indices/{series_name}/months` (admin-only) — insert month; 422 if day≠1; 409 on UNIQUE violation; 404 if series unknown
  - P3-03 regression still passes (new POST is at a different path than the banned `/api/index-observations`)
  - 10 new tests; full suite 91→103/103

**Phase 6 is now fully unblocked.** All blocking tasks (SH-P5-1..4, IDX-2..3) are on `main`. Run migration 013 on Supabase and seed Jan–May 2026 index months before the first bill entry.

### Session 20 — 2026-05-21 (P5-FUP-L3 + P5-FUP-L1 deferred LOWs)

Started smoke prep on merged `main` and cleared two of the three deferred LOW findings while the dev servers were warm.

- **P5-FUP-L3 — Unreachable 409 affordance on `agreement_number`.** Migration 002 never added a UNIQUE on `agreement_number`, so the backend can't raise a conflict, but the frontend was branching on `err.status === 409` in two places (create + edit) and the form carried a `serverFieldError` prop wired through a `useEffect` (the H-3 effect-pattern only existed because of this dead path). Removed the prop + effect + import in `ContractForm.tsx`; removed the `useState` and try/catch in `contracts/new/page.tsx` (`apiFetch` already toasts on error); removed the `onError` 409 branch and `serverFieldError` state in `OverviewTab` (`[id]/page.tsx`). Updated WORKPLAN Q6 to drop the false "server owns uniqueness" claim and note the path back if uniqueness ever becomes a product requirement. Net deletion. Lint + typecheck clean.

- **P5-FUP-L1 — Partial-success state drift in `ExtraItemDecisionList.saveChanges`.** Root cause: `Promise.all` short-circuits on the first rejection, but the other POSTs have already committed server-side. The catch path left `pending` untouched, leaving fulfilled rows showing as unsaved while the server held the new value — the dirty indicator was lying. Switched to `Promise.allSettled`, dropped the fulfilled keys from `pending`, kept failed keys in `pending` for retry (POST is idempotent — already established in M-5's audit), and changed the toast copy on partial failure to "N of M failed to save". The M-5 mid-flight-toggle invariant is preserved because we still filter from `prev` rather than overwriting.

- **Not done.** P5-FUP-L2 (delete-confirm wording for mixed selection) — still owned by [CC-SH]. Smoke pass also still pending — servers are up but Saqlain hasn't run the table yet.

### Session 19 — 2026-05-20 (P5-REVIEW remediation + merge to `main`)

CC-S ran the adversarial review on `saqlain/phase-5` (Codex-S unavailable this cycle) and posted 14 findings to `REVIEW.md`. Then the same chat remediated all of them. Worked one finding at a time with TDD inside the loop — failing test first, fix, green — and audited each finding for the same class of bug elsewhere before patching the one line the review named.

- **C-1 (CRITICAL).** Root cause was the interaction between `from __future__ import annotations` (PEP 563) and FastAPI 0.115.x's deferred resolution of `-> None` on a 204 handler. The string `"None"` resolves to `NoneType` (the class), FastAPI builds a non-None `response_field`, and the 204-no-body assertion fires at decorator time. Dropped `-> None` on `delete_contract_item`. Audit: single 204 handler and single `-> None` handler in the whole backend; same line. All 10 api modules use the future import, so the bug class would re-arm on any future 204 endpoint someone adds — left an inline comment as a tripwire for the next contributor. Regression pin is the pre-existing `test_p3_08_clean_import.py` which failed-to-collect before the fix.

- **H-1 / M-2.** `parseTsvImport` silently coerced anything-not-in-`["true","1","yes"]` to false for `is_cement_item`, and let any string through verbatim as `steel_subtype`. Extracted the parser to `frontend/lib/parseTsvImport.ts` (pure module) with explicit accept-lists; "Tru" and "TMT" now reject the row to `errors[]`. Added `vitest@2.1.9` and 12 parser tests. Also gated the "Add N rows" button so any parse error blocks the import (M-2).

- **H-2 / M-3 / M-6 / L-4.** Added `FieldNotNullableProblem` (code `field_not_nullable`) and `CementSteelConflictProblem` to `services/errors.py`. Both PUT handlers now reject explicit `null` on NOT NULL columns at the API boundary instead of letting Postgres raise an unstructured 500. PUT uses an effective-row merge for the cement+steel check so a PUT that only sets one field is also caught. UPDATE/DELETE on `contract_items` scoped to `(id, schedule_id)` for defense in depth. 15 new backend tests across `test_p5_001_contracts_put.py` and `test_p5_f3_items_crud.py` — all fail on the pre-remediation handlers.

- **H-3.** `setError` moved out of `ContractForm`'s render body into `useEffect([serverFieldError, setError])`. No RTL test added — installing `@testing-library/react` for one render-lifecycle assertion is bigger scope than the finding warrants; the verification gate's manual smoke covers the behavior pin.

- **M-4.** Zod schema now emits `null` for cleared nullable optional fields (`agreement_number`, `loa_*`, `*_date`, `contract_value`, `bid_amount`, `work_description`) so the Edit form actually clears those columns. `overall_rebate` keeps "blank → drop from body" because it's NOT NULL — and H-2's backend rule would reject an explicit null on that column anyway, so the schema must not surface one. Required typing the form against `z.input` (raw `string | undefined`) and `z.infer` (post-resolver `string | null`) via `useForm<FormInput, unknown, ContractFormValues>`. 4 schema-test cases pin the null semantics.

- **M-5.** `ExtraItemDecisionList.saveChanges` previously blew away `pending` on success — a toggle mid-flight got silently discarded. Now snapshots `savedKeys` at the start of save and uses functional `setPending(prev => filter)` to clear only the saved keys.

- **L-4** inline. **L-1 / L-2 / L-3** deferred to `P5-FUP-L1/L2/L3` in TASKS.md with acceptance criteria.

- **Lint dirt.** The branch had two pre-existing `react-hooks/set-state-in-effect` errors on `ItemsGrid.tsx` (modal reset effect + items-loaded hydration effect). Saqlain asked these to be cleared before merge. Modal: parent now gates the JSX on `importOpen` so the modal mounts fresh each open — the reset effect is dead code. Hydration: replaced the effect with React 19's documented "adjust state during render" pattern, guarded by `hydratedAt` (TanStack Query's `dataUpdatedAt` timestamp). Also removed two now-stale `eslint-disable-next-line no-console` directives in app-level error boundaries. `npm run lint` is now 0/0.

- **Verification gate (clean Python 3.11 venv, declared dep floor `fastapi==0.115.12`):** 82/82 backend (up from 67; 15 new regression pins), 99/99 engine, 16/16 frontend vitest (new infra), `next build` clean, `npm run lint` clean. The previous "67/67" was correct against the implementer's locally-installed FastAPI 0.136 (which has the upstream fix); on the declared floor the suite couldn't even be collected. Now reproducible.

- **Merge.** Fast-forwarded `main` to `saqlain/phase-5` after the verification gate passed. **Not pushed** — awaits manual push by Saqlain. Saqlain will run the WORKPLAN smoke table in tomorrow's session.

- **Lessons captured during the cycle (worth memorising):**
  - "Same dep range" doesn't mean "same FastAPI minor." The implementer's `0.136.1` had the upstream `response_field` fix the `0.115.12` floor lacks. A clean venv built straight from `pyproject.toml` against the *floor* is the only way to actually certify "clean checkout boots from declared deps."
  - Pydantic v2's `Optional[T] = None` field shape is ambiguous in PUT semantics — "client sent null" and "client omitted the key" both produce `None`. The fix is a per-model NOT NULL set + iterate `model_fields_set` at the handler; don't try to express it at the field level.
  - For "external query state → local editable state," React 19's "adjust state during render guarded by a snapshot key" pattern beats `useEffect`. Lint won't yell, and TanStack Query's `dataUpdatedAt` is the natural snapshot key.

### Session 18 — 2026-05-20 (P5-F1…F5 implementation landed)

- Implemented all five UX polish fixes in one session on `saqlain/phase-5`.
- **F1** — `TooltipHeader` custom AG Grid `headerComponent` with ⓘ icon + native `title` attribute; wired on `original_qty`, `revised_qty`, `base_rate`, `agreement_rate`, `is_cement_item`, `steel_subtype`. No external tooltip library.
- **F2** — "Import rows" toolbar button opens `ImportRowsModal` (absolutely-positioned overlay, no modal lib). `parseTsvImport` splits on `\n` / `\t`, normalises `is_cement_item` (TRUE/true/1/yes → true), and accepts blank `steel_subtype` as null. Preview table + parse-error list before commit; rows append as `_rowState: "new"`.
- **F3 backend** — `PUT` + `DELETE /api/schedules/{schedule_id}/items/{item_id}` in `backend/api/contract_items.py`. New helper `_assert_item_under_schedule_for_tenant` runs the two-step gate: first `assert_schedule_belongs_to_tenant` (tenant ownership of the schedule), then verify the item's `schedule_id` matches the URL. Either failure → 404 NotFoundProblem. `ContractItemUpdate` uses the established `model_fields_set` partial-update pattern; `steel_subtype` keeps the explicit ENUM cast (`CAST(:steel_subtype AS steel_subtype)`). 6 new tests in `test_p5_f3_items_crud.py` (PUT valid / wrong-schedule / wrong-tenant; DELETE valid / wrong-schedule / wrong-tenant). Route count assertion in `test_p3_08_clean_import.py` bumped 29 → 31.
- **F3 frontend** — `_rowState: "new" | "dirty" | "persisted"` per row. Loaded items default to `persisted`; cell edits demote `persisted → dirty` (never demote `new`). Save All routes `new → POST`, `dirty → PUT`, `persisted → skip`. Added a multi-select checkbox column (`checkboxSelection` on `item_code`, `headerCheckboxSelection`, `rowSelection="multiple"`, `suppressRowClickSelection`). "Delete selected (N)" appears when ≥1 row is selected; new rows are removed in-memory without API calls or confirms; persisted/dirty rows trigger `window.confirm(...)` then sequential `DELETE` calls, with the query invalidated only when persisted rows were touched.
- **F4** — One-line banner copy rewrite ("One or more items are marked as both a cement item and a steel item. Each item can only belong to one — please correct before saving.").
- **F5** — `ExtraItemDecisionList` rewritten around a local `pending: Record<itemId, Verdict>` map. Toggling a row updates `pending` only; clicking back to the server value drops the entry (so it stops showing as unsaved). Effective verdict for a row = `pending[id] ?? serverVerdict`; the undecided-count banner reads this merged view. "Save changes (N)" is enabled only when `pending` is non-empty, runs `Promise.all` of POSTs with `silent: true` (we render our own toast), preserves `pending` on failure for retry, and invalidates the decisions query on success. Per-row amber dot indicates a pending change.
- **Verification** — `cd backend && uv run python -m pytest -x -q` → 67 passed (61 prior + 6 new). `cd frontend && npm run build` → clean, 0 TS errors.
- **Lessons captured (used during implementation):**
  - aiosqlite doesn't bind `Decimal` to parameter values — tests with NUMERIC columns must use plain ints/floats. The Postgres `::text` casts in SELECT-back paths still fail under aiosqlite; the established pattern is to catch `OperationalError` and verify the UPDATE/DELETE landed via a plain follow-up `SELECT` (see `test_p5_001_contracts_put.py`).
  - The two-step gate (`assert_schedule_belongs_to_tenant` then per-item membership check) preserves the "wrong-tenant collapses to the same 404 as wrong-schedule" rule — no information leak.
  - `apiFetch` supports `{ silent: true }` to suppress the default Sonner toast; useful when the caller renders its own success/error UI (F5 batch save).

### Session 17 — 2026-05-20 (Smoke test complete; BUG-1 fixed; P5-F1…F5 planned)

- Restarted backend + frontend. BUG-1 diagnosed from browser devtools Network tab: actual error was **500 Internal Server Error**, not a network failure. The "Network error" toast was a misdiagnosis from the previous session.
- Root cause of 500: `INSERT INTO schedules VALUES (:stype::schedule_type …)` — SQLAlchemy's asyncpg dialect left `:stype` unsubstituted because `::schedule_type` immediately follows and breaks named-param parsing. Fix: `CAST(:stype AS schedule_type)`. One-line change in `backend/api/schedules.py`. CORS and auth were never the issue.
- Smoke test completed: all 7 flows green (Create, Edit, Validation, Schedules, Items, Mutual-exclusion warning, Extra-items).
- Saqlain ran live testing and raised 5 UX observations:
  1. Column tooltips needed on confusing Items grid fields (original_qty, revised_qty, base_rate, agreement_rate, is_cement_item, steel_subtype)
  2. No Excel paste support — multi-row copy from Excel collapses into a single cell. Decision: Option B (paste-area import dialog with TSV parsing + row preview), with Option C (file import) as a post-MVP addition.
  3. Items Save All always creates new rows — no update or delete. Decision: Option B (checkbox-select + "Delete selected" with confirmation; Save All distinguishes new/dirty/persisted rows; backend needs PUT + DELETE endpoints for items).
  4. Mutual-exclusion warning uses engine jargon ("engine treats these as mutually exclusive buckets"). Fix: user-facing copy.
  5. Extra-items auto-save feels unsafe. Decision: Option B (staged local changes + explicit "Save changes" button; batch POST on save).
- All 5 issues captured as P5-F1…F5 in TASKS.md. Implementation prompt written in WORKPLAN.md.
- P5-REVIEW is now gated on P5-F1…F5 landing.

### Session 16 — 2026-05-20 (Partial smoke; BUG-1 misdiagnosed as network error)

- Rebuilt frontend after finding stale bundle. Flows 1–3 (Create, Edit, Validation) passed.
- Flow 4 (Schedules) blocked — "Network error" toast on schedule POST. Investigated CORS + auth, found nothing. Root cause not identified (diagnosed in Session 17).
- `base_month` edit-mode fix committed to working tree (`toFormDefaults` slices to `YYYY-MM`).
- Servers shut down at end of session.

### Session 15 — 2026-05-19 (Phase 5 UI implementation — P5-001…P5-008 landed on `saqlain/phase-5`)

- Implemented all eight Phase 5 tasks end-to-end in a single session: backend PUT + expanded GET (P5-001), frontend deps + zod/zone constants (P5-002), `/contracts/new` form (P5-003), `/contracts/[id]` detail with tab shell (P5-004), Overview inline edit (P5-005), Schedules tab + `ScheduleForm` (P5-006), Items tab + AG Grid `ItemsGrid` (P5-007), extra-items decision page (P5-008).
- Backend: 6 new tests in `test_p5_001_contracts_put.py` (wrong-tenant 404, unknown 404, invalid zone 422, base_month day≠1 422, `model_fields_set` semantics, valid partial update); route count assertion in `test_p3_08` bumped 28 → 29.
- Frontend: `base_month` field uses `setValueAs` to auto-append `-01` before submit; `overall_rebate` UI says "as decimal, 0.15 = 15%" per OQ-5; items grid renders a soft warning when a row is marked both `is_cement_item=true` AND has `steel_subtype` set (engine buckets are mutually exclusive); decision toggles use TanStack `onMutate` for optimistic update + rollback on error.
- AG Grid theming via `themeQuartz.withParams({…})` + `AllCommunityModule` registration (v35 API; the docs are right, training data was wrong).
- Verified: 61/61 backend pass; `next build` reports 11 routes including 3 new (`/contracts/new`, `/contracts/[id]`, `/contracts/[id]/extra-items`).
- Branch `saqlain/phase-5` is **uncommitted** as of this entry — needs commit + push + PR + live smoke before P5-REVIEW.

### Session 14 — 2026-05-19 (TEST-P3P4 closed; Phase 5 + SH-P5 parallel tracks opened)

- TEST-P3P4 (TEST-01…07) confirmed complete and merged to `main` (fast-forwarded from `saqlain/test-p3p4`). M-1/M-2 closed.
- OQ-2 decided: B-5 items grid uses **explicit "Save All" button** — validates whole sheet client-side, then POSTs rows sequentially with progress indicator. Rationale: BOQ entry is one-time bulk import; per-row save has no atomicity and creates silent partial imports on failure.
- Shubham's parallel track (SH-P5) defined: GET bill endpoints (G-1/G-2) + export routes (G-3) on `shubham/phase-5-backend`.
- WORKPLAN.md + backend/Untitled pushed to `main` (commit `b5c0d13`).
- All context docs audited and brought to current state.

### Sessions 10–13 — 2026-05-17 (archived)

Detailed notes moved to git history and [archive/SESSION_LOG_ARCHIVE.md](archive/SESSION_LOG_ARCHIVE.md). Summary:

- **Session 10:** Phase 3 remediation (P3-01…P3-09) on `saqlain/phase-3-remediation`. Key decisions: src-layout engine packaging, API-layer tenant isolation (no RLS), pure-function domain logic, DB-enforced idempotency, typed error contract.
- **Session 11:** PR #3 merged; Codex-S post-merge regression clean (99/99 engine + 31/31 backend).
- **Session 12:** Phase 4 P4-001/002/007 — Supabase auth wiring, login/signup pages, typed `ApiProblem` client.
- **Session 13:** Phase 4 P4-004/006 complete — contract list dashboard + typed API schema generated. Infra: switched to JWKS/ES256, rotated DB password, applied DDL for migrations 010–012, provisioned tenant.

## Current Decisions

- Active docs should be read in this order: STATUS → PRODUCT → ARCHITECTURE → TASKS → REVIEW
- Historical detail should not live in the active context set when a summary/link is sufficient
- `CLAUDE.md` and `CODEX.md` act as startup instructions, not duplicate project context
- B-5 items grid: **Save All button** (not per-row save). Decided 2026-05-19. See Session 14.

## Next Actions

1. [Saqlain] Run the WORKPLAN smoke table tomorrow against the merged `main` (Create, Edit + clear optional field, Validation, Schedules, Items + bad-row TSV paste, Mutual-exclusion, Extra-items + mid-flight toggle, 409 inline error). Confirm `main` is push-ready.
2. [Saqlain] Push `main` to origin once smokes pass.
3. [CC-S] Address `P5-FUP-L1/L2/L3` (deferred LOW findings) post-merge.
4. [CC-SH] Continue SH-P5 (G-1 → G-2 → G-3); request `SH-P5-REVIEW` before merge.
