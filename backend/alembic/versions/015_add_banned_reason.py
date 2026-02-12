"""Add banned_reason column to residents

Revision ID: 015_add_banned_reason
Revises: 014_add_speed_column
Create Date: 2026-02-12
"""
from alembic import op
import sqlalchemy as sa

revision = "015_add_banned_reason"
down_revision = "014_add_speed_column"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Use SAVEPOINT pattern for idempotency on VPS
    conn = op.get_bind()
    conn.execute(sa.text("SAVEPOINT sp_banned_reason"))
    try:
        op.add_column("residents", sa.Column("banned_reason", sa.Text(), nullable=True))
    except Exception:
        conn.execute(sa.text("ROLLBACK TO SAVEPOINT sp_banned_reason"))
    else:
        conn.execute(sa.text("RELEASE SAVEPOINT sp_banned_reason"))


def downgrade() -> None:
    op.drop_column("residents", "banned_reason")
