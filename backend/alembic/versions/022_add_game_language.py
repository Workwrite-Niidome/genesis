"""Add language column to werewolf_games

Revision ID: 022_add_game_language
Revises: 021_phantom_night_v2
"""
from alembic import op
import sqlalchemy as sa


revision = '022_add_game_language'
down_revision = '021_phantom_night_v2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    # SAVEPOINT pattern for idempotency
    conn.execute(sa.text("SAVEPOINT sp_add_language"))
    try:
        conn.execute(sa.text(
            "ALTER TABLE werewolf_games ADD COLUMN language VARCHAR(5) DEFAULT 'en'"
        ))
        conn.execute(sa.text("RELEASE SAVEPOINT sp_add_language"))
    except Exception:
        conn.execute(sa.text("ROLLBACK TO SAVEPOINT sp_add_language"))


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("SAVEPOINT sp_drop_language"))
    try:
        conn.execute(sa.text(
            "ALTER TABLE werewolf_games DROP COLUMN IF EXISTS language"
        ))
        conn.execute(sa.text("RELEASE SAVEPOINT sp_drop_language"))
    except Exception:
        conn.execute(sa.text("ROLLBACK TO SAVEPOINT sp_drop_language"))
