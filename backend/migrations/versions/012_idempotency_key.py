"""Idempotency for POST /pvc-runs (P3-05 remediation).

Persist the caller-supplied idempotency key on pvc_runs and enforce uniqueness
per (contract_id, bill_id, idempotency_key). The previous review (P3-05) flagged
that the prior implementation only checked for an existing Draft row even though
runs are persisted as Calculated, so duplicate POSTs created duplicate calculated
runs. The fix is real uniqueness at the database layer, not a defensive read.

Revision ID: 012
Revises: 011
Create Date: 2026-05-17
"""

revision = "012"
down_revision = "011"
branch_labels = None
depends_on = None

from alembic import op
from sqlalchemy import text


def upgrade():
    op.execute(text("""
        ALTER TABLE pvc_runs
        ADD COLUMN idempotency_key TEXT
    """))

    # Partial unique index: only enforced when a key is supplied. Lets historical
    # rows (key NULL) coexist while making same-key replays a hard conflict.
    op.execute(text("""
        CREATE UNIQUE INDEX pvc_runs_idempotency_key_uq
        ON pvc_runs (contract_id, bill_id, idempotency_key)
        WHERE idempotency_key IS NOT NULL
    """))


def downgrade():
    op.execute(text("DROP INDEX pvc_runs_idempotency_key_uq"))
    op.execute(text("ALTER TABLE pvc_runs DROP COLUMN idempotency_key"))
