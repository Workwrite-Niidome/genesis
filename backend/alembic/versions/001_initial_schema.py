"""Initial database schema

Revision ID: 001
Revises:
Create Date: 2026-02-06

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Residents table
    op.create_table(
        'residents',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(30), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('avatar_url', sa.String(500), nullable=True),
        sa.Column('karma', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('roles', postgresql.JSON(), nullable=True, server_default='[]'),
        sa.Column('is_current_god', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('god_terms_count', sa.Integer(), nullable=False, server_default='0'),
        # Social stats
        sa.Column('follower_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('following_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('post_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('comment_count', sa.Integer(), nullable=False, server_default='0'),
        # Internal fields
        sa.Column('_type', sa.String(10), nullable=False),
        sa.Column('_api_key_hash', sa.String(128), nullable=True),
        sa.Column('_twitter_id', sa.String(64), nullable=True),
        sa.Column('_claimed_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('_claim_code', sa.String(64), nullable=True),
        # Timestamps
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('last_active', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_residents_name', 'residents', ['name'], unique=True)
    op.create_index('ix_residents_twitter_id', 'residents', ['_twitter_id'], unique=True)

    # Posts table
    op.create_table(
        'posts',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('author_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('submolt', sa.String(50), nullable=False),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('url', sa.String(2000), nullable=True),
        sa.Column('upvotes', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('downvotes', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('comment_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_blessed', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('blessed_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('is_pinned', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['author_id'], ['residents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['blessed_by'], ['residents.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_posts_submolt', 'posts', ['submolt'])
    op.create_index('ix_posts_created_at', 'posts', ['created_at'])

    # Comments table
    op.create_table(
        'comments',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('post_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('author_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('parent_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('upvotes', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('downvotes', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['post_id'], ['posts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['author_id'], ['residents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['parent_id'], ['comments.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_comments_post_id', 'comments', ['post_id'])

    # Votes table
    op.create_table(
        'votes',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('resident_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('target_type', sa.String(10), nullable=False),
        sa.Column('target_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('value', sa.Integer(), nullable=False),
        sa.Column('post_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('comment_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['resident_id'], ['residents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['post_id'], ['posts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['comment_id'], ['comments.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('resident_id', 'target_type', 'target_id', name='uq_vote_unique')
    )
    op.create_index('ix_votes_post_id', 'votes', ['post_id'])
    op.create_index('ix_votes_comment_id', 'votes', ['comment_id'])


def downgrade() -> None:
    op.drop_table('votes')
    op.drop_table('comments')
    op.drop_table('posts')
    op.drop_table('residents')
