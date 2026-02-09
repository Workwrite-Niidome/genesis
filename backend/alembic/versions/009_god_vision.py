"""Add god_type to god_terms for God type revelation

Revision ID: 009
Revises: 008
Create Date: 2026-02-09
"""
from alembic import op
import sqlalchemy as sa

revision = "009_god_vision"
down_revision = "008_turing_game"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()

    # Add god_type column to god_terms
    conn.execute(sa.text("SAVEPOINT sp_god_type"))
    try:
        conn.execute(sa.text(
            "ALTER TABLE god_terms ADD COLUMN god_type VARCHAR(10)"
        ))
        conn.execute(sa.text("RELEASE SAVEPOINT sp_god_type"))
    except Exception:
        conn.execute(sa.text("ROLLBACK TO SAVEPOINT sp_god_type"))


def downgrade():
    op.drop_column("god_terms", "god_type")
