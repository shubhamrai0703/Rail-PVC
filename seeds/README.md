# Seed scripts

Scripts to provision an invited tenant, load reference index data, and seed a
full end-to-end demo contract. They read `DATABASE_URL` from `backend/.env` and
connect with the same asyncpg pattern, so they can be run from the repo root
with a bare `uv run` — they auto re-exec under the backend environment.

## Prerequisites

- A valid `backend/.env` with a working `DATABASE_URL` (Supabase pooler URL).
  If the password contains special characters, URL-encode them (e.g. `@` → `%40`).
- Migration 019 must be applied before provisioning an invited tenant.
- The invite email must match the address used for Supabase signup.

## Run order

Provision the tenant and invite before the user logs in. Indices are global
(not tenant-scoped) and must exist before the demo contract, which validates
that the index months it needs are present.

```bash
# 1. Create the tenant + invite. Idempotent; note the printed TENANT_ID.
PROVISION_TENANT_NAME="<tenant name>" \
PROVISION_INVITE_EMAIL="<invite email>" \
uv run python seeds/provision_tenant.py

# 2. Reference index data (RBI + JPC steel). Idempotent.
uv run python seeds/seed_indices.py

# 3. Demo contract BCT-24-25-252 with two running bills. Idempotent.
SEED_TENANT_ID="<printed tenant UUID>" uv run python seeds/seed_demo_contract.py
```

All three scripts are safe to re-run sequentially. Existing rows are detected
by their natural keys and skipped, so no duplicates are created.

## Targeting a tenant

`seed_demo_contract.py` requires `SEED_TENANT_ID` and has no default. A missing
variable aborts instead of risking writes to another tenant:

```bash
SEED_TENANT_ID=<your-tenant-uuid> uv run python seeds/seed_demo_contract.py
```

Find your tenant uuid by email:

```bash
uv --project backend run python -c "
import os, asyncio, asyncpg
from dotenv import load_dotenv
from sqlalchemy.engine.url import make_url
load_dotenv('backend/.env', override=True)
u = make_url(os.environ['DATABASE_URL'].strip())
async def go():
    c = await asyncpg.connect(host=u.host, port=u.port, user=u.username,
                              password=str(u.password), database=u.database)
    for r in await c.fetch(\"select tenant_id::text, email from users where email=\$1\",
                           'you@example.com'):
        print(r['email'], '->', r['tenant_id'])
    await c.close()
asyncio.run(go())
"
```

After seeding, refresh the app and open the contract from the run summary:
`/contracts/<contract_id>/bills`.

## Troubleshooting

- **`password authentication failed`** — the `DATABASE_URL` password in
  `backend/.env` is stale or not URL-encoded. Refresh it from the Supabase
  dashboard (Project Settings → Database) and encode special characters.
- **`Missing required index observations`** — run `seed_indices.py` first.
- **`SEED_TENANT_ID is required`** — pass the UUID printed by
  `provision_tenant.py`; there is intentionally no fallback tenant.
- **`Tenant <uuid> not found`** — run `provision_tenant.py` first or pass an
  existing tenant UUID.
- **Seed succeeds but you can't see the contract** — you seeded a different
  tenant than the one your login uses. Re-run with the correct `SEED_TENANT_ID`.
