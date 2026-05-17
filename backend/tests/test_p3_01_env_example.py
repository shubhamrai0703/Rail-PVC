"""P3-01 regression: backend/.env.example must contain placeholders only.

The reviewed branch committed live-looking Supabase service keys and a
real Postgres password. This test scans the example file for the
signatures of real credentials so a future regression is caught at
test-time, not at PR-review time.
"""
from __future__ import annotations

import re
from pathlib import Path

ENV_EXAMPLE = Path(__file__).resolve().parent.parent / ".env.example"


def _content() -> str:
    return ENV_EXAMPLE.read_text()


def test_env_example_exists():
    assert ENV_EXAMPLE.exists(), "backend/.env.example must exist"


def test_no_real_jwt_in_env_example():
    # Supabase JWTs are HS256 base64url tokens; their second segment is a
    # base64 payload that is always > 80 chars for a real key. Catch any
    # value that looks like a real JWT.
    body = _content()
    for line in body.splitlines():
        if line.startswith("#") or "=" not in line:
            continue
        _, _, value = line.partition("=")
        value = value.strip()
        if re.fullmatch(r"ey[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{40,}\.[A-Za-z0-9_-]{20,}", value):
            raise AssertionError(f"real-looking JWT detected in .env.example: {line!r}")


def test_no_real_postgres_password_in_env_example():
    # Inspect only the assignment lines, not comment prose (which may use angle-bracket
    # placeholders like `<urlencoded-password>` for documentation).
    for line in _content().splitlines():
        if line.lstrip().startswith("#") or "=" not in line:
            continue
        for match in re.finditer(r"postgresql(\+asyncpg)?://[^:]+:([^@]+)@", line):
            password = match.group(2)
            assert "your" in password.lower() or "placeholder" in password.lower(), (
                f"DATABASE_URL example contains non-placeholder password: {password!r}"
            )


def test_no_supabase_project_ref_leakage():
    # Real Supabase project refs look like 20 lowercase letters in the URL;
    # placeholders must contain "your-project-ref".
    body = _content()
    for match in re.finditer(r"https://([a-z]{20})\.supabase\.co", body):
        raise AssertionError(
            f"real-looking Supabase project ref in .env.example: {match.group(0)}"
        )
