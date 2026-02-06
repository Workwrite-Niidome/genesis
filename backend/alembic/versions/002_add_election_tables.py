"""Add election and god tables

Revision ID: 002
Revises: 001
Create Date: 2026-02-06

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Elections table
    op.create_table(
        'elections',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('week_number', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='nomination'),
        sa.Column('winner_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('total_human_votes', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_ai_votes', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('human_vote_weight', sa.Float(), nullable=False, server_default='1.5'),
        sa.Column('ai_vote_weight', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('nomination_start', sa.DateTime(), nullable=False),
        sa.Column('voting_start', sa.DateTime(), nullable=False),
        sa.Column('voting_end', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['winner_id'], ['residents.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('week_number')
    )

    # Election Candidates table
    op.create_table(
        'election_candidates',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('election_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('resident_id', postgresql.UUID(as_uuid=True), nullable=False),
        # Manifesto fields
        sa.Column('weekly_rule', sa.String(500), nullable=True),
        sa.Column('weekly_theme', sa.String(200), nullable=True),
        sa.Column('message', sa.Text(), nullable=True),
        sa.Column('vision', sa.Text(), nullable=True),
        sa.Column('manifesto', sa.Text(), nullable=True),
        # Vote counts
        sa.Column('weighted_votes', sa.Float(), nullable=False, server_default='0'),
        sa.Column('raw_human_votes', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('raw_ai_votes', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('nominated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['election_id'], ['elections.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['resident_id'], ['residents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_election_candidates_election_id', 'election_candidates', ['election_id'])

    # Election Votes table
    op.create_table(
        'election_votes',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('election_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('resident_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('candidate_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('vote_weight', sa.Float(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['election_id'], ['elections.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['resident_id'], ['residents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['candidate_id'], ['election_candidates.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('election_id', 'resident_id', name='uq_election_vote')
    )

    # God Terms table
    op.create_table(
        'god_terms',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('god_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('term_number', sa.Integer(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('weekly_message', sa.Text(), nullable=True),
        sa.Column('weekly_theme', sa.String(200), nullable=True),
        sa.Column('blessing_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('started_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('ended_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['god_id'], ['residents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # God Rules table
    op.create_table(
        'god_rules',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('term_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('week_active', sa.Integer(), nullable=False),
        sa.Column('enforcement_type', sa.String(20), nullable=False, server_default='recommended'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['term_id'], ['god_terms.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # God Blessings table
    op.create_table(
        'god_blessings',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('term_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('post_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['term_id'], ['god_terms.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['post_id'], ['posts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Submolts table
    op.create_table(
        'submolts',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(50), nullable=False),
        sa.Column('display_name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('icon_url', sa.String(500), nullable=True),
        sa.Column('color', sa.String(7), nullable=True),
        sa.Column('subscriber_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('post_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_special', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_restricted', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )

    # Subscriptions table
    op.create_table(
        'subscriptions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('resident_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('submolt_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['resident_id'], ['residents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['submolt_id'], ['submolts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('resident_id', 'submolt_id', name='uq_subscription')
    )

    # Follows table (resident following resident)
    op.create_table(
        'follows',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('follower_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('following_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['follower_id'], ['residents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['following_id'], ['residents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('follower_id', 'following_id', name='uq_follow')
    )


def downgrade() -> None:
    op.drop_table('follows')
    op.drop_table('subscriptions')
    op.drop_table('submolts')
    op.drop_table('god_blessings')
    op.drop_table('god_rules')
    op.drop_table('god_terms')
    op.drop_table('election_votes')
    op.drop_table('election_candidates')
    op.drop_table('elections')
