"""Invite-only tenant provisioning for first login.

Revision ID: 019
Revises: 018
Create Date: 2026-07-19

Tenant and demo data are prepared before an outside user authenticates. The
backend may consume an invite through its privileged connection, while RLS
with no client policies keeps invite addresses unavailable to browser clients.
"""

revision = "019"
down_revision = "018"
branch_labels = None
depends_on = None

from alembic import op
from sqlalchemy import text


def upgrade():
    op.execute(text("""
        CREATE TABLE tenant_invites (
            id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id    UUID NOT NULL REFERENCES tenants(id),
            email        TEXT NOT NULL,
            created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            consumed_at  TIMESTAMPTZ,
            CHECK (email <> '' AND email = lower(btrim(email)))
        )
    """))

    op.execute(text("""
        CREATE UNIQUE INDEX tenant_invites_email_lower_uidx
        ON tenant_invites ((lower(email)))
    """))
    op.execute(text("""
        CREATE INDEX tenant_invites_tenant_id_idx
        ON tenant_invites (tenant_id)
    """))

    op.execute(text("ALTER TABLE tenant_invites ENABLE ROW LEVEL SECURITY"))
    op.execute(text("ALTER TABLE tenant_invites FORCE ROW LEVEL SECURITY"))


def downgrade():
    op.execute(text("DROP TABLE IF EXISTS tenant_invites"))
