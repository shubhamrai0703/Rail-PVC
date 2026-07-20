"""Create one tenant and one invite for invite-only first-login provisioning.

Required environment variables:

  PROVISION_TENANT_NAME   Display name for the prepared tenant
  PROVISION_INVITE_EMAIL  Supabase signup email that may join the tenant

The script reads DATABASE_URL from backend/.env, matches the other seed
scripts' asyncpg connection pattern, and is safe to re-run. The normalized
invite email is the idempotency key; a repeat prints the original tenant UUID.
"""
from __future__ import annotations

import asyncio
import os
import sys
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = REPO_ROOT / "backend"

sys.path.insert(0, str(BACKEND_DIR))

try:
    from dotenv import load_dotenv

    import asyncpg
    from sqlalchemy.engine.url import make_url
except ModuleNotFoundError:
    if os.environ.get("RAILPVC_SEED_BACKEND_UV") != "1":
        env = os.environ.copy()
        env["RAILPVC_SEED_BACKEND_UV"] = "1"
        os.execvpe(
            "uv",
            [
                "uv",
                "--project",
                str(BACKEND_DIR),
                "run",
                "python",
                str(Path(__file__).resolve()),
            ],
            env,
        )
    raise

load_dotenv(BACKEND_DIR / ".env", override=False)


@dataclass(frozen=True)
class ProvisionConfig:
    tenant_name: str
    invite_email: str

    @classmethod
    def from_env(cls) -> "ProvisionConfig":
        tenant_name = os.environ.get("PROVISION_TENANT_NAME", "").strip()
        invite_email = os.environ.get("PROVISION_INVITE_EMAIL", "").strip().lower()
        if not tenant_name:
            raise SystemExit("PROVISION_TENANT_NAME is required")
        if not invite_email:
            raise SystemExit("PROVISION_INVITE_EMAIL is required")
        if (
            invite_email.count("@") != 1
            or invite_email.startswith("@")
            or invite_email.endswith("@")
            or any(char.isspace() for char in invite_email)
        ):
            raise SystemExit("PROVISION_INVITE_EMAIL must be a valid email address")
        return cls(tenant_name=tenant_name, invite_email=invite_email)


async def connect() -> asyncpg.Connection:
    raw = os.environ["DATABASE_URL"].strip()
    url = make_url(raw)
    return await asyncpg.connect(
        host=url.host,
        port=url.port,
        user=url.username,
        password=str(url.password),
        database=url.database,
    )


async def provision(
    conn: asyncpg.Connection,
    config: ProvisionConfig,
) -> tuple[str, bool]:
    async with conn.transaction():
        # The normalized email is both the operator idempotency key and the
        # concurrency key. It prevents concurrent runs from leaving an orphan
        # tenant behind before the unique invite insert.
        await conn.execute(
            "SELECT pg_advisory_xact_lock(hashtextextended($1, 0))",
            config.invite_email,
        )

        existing = await conn.fetchrow(
            """
            SELECT tenant_id::text AS tenant_id
            FROM tenant_invites
            WHERE lower(email) = lower($1)
            """,
            config.invite_email,
        )
        if existing is not None:
            return existing["tenant_id"], False

        tenant = await conn.fetchrow(
            """
            INSERT INTO tenants (name)
            VALUES ($1)
            RETURNING id::text AS id
            """,
            config.tenant_name,
        )
        assert tenant is not None
        tenant_id = tenant["id"]

        await conn.execute(
            """
            INSERT INTO tenant_invites (tenant_id, email)
            VALUES ($1::uuid, $2)
            """,
            tenant_id,
            config.invite_email,
        )
        return tenant_id, True


async def main() -> None:
    config = ProvisionConfig.from_env()
    conn = await connect()
    try:
        tenant_id, created = await provision(conn, config)
    finally:
        await conn.close()

    action = "created" if created else "skipped"
    print(f"tenant: {action} {tenant_id}")
    print(f"invite: {action} {config.invite_email}")
    print(f"TENANT_ID={tenant_id}")


if __name__ == "__main__":
    asyncio.run(main())
