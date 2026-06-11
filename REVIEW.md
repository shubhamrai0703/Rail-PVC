# REVIEW.md — Active Review Cycle

Use this file for the current live review state only.

## Canonical Links

- Current project state: [STATUS.md](STATUS.md)
- Coding/review rules: [ENGINEERING_GUIDELINES.md](ENGINEERING_GUIDELINES.md)
- Current task board: [TASKS.md](TASKS.md)
- Historical review pointer: [archive/REVIEW_ARCHIVE.md](archive/REVIEW_ARCHIVE.md)

## Active Cycle

**P7-REVIEW** — opened 2026-06-10. Adversarial pass by **CC-S** (Fable 5) on `saqlain/phase-7` (PR [#14](https://github.com/saqlainmmomin/Rail-PVC/pull/14)) implementing Phase 7 D-1…D-4: PVC run results UI, approve flow, export buttons, run-history list, migration 015.

**Scope (on `saqlain/phase-7`):**
- `backend/api/pvc_runs.py` (new `GET /contracts/{id}/pvc-runs`; extended `GET /pvc-runs/{id}` with result totals)
- `backend/services/pvc_service.py` (persist_run_result — writes total_pvc/negative_carry_forward/quarter_used at INSERT)
- `backend/migrations/versions/015_pvc_run_outputs.py` (adds 3 nullable NUMERIC/TEXT cols to pvc_runs)
- `backend/tests/test_d1_pvc_run_results.py` (5 new tests)
- `frontend/app/(app)/contracts/[id]/bills/[billId]/page.tsx` (run-history list, Calculate-card link)
- `frontend/app/(app)/contracts/[id]/bills/[billId]/runs/[runId]/page.tsx` (new run results page)
- `frontend/lib/api/client.ts` (new `apiDownload` helper)
- `frontend/lib/pvcRunStatus.ts` + `pvcWDerivation.ts` (pure helpers + 7 vitest)

**Status (2026-06-11): ALL HIGH + MEDIUM CLOSED — merge unblocked.** H1/H2/M2/M3/M4 fixed in code (CC Responses below); M1 closed operationally (migrations applied to Supabase). 2 LOW deferred to TASKS.md (`P7-FUP-L1`, `P7-FUP-L2`). Suite after remediation: **153/153 backend** (+8 pins), 99/99 engine, 52/52 vitest, `tsc` + `eslint` + `next build` clean.

---

### [HIGH] P7-H1 — Approve button shown for all non-Approved statuses; bill can end up with multiple Approved runs

- **Files:** `frontend/app/(app)/contracts/[id]/bills/[billId]/runs/[runId]/page.tsx:139` + `backend/api/pvc_runs.py:99`
- **Verified:** Run page shows Approve button when `run.status !== "Approved"` — includes Superseded, ExceptionFlagged, Exported. The backend `approve_run` gate only rejects `status == "Approved"` — no other check. Compounding it: **nothing in the backend ever writes `superseded_by` or status `Superseded`** — `POST /pvc-runs` (calculate) always INSERTs a new `Calculated` row with no supersede logic. So the run-history list on the bill page shows two `Calculated` runs with different totals and no "current" marker; both can be independently approved; both then pass `canExportRun` and produce conflicting official Excel/PDFs for the same bill. TASKS.md D-3a specified "Approve button (Draft only)"; the implementation gates on `!== Approved` instead.
- **Proposed fix:** Restrict approve at both layers to `Calculated` (the only status produced at INSERT). Backend: add `if row["status"] not in {"Calculated", "Draft"}: raise ValidationProblem(...)`. Frontend: gate button on `run.status === "Calculated"`. Additionally, implement supersede at INSERT time in `persist_run_result` — mark prior `Calculated` runs for the same bill as `Superseded` before writing the new one — or track it as `P7-H1-FUP-SUPERSEDE` with an explicit acceptance note.
- **Test that would catch it:** assert `POST /pvc-runs/{id}/approve` returns 422 when status is `Superseded`; assert the run page does not render Approve for a Superseded run.
- **CC Response (2026-06-11): CLOSED.** Both layers gated and supersede implemented at INSERT (not deferred). Backend: `approve_run` now 422s (`ValidationProblem` with `status` extra) for any status outside `{Draft, Calculated}`; the UPDATE's WHERE re-checks `status IN ('Draft','Calculated')` so the supersede/approve race can't slip through. `persist_run_result` marks prior `Draft`/`Calculated` runs for the bill as `Superseded` with `superseded_by = <new run id>` inside the same savepoint as the INSERT — Approved rows are never touched (migration-011 trigger would forbid it anyway). Frontend: Approve renders only for `status === "Calculated"`; a Superseded run shows an explanatory banner linking to the superseding run. Pinned by `test_p7_review_h1_h2.py`: parametrized 422 for Superseded/ExceptionFlagged/Exported, 409 retained for Approved, success path asserts the race-guard WHERE, and the supersede UPDATE is asserted to scope `bill_id` + exclude the new run + touch only Draft/Calculated.

### [HIGH] P7-H2 — Run page shows live bill lines instead of the run's own snapshot

- **File:** `frontend/app/(app)/contracts/[id]/bills/[billId]/runs/[runId]/page.tsx:61`
- **Verified:** The Bill lines section calls `GET /api/bills/{billId}/lines` with queryKey `["bill-lines", billId]`. But bill lines are rewritten by the engine on every PVC run for that bill — so a historical run page shows the current (newest) run's lines alongside the old run's totals, components, and W-derivation. The run's own `bill_snapshot` JSONB is persisted in the DB for exactly this purpose but `GET /pvc-runs/{id}` does not return it and the frontend does not use it. PRODUCT.md states "Immutable PVC run snapshots — revisions create superseding runs, never overwrites."
- **Proposed fix (right altitude):** Expose snapshot-derived lines on `GET /pvc-runs/{id}` (either return `bill_snapshot` and parse client-side, or add a `/lines` sub-resource derived from the snapshot). Until then, drop the bill lines section from the run page with a note that it is deferred — rendering inconsistent audit data is worse than rendering nothing.
- **Test that would catch it:** integration test — run PVC twice with different qty; open first run; assert lines shown are from the first run, not the second.
- **CC Response (2026-06-11): CLOSED — with a premise correction.** `bill_snapshot` does *not* contain bill lines: it is the engine input (`BillPayload` — aggregate amounts only), so there was nothing snapshot-derived to expose. Fixed at the root instead: **migration 016** adds nullable `lines_snapshot` JSONB to `pvc_runs`; `persist_run_result` captures the bill's lines at INSERT (same shape as `GET /bills/{id}/lines`, numerics as text for Decimal exactness); `GET /pvc-runs/{id}` returns it; the run page renders `lines_snapshot` and the live `GET /bills/{id}/lines` query is removed. Runs that pre-date the column render an honest "lines were not captured for this run" notice instead of live (wrong) data. Pinned by `test_p7_review_h1_h2.py`: persist test asserts the captured rows land in the INSERT's `lines` param; get_run test asserts passthrough.

---

### [MEDIUM] P7-M1 — Deploy-order regression: new SELECTs reference migration-015 columns not yet applied to Supabase

- **Files:** `backend/api/pvc_runs.py:135` (`get_run` + `list_runs`); bill page always fetches `GET /contracts/{id}/pvc-runs` on load
- **Verified:** STATUS.md/D-FUP-1 explicitly confirms migration 015 has not been applied to Supabase. Both new queries SELECT `total_pvc`, `negative_carry_forward`, `quarter_used` — columns that don't exist. Deploying the code first turns the **previously working** `GET /pvc-runs/{id}` endpoint into a 500 regression.
- **Proposed fix:** Make D-FUP-1 (`alembic upgrade head` on Supabase) a hard gate that must complete before any commit on this branch is deployed. Document it explicitly in the PR description and the merge checklist.
- **CC Response (2026-06-11): CLOSED operationally.** `alembic upgrade head` run against Supabase — DB now at **016**. Two surprises fixed en route: (1) `alembic_version` was stale at 012 while migration 013's `is_admin` column already existed in the DB (applied out-of-band) — stamped 013; (2) the DB's RLS helper is named `current_tenant_id()` but migrations 009/014 reference `get_tenant_id()` — created `get_tenant_id()` per migration 009's definition (identical body) so 014's policies could apply. D-FUP-1 is therefore also done; no deploy-order regression remains. PR #14 description updated with the migration gate note.

### [MEDIUM] P7-M2 — Export failures can be fully silent (res.blob() / URIError paths)

- **Files:** `frontend/lib/api/client.ts:137` (`filenameFromDisposition`); `frontend/app/(app)/contracts/[id]/bills/[billId]/runs/[runId]/page.tsx:96` (`handleExport` bare `catch {}`)
- **Verified:** Two paths in `apiDownload` reject *after* the toast branches: (1) `res.blob()` throws on a mid-body connection drop (network failure after 200 headers); (2) `decodeURIComponent(star[1])` throws `URIError` on a malformed `%` sequence in the server's `Content-Disposition`. `handleExport` swallows both with `// apiDownload already surfaced a toast` — but it didn't. User clicks Excel, spinner ends, nothing downloads, no error.
- **Proposed fix:** (1) Wrap `res.blob()` in a try/catch that fires a toast on failure. (2) Wrap `decodeURIComponent` in a try/catch that falls back to the fallback filename. Both are 2-line fixes.
- **CC Response (2026-06-11): CLOSED.** Both paths fixed in `frontend/lib/api/client.ts`: `res.blob()` failure now toasts "Download failed" and throws `ApiError(0)`; a `URIError` from `decodeURIComponent` falls back to the caller's filename instead of aborting the download.

### [MEDIUM] P7-M3 — Lines query error renders as a factual "no lines" claim

- **File:** `frontend/app/(app)/contracts/[id]/bills/[billId]/runs/[runId]/page.tsx:330`
- **Verified:** Empty-state check `!linesQuery.isLoading && (linesQuery.data?.length ?? 0) === 0` is also true when `linesQuery.isError` (data is undefined). A 500/404 on `GET /bills/{billId}/lines` displays "No lines generated for this bill." — a claim about engine output — instead of an error state.
- **Proposed fix:** Add `linesQuery.isError` check first: render a brief error message for the failed-fetch case, reserve the "no lines" empty state for `!isError && data.length === 0`.
- **CC Response (2026-06-11): CLOSED by the H2 fix.** The run page no longer fetches live lines at all — it renders `run.lines_snapshot` from the (already error-handled) run query. Empty array → "the bill had no lines when this run was calculated"; `null` (pre-016 run) → "lines were not captured". No fetch, no misattributed empty state.

### [MEDIUM] P7-M4 — Run-history bill_id filter is case-sensitive; uppercase UUID in URL yields silent empty history

- **File:** `frontend/app/(app)/contracts/[id]/bills/[billId]/page.tsx:100`
- **Verified:** `billRuns = (runsQuery.data ?? []).filter((r) => r.bill_id === billId)`. Backend returns `bill_id::text` — always lowercase Postgres UUID. URL segment `billId` is whatever was in the href/link, but a bookmarked or manually typed uppercase UUID is valid (Postgres accepts it on the bill lookup, so the bill page renders fine) and the strict-equality filter drops all runs silently.
- **Proposed fix:** `r.bill_id.toLowerCase() === billId.toLowerCase()` — one change.
- **CC Response (2026-06-11): CLOSED.** Filter compares both sides lowercased, with a comment noting the backend emits lowercase UUIDs while the URL segment may not be.

---

### [LOW] P7-L1 — `apiDownload` copy-pastes `apiFetch`'s error pipeline; already drifted

- **File:** `frontend/lib/api/client.ts:112`
- **Cost:** Network-catch branch and `!res.ok` branch (safeJSON → extractApiProblem → ApiError → toast) duplicated. The two copies differ already (`apiFetch` falls back to string `detail` and logs on network failure; `apiDownload` does neither). The `silent` option has zero callers. Extract a shared `authedFetch` helper; leave `apiDownload` owning only the blob/filename/anchor logic.
- **Deferral acceptable:** refactor only, no user-visible behavior change.

### [LOW] P7-L2 — `describeWDerivation` silently drops unknown W keys; no arithmetic guard

- **File:** `frontend/lib/pvcWDerivation.ts:33`
- **Cost:** When P6-H1-FUP-C approach C adds a dedicated W bucket, the frontend's fixed `SUBTRACTIONS` list silently drops it — displayed subtractions stop summing to the displayed W on the audit screen, and every existing test still passes. A cheap guard: assert `base − Σ subtractions === w` and render a warning row if the residual is non-zero (catches both unknown keys and future engine rounding changes).
- **Deferral acceptable:** implement before P6-H1-FUP-C approach C ships.

---

## Closed Cycles

### P6-REVIEW — CLOSED (2026-06-09, PR #13)

Adversarial pass by **Codex-S** on Phase 6 Bill Entry UI (C-1, C-2, C-2-FIX-A/B) + C-3. 2 HIGH + 2 MEDIUM found; all four closed. P6-H1 via interim approach A (recoveries → `technical_withheld`); end-state approach C tracked as `P6-H1-FUP-C`. Suite on close: **140/140 backend, 45/45 vitest, tsc + eslint clean**, route count 42. Full per-finding detail in git at `a88b85e`:

```
git show a88b85e -- REVIEW.md
```

### P5-REVIEW — closed 2026-05-20. Adversarial pass by CC-S (Codex-S unavailable) on `saqlain/phase-5` (commits `29352a9` P5-001…P5-008 + `0e3b31f` P5-F1…F5). 14 findings: 1 CRITICAL, 3 HIGH, 6 MEDIUM, 4 LOW. All CRITICAL/HIGH/MEDIUM closed, L-4 closed inline, L-1/L-2/L-3 deferred to TASKS.md (P5-FUP-L1…L3). Pre-existing lint dirt on the branch resolved in the same chain.

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
