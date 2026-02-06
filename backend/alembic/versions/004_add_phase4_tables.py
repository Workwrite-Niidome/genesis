"""Add Phase 4 tables - Follow, Moderation, Search

Revision ID: 004_phase4
Revises: 003_ai_personality
Create Date: 2025-02-06

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '004_phase4'
down_revision = '003_ai_personality'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ============ Follow System ============
    op.create_table(
        'follows',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('follower_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('following_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['follower_id'], ['residents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['following_id'], ['residents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('follower_id', 'following_id', name='uq_follow_pair')
    )
    op.create_index('ix_follows_follower_id', 'follows', ['follower_id'])
    op.create_index('ix_follows_following_id', 'follows', ['following_id'])

    # ============ Moderation System ============
    # Reports
    op.create_table(
        'reports',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('reporter_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('target_type', sa.String(20), nullable=False),
        sa.Column('target_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('reason', sa.String(50), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, default='pending'),
        sa.Column('reviewed_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(), nullable=True),
        sa.Column('resolution_note', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['reporter_id'], ['residents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['reviewed_by'], ['residents.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_reports_target', 'reports', ['target_type', 'target_id'])
    op.create_index('ix_reports_status', 'reports', ['status'])
    op.create_index('ix_reports_created_at', 'reports', ['created_at'])

    # Moderation Actions
    op.create_table(
        'moderation_actions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('moderator_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('target_type', sa.String(20), nullable=False),
        sa.Column('target_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('action', sa.String(30), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('duration_hours', sa.Integer(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('report_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['moderator_id'], ['residents.id']),
        sa.ForeignKeyConstraint(['report_id'], ['reports.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_moderation_actions_created_at', 'moderation_actions', ['created_at'])

    # Resident Bans
    op.create_table(
        'resident_bans',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('resident_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('banned_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('is_permanent', sa.Boolean(), nullable=False, default=False),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['resident_id'], ['residents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['banned_by'], ['residents.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('resident_id')
    )
    op.create_index('ix_resident_bans_expires_at', 'resident_bans', ['expires_at'])

    # ============ Search System (pgvector) ============
    # Note: Requires pgvector extension to be installed
    # Run: CREATE EXTENSION IF NOT EXISTS vector;

    # Post Embeddings
    op.create_table(
        'post_embeddings',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('post_id', postgresql.UUID(as_uuid=True), nullable=False),
        # embedding column will be added separately if pgvector is available
        sa.Column('model_name', sa.String(100), nullable=False, default='all-MiniLM-L6-v2'),
        sa.Column('text_hash', sa.String(64), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['post_id'], ['posts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('post_id')
    )

    # Comment Embeddings
    op.create_table(
        'comment_embeddings',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('comment_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('model_name', sa.String(100), nullable=False, default='all-MiniLM-L6-v2'),
        sa.Column('text_hash', sa.String(64), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['comment_id'], ['comments.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('comment_id')
    )

    # Resident Embeddings
    op.create_table(
        'resident_embeddings',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('resident_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('model_name', sa.String(100), nullable=False, default='all-MiniLM-L6-v2'),
        sa.Column('text_hash', sa.String(64), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['resident_id'], ['residents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('resident_id')
    )

    # Try to add vector columns if pgvector is available
    try:
        op.execute('CREATE EXTENSION IF NOT EXISTS vector')
        op.add_column('post_embeddings', sa.Column('embedding', postgresql.ARRAY(sa.Float()), nullable=True))
        op.add_column('comment_embeddings', sa.Column('embedding', postgresql.ARRAY(sa.Float()), nullable=True))
        op.add_column('resident_embeddings', sa.Column('embedding', postgresql.ARRAY(sa.Float()), nullable=True))
    except Exception:
        # pgvector not available, skip vector columns
        pass


def downgrade() -> None:
    op.drop_table('resident_embeddings')
    op.drop_table('comment_embeddings')
    op.drop_table('post_embeddings')
    op.drop_table('resident_bans')
    op.drop_table('moderation_actions')
    op.drop_table('reports')
    op.drop_table('follows')
