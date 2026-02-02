"""Add world_features table for world physics layer

Revision ID: 007
Revises: 006
Create Date: 2026-02-02

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "world_features",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("feature_type", sa.String(50), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("position_x", sa.Float(), nullable=False),
        sa.Column("position_y", sa.Float(), nullable=False),
        sa.Column("radius", sa.Float(), server_default="30.0"),
        sa.Column("properties", JSONB, server_default="{}"),
        sa.Column(
            "created_by_artifact_id",
            UUID(as_uuid=True),
            sa.ForeignKey("artifacts.id"),
            nullable=True,
        ),
        sa.Column("tick_created", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "idx_world_features_position",
        "world_features",
        ["position_x", "position_y"],
    )
    op.create_index(
        "idx_world_features_type",
        "world_features",
        ["feature_type"],
    )
    op.create_index(
        "idx_world_features_active",
        "world_features",
        ["is_active"],
    )


def downgrade() -> None:
    op.drop_index("idx_world_features_active", table_name="world_features")
    op.drop_index("idx_world_features_type", table_name="world_features")
    op.drop_index("idx_world_features_position", table_name="world_features")
    op.drop_table("world_features")
