"""Force-finish stale games and clear current_game_id

One-time cleanup: the old auto-created Game #1 (187 players) blocks
all AI agents from joining new games. Force all non-finished games
to 'finished' and clear every resident's current_game_id.

Revision ID: 013_cleanup_stale_games
Revises: 012_lobby_matchmaking
Create Date: 2026-02-10
"""
from alembic import op
import sqlalchemy as sa

revision = "013_cleanup_stale_games"
down_revision = "012_lobby_matchmaking"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()

    # Force-finish all non-finished games
    conn.execute(sa.text("SAVEPOINT sp_finish_games"))
    try:
        conn.execute(sa.text(
            "UPDATE werewolf_games SET status = 'finished', "
            "winner_team = 'citizens', ended_at = NOW() "
            "WHERE status != 'finished'"
        ))
        conn.execute(sa.text("RELEASE SAVEPOINT sp_finish_games"))
    except Exception:
        conn.execute(sa.text("ROLLBACK TO SAVEPOINT sp_finish_games"))

    # Clear all current_game_id
    conn.execute(sa.text("SAVEPOINT sp_clear_game_id"))
    try:
        conn.execute(sa.text(
            "UPDATE residents SET current_game_id = NULL "
            "WHERE current_game_id IS NOT NULL"
        ))
        conn.execute(sa.text("RELEASE SAVEPOINT sp_clear_game_id"))
    except Exception:
        conn.execute(sa.text("ROLLBACK TO SAVEPOINT sp_clear_game_id"))


def downgrade():
    pass  # One-time cleanup, no rollback
