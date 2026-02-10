"""Add speed column to werewolf_games

Revision ID: 014_add_speed_column
Revises: 013_cleanup_stale_games
Create Date: 2026-02-11
"""
from alembic import op
import sqlalchemy as sa

revision = "014_add_speed_column"
down_revision = "013_cleanup_stale_games"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    # Add column only if it doesn't exist (SAVEPOINT for safety on VPS)
    conn.execute(sa.text("SAVEPOINT sp_speed"))
    try:
        op.add_column("werewolf_games", sa.Column("speed", sa.String(20), nullable=True))
    except Exception:
        conn.execute(sa.text("ROLLBACK TO SAVEPOINT sp_speed"))
    else:
        conn.execute(sa.text("RELEASE SAVEPOINT sp_speed"))


def downgrade() -> None:
    op.drop_column("werewolf_games", "speed")
