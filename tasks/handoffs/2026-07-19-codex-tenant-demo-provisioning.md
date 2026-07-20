# Handoff — Provision a tenant + seeded demo contract before an external contact logs in

Owner: Codex. Date: 2026-07-19. Repo: `/Users/saqlainmomin/railPVC` (branch off `main`; all prior branches are merged and deleted).

## Goal

An external contact (a railway contractor — first outside user) will sign up on the live app at `tenderaudit.in` with their own email. When they complete signup and log in, they must land in **their own dedicated tenant** that already contains the **BCT-24-25-252 demo contract** (schedules, BOQ items, two bills, recoveries, carry-forward) so the app is not empty on first view.

**Definition of done:** a test account signed up with a pre-invited email logs into `tenderaudit.in`, is provisioned into the prepared tenant automatically, and sees the demo contract with clickable bills at `/contracts`. A signup with a *non*-invited email still gets the current "no provisioned tenant" rejection (no open-signup tenant creation on a public site). Backend test suite green, migration applied to the live DB.

## Current state

- **Live production:** frontend on Vercel (`tenderaudit.in`), backend on Railway (`api.tenderaudit.in`), Supabase DB at alembic head **018**, unpaused. `/` is a public marketing landing page; `/signup` and `/login` work with real Supabase auth.
- **The gap:** signup creates only a Supabase auth user. `backend/services/auth.py::get_current_user` looks up a local `users` row by `supabase_auth_id` and raises `AuthProblem("Authenticated user has no provisioned tenant")` when none exists (line ~97). There is **no provisioning path** — every existing user was inserted by hand. A fresh signup today gets a broken, error-toast experience.
- **Demo seed exists:** `seeds/seed_demo_contract.py` seeds the full BCT-24-25-252 cycle. It reads `SEED_TENANT_ID` from env (defaults to `1c2c96ba-...`, Saqlain's own tenant — do **not** seed the contact's demo into that default), and its `require_tenant()` aborts if the tenant row doesn't exist. Per TASKS.md `DEMO-2`, this script has **not yet had its pre-run review** — review it before its first run against the live DB (check: idempotency, FK ordering, decimal precision, amounts reconcile to `engine/tests/fixtures/real_tenders/bct_2425_252_bill*.json`).
- Backend suite on `main`: 180 passed. Route count assertion currently pins 47 routes — bump it if you add routes.

## Design (decided — do not relitigate)

Invite-keyed provisioning, because the tenant and its demo data must exist *before* the contact ever authenticates, and open auto-provisioning (fresh tenant per signup) is unacceptable on a public site:

1. **Migration 019** — `tenant_invites` table: `id uuid pk`, `tenant_id uuid not null references tenants(id)`, `email text not null` (store lowercased; unique on lower(email)), `created_at`, `consumed_at nullable`. Follow the style of existing migrations in `backend/alembic/versions/`.
2. **Auth hook** — in `get_current_user`, when the `users` lookup misses: look up an unconsumed invite by the JWT's `email` (case-insensitive). If found, INSERT the `users` row (`tenant_id` from the invite, `supabase_auth_id` from `sub`, `email`, `is_admin=false`), mark the invite consumed, and proceed. If not found, raise the existing `AuthProblem` unchanged. Keep the write race-safe (ON CONFLICT on `users.supabase_auth_id` / re-select on conflict).
3. **Provision script** — `seeds/provision_tenant.py` following the `seed_indices.py` asyncpg + `backend/.env` `DATABASE_URL` pattern: creates a tenant (name from `PROVISION_TENANT_NAME` env) and an invite row (`PROVISION_INVITE_EMAIL` env). Idempotent; prints the tenant UUID. **Do not hard-code the contact's real name or email in the repo** — env vars only; Saqlain supplies the real values at run time.
4. **Seed the demo** — `SEED_TENANT_ID=<new tenant uuid> uv run python seeds/seed_demo_contract.py` (after the DEMO-2 review pass above).

## Key files

- `/Users/saqlainmomin/railPVC/backend/services/auth.py` — `get_current_user`; the provisioning hook goes here.
- `/Users/saqlainmomin/railPVC/backend/alembic/versions/` — migrations 001–018; add 019 here.
- `/Users/saqlainmomin/railPVC/seeds/seed_demo_contract.py` — demo seed; `TENANT_ID` via `SEED_TENANT_ID` env; `require_tenant()` gate.
- `/Users/saqlainmomin/railPVC/seeds/seed_indices.py` — the connection/idempotency pattern to mirror for the provision script.
- `/Users/saqlainmomin/railPVC/seeds/README.md` — tenant lookup query; update with the new provisioning flow.
- `/Users/saqlainmomin/railPVC/backend/tests/` — suite (180 green); auth tests use `app.dependency_overrides[get_current_user]`, so new provisioning tests must exercise the real dependency with a mocked/decoded claim set instead.
- `/Users/saqlainmomin/railPVC/TASKS.md` — `DEMO-1`/`DEMO-2` rows (seed review gate) — update status when done.
- `/Users/saqlainmomin/railPVC/STATUS.md` — update the branch/DB-head lines when the migration is applied.

## Constraints

- **Tenant isolation lives in the API layer, not RLS** — the backend uses a privileged `DATABASE_URL`; every query filters on `tenant_id` from the JWT-resolved user. Don't introduce RLS-dependent logic.
- **Alembic runs manually from a trusted machine, never on app boot.** Ship the migration; apply it to the live Supabase DB yourself (`alembic upgrade head` from `backend/`) and verify `alembic current` = 019. Note: the live DB's helper-function history has quirks (both `current_tenant_id()` and `get_tenant_id()` exist) — don't "clean up" unrelated schema.
- Non-invited signups must keep the exact current rejection behavior; no new tenant is ever created by an unauthenticated or un-invited path.
- Don't modify engine code or the demo seed's numbers — fixture values are authoritative and reconciled to the paisa.
- Credentials: `backend/.env` is git-ignored; keep it that way. No real names/emails in committed files.
- Backend route-count pin: bump only if you add routes (the auth hook adds none).

## Verification (smoke-test default — no "done on faith")

1. `uv run pytest` in `backend/` — full suite green, including new tests: invite-hit provisioning (users row created, invite consumed, second request idempotent), invite-miss rejection, case-insensitive email match.
2. Apply migration 019 to live; `alembic current` shows 019; `curl https://api.tenderaudit.in/health` OK.
3. Run `provision_tenant.py` against live with a **test** email you control; run the demo seed with the printed tenant UUID; re-run both to prove idempotency (skips, no dupes).
4. Browser pass on `tenderaudit.in`: sign up with the test email → log in → `/contracts` shows BCT-24-25-252 → open a bill, confirm lines/recoveries render. Screenshot or transcript as evidence.
5. Negative check: sign up with a second, non-invited test email → confirm the rejection path (no tenant created; check `tenants` count unchanged).
6. Leave the *real* contact's provisioning to Saqlain: document the two exact commands (provision + seed) with env-var placeholders in the Results section so he can run them with the real email.

## Report back

Append a `## Results` section to this same file: what shipped (commits/PR), test counts, live-DB evidence (alembic current, tenant UUID of the test run), browser-smoke evidence, the two ready-to-run commands for the real contact, and anything found during the DEMO-2 seed review.

## Results

Status: **partially complete; production demo seed and browser definition-of-done are blocked.** The invite-provisioning implementation and live schema migration are complete. No demo data was written after the required pre-run review found a material reconciliation failure.

### Shipped implementation

- Branch: `codex/tenant-demo-provisioning` (draft PR link added after publication).
- Migration 019 creates normalized, case-insensitive unique tenant invites with timestamps, tenant FK, and forced RLS.
- `get_current_user` now provisions only a JWT whose verified email matches a prepared invite. The CTE locks the invite, inserts an ordinary user, consumes the invite only after a successful insert, commits before the protected endpoint runs, and re-selects a concurrent winner.
- `seeds/provision_tenant.py` validates env-only name/email input, serializes concurrent runs with a transaction advisory lock, creates tenant before invite, and prints `TENANT_ID=<uuid>`.
- `seed_demo_contract.py` no longer defaults to Saqlain's tenant and no longer lets `backend/.env` overwrite a caller-supplied tenant.
- No API route was added; the pinned route count remains 47.

### Verification

- Focused provisioning/migration/auth tests: **14 passed**.
- Full backend suite: **194 passed** in 2.45s on the final working tree.
- Structured review: no remaining actionable finding. Review fixes shortened the invite lock lifetime and prevented the internal conflict sentinel from reaching `AuthUser`.
- Independent Claude adversarial route produced no usable result because its CLI was not logged in; this is recorded as a coverage limitation, not a pass.
- Supabase changelog/docs check: no hosted auth/JWT/RLS breaking change relevant to this implementation. Live auth settings report `mailer_autoconfirm=false`, so signup email confirmation is enabled.

### Live database and service evidence

- `uv run alembic current` -> **`019 (head)`**.
- Live catalog/query probe: RLS enabled and forced; zero policies; `anon` and `authenticated` each saw **0 invite rows**; expected PK, lower-email unique, and tenant indexes present.
- Duplicate normalized email and non-normalized uppercase email inserts were both rejected. All verification rows were rolled back.
- `curl -L -fsS https://api.tenderaudit.in/health` -> `{"status":"ok","service":"tenderaudit-api"}`.
- Test tenant UUID: **not created**. A controlled test email was not available, and the required demo seed cannot safely run until the DEMO-2 reconciliation gate is resolved.

### Browser smoke

Not run. The auth hook is not live until this branch merges and Railway deploys it; a controlled invited email is also required. Consequently, invited `/contracts`, clickable bill/recoveries rendering, and the uninvited negative signup remain unverified and must not be represented as passed.

### DEMO-2 pre-run review

Passed: tenant/zone/base-month configuration, FK insertion order, Decimal usage, fixture header/bucket mapping, and sequential rerun behavior. The review also found and fixed a critical operator-safety issue: the demo seed silently defaulted to a personal tenant and `.env` could override shell input.

The calculation reconciliation gate failed:

- Historical fixture-shaped data reproduces Bill 2 `76,959.55`, but Bill 1's negative carry differs (`765.30` calculated vs `635.38` pinned).
- Service-shaped data with fixture indices yields Bill 1 `0.00` (negative carry `735.54`) and Bill 2 `74,917.58`.
- Service-shaped data with the current seeded index observations yields Bill 1 `63,253.98` and Bill 2 `100,772.51`.
- The principal divergences are: fixture technical-withheld values live in `special_condition_amount` but the current service does not map that field into `technical_withheld`; Bill 2 carries a direct fixture amount while the service derives quantity x agreement rate; current index observations differ from the historical fixture snapshots.

The handoff forbids changing engine code or demo numbers and calls the fixtures authoritative. Therefore the production demo seed was deliberately not run. A domain/data decision must identify the authoritative service payload and index snapshot before this gate can pass.

### Real-contact commands

Run these only after the DEMO-2 reconciliation blocker is resolved and migration 019 plus the auth hook are deployed:

```bash
PROVISION_TENANT_NAME="<contact tenant name>" \
PROVISION_INVITE_EMAIL="<contact email>" \
uv run python seeds/provision_tenant.py

SEED_TENANT_ID="<TENANT_ID printed above>" \
uv run python seeds/seed_demo_contract.py
```

Re-run both exact commands to confirm skips/no duplicates, then complete invited and uninvited browser smoke before giving the contact access.
