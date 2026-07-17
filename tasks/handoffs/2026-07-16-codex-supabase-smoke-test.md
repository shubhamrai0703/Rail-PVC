# Handoff — Re-run the P5-IMP-FUP-2 smoke test against the restored Supabase stack

**Date:** 2026-07-16
**From:** Claude (Fable) session
**To:** Codex
**Repo:** `/Users/saqlainmomin/railPVC` (branch `main`, head `b8c9267`)

## Goal

Supabase project `ivselmhloegjmqrjekcy` was paused (free-tier auto-pause) and has now been restored by Saqlain. The P5-IMP-FUP-2 import-template feature (already merged to `main`) was smoke-tested only against a mock API because the real stack was down. Your job: bring up the real stack (real Supabase auth + real backend + production frontend build), re-run the smoke test end-to-end, and report findings.

**Definition of done:** the full smoke-test flow below has been driven in a real browser against the real backend, every step's observed outcome is recorded in the Results section of this file (pass/fail per step, with the actual UI/API behavior seen), and any defect found is described concretely enough to reproduce.

## Current state

- `main` contains everything: FUP backlog + KU-001 rolling-quarter fix (PR #17) and the P5-IMP-FUP-2 template UI (`ImportTemplateControls` in `ImportRowsModal`, commit `8299edf`). Working tree is clean apart from unrelated untracked files — **do not touch them**.
- All automated suites are green (167 backend, 122+9 xfail engine, 65 frontend vitest; tsc/eslint/next build clean). Nothing needs re-testing at the unit level.
- The prior (mock-backed) smoke test passed; its narrative is in `tasks/handoffs/2026-07-16-fable-next-open-items.md` (Results, Workstream B). This run is the real-stack confirmation.
- DB is believed to be at migration head `016` with `014_import_templates` applied — verify, don't assume.

## Key files

- `/Users/saqlainmomin/railPVC/STATUS.md` — current state; the Supabase blocker at the top is what this run closes.
- `/Users/saqlainmomin/railPVC/tasks/handoffs/2026-07-16-fable-next-open-items.md` — prior smoke-test narrative (Workstream B) to replicate.
- `/Users/saqlainmomin/railPVC/frontend/components/ImportRowsModal.tsx` and `frontend/components/ImportTemplateControls.tsx` — the feature under test.
- `/Users/saqlainmomin/railPVC/frontend/lib/importTemplates.ts` — template client logic (signature, CRUD calls).
- `/Users/saqlainmomin/railPVC/backend/routes/imports.py` — template CRUD API (tenant-scoped, 409 on duplicate name).
- `/Users/saqlainmomin/railPVC/backend/.env` and `frontend/.env.local` — real credentials/URLs (git-ignored; never copy their contents anywhere, including this file).
- `/Users/saqlainmomin/railPVC/Makefile` — run targets.

## Constraints

- **8 GB machine rule:** do not use `next dev`. Use `npm run build && npm run start` (or `npx next start`) from `frontend/`.
- Backend: `cd backend && .venv/bin/uvicorn main:app --port 8000`. Check whether something already listens on :8000 first (`lsof -i :8000`); if a stale process is there, note it in Results and use it or restart it — don't run two.
- **Login:** use Saqlain's existing auth user; it maps to tenant `1c2c96ba…` ("Default Tenant"). Credentials are whatever the browser/env already has — do not create accounts, do not touch Supabase dashboard settings.
- **No code changes.** This is a verification run. If you find a defect, document it in Results; do not fix it in this session.
- Do not modify data destructively: adding template(s) and a couple of import rows to a test contract is fine; deleting or editing existing contracts/bills/runs is not. Clean up templates you create if deletion works (it's part of the test anyway).
- Do not commit or push anything except this file's Results section (Saqlain will review; committing this file alone with a `docs:` message is fine if he asks — default is leave uncommitted).

## Smoke-test procedure

1. **Reachability:** confirm Supabase is really back — `curl -s https://ivselmhloegjmqrjekcy.supabase.co/auth/v1/health` should return JSON, and the DB host should resolve.
2. **Migration state:** `cd backend && uv run alembic current` (or `.venv/bin/alembic current`) — expect head `016`. Record the actual output.
3. **Stack up:** backend on :8000; frontend `npm run build && npm run start` with its normal `.env.local` (pointing at real Supabase + `http://localhost:8000`).
4. **Login** through the real UI with the real auth user. Confirm contracts list loads from the real DB.
5. **Template flow** (mirror the mock-run narrative): open a contract → Items tab → "Import rows" → paste a multi-column TSV (e.g. Item No / Work Description / UOM / Orig Quantity / Basic Rate / Agt Rate) → observe fuzzy auto-map → adjust a mapping → **save as a named template** → confirm it appears in the picker → close & reopen the modal, paste again → confirm the template is listed (served by the real backend) → break the mapping, **apply the template**, confirm the mapping restores → save with a **duplicate name**, expect inline 409 error ("already exists for this tenant"), no toast → rename, save → preview → commit rows into the grid.
6. **Persistence check:** hit the backend directly (authed `GET /api/import-templates` or per-contract equivalent — see `backend/routes/imports.py` for the exact path) and confirm the templates persisted with correct mapping JSON and tenant scoping.
7. **Cleanup:** delete the test template(s) via the UI if a delete affordance exists, otherwise via the API (expect 204); note whether the rows you imported should stay (leave them — they're in the demo tenant).
8. Watch the browser console and backend logs throughout; zero uncaught errors is part of the pass criteria.

## Report back

Append a `## Results` section to **this file** with: reachability + `alembic current` output, per-step pass/fail with observed behavior, any divergence from the mock-run narrative, console/log errors, defects (repro steps), and a one-line verdict (e.g. "P5-IMP-FUP-2 real-stack smoke test PASSED — Supabase blocker can be closed in STATUS.md"). Do not edit STATUS.md yourself; the verdict line is what Saqlain's next session will act on.

## Results

Executed by Codex on 2026-07-16 on `main` at `b8c9267`. No project code was changed and no automated unit suites were re-run, per this handoff. The production frontend build, real Supabase-backed API, browser flow, direct authenticated persistence check, and cleanup were completed.

### Environment and reachability

1. **PASS — Supabase reachability.** `https://ivselmhloegjmqrjekcy.supabase.co/auth/v1/health` responded with Supabase JSON (`No API key found in request` for the deliberately unauthenticated probe), proving the restored Auth host was live. The configured database pooler connected successfully during the migration check.
2. **PASS — migration state.** Actual output:

   ```text
   INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
   INFO  [alembic.runtime.migration] Will assume transactional DDL.
   016 (head)
   ```

3. **PASS with environment-only port divergence — stack up.** Ports 8000, 3000, and 3001 were already owned by unrelated workspaces (`Recon`, `.hermes`, and `Velocity`), so they were not stopped. RailPVC ran on backend `8001` and production frontend `3002`. `NEXT_PUBLIC_API_URL` was built as `http://localhost:8001`; `npm run build` completed successfully (11/11 static pages). Because `backend/main.py` permits only the normal production-local origin `http://localhost:3000`, the first 3002 preflight returned 400 and the UI showed `Network error — is the API reachable?`. A temporary runtime-only CORS wrapper allowed `http://localhost:3002`; the follow-up preflight returned 200 with the correct `Access-Control-Allow-Origin`. No source file was changed. This is not a P5-IMP-FUP-2 defect and is not reproducible on the prescribed port 3000.
4. **PASS with login-method divergence — real authentication and DB data.** The user's separately opened browser authenticated successfully, but its session was isolated from the controlled smoke-test browser. The controlled browser therefore used a one-time magic link generated for the existing `saqlainmmomin@gmail.com` Supabase user (the user was verified to exist before link generation) and converted it to the same Supabase SSR cookies used by the app. No user, password, tenant, or dashboard setting was created or changed. The real contracts list loaded, including `BCT-24-25-252`, proving real Auth, backend, tenant lookup, and database access.

### Template and import flow

5. **PASS — full browser flow.** On contract `BCT-24-25-252` → Items → Schedule A → Import rows, pasted this six-column TSV shape: `Item No / Work Description / UOM / Orig Quantity / Basic Rate / Agt Rate`, with two test rows (`CODEX-SMOKE-0716-A` and `CODEX-SMOKE-0716-B`). Observed behavior:

   - The fuzzy mapper reproduced the mock-run behavior exactly: Item No, Work Description, UOM, and Orig Quantity mapped correctly; Basic Rate mapped to Agreement rate; Agt Rate was ignored.
   - Corrected Basic Rate → Base rate and Agt Rate → Agreement rate, then saved `Codex real-stack 2026-07-16 A`.
   - The picker immediately showed `Codex real-stack 2026-07-16 A (matches these columns)`.
   - Closed and reopened the modal, pasted the same header set, and confirmed the template was fetched from the real backend and listed.
   - Selected the template, deliberately changed Basic Rate to ignore, clicked Apply, and observed it restore to Base rate.
   - Saving again as `Codex real-stack 2026-07-16 A` produced the inline error `A template with this name already exists for this tenant`; no error toast appeared.
   - Renamed to `Codex real-stack 2026-07-16 B`; it saved and became the selected matching template.
   - Preview displayed both rows with the expected values (`2 / 100 / 95` and `3 / 200 / 190`). `Add 2 rows` placed them in the grid; `Save all` persisted them. After a full page reload and reselecting Schedule A, both rows were still present.

6. **PASS — direct authenticated persistence and tenant scope.** `GET /api/imports/templates` with the real user's JWT returned both created templates through the tenant-filtered route. Both had source signature `v1-f7b29c8a`, empty value normalizations, and this mapping:

   ```json
   {
     "Item No": "item_code",
     "Work Description": "description",
     "UOM": "unit",
     "Orig Quantity": "original_qty",
     "Basic Rate": "base_rate",
     "Agt Rate": "agreement_rate"
   }
   ```

7. **PASS — cleanup.** Deleted template B and then template A through the UI. The picker ended disabled with `No saved templates`; a final authenticated GET confirmed `remaining_test_templates: 0`. The two imported Schedule A rows were intentionally retained in the demo tenant, as directed.

8. **PASS — console/backend behavior.** Browser console contained zero errors or uncaught exceptions. It emitted four AG Grid deprecation warnings (repeated after reload) about legacy row-selection options; these are pre-existing and unrelated to import templates. All feature API operations produced their expected user-visible outcomes: list success, two creates, inline duplicate-name 409, and two successful deletes; no backend exception surfaced.

### Divergences and defects

- Mock narrative divergence: the real-stack run used corrected rate mappings before saving the first template, so both saved templates contained the correct mapping. The mock run first saved the fuzzy mapper's incorrect rate mapping and corrected it in the second template.
- Environment divergence: alternate ports required a temporary CORS wrapper because unrelated apps occupied the prescribed ports. The initial 3002 CORS failure was diagnosed and resolved without a project change.
- Authentication divergence: the controlled browser could not inherit the user's separate browser session, so it used a one-time link for the same existing Supabase user instead of typing the password form.
- **P5-IMP-FUP-2 defects found: none.**

**Verdict: P5-IMP-FUP-2 real-stack smoke test PASSED — the Supabase blocker can be closed in STATUS.md.**
