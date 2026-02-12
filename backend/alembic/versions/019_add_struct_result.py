"""Add struct_result JSON column to residents

Revision ID: 019_add_struct_result
Revises: 018_add_struct_code
Create Date: 2026-02-12
"""
from alembic import op
import sqlalchemy as sa

revision = "019_add_struct_result"
down_revision = "018_add_struct_code"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("SAVEPOINT sp_struct_result"))
    try:
        op.add_column("residents", sa.Column("struct_result", sa.JSON(), nullable=True))
    except Exception:
        conn.execute(sa.text("ROLLBACK TO SAVEPOINT sp_struct_result"))
    else:
        conn.execute(sa.text("RELEASE SAVEPOINT sp_struct_result"))


def downgrade() -> None:
    op.drop_column("residents", "struct_result")
