"""Add AI identity and thoughts

Revision ID: 002
Revises: 001
Create Date: 2026-02-01

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add name column to ais table
    op.add_column("ais", sa.Column("name", sa.String(100), nullable=True))
    # Backfill existing rows with a unique name based on id
    op.execute("UPDATE ais SET name = 'Entity-' || LEFT(id::text, 8) WHERE name IS NULL")
    op.alter_column("ais", "name", nullable=False)
    op.create_unique_constraint("uq_ais_name", "ais", ["name"])

    # Add personality_traits column to ais table
    op.add_column(
        "ais",
        sa.Column(
            "personality_traits",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )

    # Create ai_thoughts table
    op.create_table(
        "ai_thoughts",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "ai_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ais.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("tick_number", sa.BigInteger(), nullable=False),
        sa.Column("thought_type", sa.String(50), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("action", postgresql.JSONB(), nullable=True),
        sa.Column("context", postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )
    op.create_index("idx_ai_thoughts_ai_id", "ai_thoughts", ["ai_id"])
    op.create_index("idx_ai_thoughts_tick", "ai_thoughts", ["tick_number"])
    op.create_index(
        "idx_ai_thoughts_created", "ai_thoughts", ["created_at"]
    )


def downgrade() -> None:
    op.drop_table("ai_thoughts")
    op.drop_constraint("uq_ais_name", "ais", type_="unique")
    op.drop_column("ais", "personality_traits")
    op.drop_column("ais", "name")
