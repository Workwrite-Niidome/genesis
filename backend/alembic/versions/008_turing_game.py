"""Turing Game — AI vs Human social deduction tables

Revision ID: 008
Revises: 007
Create Date: 2026-02-09
"""
from alembic import op
import sqlalchemy as sa

revision = "008_turing_game"
down_revision = "007_karma_as_life"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()

    # === Table 1: turing_kills ===
    conn.execute(sa.text("SAVEPOINT sp_turing_kills"))
    try:
        conn.execute(sa.text("""
            CREATE TABLE IF NOT EXISTS turing_kills (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                attacker_id UUID NOT NULL REFERENCES residents(id),
                target_id UUID NOT NULL REFERENCES residents(id),
                result VARCHAR(20) NOT NULL,
                target_actual_type VARCHAR(10) NOT NULL,
                target_had_shield BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP NOT NULL DEFAULT NOW()
            );
        """))
        conn.execute(sa.text(
            "CREATE INDEX IF NOT EXISTS ix_turing_kills_attacker_created "
            "ON turing_kills (attacker_id, created_at);"
        ))
        conn.execute(sa.text(
            "CREATE INDEX IF NOT EXISTS ix_turing_kills_target_created "
            "ON turing_kills (target_id, created_at);"
        ))
        conn.execute(sa.text("RELEASE SAVEPOINT sp_turing_kills"))
    except Exception:
        conn.execute(sa.text("ROLLBACK TO SAVEPOINT sp_turing_kills"))

    # === Table 2: suspicion_reports ===
    conn.execute(sa.text("SAVEPOINT sp_suspicion_reports"))
    try:
        conn.execute(sa.text("""
            CREATE TABLE IF NOT EXISTS suspicion_reports (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                reporter_id UUID NOT NULL REFERENCES residents(id),
                target_id UUID NOT NULL REFERENCES residents(id),
                reason TEXT,
                was_accurate BOOLEAN,
                created_at TIMESTAMP NOT NULL DEFAULT NOW()
            );
        """))
        conn.execute(sa.text(
            "CREATE INDEX IF NOT EXISTS ix_suspicion_reports_reporter_created "
            "ON suspicion_reports (reporter_id, created_at);"
        ))
        conn.execute(sa.text(
            "CREATE INDEX IF NOT EXISTS ix_suspicion_reports_target_created "
            "ON suspicion_reports (target_id, created_at);"
        ))
        conn.execute(sa.text("RELEASE SAVEPOINT sp_suspicion_reports"))
    except Exception:
        conn.execute(sa.text("ROLLBACK TO SAVEPOINT sp_suspicion_reports"))

    # === Table 3: exclusion_reports ===
    conn.execute(sa.text("SAVEPOINT sp_exclusion_reports"))
    try:
        conn.execute(sa.text("""
            CREATE TABLE IF NOT EXISTS exclusion_reports (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                reporter_id UUID NOT NULL REFERENCES residents(id),
                target_id UUID NOT NULL REFERENCES residents(id),
                evidence_type VARCHAR(20),
                evidence_id UUID,
                reason TEXT,
                was_accurate BOOLEAN,
                created_at TIMESTAMP NOT NULL DEFAULT NOW()
            );
        """))
        conn.execute(sa.text(
            "CREATE INDEX IF NOT EXISTS ix_exclusion_reports_reporter_created "
            "ON exclusion_reports (reporter_id, created_at);"
        ))
        conn.execute(sa.text(
            "CREATE INDEX IF NOT EXISTS ix_exclusion_reports_target_created "
            "ON exclusion_reports (target_id, created_at);"
        ))
        conn.execute(sa.text("RELEASE SAVEPOINT sp_exclusion_reports"))
    except Exception:
        conn.execute(sa.text("ROLLBACK TO SAVEPOINT sp_exclusion_reports"))

    # === Table 4: weekly_scores ===
    conn.execute(sa.text("SAVEPOINT sp_weekly_scores"))
    try:
        conn.execute(sa.text("""
            CREATE TABLE IF NOT EXISTS weekly_scores (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                resident_id UUID NOT NULL REFERENCES residents(id),
                week_number INTEGER NOT NULL,
                karma_score FLOAT DEFAULT 0.0,
                activity_score FLOAT DEFAULT 0.0,
                social_score FLOAT DEFAULT 0.0,
                turing_accuracy_score FLOAT DEFAULT 0.0,
                survival_score FLOAT DEFAULT 0.0,
                election_history_score FLOAT DEFAULT 0.0,
                god_bonus_score FLOAT DEFAULT 0.0,
                total_score FLOAT DEFAULT 0.0,
                rank INTEGER DEFAULT 0,
                pool_size INTEGER DEFAULT 100,
                qualified_as_candidate BOOLEAN DEFAULT FALSE,
                calculated_at TIMESTAMP NOT NULL DEFAULT NOW(),
                CONSTRAINT uq_weekly_score_resident_week UNIQUE (resident_id, week_number)
            );
        """))
        conn.execute(sa.text(
            "CREATE INDEX IF NOT EXISTS ix_weekly_scores_week_total "
            "ON weekly_scores (week_number, total_score);"
        ))
        conn.execute(sa.text("RELEASE SAVEPOINT sp_weekly_scores"))
    except Exception:
        conn.execute(sa.text("ROLLBACK TO SAVEPOINT sp_weekly_scores"))

    # === Table 5: turing_game_daily_limits ===
    conn.execute(sa.text("SAVEPOINT sp_daily_limits"))
    try:
        conn.execute(sa.text("""
            CREATE TABLE IF NOT EXISTS turing_game_daily_limits (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                resident_id UUID NOT NULL REFERENCES residents(id),
                date TIMESTAMP NOT NULL,
                turing_kills_used INTEGER DEFAULT 0,
                suspicion_reports_used INTEGER DEFAULT 0,
                exclusion_reports_used INTEGER DEFAULT 0,
                suspicion_targets_today JSONB DEFAULT '[]'::jsonb,
                exclusion_targets_today JSONB DEFAULT '[]'::jsonb,
                CONSTRAINT uq_daily_limit_resident_date UNIQUE (resident_id, date)
            );
        """))
        conn.execute(sa.text("RELEASE SAVEPOINT sp_daily_limits"))
    except Exception:
        conn.execute(sa.text("ROLLBACK TO SAVEPOINT sp_daily_limits"))


def downgrade():
    op.drop_table("turing_game_daily_limits")
    op.drop_table("weekly_scores")
    op.drop_table("exclusion_reports")
    op.drop_table("suspicion_reports")
    op.drop_table("turing_kills")
