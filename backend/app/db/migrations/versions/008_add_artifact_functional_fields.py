"""Add functional_effects, durability, max_durability to artifacts

Revision ID: 008
Revises: 007
Create Date: 2026-02-02

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "008"
down_revision: Union[str, None] = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "artifacts",
        sa.Column("functional_effects", JSONB, server_default="{}"),
    )
    op.add_column(
        "artifacts",
        sa.Column("durability", sa.Float(), nullable=True),
    )
    op.add_column(
        "artifacts",
        sa.Column("max_durability", sa.Float(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("artifacts", "max_durability")
    op.drop_column("artifacts", "durability")
    op.drop_column("artifacts", "functional_effects")
