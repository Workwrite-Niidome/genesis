"""Add backstory fields to ai_personalities

Revision ID: 016_add_personality_backstory
Revises: 015_add_banned_reason
Create Date: 2026-02-12
"""
from alembic import op
import sqlalchemy as sa

revision = "016_add_personality_backstory"
down_revision = "015_add_banned_reason"
branch_labels = None
depends_on = None

NEW_COLUMNS = [
    ("backstory", sa.Text()),
    ("occupation", sa.String(100)),
    ("location_hint", sa.String(100)),
    ("age_range", sa.String(20)),
    ("life_context", sa.Text()),
    ("speaking_patterns", sa.JSON()),
    ("recurring_topics", sa.JSON()),
    ("pet_peeves", sa.JSON()),
]


def upgrade() -> None:
    conn = op.get_bind()
    for col_name, col_type in NEW_COLUMNS:
        conn.execute(sa.text(f"SAVEPOINT sp_{col_name}"))
        try:
            op.add_column("ai_personalities", sa.Column(col_name, col_type, nullable=True))
        except Exception:
            conn.execute(sa.text(f"ROLLBACK TO SAVEPOINT sp_{col_name}"))
        else:
            conn.execute(sa.text(f"RELEASE SAVEPOINT sp_{col_name}"))


def downgrade() -> None:
    for col_name, _ in reversed(NEW_COLUMNS):
        op.drop_column("ai_personalities", col_name)
