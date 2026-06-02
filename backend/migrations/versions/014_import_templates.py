"""import_templates — saved column-mapping templates for items import

Revision ID: 014
Revises: 013
Create Date: 2026-06-02

Persists per-tenant column-mapping templates for the smart items-import
flow (P5-IMP). When a user imports a BOQ Excel sheet, the mapping from
source headers → target item fields can be saved here and re-applied to
future imports with matching `source_signature` (sorted+normalized hash
of the source headers).

`mapping` and `value_normalizations` are jsonb. Shape is owned by the
frontend / API contract — column added without a strict schema so the
client can evolve (e.g. add per-column transforms) without a migration.

RLS follows the same `tenant_id = get_tenant_id()` pattern as the rest
of the schema (defense-in-depth — primary gate is the API tenant
filter).
"""

revision = "014"
down_revision = "013"
branch_labels = None
depends_on = None

from alembic import op
from sqlalchemy import text


def upgrade():
    op.execute(text("""
        CREATE TABLE import_templates (
            id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id             UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            name                  TEXT NOT NULL,
            source_signature      TEXT NOT NULL,
            mapping               JSONB NOT NULL,
            value_normalizations  JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_by            UUID REFERENCES users(id) ON DELETE SET NULL,
            created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE (tenant_id, name)
        )
    """))

    op.execute(text(
        "CREATE INDEX import_templates_tenant_signature_idx "
        "ON import_templates(tenant_id, source_signature)"
    ))

    op.execute(text("ALTER TABLE import_templates ENABLE ROW LEVEL SECURITY"))
    op.execute(text("ALTER TABLE import_templates FORCE ROW LEVEL SECURITY"))

    op.execute(text("""
        CREATE POLICY import_templates_select ON import_templates FOR SELECT
        USING (tenant_id = get_tenant_id())
    """))
    op.execute(text("""
        CREATE POLICY import_templates_insert ON import_templates FOR INSERT
        WITH CHECK (tenant_id = get_tenant_id())
    """))
    op.execute(text("""
        CREATE POLICY import_templates_update ON import_templates FOR UPDATE
        USING (tenant_id = get_tenant_id())
        WITH CHECK (tenant_id = get_tenant_id())
    """))
    op.execute(text("""
        CREATE POLICY import_templates_delete ON import_templates FOR DELETE
        USING (tenant_id = get_tenant_id())
    """))


def downgrade():
    op.execute(text("DROP TABLE IF EXISTS import_templates"))
