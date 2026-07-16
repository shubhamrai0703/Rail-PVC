# Handoff: Next open items after FUP backlog + KU-001 merge

Target agent: Fable 5, fresh session. Assume zero context beyond this file and the files it links. `main` is at commit `f164bc1` (PR [#17](https://github.com/saqlainmmomin/Rail-PVC/pull/17), merged 2026-07-16) — pull `main` before starting.

## Context

`saqlain/fup-backlog` just merged to `main`: three FUP tickets (P6-H1-FUP-C, P7-FUP-L1/L2, P5-IMP-FUP-1) plus the KU-001 rolling-quarter remediation (engine now resolves rolling quarters from the contract's `base_month` instead of fixed calendar quarters). Read [STATUS.md](../../STATUS.md) first — it's the shortest path to current branch/blocker state and links to the two source handoffs (`2026-07-15-ccs-quarter-convention.md`, `2026-07-16-sol-quarter-rolling-fix.md`) if you need the quarter-fix backstory.

This handoff covers the next two independent workstreams from `STATUS.md`'s "Current Priorities". They do not touch the same files — **pick a workstream and stay in its lane**; do not let the quarter-review work drift into template-UI files or vice versa.

Two items from the priorities list are explicitly **not** in scope here:
- `C-3-FUP-NET` (validate `net_amount` formula) — blocked on a real Railway bill submission that doesn't exist yet. Nothing to implement.
- `[CC-SH] Next task TBD` — unassigned, no spec.

---

## Workstream A — Quarter-fix hardening (review + domain investigation)

Two related, small tasks touching the same area (`engine/engine/quarter.py`, its fixtures) that a KU-001 adversarial reviewer flagged as follow-up. Do both in this workstream since they share context.

### A1. Adversarial review of the KU-001 rolling-quarter change (`KU-001-REVIEW` in TASKS.md)

**Goal:** the quarter-convention change (`engine/engine/quarter.py`, `engine/engine/calculator.py:318`, `backend/services/pvc_service.py:549`) has never had an adversarial pass — it only had the implementing agent's own verification. Review it like `P7-REVIEW` did for Phase 7 (see [REVIEW.md](../../REVIEW.md) for the format: `[HIGH]`/`[MEDIUM]`/`[LOW]` findings with file:line, a "Verified:" paragraph showing you traced the actual behavior, and a cost/impact statement).

CC-S (the implementing session) explicitly flagged three things to scrutinize, in `tasks/handoffs/2026-07-16-sol-quarter-rolling-fix.md`'s final section:
1. **Month-delta boundary** — `resolve_quarter` computes `months_since_base` via plain year/month arithmetic (`quarter.py:19-23`) and quarter 1 starts at `months_since_base == 1`. Verify this is exactly "the month immediately after `base_month`" for every day-of-month, not just `base_month` stored as day=01 (confirm the assumption that `base_month` is always day=01 holds at the DB/API boundary, not just in fixtures).
2. **December/year rollover** — `divmod(base_month_index + offset, 12)` in `quarter.py:33`. Check a base month of e.g. November or December against a multi-year contract; write a boundary test if the existing `engine/tests/test_quarter.py` doesn't already cover it explicitly (it was rewritten as part of the fix — read it first, don't duplicate coverage).
3. **Unbounded `Q10+` labels** — no upper bound on `quarter_number`. Check whether anything downstream (frontend badge rendering, export templates, DB column width on `pvc_runs.quarter_used TEXT`) assumes a small/bounded quarter number or a specific label format (old code produced `"Q2-FY2025-26"` — grep for any remaining assumption about that shape, e.g. string length checks, regex, FY parsing).

Also verify the pre-Q1 validation-error path (`quarter.py:24-25`, surfaced through `calculator.py`) actually blocks the run end-to-end (unit test through to the API error contract), not just at the resolver level.

**If you find real bugs:** fix them with a minimal diff, add a regression test, and note the fix in Results. **If everything checks out:** say so explicitly per finding — this file becomes the record that the KU-001 change was reviewed.

### A2. STC hard-coded quarter-average domain question (`KU-001-STC-AVG` in TASKS.md)

**Not a code task by default — an investigation task.** Two golden fixtures remain `xfail`: `stc_cop_bill1_q3.json` and `stc_cop_bill2_q4.json` (`engine/tests/fixtures/real_tenders/`). Per the Sol handoff's Results section: these resolve the *correct* rolling window now, but the source workbook's Tables 8/9 hard-code **rounded two-decimal quarter averages** rather than deriving full-precision averages from the verbatim monthly index observations the engine uses — a Δ₹42.12 divergence on Bill 1 (tolerance is 0.15).

Your job:
1. Read the workbook-derived fixture JSONs for these two bills and confirm the divergence is purely a rounding/averaging-method difference (not a data error) — the fixture's `notes` field and the Sol handoff already document this; verify it against the actual numbers rather than taking it on faith.
2. Write up, in this handoff's Results section, the two candidate resolutions in concrete terms so Saqlain can make the domain call in one read:
   - **Option 1:** engine keeps deriving full-precision monthly averages (current behavior) — workbook is "wrong" (imprecise), fixtures stay `xfail` with a documented reason, no code change.
   - **Option 2:** engine adopts round-to-2-decimals-per-month-then-average (or whatever the workbook's actual method is — determine this precisely from the workbook structure, don't guess) as the production rounding rule — this would be a real `calculator.py`/`w_derivation.py` change requiring its own review, and you should scope but **not implement** it without an explicit go-ahead, since it changes money-math for every contract, not just STC.
3. Do not change `calculator.py`, `w_derivation.py`, or any component math in this workstream. Do not touch the fixture `expected.total_pvc` values (workbook ground truth, per the existing constraint in the Sol handoff).

**Definition of done for A2:** a written decision brief in Results, not a code change, unless Saqlain has approved Option 2 explicitly in chat before you touch calculation code.

### Key files for Workstream A

- `engine/engine/quarter.py` — the resolver.
- `engine/engine/calculator.py:318` — caller.
- `backend/services/pvc_service.py:549` — backend caller.
- `engine/tests/test_quarter.py`, `engine/tests/test_calculator.py` — existing coverage; read before adding more.
- `engine/tests/fixtures/real_tenders/stc_cop_bill1_q3.json`, `stc_cop_bill2_q4.json` — the two STC fixtures in question.
- `engine/tests/test_real_tender_fixtures.py` — the xfail harness; per-fixture `notes.xfail_reason` explains current disposition.
- `tasks/handoffs/2026-07-16-sol-quarter-rolling-fix.md` — full implementation + verification record; its final "Reviewer scrutiny" section is your starting checklist.
- `REVIEW.md` — format reference for how findings get written up (see the `P7-REVIEW` closed cycle).

### Verification for Workstream A

```bash
cd /Users/saqlainmomin/railPVC/engine
uv run pytest tests/test_quarter.py tests/test_calculator.py -v
uv run pytest                                          # full engine suite — must stay 119 passed, 9 xfailed unless you fix a real bug
cd /Users/saqlainmomin/railPVC/backend
uv run pytest                                          # full backend suite — must stay 166/166 unless you fix a real bug
```

If A1 finds and fixes a bug, paste before/after pytest output. If A1 finds nothing, paste the suite output proving you ran it, plus your per-item findings (even "no defect found, here's what I checked and how").

---

## Workstream B — P5-IMP-FUP-2: templates apply/save UI

**Goal:** `ImportRowsModal` (the xlsx/paste smart-import flow used from the contract Items grid) can auto-map columns via fuzzy matching, but has no way to save a column mapping as a reusable named template or apply a previously saved one. The backend for this already exists and is wired — this is a frontend-only task. Definition of done: a user can, from `ImportRowsModal`, save the current column mapping as a named template and, on a future import, pick a saved template to pre-fill the mapping — with `npm run build`, `tsc --noEmit`, `eslint`, and `vitest` all clean, and a manual browser smoke test of save → reload modal → apply.

### Current state

- Backend is live on `main` (route count is 47 as of this merge): `backend/api/imports.py` exposes, under `/api/imports` (see `router = APIRouter(prefix="/api/imports", ...)` at line 40):
  - `GET /templates` (line 89) — list saved templates for the tenant.
  - `POST /templates` (line 112, 201) — create a template `{name, target_field_mapping, ...}` — read the Pydantic request/response models directly in the file, don't assume shape.
  - `DELETE /templates/{template_id}` (line 158, 204).
  - `POST /suggest-mapping` (line 190) — the AI mapper (Claude Haiku 4.5), already wired per `P5-IMP-FUP-1`. Out of scope for this task — the frontend's AI button is already stubbed/disabled; leave it alone unless picking it up is trivial and unblocks nothing else (it isn't part of this ticket).
  - Migration `014_import_templates.py` (`backend/migrations/versions/`) — already applied per FUP-1's route-count bump; verify against Supabase before assuming so (`alembic current` from `backend/`).
- Frontend: `frontend/components/contracts/ImportRowsModal.tsx` — the modal doing file/paste ingestion, sheet/header picking, and the fuzzy auto-map (`frontend/lib/fuzzyHeaderMap.ts`) into a `Mapping` type (`frontend/lib/normalizeImportRows.ts`). Mapping state lives in `mappingOverrides` (`ImportRowsModal.tsx:69`), typed `Mapping` from `normalizeImportRows.ts`. No template save/load UI exists yet — you're adding it to this component (or a sibling component it composes, your call).
- `frontend/lib/api/schema.ts` is generated from the live OpenAPI schema — regenerate it if the template endpoints aren't already reflected (check first; it may already include them since the backend has been live since FUP-1).

### Design constraints (match existing patterns — don't invent new ones)

- Auth/fetch: use the existing `apiFetch`/`authedFetch` pattern in `frontend/lib/api/client.ts` (just extracted in P7-FUP-L1 — read it, it now has `resolveErrorMessage` for two-tier error handling). Don't hand-roll fetch calls.
- Error handling: inline error display for 409/422-style conflicts, matching how `ContractForm`, `BillHeaderForm`, etc. do it elsewhere in the codebase (see `frontend/components/` for examples) — grep for `ApiError` usage patterns before designing your own.
- State: this codebase prefers TanStack Query for server state (see `runs/[runId]/page.tsx` or `bills/[billId]/page.tsx` for the pattern) — use `useQuery`/`useMutation` for template list/create/delete, not manual `useState` + `useEffect` fetch.
- Styling: reuse existing `Button`/form primitives from `frontend/components/ui/` — this modal already imports `Button` from there.
- Tenant scoping: templates are presumably tenant-scoped server-side (check `backend/api/imports.py` for the tenant-gate pattern — it should mirror every other route in this codebase via `assert_contract_belongs_to_tenant`-style helpers, though templates aren't attached to a contract, so check what they *are* scoped to before assuming).

### What NOT to touch

- `backend/api/imports.py`'s `/suggest-mapping` route or the AI-mapper button state (out of scope, separate ticket).
- `engine/`, `backend/services/pvc_service.py`, anything quarter-related — that's Workstream A, do not mix commits/PRs between the two workstreams if you pick up both.
- Migration 014 — already applied; don't write a new migration for this UI-only task.

### Verification

```bash
cd /Users/saqlainmomin/railPVC/backend
uv run pytest tests/test_p5_imp_imports.py -v    # confirm the 11 existing template/mapper tests still pass unmodified
cd /Users/saqlainmomin/railPVC/frontend
npx tsc --noEmit && npm run lint && npm run build && npx vitest run
```

Then a manual browser smoke test (per this repo's smoke-test-default convention — see `~/.claude/CLAUDE.md` operating rules if unfamiliar): open a contract's Items tab, launch "Import rows", map a few columns, save as a template with a name, close the modal, reopen it, and confirm the saved template appears and applying it restores the mapping. Screenshot or describe the actual UI state observed — don't claim this worked without having driven it.

---

## Report back

Append a `## Results` section to **this file** with:
- Workstream A: per-item (A1's three scrutiny points + the pre-Q1 path, and A2's decision brief) findings, pytest output, and any fixes made with file:line.
- Workstream B: files touched, the template CRUD flow as implemented, pytest + tsc/lint/build/vitest output, and the manual smoke-test narrative.
- Update `STATUS.md` and `TASKS.md` to reflect whatever you closed (mark `KU-001-REVIEW` / `KU-001-STC-AVG` / `P5-IMP-FUP-2` rows in TASKS.md as complete/pending-decision as appropriate) — do not silently leave the task board stale.
- Do not commit or push without checking with Saqlain first — leave changes in the working tree unless told otherwise, same convention as the prior two handoffs in this directory.

## Results

Executed by Fable 5 on 2026-07-16 on `main` at `f164bc1`. Both workstreams done; all changes left uncommitted in the working tree per the convention above. Note: a parallel Opus session (`2026-07-16-opus-ku001-adversarial-review.md`) was spawned for the formal KU-001 REVIEW.md cycle while this session ran — it added a third boundary test to `test_quarter.py` (second-year-boundary case); nothing below conflicts with it, and TASKS.md marks `KU-001-REVIEW` as jointly in progress until its REVIEW.md entry lands.

### Workstream A1 — adversarial review findings

**No defects found.** Per-item disposition:

1. **Month-delta boundary — no defect.** `resolve_quarter` uses only `year`/`month` in both the delta (`quarter.py:19-23`) and the window construction (`quarter.py:29-34`); day-of-month is arithmetically invisible, so Q1 starts exactly at "the month immediately after `base_month`" for every day-of-month on either argument (covered by `test_day_of_month_is_ignored_for_base_and_measurement`). The day=01 assumption **does hold at the API boundary**: `backend/api/contracts.py:127` (create) and `:213` (PATCH) both reject `base_month.day != 1` with a structured `ValidationProblem`. The DB column (`002_contracts.py:51`) is `DATE NOT NULL` with no CHECK constraint, so only a direct-SQL write could smuggle in a non-1 day — and even then the resolver stays correct; the only effect would be `build_index_snapshot` (`pvc_service.py:463-470`, exact-date `o.month = ANY(:months)` lookup) missing the base-month observation and blocking the run with missing-index validation errors — a safe failure, not wrong money-math. LOW observation, no action required: a DB CHECK (`date_trunc('month', base_month) = base_month`) would close that residual gap; not worth a migration on dev-only data.
2. **December/year rollover — no defect.** Hand-traced base Nov-2023 (Q1 = Dec-23/Jan-24/Feb-24, window straddling year-end) and base Dec-2023 on a multi-year contract (Q1 = Jan–Mar 2024 ⇒ Q9 = Jan–Mar 2026): `divmod(base_month_index + offset, 12)` on the 0-based month index is exact at every boundary. The pre-existing suite covered an October base (window wrap) but had no Nov/Dec base case, so two boundary tests were added — `test_november_base_quarter_one_crosses_year_boundary` and `test_december_base_multi_year_contract` (`engine/tests/test_quarter.py:28-37`); the parallel Opus session added a third (`test_late_quarter_window_straddles_second_year_boundary`). All pass.
3. **Unbounded `Q10+` labels — no defect.** `pvc_runs.quarter_used` is unconstrained `TEXT` (migration `015_pvc_run_outputs.py:39`). Frontend renders it as an opaque string only: `runs/[runId]/page.tsx:221` (`run.quarter_used ?? "—"`) and `bills/[billId]/page.tsx:289` (`String(pvcRun.data.quarter_used)`); no length/regex/FY assumption exists anywhere in `frontend/` (grep for `FY`, quarter parsing — clean). Excel/PDF exports (`backend/services/exports.py`) never render the quarter label at all. Nothing downstream assumes a bounded quarter number.
4. **Pre-Q1 validation path — verified end-to-end.** Resolver returns `("", [])` (`quarter.py:24-25`) → `calculate_pvc` appends the structured message and returns a blocked result (`calculator.py:321-326`) → `execute_pvc_run` raises `EngineValidationProblem` (`pvc_service.py:570-572`), a 422 with `code="engine_validation_error"` and `validation_errors: [...]` (`services/errors.py:91-101`), surfaced through the `register_exception_handlers` hook in `main.py:40`. `backend/tests/test_p3_04_zone_snapshot.py:167-200` drives the real `execute_pvc_run` with only I/O boundaries mocked and asserts status 422 + the exact message; it also proves `build_index_snapshot` receives `months == []` harmlessly (the query degrades to base-month-only). The frontend's `apiFetch` already has a dedicated `engine_validation_error` branch (`lib/api/client.ts:236-239`) that surfaces the first validation error. No gap found between the resolver and the user-visible contract.

Verification output (after the added tests):

```text
tests/test_quarter.py + tests/test_calculator.py:  41 passed in 0.22s
full engine suite:   122 passed, 9 xfailed in 3.01s   (baseline 119+9; +3 new boundary tests)
full backend suite:  166 passed in 2.56s              (unchanged)
```

### Workstream A2 — STC hard-coded quarter-average decision brief

**Verified against the live workbook, not the fixture notes.** `PVC/COP & Seating/Banjara - STC COP - Apr 2022 GCC.xlsx`, Tables 8 (Bill 1/Q3) and 9 (Bill 2/Q4), column D ("Average Index of quarter") contains **literal typed numbers, not formulas** — the workbook genuinely hard-codes its quarter averages.

**The workbook's exact method, determined numerically:** for each series, take the plain mean of the three monthly observations (the same verbatim observations the fixtures carry), then round **half-up to 2 decimal places**, and use that rounded average in every formula line (`amount × (avg − base)/base × weight`, each line itself rounded to 2dp). Evidence:

- All 9 hard-coded D-column values in Table 8 match avg-then-round-2dp of the fixture observations exactly (e.g. labour `(139.2+138.9+139.4)/3 = 139.1667 → 139.17`; steel angles `62495.5567 → 62495.56`). Same for every D value in Table 9.
- Recomputing all 25 formula lines per table with those rounded averages and summing reproduces the workbook totals **to the paisa**: Bill 1 `-120623.44` (= Table 8!L30 = fixture expected), Bill 2 `-54035.63` (= Table 9!L30 = fixture expected). Zero per-line mismatches.

So the Δ (engine `-120665.56` vs workbook `-120623.44`, Δ₹42.12 on Bill 1) is **purely the averaging-precision rule — confirmed not a data error**. The monthly observations are identical on both sides.

**Option 1 — keep full-precision averages (current engine behavior).** The engine is arithmetically *more* correct; the workbook loses precision by rounding an intermediate. No code change, no review cycle, no risk to the 9 currently-passing golden fixtures. The two STC fixtures stay xfail with `xfail_reason` already documenting exactly this (they do — verified). Cost: RailPVC's output will disagree with this contractor's submitted workbooks by tens of rupees per bill, which a Railway bill passing officer comparing against the contractor's sheet would flag.

**Option 2 — adopt the workbook rule (round quarter average to 2dp, half-up, before use).** Single choke point: `_quarter_avg` in `engine/components.py:49-56` (used by general components, cement, and single-series steel) — add a `.quantize(Decimal("0.01"), ROUND_HALF_UP)` on return. One open sub-question needs its own workbook check before implementing: the SL4 steel-other derived average (`components.py:186-189`) averages *series averages* — whether the workbook rounds before or after that second averaging isn't determinable from STC alone (its Table 8 SL4 value matches the fixture's pre-derived `steel_other_sections` series either way). This changes money-math for **every contract**, not just STC, so per the handoff it is scoped only: it would flip both STC fixtures to genuine PASS, requires re-pinning the JRH/BCT fixtures' expectations (their engine totals shift by paisa), a full adversarial review, and possibly a rules flag if Railway ever supplies a full-precision counter-example.

**Recommendation:** the deciding fact is that the 2dp-average behavior appears in a real accepted Railway submission, and PVC bills are reconciled against contractor workbooks line-by-line. If other contractors' workbooks (JRH/BCT) show the same rounding convention, Option 2 is the domain-correct rule, not a bug-compatibility hack — worth one check of a JRH/BCT averages sheet before deciding. Until then: **no code changed, fixtures untouched, both stay xfail** — the decision is Saqlain's.

### Workstream B — P5-IMP-FUP-2 templates apply/save UI

**Files touched:**

- `frontend/lib/importTemplates.ts` (new) — `ImportTemplate` type; `headerSignature()` (FNV-1a 32-bit over normalized, sorted headers → `v1-xxxxxxxx`, order/case/punctuation-insensitive, well under the backend's 200-char limit); `applyTemplateMapping()` (normalized-header matching, unknown headers → ignore, invalid targets dropped).
- `frontend/lib/fuzzyHeaderMap.ts` — exported `normalizeHeader()` wrapper so the signature shares the mapper's normalization.
- `frontend/components/contracts/ImportTemplateControls.tsx` (new) — the template bar: TanStack `useQuery` list (templates matching the current signature sort first, labelled "(matches these columns)"), Apply/Delete, and an expandable save-as form. `useMutation` for create/delete with `silent: true` + inline error rendering (409 duplicate name shows the backend message in a red inline box, per the ContractForm-style pattern). Cache invalidated via `invalidateQueries(["import-templates"])`.
- `frontend/components/contracts/ImportRowsModal.tsx` — renders `ImportTemplateControls` above the mapping table; `onApply` feeds `setMappingOverrides`.
- `frontend/lib/importTemplates.test.ts` (new) — 11 vitest cases (signature stability/normalization/sensitivity/length; apply filtering/normalization/invalid-target/null handling).
- `frontend/lib/api/schema.ts` — regenerated from the live FastAPI app's OpenAPI dump (47 routes; template + suggest-mapping endpoints now reflected). No backend files touched; `/suggest-mapping` and the AI button untouched.

**Verification (all clean):**

```text
backend tests/test_p5_imp_imports.py:  11 passed (unmodified)
npx tsc --noEmit:                      clean
npm run lint:                          clean
npx vitest run:                        65 passed (54 baseline + 11 new)
npm run build:                         ✓ Compiled successfully, 11/11 pages
```

**Migration 014 check:** `uv run alembic current` could **not** be verified against Supabase — see the blocker below. Prior records (REVIEW.md P7 M1, FUP-1) state the DB is at head 016 with 014 applied; no new migration was written.

**⚠ Supabase project unreachable — smoke test ran against a mock.** The project `ivselmhloegjmqrjekcy` is down: pooler answers `(ENOTFOUND) tenant/user … not found`, `db.…supabase.co` is NXDOMAIN, and `https://…supabase.co/auth/v1/health` doesn't respond. It looks paused (free-tier auto-pause) — restoring it from the Supabase dashboard is on you, and re-running this smoke test against the real backend afterwards is recommended. With no local Postgres/Docker on this machine, the smoke test was run against a faithful stand-in: a scratchpad FastAPI mock serving the GoTrue auth subset plus the contract/schedule/items reads and the template CRUD **with the real backend's semantics** (201 create, 409 duplicate-name with the same `ApiProblem` body, 204 delete) — the real contract behavior itself is pinned by the 11 unmodified backend tests. The frontend was production-built with `NEXT_PUBLIC_SUPABASE_URL`/`NEXT_PUBLIC_API_URL` pointed at the mock and served via `next start`.

**Smoke-test narrative (driven in the in-app browser, screenshots taken at each step):** signed in → contract `BCT-SMOKE-01` → Items tab → "Import rows" → pasted a 6-column TSV (Item No / Work Description / UOM / Orig Quantity / Basic Rate / Agt Rate). Fuzzy auto-map filled 4 columns correctly but mis-mapped "Basic Rate" → Agreement rate and ignored "Agt Rate" (pre-existing mapper behavior — exactly the case templates exist for). Saved the mapping as "Vendor BOQ v1" → picker immediately showed it as "(matches these columns)". Closed the modal (overlay click), reopened, pasted new rows with the same headers → saved template listed from the server. Corrected the two rate columns manually, hit save with the duplicate name "Vendor BOQ v1" → **inline red error "A template with this name already exists for this tenant", no toast**. Renamed to "Vendor BOQ v2 (corrected rates)" → saved, auto-selected. Deliberately broke the mapping (Basic Rate → ignore) → Apply → **mapping restored to Base rate**. Preview rendered both rows; "Add 2 rows" committed them into the Items grid (rows 004/005 visible). Zero console errors. Server-side state confirmed both templates persisted with correct mapping JSON and the identical deterministic signature `v1-f7b29c8a` for the shared header set. Cleanup: mock + `next start` stopped, frontend rebuilt with normal env so `.next` doesn't point at the mock; the user's pre-existing process on :8000 was left untouched.

### Task-board updates

- `TASKS.md`: `P5-IMP-FUP-2` → complete (working tree); `KU-001-REVIEW` → in progress `[Fable]+[Opus]` (this file's A1 pass done; formal REVIEW.md entry owned by the parallel Opus session); `KU-001-STC-AVG` → pending **Saqlain's** decision, investigation complete.
- `STATUS.md`: updated (working-tree state, Supabase-unreachable blocker, priorities).
- Nothing committed or pushed.
