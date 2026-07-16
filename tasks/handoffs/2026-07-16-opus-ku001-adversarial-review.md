# Handoff: KU-001-REVIEW — adversarial review of the rolling-quarter fix

Target agent: Opus 4.8, fresh session. Assume zero context beyond this file and the files it links. `main` is at commit `f164bc1` (PR [#17](https://github.com/saqlainmmomin/Rail-PVC/pull/17), merged 2026-07-16) — pull `main` before starting.

There are uncommitted changes in the working tree from a parallel session (frontend import-template UI work, plus two new quarter boundary tests already added to `engine/tests/test_quarter.py`). They don't touch the files in scope here — leave them alone, don't commit them, don't let them block you.

## Goal

Do an adversarial review of the KU-001 rolling-quarter change — the engine's quarter resolver was rewritten to derive rolling quarters from each contract's `base_month` instead of fixed calendar quarters. This shipped in PR #17 with only the implementing agent's own verification; nobody has tried to break it yet. This is the `KU-001-REVIEW` row in [TASKS.md](../../TASKS.md) (currently `pending`, owner `[CODEX-S]` — you're picking it up instead).

**Definition of done:** a written review appended to [REVIEW.md](../../REVIEW.md) in the existing `[HIGH]`/`[MEDIUM]`/`[LOW]` format (see the `P7-REVIEW` cycle already in that file for the exact shape: file:line, a "Verified:" paragraph showing you traced actual behavior — not just read the code, a proposed fix, and "test that would catch it"). If you find nothing, each of the four scrutiny points below still needs an explicit "no defect found, here's what I checked and how" — this file becomes the record that the change was reviewed, not just that it was skimmed.

## Current state

The resolver landed at `engine/engine/quarter.py`:

```python
def resolve_quarter(measurement_date: date, base_month: date) -> tuple[str, list[str]]:
    months_since_base = (
        (measurement_date.year - base_month.year) * 12
        + measurement_date.month
        - base_month.month
    )
    if months_since_base <= 0:
        return "", []

    quarter_number = ((months_since_base - 1) // 3) + 1
    quarter_start_offset = (quarter_number - 1) * 3 + 1
    base_month_index = base_month.year * 12 + base_month.month - 1

    quarter_months: list[str] = []
    for offset in range(quarter_start_offset, quarter_start_offset + 3):
        year, zero_based_month = divmod(base_month_index + offset, 12)
        quarter_months.append(f"{year}-{zero_based_month + 1:02d}")

    return f"Q{quarter_number}", quarter_months
```

Called from `engine/engine/calculator.py:318` (the pure calc path — blocks the run with a validation error if `quarter_months` comes back empty) and mirrored in `backend/services/pvc_service.py:549` (loads index observations for the same months the engine will resolve — these two call sites **must** stay in lock-step; if you find a discrepancy between them, that's a real bug, not a style note).

Old code (pre-fix) produced fixed-calendar labels like `"Q2-FY2025-26"`. New code produces plain ordinal labels (`"Q1"`, `"Q9"`, ...) with no upper bound. `pvc_runs.quarter_used` is a nullable `TEXT` column (migration `015_pvc_run_outputs.py`) — no length constraint at the DB layer.

Existing coverage (read before adding more — don't duplicate):
- `engine/tests/test_quarter.py` — resolver unit tests, including two boundary tests just added by the parallel session (Nov base crossing year-end, Dec base on a multi-year contract → Q9). Currently 10 passed.
- `engine/tests/test_calculator.py::TestValidationBlocking::test_measurement_in_base_month_blocks_before_index_validation` — confirms the pre-Q1 empty-months case surfaces as a validation error at the engine layer.
- `backend/tests/test_p3_04_zone_snapshot.py:199` — same pre-Q1 message asserted at a backend layer.

## Scrutiny points (from the implementing session's own handoff)

The implementing agent (Sol, in `tasks/handoffs/2026-07-16-sol-quarter-rolling-fix.md`) flagged four things nobody has independently verified. Treat each as a real review item, not a checkbox:

1. **Month-delta boundary.** `months_since_base` is plain year/month arithmetic (`quarter.py:19-23`); quarter 1 starts at `months_since_base == 1`. Confirm this is exactly "the month immediately after `base_month`" *regardless of day-of-month* — i.e. verify the assumption that `base_month` is always stored as day=01 actually holds at the DB/API boundary (check the contract creation/edit path and the migration/column definition for `base_month`), not just in test fixtures. If `base_month` can ever carry a non-1 day value, walk through what `resolve_quarter` does with it — does day-of-month leak into the boundary decision anywhere, or is the arithmetic genuinely day-invariant? Prove it either way.

2. **December/year rollover.** `divmod(base_month_index + offset, 12)` at `quarter.py:33`. Trace a base month of November and one of December against a multi-year contract (Q9+, spanning 2+ calendar years) by hand or with a throwaway script, and confirm the emitted `year-MM` strings are correct at every year boundary the offset crosses — not just the first one. The two boundary tests already in `test_quarter.py` cover single-year-boundary cases; check whether a *second* year boundary (e.g. a base month late in the year with a large enough `months_since_base` to cross two Jan 1sts) is covered — if not, add it.

3. **Unbounded `Q10+` labels.** No upper bound on `quarter_number`. Grep the frontend and export/report templates for any remaining assumption about the old `"Q2-FY2025-26"` shape — fixed length, regex anchored to that pattern, FY parsing, truncation. Known touch points to check: `frontend/app/(app)/contracts/[id]/bills/[billId]/runs/[runId]/page.tsx` and `frontend/app/(app)/contracts/[id]/bills/[billId]/page.tsx` (both render `quarter_used` directly as of this writing — confirm they still just interpolate the string with no format assumption), any PDF/Excel export code, and the `quarter_used TEXT` column itself (no length constraint found in migration `015_pvc_run_outputs.py` — confirm that's still true and that no downstream `VARCHAR(n)` truncates it).

4. **Pre-Q1 validation-error path, end-to-end.** Confirm the block isn't just a unit-test assertion at the resolver/calculator level — trace it through to the actual API error contract a frontend caller would see (i.e. does a bill with `measurement_date` in or before `base_month` actually fail the run with a user-visible 4xx and the expected message, all the way from `POST` to response body, not just at `calculate_pvc()`'s return value). `backend/tests/test_p3_04_zone_snapshot.py:199` is the closest existing test — read it and confirm it actually drives the full path rather than mocking around the resolver.

## Key files

- `engine/engine/quarter.py` — the resolver under review.
- `engine/engine/calculator.py:318` — engine caller.
- `backend/services/pvc_service.py:549` — backend caller (must stay in lock-step with the engine's resolution).
- `engine/tests/test_quarter.py`, `engine/tests/test_calculator.py` — existing coverage.
- `backend/tests/test_p3_04_zone_snapshot.py` — backend-level pre-Q1 coverage.
- `backend/migrations/versions/015_pvc_run_outputs.py` — `quarter_used TEXT` column definition.
- `tasks/handoffs/2026-07-16-sol-quarter-rolling-fix.md` — full implementation + verification record; read its final section for the original scrutiny list this handoff expands on.
- [REVIEW.md](../../REVIEW.md) — format reference (`P7-REVIEW` cycle) and where your findings go.
- [TASKS.md](../../TASKS.md):231 — the `KU-001-REVIEW` row to update when done.

## Constraints

- Stay in this lane. Do not touch `frontend/components/contracts/ImportRowsModal.tsx`, `frontend/lib/importTemplates.ts`, `frontend/lib/importTemplates.test.ts`, `frontend/components/contracts/ImportTemplateControls.tsx`, or `frontend/lib/api/schema.ts` — those are uncommitted work from a separate, unrelated workstream (P5-IMP-FUP-2) sitting in the same working tree. If they conflict with your `git status` expectations, that's why — leave them as-is.
- Do not touch the STC quarter-average domain question (`KU-001-STC-AVG` in TASKS.md, the two `xfail` fixtures `stc_cop_bill1_q3.json` / `stc_cop_bill2_q4.json`) — separate ticket, out of scope here.
- If you find a real bug: fix it with a minimal diff, add a regression test, note the fix in your REVIEW.md entry with before/after pytest output. If you find nothing on a given scrutiny point: say so explicitly with what you checked and how — silence reads as "not reviewed."
- Do not commit or push without checking with Saqlain first — leave changes in the working tree.

## Verification

```bash
cd /Users/saqlainmomin/railPVC/engine
uv run pytest tests/test_quarter.py tests/test_calculator.py -v
uv run pytest                                          # full engine suite — must stay green (10+ quarter tests, rest unchanged) unless you fix a real bug
cd /Users/saqlainmomin/railPVC/backend
uv run pytest                                          # full backend suite — must stay 166/166 unless you fix a real bug
```

Paste full suite output in your Results section. If you fixed a bug, paste before/after.

## Report back

Append a `## Results` section to **this file** with:
- Per scrutiny point (1–4 above): finding, evidence you traced (not just read), and disposition (no defect / bug found and fixed / bug found and deferred with reason).
- Any new tests added, with file:line.
- Full pytest output (engine + backend).
- Your `[HIGH]`/`[MEDIUM]`/`[LOW]` entries as appended to REVIEW.md (paste them here too, or link the section).
- Update [TASKS.md](../../TASKS.md):231 (`KU-001-REVIEW` row) to reflect closed/still-open status — do not leave the task board stale.

## Results

Executed 2026-07-16 by Claude (Fable 5) on `main` at `f164bc1`. Full review record appended to [REVIEW.md](../../REVIEW.md) as the **KU-001-REVIEW** cycle (now the top entry under "Active Cycle", status CLOSED). All changes left uncommitted in the working tree per the constraint. Note: the parallel session (`2026-07-16-fable-next-open-items.md`) ran its own quick A1 pass concurrently and updated the TASKS.md row twice mid-review; nothing in its findings conflicts with mine, and the row is now closed with the final state.

**Verdict: no HIGH/MEDIUM defects. 1 LOW deferred (KU1R-L1). 2 coverage gaps closed with new tests.**

### Per scrutiny point

**1. Month-delta boundary / day=01 invariant — no defect.**
Evidence traced: `resolve_quarter` reads only `.year`/`.month` (`quarter.py:19-24`) — but rather than trust inspection, I brute-forced it: 99,696 `(base_month, measurement_date)` pairs (bases 2020-01…2027-12 × days 1/15/28; measurements spanning 14 months before base to ~10 years after × days 1/10/31) against an independent month-stepping reference implementation (no shared divmod/index arithmetic) — **0 mismatches**. Q1 begins exactly at the month after `base_month` for every day combination; day-of-month cannot leak into the boundary. The day=01 storage assumption was verified at every write path, not just fixtures: API create rejects `day != 1` (`api/contracts.py:127`), API update likewise (`:213`), `create_contract_with_default_rule_set` (`pvc_service.py:239`) is reachable only from the validated route, `seeds/seed_demo_contract.py:106` hardcodes `date(2024, 12, 1)`, and `api/imports.py` never writes contracts. Gap: the DB column is bare `DATE NOT NULL` (migration `002_contracts.py:51`) with no CHECK — filed as **[LOW] KU1R-L1** (a day≠1 value written by direct SQL wouldn't break quarter math, which is day-invariant, but would make `build_index_snapshot`'s exact-date match at `pvc_service.py:463` silently miss the base-month observation and block runs with a misleading "missing index" error). Disposition: no defect; LOW deferred with proposed `CHECK (EXTRACT(DAY FROM base_month) = 1)` migration.

**2. December/year rollover — no defect; missing test added.**
Evidence traced: the same brute-force sweep covers every year boundary in the range; explicit traces for the flagged cases: base Nov-2023, measurement 2025-12-15 → `('Q9', ['2025-12', '2026-01', '2026-02'])` — the emitted window itself straddles the **second** Jan 1st after base; base Dec-2023, measurement 2027-01-05 → `('Q13', ['2027-01', '2027-02', '2027-03'])` — three Jan 1sts crossed. The two pre-existing boundary tests (Nov base Q1, Dec base Q9) only exercise windows straddling or following the *first* boundary; no test had a window straddling a later one. Disposition: no defect; coverage gap fixed (test below).

**3. Unbounded `Q10+` labels — no defect.**
Evidence traced: grepped `frontend/app`, `frontend/components`, `frontend/lib` and the entire backend for `FY`, `Q[0-9]-`, and any quarter parsing — zero format consumers. `bills/[billId]/page.tsx:289` renders `String(pvcRun.data.quarter_used)`; `runs/[runId]/page.tsx:221` renders `run.quarter_used ?? "—"` — both opaque. `backend/services/exports.py` / `api/exports.py` never reference quarter at all. `pvc_runs.quarter_used` remains unconstrained `TEXT` (migration `015:39`); no later migration adds a length limit (head is 016), no `VARCHAR(n)` anywhere downstream. Minor observation, not a finding: the bill page types the POST payload's `quarter_used` as `string | number` (line 52) vs the run page's `string | null` — harmless, since blocked runs 422 before persisting so a successful POST always carries a real label. Disposition: no defect.

**4. Pre-Q1 validation path end-to-end — chain verified; HTTP link untested, now pinned.**
Evidence traced: `test_p3_04_zone_snapshot.py:199` (`test_execute_pvc_run_surfaces_pre_base_engine_validation`) does **not** mock around the resolver — it stubs only the DB session and payload/snapshot builders, then runs the real `resolve_quarter` + `calculate_pvc` inside `execute_pvc_run`, asserting `EngineValidationProblem` with `status_code == 422` and the exact message. `test_p3_09_error_contract.py:23` pins the `detail` shape (`code="engine_validation_error"`, full error list), and `register_exception_handlers` (errors.py:170, wired in `main.py:40`) converts any `ApiProblem` to a JSON response. The one link no test drove: POST route → handler → actual HTTP response body. Added an HTTP-level pin (test below). Lock-step check from the handoff: `pvc_service.py:547` imports the engine's own `resolve_quarter` and feeds it the same `contract_row["base_month"]` it passes into `IndexSnapshot` — no discrepancy between engine and backend resolution. Disposition: no defect; coverage gap fixed.

### New tests added

- `engine/tests/test_quarter.py:39` — `test_late_quarter_window_straddles_second_year_boundary`: base Nov-2023, measurement 2025-12-15 → Q9 = `["2025-12", "2026-01", "2026-02"]` (window straddles the second Jan 1st after base).
- `backend/tests/test_p3_04_zone_snapshot.py` (appended at end) — `test_pre_base_bill_returns_422_engine_validation_over_http`: TestClient drives the real `POST /api/contracts/{id}/pvc-runs` with auth/session dependency overrides (pattern from `test_p3_bf_4_documents.py:145`); only DB and builders stubbed; asserts HTTP 422, `detail.code == "engine_validation_error"`, the exact pre-base message, and `persist_run_result` never awaited.

Brute-force verification script (not committed — throwaway per handoff): scratchpad `verify_quarter.py`, output `checked=99696 mismatches=0`.

### Full pytest output

```
engine  (cd engine && uv run pytest):
======================== 122 passed, 9 xfailed in 3.16s ========================

backend (cd backend && uv run pytest):
============================= 167 passed in 2.20s ==============================
```

(Engine was 121+9 before this review — +1 quarter boundary test. Backend was 166 — +1 HTTP-level pin. The handoff's "must stay 166/166" baseline is exceeded by design: the added test is the regression pin for scrutiny point 4, no existing test changed.)

### REVIEW.md entries

Appended as the **KU-001-REVIEW** cycle at the top of [REVIEW.md](../../REVIEW.md) "Active Cycle": a four-point verification record (each with files, traced evidence, and fix-applied notes) plus one finding:

- **[LOW] KU1R-L1 — `base_month` first-of-month invariant enforced only at the API layer.** `contracts.base_month` is `DATE NOT NULL` with no CHECK (migration `002:51`); day=01 lives solely in `api/contracts.py`. Consequence of a bypass is not wrong math (resolver proven day-invariant) but a silently missing base-month observation in `build_index_snapshot`'s exact-date match → every run on that contract blocks with a misleading "missing index" error. Proposed fix: `CHECK (EXTRACT(DAY FROM base_month) = 1)` in the next migration. Not testable at the aiosqlite layer; verify against Supabase. Deferral acceptable.

No HIGH, no MEDIUM.

### Task board

[TASKS.md](../../TASKS.md):231 `KU-001-REVIEW` updated → **complete** `[Fable]+[Opus]`, with the final suite counts (engine 122/9 xfailed, backend 167/167) and a pointer to the REVIEW.md cycle. Working tree changes (this review): `engine/tests/test_quarter.py`, `backend/tests/test_p3_04_zone_snapshot.py`, `REVIEW.md`, `TASKS.md`, this file — all uncommitted pending Saqlain per the handoff constraint.
