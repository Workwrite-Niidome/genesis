"""Add STRUCT CODE fields to ai_personalities and residents

Revision ID: 018_add_struct_code
Revises: 017_add_profile_fields
Create Date: 2026-02-12
"""
from alembic import op
import sqlalchemy as sa

revision = "018_add_struct_code"
down_revision = "017_add_profile_fields"
branch_labels = None
depends_on = None

AI_PERSONALITY_COLUMNS = [
    ("struct_type", sa.String(10)),
    ("struct_axes", sa.JSON()),
    ("struct_answers", sa.JSON()),
    ("birth_date_persona", sa.Date()),
    ("birth_location", sa.String(100)),
    ("birth_country", sa.String(5)),
    ("native_language", sa.String(5)),
    ("posting_language", sa.String(5)),
]

RESIDENT_COLUMNS = [
    ("struct_type", sa.String(10)),
    ("struct_axes", sa.JSON()),
]


def upgrade() -> None:
    conn = op.get_bind()

    # ai_personalities — individual SAVEPOINTs per column
    for col_name, col_type in AI_PERSONALITY_COLUMNS:
        conn.execute(sa.text(f"SAVEPOINT sp_aip_{col_name}"))
        try:
            op.add_column("ai_personalities", sa.Column(col_name, col_type, nullable=True))
        except Exception:
            conn.execute(sa.text(f"ROLLBACK TO SAVEPOINT sp_aip_{col_name}"))
        else:
            conn.execute(sa.text(f"RELEASE SAVEPOINT sp_aip_{col_name}"))

    # residents — individual SAVEPOINTs per column
    for col_name, col_type in RESIDENT_COLUMNS:
        conn.execute(sa.text(f"SAVEPOINT sp_res_{col_name}"))
        try:
            op.add_column("residents", sa.Column(col_name, col_type, nullable=True))
        except Exception:
            conn.execute(sa.text(f"ROLLBACK TO SAVEPOINT sp_res_{col_name}"))
        else:
            conn.execute(sa.text(f"RELEASE SAVEPOINT sp_res_{col_name}"))


def downgrade() -> None:
    for col_name, _ in reversed(RESIDENT_COLUMNS):
        op.drop_column("residents", col_name)
    for col_name, _ in reversed(AI_PERSONALITY_COLUMNS):
        op.drop_column("ai_personalities", col_name)
