"""pvc_rule_sets quarter-average precision policy

Revision ID: 018
Revises: 017
Create Date: 2026-07-19

KU-001-STC-AVG. Quarterly series averages normally retain full precision.
Some versioned rule sets explicitly require ROUND_HALF_UP to two decimal
places before formula use. Persisting that choice on the referenced rule-set
row keeps each PVC run deterministic and auditable.
"""

revision = "018"
down_revision = "017"
branch_labels = None
depends_on = None

from alembic import op
from sqlalchemy import text


def upgrade():
    op.execute(text("""
        ALTER TABLE pvc_rule_sets
            ADD COLUMN quarter_avg_precision TEXT NOT NULL DEFAULT 'full'
            CHECK (quarter_avg_precision IN ('full', 'half_up_2dp'))
    """))


def downgrade():
    op.execute(text("""
        ALTER TABLE pvc_rule_sets
            DROP COLUMN IF EXISTS quarter_avg_precision
    """))
