"""Add world_saga table for epic saga generation

Revision ID: 005
Revises: 004
Create Date: 2026-02-01

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "world_saga",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("era_number", sa.Integer(), nullable=False, unique=True),
        sa.Column("start_tick", sa.BigInteger(), nullable=False),
        sa.Column("end_tick", sa.BigInteger(), nullable=False),
        sa.Column("chapter_title", sa.String(500), nullable=False),
        sa.Column("narrative", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column(
            "era_statistics",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "key_events",
            postgresql.JSONB(),
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "key_characters",
            postgresql.JSONB(),
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("mood", sa.String(100), nullable=True),
        sa.Column("generation_time_ms", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )
    op.create_index("idx_world_saga_era_number", "world_saga", ["era_number"])


def downgrade() -> None:
    op.drop_index("idx_world_saga_era_number", table_name="world_saga")
    op.drop_table("world_saga")
