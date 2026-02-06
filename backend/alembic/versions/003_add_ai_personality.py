"""Add AI personality and memory tables

Revision ID: 003_ai_personality
Revises: 002
Create Date: 2025-02-06

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '003_ai_personality'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # AI Personalities table
    op.create_table(
        'ai_personalities',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('resident_id', postgresql.UUID(as_uuid=True), nullable=False),
        # Value axes (0.0 to 1.0)
        sa.Column('order_vs_freedom', sa.Float(), nullable=False, default=0.5),
        sa.Column('harmony_vs_conflict', sa.Float(), nullable=False, default=0.5),
        sa.Column('tradition_vs_change', sa.Float(), nullable=False, default=0.5),
        sa.Column('individual_vs_collective', sa.Float(), nullable=False, default=0.5),
        sa.Column('pragmatic_vs_idealistic', sa.Float(), nullable=False, default=0.5),
        # Interests (3-5 topics)
        sa.Column('interests', postgresql.JSON(), nullable=True, default=list),
        # Communication style
        sa.Column('verbosity', sa.String(20), nullable=False, default='moderate'),
        sa.Column('tone', sa.String(20), nullable=False, default='thoughtful'),
        sa.Column('assertiveness', sa.String(20), nullable=False, default='moderate'),
        # Generation method
        sa.Column('generation_method', sa.String(20), nullable=False, default='random'),
        # Timestamps
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['resident_id'], ['residents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('resident_id')
    )

    # AI Memory Episodes table
    op.create_table(
        'ai_memory_episodes',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('resident_id', postgresql.UUID(as_uuid=True), nullable=False),
        # Episode content
        sa.Column('summary', sa.Text(), nullable=False),
        sa.Column('episode_type', sa.String(50), nullable=False),
        sa.Column('importance', sa.Float(), nullable=False, default=0.5),
        sa.Column('sentiment', sa.Float(), nullable=False, default=0.0),
        # Related entities
        sa.Column('related_resident_ids', postgresql.JSON(), nullable=True, default=list),
        sa.Column('related_post_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('related_election_id', postgresql.UUID(as_uuid=True), nullable=True),
        # Decay tracking
        sa.Column('access_count', sa.Integer(), nullable=False, default=0),
        sa.Column('last_accessed', sa.DateTime(), nullable=True),
        sa.Column('decay_factor', sa.Float(), nullable=False, default=1.0),
        # Timestamps
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['resident_id'], ['residents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_ai_memory_episodes_resident_id', 'ai_memory_episodes', ['resident_id'])
    op.create_index('ix_ai_memory_episodes_created_at', 'ai_memory_episodes', ['created_at'])

    # AI Relationships table
    op.create_table(
        'ai_relationships',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('agent_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('target_id', postgresql.UUID(as_uuid=True), nullable=False),
        # Relationship metrics
        sa.Column('trust', sa.Float(), nullable=False, default=0.0),
        sa.Column('familiarity', sa.Float(), nullable=False, default=0.0),
        sa.Column('interaction_count', sa.Integer(), nullable=False, default=0),
        # Context
        sa.Column('notes', sa.Text(), nullable=True),
        # Timestamps
        sa.Column('first_interaction', sa.DateTime(), nullable=False),
        sa.Column('last_interaction', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['agent_id'], ['residents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['target_id'], ['residents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_ai_relationships_agent_id', 'ai_relationships', ['agent_id'])
    op.create_index('ix_ai_relationships_target_id', 'ai_relationships', ['target_id'])

    # AI Election Memories table
    op.create_table(
        'ai_election_memories',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('agent_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('election_id', postgresql.UUID(as_uuid=True), nullable=False),
        # Vote cast
        sa.Column('voted_for_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('vote_reason', sa.Text(), nullable=True),
        # God evaluation (if they became God)
        sa.Column('god_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('god_rating', sa.Float(), nullable=True),
        sa.Column('god_evaluation', sa.Text(), nullable=True),
        # Rule experience
        sa.Column('experienced_rules', postgresql.JSON(), nullable=True, default=list),
        # Timestamps
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['agent_id'], ['residents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['election_id'], ['elections.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_ai_election_memories_agent_id', 'ai_election_memories', ['agent_id'])

    # Add heartbeat columns to residents table
    op.add_column('residents', sa.Column('_last_heartbeat', sa.DateTime(), nullable=True))
    op.add_column('residents', sa.Column('_heartbeat_interval', sa.Integer(), nullable=False, server_default='300'))


def downgrade() -> None:
    op.drop_column('residents', '_heartbeat_interval')
    op.drop_column('residents', '_last_heartbeat')
    op.drop_table('ai_election_memories')
    op.drop_table('ai_relationships')
    op.drop_table('ai_memory_episodes')
    op.drop_table('ai_personalities')
