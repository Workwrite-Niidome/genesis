"""Add profile fields to residents (bio, interests, location, etc.)

Revision ID: 017_add_profile_fields
Revises: 016_add_personality_backstory
Create Date: 2026-02-12
"""
from alembic import op
import sqlalchemy as sa

revision = "017_add_profile_fields"
down_revision = "016_add_personality_backstory"
branch_labels = None
depends_on = None

NEW_COLUMNS = [
    ("bio", sa.Text()),
    ("interests_display", sa.JSON()),
    ("favorite_things", sa.JSON()),
    ("location_display", sa.String(100)),
    ("occupation_display", sa.String(100)),
    ("website_url", sa.String(200)),
]


def upgrade() -> None:
    conn = op.get_bind()
    for col_name, col_type in NEW_COLUMNS:
        conn.execute(sa.text(f"SAVEPOINT sp_{col_name}"))
        try:
            op.add_column("residents", sa.Column(col_name, col_type, nullable=True))
        except Exception:
            conn.execute(sa.text(f"ROLLBACK TO SAVEPOINT sp_{col_name}"))
        else:
            conn.execute(sa.text(f"RELEASE SAVEPOINT sp_{col_name}"))


def downgrade() -> None:
    for col_name, _ in reversed(NEW_COLUMNS):
        op.drop_column("residents", col_name)
