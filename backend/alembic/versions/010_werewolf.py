"""Add Phantom Night (werewolf game) tables

Revision ID: 010_werewolf
Revises: 009_god_vision
Create Date: 2026-02-10
"""
from alembic import op
import sqlalchemy as sa

revision = "010_werewolf"
down_revision = "009_god_vision"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()

    # ── werewolf_games table ──────────────────────────────────────────
    conn.execute(sa.text("SAVEPOINT sp_werewolf_games"))
    try:
        conn.execute(sa.text("""
            CREATE TABLE IF NOT EXISTS werewolf_games (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                game_number INTEGER NOT NULL UNIQUE,
                status VARCHAR(20) NOT NULL DEFAULT 'preparing',
                current_phase VARCHAR(10),
                current_round INTEGER NOT NULL DEFAULT 0,
                phase_started_at TIMESTAMP,
                phase_ends_at TIMESTAMP,
                day_duration_hours INTEGER NOT NULL DEFAULT 20,
                night_duration_hours INTEGER NOT NULL DEFAULT 4,
                total_players INTEGER NOT NULL DEFAULT 0,
                phantom_count INTEGER NOT NULL DEFAULT 0,
                citizen_count INTEGER NOT NULL DEFAULT 0,
                oracle_count INTEGER NOT NULL DEFAULT 0,
                guardian_count INTEGER NOT NULL DEFAULT 0,
                fanatic_count INTEGER NOT NULL DEFAULT 0,
                winner_team VARCHAR(20),
                created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                started_at TIMESTAMP,
                ended_at TIMESTAMP
            );
        """))
        conn.execute(sa.text("RELEASE SAVEPOINT sp_werewolf_games"))
    except Exception:
        conn.execute(sa.text("ROLLBACK TO SAVEPOINT sp_werewolf_games"))

    # ── werewolf_roles table ──────────────────────────────────────────
    conn.execute(sa.text("SAVEPOINT sp_werewolf_roles"))
    try:
        conn.execute(sa.text("""
            CREATE TABLE IF NOT EXISTS werewolf_roles (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                game_id UUID NOT NULL REFERENCES werewolf_games(id),
                resident_id UUID NOT NULL REFERENCES residents(id),
                role VARCHAR(20) NOT NULL,
                team VARCHAR(20) NOT NULL,
                is_alive BOOLEAN NOT NULL DEFAULT TRUE,
                eliminated_round INTEGER,
                eliminated_by VARCHAR(20),
                investigation_results JSONB DEFAULT '[]'::jsonb,
                night_action_taken BOOLEAN NOT NULL DEFAULT FALSE,
                day_vote_cast BOOLEAN NOT NULL DEFAULT FALSE,
                UNIQUE(game_id, resident_id)
            );
        """))
        conn.execute(sa.text("RELEASE SAVEPOINT sp_werewolf_roles"))
    except Exception:
        conn.execute(sa.text("ROLLBACK TO SAVEPOINT sp_werewolf_roles"))

    # ── night_actions table ───────────────────────────────────────────
    conn.execute(sa.text("SAVEPOINT sp_night_actions"))
    try:
        conn.execute(sa.text("""
            CREATE TABLE IF NOT EXISTS night_actions (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                game_id UUID NOT NULL REFERENCES werewolf_games(id),
                actor_id UUID NOT NULL REFERENCES residents(id),
                target_id UUID NOT NULL REFERENCES residents(id),
                round_number INTEGER NOT NULL,
                action_type VARCHAR(30) NOT NULL,
                result VARCHAR(30),
                created_at TIMESTAMP NOT NULL DEFAULT NOW()
            );
        """))
        conn.execute(sa.text("RELEASE SAVEPOINT sp_night_actions"))
    except Exception:
        conn.execute(sa.text("ROLLBACK TO SAVEPOINT sp_night_actions"))

    # ── day_votes table ───────────────────────────────────────────────
    conn.execute(sa.text("SAVEPOINT sp_day_votes"))
    try:
        conn.execute(sa.text("""
            CREATE TABLE IF NOT EXISTS day_votes (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                game_id UUID NOT NULL REFERENCES werewolf_games(id),
                voter_id UUID NOT NULL REFERENCES residents(id),
                target_id UUID NOT NULL REFERENCES residents(id),
                round_number INTEGER NOT NULL,
                reason TEXT,
                created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
                UNIQUE(game_id, voter_id, round_number)
            );
        """))
        conn.execute(sa.text("RELEASE SAVEPOINT sp_day_votes"))
    except Exception:
        conn.execute(sa.text("ROLLBACK TO SAVEPOINT sp_day_votes"))

    # ── werewolf_game_events table ────────────────────────────────────
    conn.execute(sa.text("SAVEPOINT sp_werewolf_events"))
    try:
        conn.execute(sa.text("""
            CREATE TABLE IF NOT EXISTS werewolf_game_events (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                game_id UUID NOT NULL REFERENCES werewolf_games(id),
                round_number INTEGER NOT NULL,
                phase VARCHAR(10) NOT NULL,
                event_type VARCHAR(30) NOT NULL,
                message TEXT NOT NULL,
                target_id UUID REFERENCES residents(id),
                revealed_role VARCHAR(20),
                revealed_type VARCHAR(10),
                created_at TIMESTAMP NOT NULL DEFAULT NOW()
            );
        """))
        conn.execute(sa.text("RELEASE SAVEPOINT sp_werewolf_events"))
    except Exception:
        conn.execute(sa.text("ROLLBACK TO SAVEPOINT sp_werewolf_events"))

    # ── Add current_game_id to residents ──────────────────────────────
    conn.execute(sa.text("SAVEPOINT sp_resident_game_id"))
    try:
        conn.execute(sa.text(
            "ALTER TABLE residents ADD COLUMN current_game_id UUID REFERENCES werewolf_games(id)"
        ))
        conn.execute(sa.text("RELEASE SAVEPOINT sp_resident_game_id"))
    except Exception:
        conn.execute(sa.text("ROLLBACK TO SAVEPOINT sp_resident_game_id"))

    # ── Indexes ───────────────────────────────────────────────────────
    for idx_sql in [
        "CREATE INDEX IF NOT EXISTS ix_werewolf_roles_game_id ON werewolf_roles(game_id);",
        "CREATE INDEX IF NOT EXISTS ix_werewolf_roles_resident_id ON werewolf_roles(resident_id);",
        "CREATE INDEX IF NOT EXISTS ix_night_actions_game_id ON night_actions(game_id);",
        "CREATE INDEX IF NOT EXISTS ix_day_votes_game_id ON day_votes(game_id);",
        "CREATE INDEX IF NOT EXISTS ix_werewolf_events_game_id ON werewolf_game_events(game_id);",
        "CREATE INDEX IF NOT EXISTS ix_werewolf_games_status ON werewolf_games(status);",
    ]:
        conn.execute(sa.text(f"SAVEPOINT sp_idx"))
        try:
            conn.execute(sa.text(idx_sql))
            conn.execute(sa.text("RELEASE SAVEPOINT sp_idx"))
        except Exception:
            conn.execute(sa.text("ROLLBACK TO SAVEPOINT sp_idx"))


def downgrade():
    op.drop_table("werewolf_game_events")
    op.drop_table("day_votes")
    op.drop_table("night_actions")
    op.drop_table("werewolf_roles")
    op.execute("ALTER TABLE residents DROP COLUMN IF EXISTS current_game_id")
    op.drop_table("werewolf_games")
