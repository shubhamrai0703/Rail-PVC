"""Durable Supabase document-object cleanup queue.

Revision ID: 020
Revises: 019
Create Date: 2026-07-23

The queue deliberately keeps ``source_contract_id`` without a foreign key:
the source contract is deleted in the same transaction that creates the job.
No client RLS policy is defined; only the privileged backend may inspect or
process retained storage paths.
"""

revision = "020"
down_revision = "019"
branch_labels = None
depends_on = None

from alembic import op
from sqlalchemy import text


def upgrade():
    op.execute(text("""
        CREATE TABLE document_cleanup_jobs (
            id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id          UUID NOT NULL REFERENCES tenants(id),
            source_contract_id UUID NOT NULL,
            storage_path       TEXT NOT NULL,
            attempt_count      INTEGER NOT NULL DEFAULT 0
                               CHECK (attempt_count >= 0),
            last_error         TEXT,
            created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            last_attempt_at    TIMESTAMPTZ,
            next_attempt_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            completed_at       TIMESTAMPTZ,
            quarantined_at     TIMESTAMPTZ,
            claim_token        UUID,
            claim_expires_at   TIMESTAMPTZ,
            CHECK (
                (claim_token IS NULL) = (claim_expires_at IS NULL)
            ),
            CHECK (
                storage_path LIKE (
                    tenant_id::text || '/' ||
                    source_contract_id::text || '/%'
                )
            ),
            UNIQUE (storage_path)
        )
    """))
    op.execute(text("""
        CREATE INDEX document_cleanup_jobs_pending_tenant_idx
        ON document_cleanup_jobs (
            tenant_id, next_attempt_at, claim_expires_at, created_at, id
        )
        WHERE completed_at IS NULL AND quarantined_at IS NULL
    """))
    op.execute(text("DROP POLICY IF EXISTS documents_insert ON documents"))
    op.execute(text("DROP POLICY IF EXISTS documents_delete ON documents"))
    op.execute(text(
        "ALTER TABLE document_cleanup_jobs ENABLE ROW LEVEL SECURITY"
    ))
    op.execute(text(
        "ALTER TABLE document_cleanup_jobs FORCE ROW LEVEL SECURITY"
    ))


def downgrade():
    op.execute(text("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM document_cleanup_jobs
                WHERE completed_at IS NULL
            ) THEN
                RAISE EXCEPTION
                    'cannot downgrade: pending document cleanup jobs exist';
            END IF;
        END
        $$
    """))
    op.execute(text("DROP TABLE document_cleanup_jobs"))
    op.execute(text("""
        CREATE POLICY documents_insert ON documents FOR INSERT
        WITH CHECK (
            contract_id IN (
                SELECT id FROM contracts
                WHERE tenant_id = get_tenant_id()
            )
        )
    """))
    op.execute(text("""
        CREATE POLICY documents_delete ON documents FOR DELETE
        USING (
            contract_id IN (
                SELECT id FROM contracts
                WHERE tenant_id = get_tenant_id()
            )
        )
    """))
