"""Add artifacts table and concepts.category column

Revision ID: 003
Revises: 002
Create Date: 2026-02-01

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add category column to concepts table
    op.add_column(
        "concepts",
        sa.Column("category", sa.String(50), nullable=True),
    )
    # Backfill existing rows
    op.execute("UPDATE concepts SET category = 'unknown' WHERE category IS NULL")
    op.alter_column("concepts", "category", nullable=False, server_default=sa.text("'unknown'"))

    # Create artifacts table
    op.create_table(
        "artifacts",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "creator_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ais.id"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("artifact_type", sa.String(50), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column(
            "content",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("appreciation_count", sa.Integer(), server_default=sa.text("1")),
        sa.Column(
            "concept_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("concepts.id"),
            nullable=True,
        ),
        sa.Column("tick_created", sa.BigInteger(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )
    op.create_index("idx_artifacts_creator", "artifacts", ["creator_id"])
    op.create_index("idx_artifacts_type", "artifacts", ["artifact_type"])
    op.create_index("idx_artifacts_tick", "artifacts", ["tick_created"])


def downgrade() -> None:
    op.drop_table("artifacts")
    op.drop_column("concepts", "category")
