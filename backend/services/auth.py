"""Supabase JWT verification and tenant context.

Every protected route depends on `get_current_user`, which:
  1. Extracts the Bearer token from the Authorization header
  2. Verifies its signature via Supabase's JWKS endpoint (supports ES256 and HS256)
  3. Looks up the local `users` row by supabase_auth_id to resolve tenant_id

The tenant_id is the authority for tenant isolation everywhere downstream.
Routes MUST pass it into every query — the backend uses a privileged DB
connection (see services/db.py), so RLS does not protect us at runtime
(P3-03). Tenant isolation is the API layer's job, not the database's.

Note: Supabase newer projects issue ES256 tokens signed with an EC key pair.
We verify via JWKS (PyJWKClient caches the public key) rather than a static
HS256 secret, which supports both algorithms transparently.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache

import jwt
from jwt import PyJWKClient
from fastapi import Depends, Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from .db import get_session
from .errors import AuthProblem


@dataclass(frozen=True)
class AuthUser:
    user_id: str          # internal users.id (UUID)
    tenant_id: str        # users.tenant_id (UUID)
    auth_id: str          # Supabase auth.users.id
    email: str | None
    display_name: str | None  # email or claim — used as approved_by


@lru_cache(maxsize=1)
def _jwks_client() -> PyJWKClient:
    url = os.environ.get("SUPABASE_URL", "").rstrip("/")
    if not url:
        raise AuthProblem("Auth not configured: SUPABASE_URL unset")
    return PyJWKClient(f"{url}/auth/v1/.well-known/jwks.json", cache_keys=True)


def _bearer(request: Request) -> str:
    auth = request.headers.get("authorization") or request.headers.get("Authorization")
    if not auth or not auth.lower().startswith("bearer "):
        raise AuthProblem("Missing or malformed Authorization header")
    return auth.split(" ", 1)[1].strip()


def _decode(token: str) -> dict:
    try:
        signing_key = _jwks_client().get_signing_key_from_jwt(token)
        return jwt.decode(
            token,
            signing_key.key,
            algorithms=["ES256", "HS256"],
            audience="authenticated",
            options={"require": ["exp", "sub"]},
        )
    except AuthProblem:
        raise
    except jwt.PyJWTError as exc:
        raise AuthProblem(f"Invalid token: {exc}") from exc
    except Exception as exc:
        raise AuthProblem(f"Token verification failed: {exc}") from exc


async def get_current_user(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> AuthUser:
    token = _bearer(request)
    claims = _decode(token)
    auth_id = str(claims.get("sub"))
    email = claims.get("email")

    row = (
        await session.execute(
            text("""
                SELECT id::text AS id, tenant_id::text AS tenant_id, email
                FROM users
                WHERE supabase_auth_id = :auth_id
            """),
            {"auth_id": auth_id},
        )
    ).mappings().first()

    if row is None:
        raise AuthProblem("Authenticated user has no provisioned tenant")

    return AuthUser(
        user_id=row["id"],
        tenant_id=row["tenant_id"],
        auth_id=auth_id,
        email=row["email"] or email,
        display_name=row["email"] or email or auth_id,
    )
