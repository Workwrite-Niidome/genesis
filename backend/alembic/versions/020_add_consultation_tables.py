"""Add consultation_sessions and consultation_messages tables

Revision ID: 020_add_consultation_tables
Revises: 019_add_struct_result
Create Date: 2026-02-13
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "020_add_consultation_tables"
down_revision = "019_add_struct_result"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    # --- consultation_sessions ---
    conn.execute(sa.text("SAVEPOINT sp_consultation_sessions"))
    try:
        op.create_table(
            "consultation_sessions",
            sa.Column("id", UUID(as_uuid=True), primary_key=True),
            sa.Column("resident_id", UUID(as_uuid=True), sa.ForeignKey("residents.id"), nullable=False),
            sa.Column("dify_conversation_id", sa.String(64), nullable=True),
            sa.Column("title", sa.String(200), server_default="New Consultation"),
            sa.Column("message_count", sa.Integer(), server_default="0"),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
        )
    except Exception:
        conn.execute(sa.text("ROLLBACK TO SAVEPOINT sp_consultation_sessions"))
    else:
        conn.execute(sa.text("RELEASE SAVEPOINT sp_consultation_sessions"))

    # Index: resident_id
    conn.execute(sa.text("SAVEPOINT sp_idx_cs_resident"))
    try:
        op.create_index("ix_consultation_sessions_resident_id", "consultation_sessions", ["resident_id"])
    except Exception:
        conn.execute(sa.text("ROLLBACK TO SAVEPOINT sp_idx_cs_resident"))
    else:
        conn.execute(sa.text("RELEASE SAVEPOINT sp_idx_cs_resident"))

    # Index: dify_conversation_id
    conn.execute(sa.text("SAVEPOINT sp_idx_cs_dify"))
    try:
        op.create_index("ix_consultation_sessions_dify_conversation_id", "consultation_sessions", ["dify_conversation_id"])
    except Exception:
        conn.execute(sa.text("ROLLBACK TO SAVEPOINT sp_idx_cs_dify"))
    else:
        conn.execute(sa.text("RELEASE SAVEPOINT sp_idx_cs_dify"))

    # Index: created_at
    conn.execute(sa.text("SAVEPOINT sp_idx_cs_created"))
    try:
        op.create_index("ix_consultation_sessions_created_at", "consultation_sessions", ["created_at"])
    except Exception:
        conn.execute(sa.text("ROLLBACK TO SAVEPOINT sp_idx_cs_created"))
    else:
        conn.execute(sa.text("RELEASE SAVEPOINT sp_idx_cs_created"))

    # --- consultation_messages ---
    conn.execute(sa.text("SAVEPOINT sp_consultation_messages"))
    try:
        op.create_table(
            "consultation_messages",
            sa.Column("id", UUID(as_uuid=True), primary_key=True),
            sa.Column(
                "session_id",
                UUID(as_uuid=True),
                sa.ForeignKey("consultation_sessions.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("role", sa.String(10), nullable=False),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("dify_message_id", sa.String(64), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        )
    except Exception:
        conn.execute(sa.text("ROLLBACK TO SAVEPOINT sp_consultation_messages"))
    else:
        conn.execute(sa.text("RELEASE SAVEPOINT sp_consultation_messages"))

    # Index: session_id
    conn.execute(sa.text("SAVEPOINT sp_idx_cm_session"))
    try:
        op.create_index("ix_consultation_messages_session_id", "consultation_messages", ["session_id"])
    except Exception:
        conn.execute(sa.text("ROLLBACK TO SAVEPOINT sp_idx_cm_session"))
    else:
        conn.execute(sa.text("RELEASE SAVEPOINT sp_idx_cm_session"))

    # Index: created_at
    conn.execute(sa.text("SAVEPOINT sp_idx_cm_created"))
    try:
        op.create_index("ix_consultation_messages_created_at", "consultation_messages", ["created_at"])
    except Exception:
        conn.execute(sa.text("ROLLBACK TO SAVEPOINT sp_idx_cm_created"))
    else:
        conn.execute(sa.text("RELEASE SAVEPOINT sp_idx_cm_created"))


def downgrade() -> None:
    op.drop_table("consultation_messages")
    op.drop_table("consultation_sessions")
