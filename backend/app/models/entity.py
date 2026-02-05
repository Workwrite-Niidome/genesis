"""GENESIS v3 Entity Model — unified representation for all beings.

There are no 'AI' or 'human' types in the world.
Every being is an 'entity'. The world does not distinguish.
"""
import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger, Boolean, DateTime, Float, ForeignKey,
    Index, Integer, String, Text, func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class Entity(Base):
    """A being in the GENESIS world. AI, user agent, or human avatar — indistinguishable."""
    __tablename__ = "entities"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)

    # Origin type is stored for internal bookkeeping only.
    # The world itself never exposes this to other entities.
    origin_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="native"
    )  # 'native', 'user_agent', 'human_avatar'
    owner_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )  # For user agents / human avatars

    # 3D position
    position_x: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    position_y: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    position_z: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    facing_x: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    facing_z: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # 18-axis numeric personality (immutable core)
    personality: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    # Mutable state: needs, behavior_mode, inventory, etc.
    state: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    # Appearance (voxel avatar data)
    appearance: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    # User agent policy (only for user agents)
    agent_policy: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    is_alive: Mapped[bool] = mapped_column(Boolean, default=True)
    is_god: Mapped[bool] = mapped_column(Boolean, default=False)

    # Meta awareness (observer attention tracking)
    meta_awareness: Mapped[float] = mapped_column(Float, default=0.0)

    birth_tick: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    death_tick: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    memories: Mapped[list["EpisodicMemory"]] = relationship(
        back_populates="entity", cascade="all, delete-orphan"
    )
    semantic_entries: Mapped[list["SemanticMemory"]] = relationship(
        back_populates="entity", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_entities_alive", "is_alive"),
        Index("ix_entities_position", "position_x", "position_y", "position_z"),
    )


class EpisodicMemory(Base):
    """Event-based memory with TTL based on importance."""
    __tablename__ = "episodic_memories"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    entity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("entities.id", ondelete="CASCADE"), nullable=False
    )
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    importance: Mapped[float] = mapped_column(Float, default=0.5)
    tick: Mapped[int] = mapped_column(BigInteger, nullable=False)
    related_entity_ids: Mapped[list] = mapped_column(JSONB, default=list)
    location_x: Mapped[float] = mapped_column(Float, nullable=True)
    location_y: Mapped[float] = mapped_column(Float, nullable=True)
    location_z: Mapped[float] = mapped_column(Float, nullable=True)
    ttl: Mapped[int] = mapped_column(Integer, nullable=False, default=10000)
    memory_type: Mapped[str] = mapped_column(String(50), default="event")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    entity: Mapped["Entity"] = relationship(back_populates="memories")

    __table_args__ = (
        Index("ix_episodic_entity_tick", "entity_id", "tick"),
        Index("ix_episodic_importance", "entity_id", "importance"),
    )


class SemanticMemory(Base):
    """Knowledge-based memory — facts, concepts, world knowledge."""
    __tablename__ = "semantic_memories"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    entity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("entities.id", ondelete="CASCADE"), nullable=False
    )
    key: Mapped[str] = mapped_column(String(200), nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    source_tick: Mapped[int] = mapped_column(BigInteger, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    entity: Mapped["Entity"] = relationship(back_populates="semantic_entries")

    __table_args__ = (
        Index("ix_semantic_entity_key", "entity_id", "key", unique=True),
    )


class EntityRelationship(Base):
    """7-axis relationship between two entities."""
    __tablename__ = "entity_relationships"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    entity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("entities.id", ondelete="CASCADE"), nullable=False
    )
    target_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("entities.id", ondelete="CASCADE"), nullable=False
    )

    # 7 axes: -100 to 100 (or 0 to 100 for some)
    trust: Mapped[float] = mapped_column(Float, default=0.0)        # -100 ~ 100
    familiarity: Mapped[float] = mapped_column(Float, default=0.0)  # 0 ~ 100
    respect: Mapped[float] = mapped_column(Float, default=0.0)      # 0 ~ 100
    fear: Mapped[float] = mapped_column(Float, default=0.0)         # 0 ~ 100
    rivalry: Mapped[float] = mapped_column(Float, default=0.0)      # 0 ~ 100
    gratitude: Mapped[float] = mapped_column(Float, default=0.0)    # 0 ~ 100
    anger: Mapped[float] = mapped_column(Float, default=0.0)        # 0 ~ 100

    # Extra dimensions
    debt: Mapped[float] = mapped_column(Float, default=0.0)         # -100 ~ 100
    alliance: Mapped[bool] = mapped_column(Boolean, default=False)

    last_interaction_tick: Mapped[int] = mapped_column(BigInteger, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        Index("ix_relationship_pair", "entity_id", "target_id", unique=True),
    )
