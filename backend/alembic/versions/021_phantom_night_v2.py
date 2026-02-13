"""Phantom Night v2 — Real-time chat werewolf

- Create game_messages table for in-game chat
- Change werewolf_games duration columns from hours to minutes
- Delete all existing game data (clean start for v2)

Revision ID: 021_phantom_night_v2
Revises: 020_add_consultation_tables
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision = '021_phantom_night_v2'
down_revision = '020_add_consultation_tables'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Clean start: delete all existing game data ──
    op.execute("DELETE FROM werewolf_game_events")
    op.execute("DELETE FROM night_actions")
    op.execute("DELETE FROM day_votes")
    op.execute("DELETE FROM werewolf_roles")
    # Clear current_game_id references before deleting games
    op.execute("UPDATE residents SET current_game_id = NULL WHERE current_game_id IS NOT NULL")
    op.execute("DELETE FROM werewolf_games")

    # ── Create game_messages table ──
    op.create_table(
        'game_messages',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('game_id', UUID(as_uuid=True), sa.ForeignKey('werewolf_games.id'), nullable=False, index=True),
        sa.Column('sender_id', UUID(as_uuid=True), sa.ForeignKey('residents.id'), nullable=True),
        sa.Column('sender_name', sa.String(100), nullable=False),
        sa.Column('content', sa.Text, nullable=False),
        sa.Column('message_type', sa.String(20), nullable=False, server_default='chat'),
        sa.Column('round_number', sa.Integer, nullable=False),
        sa.Column('phase', sa.String(10), nullable=False),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now(), index=True),
    )
    op.create_index('ix_game_messages_game_created', 'game_messages', ['game_id', 'created_at'])
    op.create_index('ix_game_messages_game_type_created', 'game_messages', ['game_id', 'message_type', 'created_at'])

    # ── Change duration columns from hours to minutes ──
    # Use SAVEPOINT for safety on VPS with potentially different schema
    op.execute("SAVEPOINT add_day_minutes")
    try:
        op.add_column('werewolf_games', sa.Column('day_duration_minutes', sa.Integer, server_default='5'))
        op.execute("RELEASE SAVEPOINT add_day_minutes")
    except Exception:
        op.execute("ROLLBACK TO SAVEPOINT add_day_minutes")

    op.execute("SAVEPOINT add_night_minutes")
    try:
        op.add_column('werewolf_games', sa.Column('night_duration_minutes', sa.Integer, server_default='2'))
        op.execute("RELEASE SAVEPOINT add_night_minutes")
    except Exception:
        op.execute("ROLLBACK TO SAVEPOINT add_night_minutes")

    # Drop old hour columns (safe since we deleted all data)
    op.execute("SAVEPOINT drop_day_hours")
    try:
        op.drop_column('werewolf_games', 'day_duration_hours')
        op.execute("RELEASE SAVEPOINT drop_day_hours")
    except Exception:
        op.execute("ROLLBACK TO SAVEPOINT drop_day_hours")

    op.execute("SAVEPOINT drop_night_hours")
    try:
        op.drop_column('werewolf_games', 'night_duration_hours')
        op.execute("RELEASE SAVEPOINT drop_night_hours")
    except Exception:
        op.execute("ROLLBACK TO SAVEPOINT drop_night_hours")


def downgrade() -> None:
    op.drop_table('game_messages')
    op.add_column('werewolf_games', sa.Column('day_duration_hours', sa.Integer, server_default='20'))
    op.add_column('werewolf_games', sa.Column('night_duration_hours', sa.Integer, server_default='4'))
    op.execute("SAVEPOINT drop_new_cols")
    try:
        op.drop_column('werewolf_games', 'day_duration_minutes')
        op.drop_column('werewolf_games', 'night_duration_minutes')
        op.execute("RELEASE SAVEPOINT drop_new_cols")
    except Exception:
        op.execute("ROLLBACK TO SAVEPOINT drop_new_cols")
