"""GENESIS v3 tables: entities, episodic_memories, semantic_memories,
entity_relationships, voxel_blocks, structures, world_events, zones.

Adds the new v3 model layer alongside existing v1/v2 tables (ais, events,
interactions, observers, concepts, artifacts, ticks, world_saga, etc.).
No existing tables are modified or dropped — full backward compatibility.

Revision ID: 009
Revises: 008
Create Date: 2026-02-05

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "009"
down_revision: Union[str, None] = "008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── entities ────────────────────────────────────────────────────
    # Unified being model replacing the old AI/human distinction.
    op.create_table(
        "entities",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False, unique=True),
        sa.Column("origin_type", sa.String(20), nullable=False, server_default="native"),
        sa.Column("owner_user_id", UUID(as_uuid=True), nullable=True),
        sa.Column("position_x", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("position_y", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("position_z", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("facing_x", sa.Float, nullable=False, server_default="1.0"),
        sa.Column("facing_z", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("personality", JSONB, nullable=False, server_default="{}"),
        sa.Column("state", JSONB, nullable=False, server_default="{}"),
        sa.Column("appearance", JSONB, nullable=False, server_default="{}"),
        sa.Column("agent_policy", JSONB, nullable=True),
        sa.Column("is_alive", sa.Boolean, server_default="true"),
        sa.Column("is_god", sa.Boolean, server_default="false"),
        sa.Column("meta_awareness", sa.Float, server_default="0.0"),
        sa.Column("birth_tick", sa.BigInteger, nullable=False, server_default="0"),
        sa.Column("death_tick", sa.BigInteger, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_entities_alive", "entities", ["is_alive"])
    op.create_index(
        "ix_entities_position", "entities",
        ["position_x", "position_y", "position_z"],
    )

    # ── episodic_memories ───────────────────────────────────────────
    # Event-based memory with TTL based on importance.
    op.create_table(
        "episodic_memories",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "entity_id", UUID(as_uuid=True),
            sa.ForeignKey("entities.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("summary", sa.Text, nullable=False),
        sa.Column("importance", sa.Float, server_default="0.5"),
        sa.Column("tick", sa.BigInteger, nullable=False),
        sa.Column("related_entity_ids", JSONB, server_default="[]"),
        sa.Column("location_x", sa.Float, nullable=True),
        sa.Column("location_y", sa.Float, nullable=True),
        sa.Column("location_z", sa.Float, nullable=True),
        sa.Column("ttl", sa.Integer, nullable=False, server_default="10000"),
        sa.Column("memory_type", sa.String(50), server_default="event"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_episodic_entity_tick", "episodic_memories", ["entity_id", "tick"])
    op.create_index("ix_episodic_importance", "episodic_memories", ["entity_id", "importance"])

    # ── semantic_memories ───────────────────────────────────────────
    # Knowledge-based memory: facts, concepts, world knowledge.
    op.create_table(
        "semantic_memories",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "entity_id", UUID(as_uuid=True),
            sa.ForeignKey("entities.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("key", sa.String(200), nullable=False),
        sa.Column("value", sa.Text, nullable=False),
        sa.Column("confidence", sa.Float, server_default="1.0"),
        sa.Column("source_tick", sa.BigInteger, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(
        "ix_semantic_entity_key", "semantic_memories",
        ["entity_id", "key"], unique=True,
    )

    # ── entity_relationships ────────────────────────────────────────
    # 7-axis relationship between two entities, plus debt and alliance.
    op.create_table(
        "entity_relationships",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "entity_id", UUID(as_uuid=True),
            sa.ForeignKey("entities.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column(
            "target_id", UUID(as_uuid=True),
            sa.ForeignKey("entities.id", ondelete="CASCADE"), nullable=False,
        ),
        # 7 core axes
        sa.Column("trust", sa.Float, server_default="0.0"),
        sa.Column("familiarity", sa.Float, server_default="0.0"),
        sa.Column("respect", sa.Float, server_default="0.0"),
        sa.Column("fear", sa.Float, server_default="0.0"),
        sa.Column("rivalry", sa.Float, server_default="0.0"),
        sa.Column("gratitude", sa.Float, server_default="0.0"),
        sa.Column("anger", sa.Float, server_default="0.0"),
        # Extra dimensions
        sa.Column("debt", sa.Float, server_default="0.0"),
        sa.Column("alliance", sa.Boolean, server_default="false"),
        sa.Column("last_interaction_tick", sa.BigInteger, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(
        "ix_relationship_pair", "entity_relationships",
        ["entity_id", "target_id"], unique=True,
    )

    # ── structures ──────────────────────────────────────────────────
    # Named collection of voxels (must be created before voxel_blocks
    # in case we later add a FK from voxel_blocks.structure_id).
    op.create_table(
        "structures",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(200), nullable=True),
        sa.Column("owner_id", UUID(as_uuid=True), nullable=True),
        sa.Column("structure_type", sa.String(50), nullable=False, server_default="building"),
        sa.Column("min_x", sa.Integer, nullable=False, server_default="0"),
        sa.Column("min_y", sa.Integer, nullable=False, server_default="0"),
        sa.Column("min_z", sa.Integer, nullable=False, server_default="0"),
        sa.Column("max_x", sa.Integer, nullable=False, server_default="0"),
        sa.Column("max_y", sa.Integer, nullable=False, server_default="0"),
        sa.Column("max_z", sa.Integer, nullable=False, server_default="0"),
        sa.Column("properties", JSONB, server_default="{}"),
        sa.Column("created_tick", sa.BigInteger, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── voxel_blocks ────────────────────────────────────────────────
    # A single voxel in the world. 1 voxel = 1 m cubed.
    op.create_table(
        "voxel_blocks",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("x", sa.Integer, nullable=False),
        sa.Column("y", sa.Integer, nullable=False),
        sa.Column("z", sa.Integer, nullable=False),
        sa.Column("color", sa.String(7), nullable=False, server_default="#888888"),
        sa.Column("material", sa.String(20), nullable=False, server_default="solid"),
        sa.Column("has_collision", sa.Boolean, server_default="true"),
        sa.Column("placed_by", UUID(as_uuid=True), nullable=True),
        sa.Column("structure_id", UUID(as_uuid=True), nullable=True),
        sa.Column("placed_tick", sa.BigInteger, nullable=False, server_default="0"),
    )
    op.create_index("ix_voxel_position", "voxel_blocks", ["x", "y", "z"], unique=True)
    op.create_index("ix_voxel_structure", "voxel_blocks", ["structure_id"])

    # ── world_events ────────────────────────────────────────────────
    # Event sourcing: every state change is recorded as a world event.
    op.create_table(
        "world_events",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("tick", sa.BigInteger, nullable=False),
        sa.Column("actor_id", UUID(as_uuid=True), nullable=True),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("params", JSONB, server_default="{}"),
        sa.Column("result", sa.String(20), nullable=False, server_default="accepted"),
        sa.Column("reason", sa.String(200), nullable=True),
        sa.Column("position_x", sa.Float, nullable=True),
        sa.Column("position_y", sa.Float, nullable=True),
        sa.Column("position_z", sa.Float, nullable=True),
        sa.Column("importance", sa.Float, server_default="0.5"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_world_event_tick", "world_events", ["tick"])
    op.create_index("ix_world_event_actor", "world_events", ["actor_id"])
    op.create_index("ix_world_event_type", "world_events", ["event_type"])

    # ── zones ───────────────────────────────────────────────────────
    # Named region in the world: territory, hub, etc.
    op.create_table(
        "zones",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("owner_id", UUID(as_uuid=True), nullable=True),
        sa.Column("zone_type", sa.String(50), server_default="open"),
        sa.Column("min_x", sa.Integer, nullable=False),
        sa.Column("min_y", sa.Integer, nullable=False),
        sa.Column("min_z", sa.Integer, nullable=False),
        sa.Column("max_x", sa.Integer, nullable=False),
        sa.Column("max_y", sa.Integer, nullable=False),
        sa.Column("max_z", sa.Integer, nullable=False),
        sa.Column("rules", JSONB, server_default="{}"),
        sa.Column("created_tick", sa.BigInteger, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    # Drop indexes explicitly, then tables in reverse dependency order.

    # zones (no FK deps)
    op.drop_table("zones")

    # world_events
    op.drop_index("ix_world_event_type", table_name="world_events")
    op.drop_index("ix_world_event_actor", table_name="world_events")
    op.drop_index("ix_world_event_tick", table_name="world_events")
    op.drop_table("world_events")

    # voxel_blocks
    op.drop_index("ix_voxel_structure", table_name="voxel_blocks")
    op.drop_index("ix_voxel_position", table_name="voxel_blocks")
    op.drop_table("voxel_blocks")

    # structures
    op.drop_table("structures")

    # entity_relationships (FK -> entities)
    op.drop_index("ix_relationship_pair", table_name="entity_relationships")
    op.drop_table("entity_relationships")

    # semantic_memories (FK -> entities)
    op.drop_index("ix_semantic_entity_key", table_name="semantic_memories")
    op.drop_table("semantic_memories")

    # episodic_memories (FK -> entities)
    op.drop_index("ix_episodic_importance", table_name="episodic_memories")
    op.drop_index("ix_episodic_entity_tick", table_name="episodic_memories")
    op.drop_table("episodic_memories")

    # entities (referenced by memories + relationships — drop last)
    op.drop_index("ix_entities_position", table_name="entities")
    op.drop_index("ix_entities_alive", table_name="entities")
    op.drop_table("entities")
