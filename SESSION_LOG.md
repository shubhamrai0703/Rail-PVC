# SESSION_LOG.md — Current Operational Log

Keep this file small.

Use it for current milestone decisions and recent sessions only.

## Canonical Links

- Current state: [STATUS.md](STATUS.md)
- Active task board: [TASKS.md](TASKS.md)
- Active review cycle: [REVIEW.md](REVIEW.md)
- Historical archive pointer: [archive/SESSION_LOG_ARCHIVE.md](archive/SESSION_LOG_ARCHIVE.md)

## Current Project State

- Phase 0–3 complete. Phase 4 **fully complete** on `main` (2026-05-17) — all P4-001…P4-007 done.
- Local backend running: `cd backend && uv run uvicorn main:app --reload --port 8000`
- Local frontend running: `cd frontend && npm start` (port 3000)
- DB: Supabase at `ivselmhloegjmqrjekcy.supabase.co`, migrations at head (012), DDL for 010–012 applied manually (see Session 13).
- Tenant provisioned for `saqlainmmomin@gmail.com` — tenant_id `bd589426-93ba-4847-b5f3-1f69b020b4c0`.
- **Pending**: backend `tests/` use HS256 tokens; auth now uses JWKS/ES256 — test suite will fail until updated.

## Recent Sessions

### Session 13 — 2026-05-17 (Phase 4 complete: P4-004, P4-006 + infra fixes)

**P4-006 — Typed API schema generated**
- `npm run gen:api` against live `http://localhost:8000/openapi.json` → `lib/api/schema.ts` (970 lines, full `paths` + `operations` + `components`)

**P4-004 — Contract list dashboard wired**
- Replaced smoke-test placeholder in `app/(app)/contracts/page.tsx` with a real TanStack Query hook (`useContracts`) hitting `GET /api/contracts`
- Empty state when no contracts; table view with tender number, contractor, base month, zone, status badge, and disabled View button (Phase 5)

**Infrastructure fixes required before the above could work:**

1. **Supabase JWKS / ES256** — new Supabase projects issue ES256 tokens, not HS256. `services/auth.py` was hardcoded to `HS256`. Updated to use `PyJWKClient` against `/auth/v1/.well-known/jwks.json`; supports both algorithms. `SUPABASE_JWT_SECRET` env var is no longer used for verification (still present but inert).

2. **DB password rotation** — old `Ghost028301@` was expired. Updated `backend/.env` to `Vihandatad00`. DB confirmed reachable and at migration head.

3. **Missing DDL (migrations 010–012 not applied)** — alembic was stamped at 012 but the actual DDL had never run against this Supabase instance. Applied manually: `railway_zone` enum + column, `prevent_approved_run_update` trigger, `idempotency_key` column + partial unique index.

4. **Tenant provisioning** — `saqlainmmomin@gmail.com` had no row in `users`/`tenants`. Provisioned via one-off Python script. Tenant ID: `bd589426-93ba-4847-b5f3-1f69b020b4c0`.

**Pending items flagged:**
- Backend `tests/` mint HS256 tokens with `SUPABASE_JWT_SECRET` — all auth-dependent tests will fail now that auth uses JWKS/ES256. Needs a test-helper update before next review cycle.
- `SUPABASE_JWT_SECRET` in `.env` is now inert — can be removed or left as documentation.

### Session 12 — 2026-05-17 (Phase 4: P4-007, P4-001, P4-002)

Completed the three unblocked Phase 4 tasks in one pass. P4-004 and P4-006 remain blocked on backend deploy.

**P4-007 — Typed error contract in `apiFetch`**
- Added `ApiProblem` discriminated union (7 shapes matching `services/errors.py`)
- `ApiError` gains `detail?: ApiProblem` — callers can now `switch (err.detail?.code)`
- `extractApiProblem()` runtime guard; `toastDescription()` with code-specific copy (`engine_validation_error` → first error string, `idempotency_conflict` / `immutable_approved_run` → appends `run_id`)

**P4-001 — Supabase auth client wiring**
- Fixed leading-space bug in `frontend/.env.local` and `backend/.env` (dotenv kept `" value"` literally)
- Installed `@supabase/ssr@0.10.3`
- `lib/supabase/client.ts` — browser singleton (`createBrowserClient`)
- `lib/supabase/server.ts` — server/RSC client (`createServerClient` + cookies); silent catch on setAll from Server Components
- `middleware.ts` — protects all app routes; redirects unauthenticated to `/login`; redirects authenticated users away from auth pages
- `apiFetch` auto-injects `Authorization: Bearer <token>` (lazy browser-only import, no SSR breakage); caller-supplied `Authorization` wins
- `Header.tsx` — user avatar (initial circle) + sign-out dropdown; `useUser()` hook hydrates after mount

**P4-002 — Auth pages**
- `app/(auth)/layout.tsx` — centered auth layout with RailPVC brand mark
- `app/(auth)/login/page.tsx` — email/password form, inline error pill, redirect + `router.refresh()` on success
- `app/(auth)/signup/page.tsx` — confirm-password validation, 8-char minimum, "check your email" confirmation state
- `app/auth/callback/route.ts` — PKCE code exchange for email confirmation / magic links

Files changed: `lib/api/client.ts`, `lib/supabase/{client,server}.ts`, `middleware.ts`, `components/shell/Header.tsx`, `app/(auth)/**`, `app/auth/callback/route.ts`, `frontend/.env.local`, `backend/.env`, `TASKS.md`, `SESSION_LOG.md`, `STATUS.md`

Verification: `tsc --noEmit` clean; `next build` clean (10 routes, middleware proxy active); Supabase REST 200 with anon key confirmed pre-work.

### Session 11 — 2026-05-17 (Phase 3 remediation merged + branch cleanup + post-merge regression)

- PR #3 merged to `main` (merge commit `07838f4`)
- Deleted `saqlain/phase-3-remediation` (local + origin) and `saqlain/phase-4` (local + origin) — superseded
- Slimmed `REVIEW.md` to closure-pointer state per the active-state-files rule
- `STATUS.md` / `TASKS.md` updated: no active cycle; next workstream is Phase 3 backfill (CC-SH) + Phase 4 integration (CC-S)
- **[CODEX-S] ran a post-merge regression check on `main` — no findings.** Engine 99/99 + backend 31/31 passing; clean `import engine` from packaged path; `from main import app` registers 21 routes; tenant scoping, no global index writes, typed error contract, idempotency logic all still match review intent.

### Session 10 — 2026-05-17 (Phase 3 remediation, branch `saqlain/phase-3-remediation`)

Closed all merge-blocking findings `P3-01…P3-08` plus the MEDIUM `P3-09` in one pass. CC responses in [REVIEW.md](REVIEW.md) per finding.

Key design decisions:

- **Engine packaging is src-layout now.** Root cause for `P3-08` was hatchling's `packages = ["engine"]` looking for `engine/engine/` against a flat layout that put modules at `engine/*.py`. Moved modules into `engine/engine/` as `git mv` renames. No source changes; tests import unchanged. Pinned by a subprocess test that runs `import engine` with empty `PYTHONPATH`.
- **Tenant isolation is the API layer's job, not RLS's.** The backend uses a privileged `DATABASE_URL`, so RLS is documentation. Every route filters on `tenant_id` derived from the JWT (`backend/services/auth.py`). For shared global tables (`index_observations`, `index_series`), the tenant API exposes `GET` only — writes are out-of-band via seed/admin scripts using the service-role key. This is the structural fix for `P3-03`.
- **Domain logic lives in pure functions; routes are thin SQL wrappers.** `merge_extra_item_decisions`, `select_zone_series`, `default_rule_set_payload`, `assert_item_belongs_to_contract` — all unit-testable without Postgres. The route handlers compose them with `text()` SQL. This is what makes the P3 fixes pinnable without integration setup.
- **Idempotency is enforced at the database, not in application code.** Migration `012` adds a partial unique index `(contract_id, bill_id, idempotency_key) WHERE idempotency_key IS NOT NULL`. The API pre-check produces a friendly `409` with the existing `run_id`; the index is the actual guarantee.
- **Typed error contract is the API surface.** `services/errors.py` defines `ApiProblem` subclasses; FastAPI exception handlers render them as `{"detail": {"code", "message", ...extra}}`. Engine `validation_errors` come through as `code="engine_validation_error"` with the full list, idempotency conflicts as `code="idempotency_conflict"` with `run_id`. The frontend client work to consume these is queued as `P4-007`.

Files changed:

- `engine/` — six `git mv` renames into `engine/engine/`; `engine/pyproject.toml` unchanged
- `backend/.env.example` — placeholders only, documents all required env vars
- `backend/pyproject.toml` — adds `pyjwt`, `httpx`/`pytest`/`pytest-asyncio`/`aiosqlite` (dev), `pytest.ini_options`
- `backend/main.py` — wires all routers and `register_exception_handlers`
- `backend/api/` — new: `contracts`, `bills`, `extra_items`, `carry_forwards`, `indices`, `pvc_rules`, `pvc_runs`
- `backend/services/` — new: `db`, `auth`, `errors`, `zone_mapping`, `pvc_service`
- `backend/migrations/versions/012_idempotency_key.py` — new
- `backend/tests/` — 8 test modules, one per finding (`test_p3_01` … `test_p3_09`)

Verification:

- 99 engine tests + 31 backend tests = 130 passing, 0 failing
- `uv run python -c "import engine"` succeeds from a clean `backend/.venv` with no `PYTHONPATH`
- `uv run python -c "from main import app"` resolves all routes

Out-of-band action required:

- Rotate the previously-exposed Supabase project keys + Postgres password. The test in `backend/tests/test_p3_01_env_example.py` will block any future re-introduction.

## Current Decisions

- Active docs should be read in this order:
  1. [STATUS.md](STATUS.md)
  2. [PRODUCT.md](PRODUCT.md)
  3. [ARCHITECTURE.md](ARCHITECTURE.md)
  4. [TASKS.md](TASKS.md)
  5. [REVIEW.md](REVIEW.md)
- Historical detail should not live in the active context set when a summary/link is sufficient
- `CLAUDE.md` and `CODEX.md` should act as startup instructions, not duplicate project context

## Next Actions

1. [CC-SH] Branch off `main` for Phase 3 backfill endpoints (schedules / contract_items / recoveries / documents). Patterns documented in PR #3 description.
2. [CC-S] Frontend `apiFetch` consumes typed `detail.code` (P4-007); wire P4-001 / P4-004.
3. Rotate exposed Supabase credentials out-of-band.
