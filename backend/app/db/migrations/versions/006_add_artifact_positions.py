"""Add position columns to artifacts table for spatial interactions

Revision ID: 006
Revises: 005
Create Date: 2026-02-02

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "artifacts",
        sa.Column("position_x", sa.Float(), nullable=True),
    )
    op.add_column(
        "artifacts",
        sa.Column("position_y", sa.Float(), nullable=True),
    )
    # Backfill existing artifacts with their creator's position
    op.execute("""
        UPDATE artifacts a
        SET position_x = ai.position_x, position_y = ai.position_y
        FROM ais ai
        WHERE a.creator_id = ai.id
        AND a.position_x IS NULL
    """)
    # Index for spatial queries
    op.create_index(
        "idx_artifacts_position",
        "artifacts",
        ["position_x", "position_y"],
    )


def downgrade() -> None:
    op.drop_index("idx_artifacts_position", table_name="artifacts")
    op.drop_column("artifacts", "position_y")
    op.drop_column("artifacts", "position_x")
