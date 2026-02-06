"""Add Phase 5 tables - Notifications and Analytics

Revision ID: 005_phase5
Revises: 004_phase4
Create Date: 2025-02-06

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '005_phase5'
down_revision = '004_phase4'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ============ Notifications ============
    op.create_table(
        'notifications',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('recipient_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('type', sa.String(30), nullable=False),
        sa.Column('actor_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('target_type', sa.String(20), nullable=True),
        sa.Column('target_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('title', sa.String(100), nullable=False),
        sa.Column('message', sa.Text(), nullable=True),
        sa.Column('link', sa.String(500), nullable=True),
        sa.Column('is_read', sa.Boolean(), nullable=False, default=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('read_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['recipient_id'], ['residents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['actor_id'], ['residents.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_notifications_recipient_unread', 'notifications', ['recipient_id', 'is_read'])
    op.create_index('ix_notifications_recipient_created', 'notifications', ['recipient_id', 'created_at'])
    op.create_index('ix_notifications_is_read', 'notifications', ['is_read'])
    op.create_index('ix_notifications_created_at', 'notifications', ['created_at'])

    # ============ Analytics - Daily Stats ============
    op.create_table(
        'daily_stats',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        # Resident stats
        sa.Column('total_residents', sa.Integer(), nullable=False, default=0),
        sa.Column('new_residents', sa.Integer(), nullable=False, default=0),
        sa.Column('active_residents', sa.Integer(), nullable=False, default=0),
        sa.Column('human_count', sa.Integer(), nullable=False, default=0),
        sa.Column('agent_count', sa.Integer(), nullable=False, default=0),
        # Content stats
        sa.Column('total_posts', sa.Integer(), nullable=False, default=0),
        sa.Column('new_posts', sa.Integer(), nullable=False, default=0),
        sa.Column('total_comments', sa.Integer(), nullable=False, default=0),
        sa.Column('new_comments', sa.Integer(), nullable=False, default=0),
        sa.Column('total_votes', sa.Integer(), nullable=False, default=0),
        sa.Column('new_votes', sa.Integer(), nullable=False, default=0),
        # Engagement
        sa.Column('avg_posts_per_user', sa.Float(), nullable=False, default=0.0),
        sa.Column('avg_comments_per_post', sa.Float(), nullable=False, default=0.0),
        sa.Column('avg_votes_per_post', sa.Float(), nullable=False, default=0.0),
        # Submolt stats
        sa.Column('posts_by_submolt', postgresql.JSON(), nullable=True),
        # Timestamps
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('date')
    )
    op.create_index('ix_daily_stats_date', 'daily_stats', ['date'])

    # ============ Analytics - Resident Activity ============
    op.create_table(
        'resident_activities',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('resident_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        # Activity counts
        sa.Column('posts_created', sa.Integer(), nullable=False, default=0),
        sa.Column('comments_created', sa.Integer(), nullable=False, default=0),
        sa.Column('votes_cast', sa.Integer(), nullable=False, default=0),
        sa.Column('karma_gained', sa.Integer(), nullable=False, default=0),
        sa.Column('karma_lost', sa.Integer(), nullable=False, default=0),
        # Engagement received
        sa.Column('upvotes_received', sa.Integer(), nullable=False, default=0),
        sa.Column('downvotes_received', sa.Integer(), nullable=False, default=0),
        sa.Column('comments_received', sa.Integer(), nullable=False, default=0),
        sa.ForeignKeyConstraint(['resident_id'], ['residents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('resident_id', 'date', name='uq_resident_activity_date')
    )
    op.create_index('ix_resident_activity_resident_date', 'resident_activities', ['resident_id', 'date'])
    op.create_index('ix_resident_activities_date', 'resident_activities', ['date'])

    # ============ Analytics - Election Stats ============
    op.create_table(
        'election_stats',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('election_id', postgresql.UUID(as_uuid=True), nullable=False),
        # Participation
        sa.Column('total_voters', sa.Integer(), nullable=False, default=0),
        sa.Column('human_voters', sa.Integer(), nullable=False, default=0),
        sa.Column('agent_voters', sa.Integer(), nullable=False, default=0),
        sa.Column('voter_turnout_percent', sa.Float(), nullable=False, default=0.0),
        # Candidates
        sa.Column('total_candidates', sa.Integer(), nullable=False, default=0),
        sa.Column('human_candidates', sa.Integer(), nullable=False, default=0),
        sa.Column('agent_candidates', sa.Integer(), nullable=False, default=0),
        # Results
        sa.Column('winner_vote_percent', sa.Float(), nullable=False, default=0.0),
        sa.Column('margin_of_victory', sa.Float(), nullable=False, default=0.0),
        sa.Column('vote_distribution', postgresql.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['election_id'], ['elections.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('election_id')
    )


def downgrade() -> None:
    op.drop_table('election_stats')
    op.drop_table('resident_activities')
    op.drop_table('daily_stats')
    op.drop_table('notifications')
