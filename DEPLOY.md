# DEPLOY.md — Getting TenderAudit live at tenderaudit.in

Target topology:

```
tenderaudit.in, www.tenderaudit.in  →  Vercel (Next.js frontend)
api.tenderaudit.in                  →  Railway (FastAPI backend)   ← recommended; Render works identically
Supabase (existing project ivselmhloegjmqrjekcy)  →  Postgres + Auth + Storage (unchanged)
```

Order matters: backend first (frontend needs its URL), then frontend, then DNS, then Supabase auth config.

## 0. Prerequisites (one-time decisions)

- [ ] Merge `saqlain/parallel-backlog` and `saqlain/fup-backlog` PRs, then `saqlain/tenderaudit-rename`, so `main` is the deployable branch.
- [ ] **Supabase pausing:** free-tier projects auto-pause on inactivity (happened 2026-07-16). Before sharing with contacts, either upgrade the project to Pro or accept the risk and set a keep-alive ping (e.g. a cron hitting `/health` → DB daily). A paused project = the whole app down.
- [ ] **Tenant provisioning:** new signups get `Authenticated user has no provisioned tenant`. For the first contacts, provision manually per person: insert `tenants` row + `users` mapping (supabase_auth_id → tenant), then optionally run `backend/seeds/seed_demo_contract.py` with that tenant ID so they land in a populated app. Auto-provisioning on signup is a future ticket.

## 1. Backend → Railway

1. New Railway project → deploy from GitHub repo. **Root Directory: leave blank** (repo root) — Railway auto-detects the repo-root `Dockerfile` and builds from it. Do not set a custom Build or Start Command; the Dockerfile's `CMD` handles the start.
   - Why a Dockerfile instead of Railway's Railpack auto-detection: `backend/`'s `railpvc-engine` dependency is an editable install at `../engine`, a sibling directory. Railpack scopes its build context to whatever Root Directory you give it, so pointing it at `backend/` breaks the `../engine` reference, and leaving it blank makes Railpack's own app-detection ambiguous across the monorepo (`frontend/`, `backend/`, docs, etc). A Dockerfile's build context is always the repo root regardless, sidestepping both failure modes.
2. Environment variables (values from `backend/.env` / Supabase dashboard — never commit them):
   - `SUPABASE_URL`
   - `SUPABASE_ANON_KEY`
   - `SUPABASE_SERVICE_ROLE_KEY`
   - `SUPABASE_JWT_SECRET`
   - `DATABASE_URL` (asyncpg pooler URL; password URL-encoded)
   - `OPENROUTER_API_KEY` (optional — only the import column-mapper 503s without it; via OpenRouter, not Anthropic directly)
   - `OPENROUTER_MODEL` (optional — defaults to `anthropic/claude-haiku-4.5`)
   - `CORS_ORIGINS=https://tenderaudit.in,https://www.tenderaudit.in`
3. Expose the service: Settings → Networking → Generate Domain (quick Railway URL for testing) or Custom Domain → `api.tenderaudit.in` (Railway shows the CNAME + TXT verify record for GoDaddy — step 3 below).
4. Migrations: DB is already at head `017`; nothing to run. Future migrations stay a manual `alembic upgrade head` from a trusted machine (service-role path), not part of app boot.
5. Smoke: `curl https://api.tenderaudit.in/health` → `{"status":"ok","service":"tenderaudit-api"}`.

## 2. Frontend → Vercel

1. Import the repo in Vercel, root directory `frontend/`, framework preset Next.js (build `next build`, defaults fine).
2. Environment variables:
   - `NEXT_PUBLIC_SUPABASE_URL`
   - `NEXT_PUBLIC_SUPABASE_ANON_KEY`
   - `NEXT_PUBLIC_API_URL=https://api.tenderaudit.in`
3. Domains: add `tenderaudit.in` (primary) and `www.tenderaudit.in` (redirect → apex). Vercel shows the exact DNS records for step 3.

## 3. DNS at GoDaddy

| Type | Name | Value | Purpose |
|---|---|---|---|
| A | `@` | `76.76.21.21` (use the value Vercel shows) | apex → Vercel |
| CNAME | `www` | `cname.vercel-dns.com` (as shown by Vercel) | www → Vercel |
| CNAME | `api` | Railway-provided target | api → backend |

Propagation is usually minutes; both platforms verify and issue certs automatically.

## 4. Supabase auth config

Dashboard → Authentication → URL Configuration:

- [ ] Site URL: `https://tenderaudit.in`
- [ ] Redirect URLs: add `https://tenderaudit.in/**` and `https://www.tenderaudit.in/**`. Keep `http://localhost:3000/**` so local dev keeps working.

Without this, production logins/magic links bounce — the allowlist currently only has localhost.

## 5. Launch smoke checklist (run in a real browser on the live domain)

- [ ] `https://api.tenderaudit.in/health` returns ok; `https://api.tenderaudit.in/docs` loads.
- [ ] `https://tenderaudit.in` loads, title/branding say TenderAudit.
- [ ] Log in with the real account → contracts list renders with data (no CORS errors in console).
- [ ] Open a contract → Items grid, Bills, a PVC run detail page.
- [ ] Trigger one export (Excel) end-to-end.
- [ ] Log in as a freshly provisioned contact account → seeded demo contract visible.

## Known caveats to disclose (not blockers)

- KU-001-STC-AVG rounding decision open: STC-style quarter averages may differ at paisa level from contractor workbooks until decided.
- Export submission-format parity: first pass done (P8-REVIEW); multi-sheet audit trail, steel sub-lines, cover page still open.
