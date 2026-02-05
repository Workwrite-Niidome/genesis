"""Add users table for OAuth-authenticated users.

Users sign in via Google or GitHub OAuth. Each user can create and manage
AI agents in the GENESIS world. The ``entities.owner_user_id`` column
(added in 009) references this table logically, but we do not add a
hard FK constraint so the v3 entity layer stays decoupled.

Revision ID: 010
Revises: 009
Create Date: 2026-02-05

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = "010"
down_revision: Union[str, None] = "009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("display_name", sa.String(200), nullable=False),
        sa.Column("avatar_url", sa.String(500), nullable=True),
        sa.Column("provider", sa.String(20), nullable=False),
        sa.Column("provider_id", sa.String(200), nullable=False),
        sa.Column("is_premium", sa.Boolean, server_default="false"),
        sa.Column("agent_slots", sa.Integer, nullable=False, server_default="1"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column(
            "last_login",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_users_provider",
        "users",
        ["provider", "provider_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_users_provider", table_name="users")
    op.drop_table("users")
