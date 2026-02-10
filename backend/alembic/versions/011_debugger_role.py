"""Add Debugger role — debugger_count column to werewolf_games

Revision ID: 011_debugger_role
Revises: 010_werewolf
Create Date: 2026-02-10
"""
from alembic import op
import sqlalchemy as sa

revision = "011_debugger_role"
down_revision = "010_werewolf"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()

    # Add debugger_count column to werewolf_games
    conn.execute(sa.text("SAVEPOINT sp_debugger_count"))
    try:
        conn.execute(sa.text(
            "ALTER TABLE werewolf_games ADD COLUMN debugger_count INTEGER NOT NULL DEFAULT 0"
        ))
        conn.execute(sa.text("RELEASE SAVEPOINT sp_debugger_count"))
    except Exception:
        conn.execute(sa.text("ROLLBACK TO SAVEPOINT sp_debugger_count"))


def downgrade():
    op.drop_column("werewolf_games", "debugger_count")
