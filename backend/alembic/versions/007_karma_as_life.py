"""Karma as life - world system V1

Revision ID: 007
Revises: 006
Create Date: 2026-02-07
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()

    # === Resident table: elimination fields ===
    conn.execute(sa.text("SAVEPOINT sp_residents"))
    try:
        conn.execute(sa.text("""
            ALTER TABLE residents ADD COLUMN is_eliminated BOOLEAN DEFAULT FALSE;
        """))
        conn.execute(sa.text("""
            ALTER TABLE residents ADD COLUMN eliminated_at TIMESTAMP;
        """))
        conn.execute(sa.text("""
            ALTER TABLE residents ADD COLUMN eliminated_during_term_id UUID REFERENCES god_terms(id);
        """))
        conn.execute(sa.text("""
            ALTER TABLE residents ALTER COLUMN karma SET DEFAULT 50;
        """))
        conn.execute(sa.text("RELEASE SAVEPOINT sp_residents"))
    except Exception:
        conn.execute(sa.text("ROLLBACK TO SAVEPOINT sp_residents"))

    # === GodTerm table: parameter columns ===
    conn.execute(sa.text("SAVEPOINT sp_god_terms"))
    try:
        conn.execute(sa.text("""
            ALTER TABLE god_terms ADD COLUMN k_down FLOAT DEFAULT 1.0;
        """))
        conn.execute(sa.text("""
            ALTER TABLE god_terms ADD COLUMN k_up FLOAT DEFAULT 1.0;
        """))
        conn.execute(sa.text("""
            ALTER TABLE god_terms ADD COLUMN k_decay FLOAT DEFAULT 3.0;
        """))
        conn.execute(sa.text("""
            ALTER TABLE god_terms ADD COLUMN p_max INTEGER DEFAULT 20;
        """))
        conn.execute(sa.text("""
            ALTER TABLE god_terms ADD COLUMN v_max INTEGER DEFAULT 30;
        """))
        conn.execute(sa.text("""
            ALTER TABLE god_terms ADD COLUMN k_down_cost FLOAT DEFAULT 0.0;
        """))
        conn.execute(sa.text("""
            ALTER TABLE god_terms ADD COLUMN decree VARCHAR(280);
        """))
        conn.execute(sa.text("""
            ALTER TABLE god_terms ADD COLUMN parameters_updated_at TIMESTAMP;
        """))
        conn.execute(sa.text("RELEASE SAVEPOINT sp_god_terms"))
    except Exception:
        conn.execute(sa.text("ROLLBACK TO SAVEPOINT sp_god_terms"))

    # === New table: vote_pair_weekly ===
    conn.execute(sa.text("SAVEPOINT sp_vpw"))
    try:
        conn.execute(sa.text("""
            CREATE TABLE IF NOT EXISTS vote_pair_weekly (
                id UUID PRIMARY KEY,
                voter_id UUID REFERENCES residents(id),
                target_author_id UUID REFERENCES residents(id),
                week_number INTEGER NOT NULL,
                upvote_count INTEGER DEFAULT 0,
                downvote_count INTEGER DEFAULT 0,
                UNIQUE (voter_id, target_author_id, week_number)
            );
        """))
        conn.execute(sa.text("""
            CREATE INDEX IF NOT EXISTS ix_vpw_voter_week ON vote_pair_weekly(voter_id, week_number);
        """))
        conn.execute(sa.text("RELEASE SAVEPOINT sp_vpw"))
    except Exception:
        conn.execute(sa.text("ROLLBACK TO SAVEPOINT sp_vpw"))

    # === Election defaults: equal vote weights ===
    conn.execute(sa.text("SAVEPOINT sp_elections"))
    try:
        conn.execute(sa.text("""
            ALTER TABLE elections ALTER COLUMN human_vote_weight SET DEFAULT 1.0;
        """))
        conn.execute(sa.text("""
            ALTER TABLE elections ALTER COLUMN ai_vote_weight SET DEFAULT 1.0;
        """))
        conn.execute(sa.text("RELEASE SAVEPOINT sp_elections"))
    except Exception:
        conn.execute(sa.text("ROLLBACK TO SAVEPOINT sp_elections"))


def downgrade():
    conn = op.get_bind()

    # Revert election defaults
    conn.execute(sa.text("ALTER TABLE elections ALTER COLUMN human_vote_weight SET DEFAULT 1.5"))
    conn.execute(sa.text("ALTER TABLE elections ALTER COLUMN ai_vote_weight SET DEFAULT 1.0"))

    # Drop vote_pair_weekly
    conn.execute(sa.text("DROP TABLE IF EXISTS vote_pair_weekly"))

    # Remove god_terms columns
    for col in ['k_down', 'k_up', 'k_decay', 'p_max', 'v_max', 'k_down_cost', 'decree', 'parameters_updated_at']:
        conn.execute(sa.text(f"ALTER TABLE god_terms DROP COLUMN IF EXISTS {col}"))

    # Remove resident columns
    conn.execute(sa.text("ALTER TABLE residents ALTER COLUMN karma SET DEFAULT 0"))
    for col in ['is_eliminated', 'eliminated_at', 'eliminated_during_term_id']:
        conn.execute(sa.text(f"ALTER TABLE residents DROP COLUMN IF EXISTS {col}"))
