"""Add lobby/matchmaking columns to werewolf_games

Revision ID: 012_lobby_matchmaking
Revises: 011_debugger_role
Create Date: 2026-02-10
"""
from alembic import op
import sqlalchemy as sa

revision = "012_lobby_matchmaking"
down_revision = "011_debugger_role"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()

    # Add max_players column
    conn.execute(sa.text("SAVEPOINT sp_max_players"))
    try:
        conn.execute(sa.text(
            "ALTER TABLE werewolf_games ADD COLUMN max_players INTEGER"
        ))
        conn.execute(sa.text("RELEASE SAVEPOINT sp_max_players"))
    except Exception:
        conn.execute(sa.text("ROLLBACK TO SAVEPOINT sp_max_players"))

    # Add creator_id column
    conn.execute(sa.text("SAVEPOINT sp_creator_id"))
    try:
        conn.execute(sa.text(
            "ALTER TABLE werewolf_games ADD COLUMN creator_id UUID REFERENCES residents(id)"
        ))
        conn.execute(sa.text("RELEASE SAVEPOINT sp_creator_id"))
    except Exception:
        conn.execute(sa.text("ROLLBACK TO SAVEPOINT sp_creator_id"))


def downgrade():
    op.drop_column("werewolf_games", "creator_id")
    op.drop_column("werewolf_games", "max_players")
