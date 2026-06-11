"""pvc_run_lines_snapshot — capture bill lines per run

Revision ID: 016
Revises: 015
Create Date: 2026-06-11

P7-H2. `bill_snapshot` (migration 007) holds the engine *input* — aggregate
amounts only — so the per-item bill lines a run was calculated from were never
persisted. Bill lines are mutable after a run (bill edit + recalculate), which
left historical run pages rendering the *current* lines next to the old run's
totals: inconsistent audit data.

This adds `lines_snapshot` JSONB, written at run INSERT with the bill's lines
exactly as `GET /bills/{id}/lines` would have returned them at that moment.
Nullable: runs created before this column show "lines not captured" rather
than live (wrong) data.
"""

revision = "016"
down_revision = "015"
branch_labels = None
depends_on = None

from alembic import op
from sqlalchemy import text


def upgrade():
    op.execute(text("""
        ALTER TABLE pvc_runs
            ADD COLUMN lines_snapshot JSONB
    """))


def downgrade():
    op.execute(text("""
        ALTER TABLE pvc_runs
            DROP COLUMN IF EXISTS lines_snapshot
    """))
