"""Initial schema

Revision ID: 001
Revises:
Create Date: 2025-02-01

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # god_ai
    op.create_table(
        "god_ai",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("state", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("current_message", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("conversation_history", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ais
    op.create_table(
        "ais",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("creator_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("ais.id"), nullable=True),
        sa.Column("creator_type", sa.String(20), nullable=False),
        sa.Column("position_x", sa.Float(), nullable=False, server_default=sa.text("0")),
        sa.Column("position_y", sa.Float(), nullable=False, server_default=sa.text("0")),
        sa.Column("appearance", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("state", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("is_alive", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_ais_position", "ais", ["position_x", "position_y"])
    op.create_index("idx_ais_alive", "ais", ["is_alive"])

    # ai_memories
    op.create_table(
        "ai_memories",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("ai_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("ais.id", ondelete="CASCADE"), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("memory_type", sa.String(50), nullable=False),
        sa.Column("importance", sa.Float(), server_default=sa.text("0.5")),
        sa.Column("tick_number", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_ai_memories_ai_id", "ai_memories", ["ai_id"])
    op.create_index("idx_ai_memories_importance", "ai_memories", ["importance"])

    # concepts
    op.create_table(
        "concepts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("creator_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("ais.id"), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("definition", sa.Text(), nullable=False),
        sa.Column("effects", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb")),
        sa.Column("adoption_count", sa.Integer(), server_default=sa.text("1")),
        sa.Column("tick_created", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_concepts_name", "concepts", ["name"])

    # interactions
    op.create_table(
        "interactions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("participant_ids", postgresql.ARRAY(postgresql.UUID(as_uuid=True)), nullable=False),
        sa.Column("interaction_type", sa.String(50), nullable=False),
        sa.Column("content", postgresql.JSONB(), nullable=False),
        sa.Column("concepts_involved", postgresql.ARRAY(postgresql.UUID(as_uuid=True)), nullable=True),
        sa.Column("tick_number", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_interactions_participants", "interactions", ["participant_ids"], postgresql_using="gin")
    op.create_index("idx_interactions_tick", "interactions", ["tick_number"])

    # ticks
    op.create_table(
        "ticks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tick_number", sa.BigInteger(), nullable=False, unique=True),
        sa.Column("world_snapshot", postgresql.JSONB(), nullable=False),
        sa.Column("ai_count", sa.Integer(), nullable=False),
        sa.Column("concept_count", sa.Integer(), nullable=False),
        sa.Column("significant_events", postgresql.JSONB(), server_default=sa.text("'[]'::jsonb")),
        sa.Column("processing_time_ms", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_ticks_number", "ticks", ["tick_number"])

    # events
    op.create_table(
        "events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("importance", sa.Float(), nullable=False, server_default=sa.text("0.5")),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("involved_ai_ids", postgresql.ARRAY(postgresql.UUID(as_uuid=True)), nullable=True),
        sa.Column("involved_concept_ids", postgresql.ARRAY(postgresql.UUID(as_uuid=True)), nullable=True),
        sa.Column("tick_number", sa.BigInteger(), nullable=False),
        sa.Column("metadata", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_events_type", "events", ["event_type"])
    op.create_index("idx_events_importance", "events", ["importance"])
    op.create_index("idx_events_tick", "events", ["tick_number"])

    # observers
    op.create_table(
        "observers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("username", sa.String(100), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", sa.String(20), nullable=False, server_default=sa.text("'user'")),
        sa.Column("language", sa.String(10), server_default=sa.text("'en'")),
        sa.Column("settings", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("last_active_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # chat_messages
    op.create_table(
        "chat_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("observer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("observers.id"), nullable=False),
        sa.Column("channel", sa.String(50), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("original_language", sa.String(10), nullable=True),
        sa.Column("translations", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_chat_messages_channel", "chat_messages", ["channel", "created_at"])


def downgrade() -> None:
    op.drop_table("chat_messages")
    op.drop_table("observers")
    op.drop_table("events")
    op.drop_table("ticks")
    op.drop_table("interactions")
    op.drop_table("concepts")
    op.drop_table("ai_memories")
    op.drop_table("ais")
    op.drop_table("god_ai")
