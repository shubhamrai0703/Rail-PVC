"""pvc_run_outputs — persist engine result totals on pvc_runs

Revision ID: 015
Revises: 014
Create Date: 2026-06-09

Phase 7. The PVC engine returns `total_pvc`, `negative_carry_forward`
(the amount to recover from the next bill under the zero_floor policy),
and `quarter_used` from each run, but the original `pvc_runs` table
(migration 007) only persisted the W-derivation and snapshots — the
result totals were available only in the synchronous POST response and
lost thereafter. That left the output carry-forward unretrievable, an
audit gap once the run-results UI (D-2) needs to display it.

This adds the three result fields as first-class columns, written at run
INSERT from the engine result. `total_pvc` remains derivable as the sum
of `pvc_components.pvc_value`, but storing it makes the run-history list
(D-1b) a single-row read instead of a per-run aggregate.

All three are nullable: existing dev rows pre-date this column and the
engine emits `total_pvc=NULL` / `quarter_used=NULL` for runs blocked
before computation.
"""

revision = "015"
down_revision = "014"
branch_labels = None
depends_on = None

from alembic import op
from sqlalchemy import text


def upgrade():
    op.execute(text("""
        ALTER TABLE pvc_runs
            ADD COLUMN total_pvc              NUMERIC(15, 4),
            ADD COLUMN negative_carry_forward NUMERIC(15, 4),
            ADD COLUMN quarter_used           TEXT
    """))


def downgrade():
    op.execute(text("""
        ALTER TABLE pvc_runs
            DROP COLUMN IF EXISTS total_pvc,
            DROP COLUMN IF EXISTS negative_carry_forward,
            DROP COLUMN IF EXISTS quarter_used
    """))
