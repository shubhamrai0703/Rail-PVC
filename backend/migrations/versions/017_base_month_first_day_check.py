"""contracts.base_month must be the first of the month — DB CHECK

Revision ID: 017
Revises: 016
Create Date: 2026-07-17

KU1R-L1 (REVIEW.md, KU-001-REVIEW's one deferred LOW). The day=01 invariant
on `contracts.base_month` is enforced only at the API layer (create + update
in `api/contracts.py`); the column itself is bare `DATE NOT NULL`. A day≠1
value written by direct SQL (seed drift, a future import path, a manual
Supabase edit) would not break quarter math — `resolve_quarter` is provably
day-invariant — but `build_index_snapshot` matches observations by exact
date, so the run would block with a misleading "missing index" error instead
of pointing at the malformed base month. This closes that residual gap at
the storage layer.

Postgres-only (aiosqlite test fixtures never run migrations); verified
against the live DB by applying `alembic upgrade head` and confirming a
day≠1 INSERT is rejected.
"""

revision = "017"
down_revision = "016"
branch_labels = None
depends_on = None

from alembic import op
from sqlalchemy import text


def upgrade():
    op.execute(text("""
        ALTER TABLE contracts
            ADD CONSTRAINT contracts_base_month_first_day
            CHECK (EXTRACT(DAY FROM base_month) = 1)
    """))


def downgrade():
    op.execute(text("""
        ALTER TABLE contracts
            DROP CONSTRAINT IF EXISTS contracts_base_month_first_day
    """))
