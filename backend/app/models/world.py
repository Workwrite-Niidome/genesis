"""GENESIS v3 World Models — voxels, structures, events."""
import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger, Boolean, DateTime, Float, Index,
    Integer, SmallInteger, String, Text, func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class VoxelBlock(Base):
    """A single voxel in the world. 1 voxel = 1m³."""
    __tablename__ = "voxel_blocks"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    # Position (integer grid coordinates)
    x: Mapped[int] = mapped_column(Integer, nullable=False)
    y: Mapped[int] = mapped_column(Integer, nullable=False)
    z: Mapped[int] = mapped_column(Integer, nullable=False)

    # Block properties
    color: Mapped[str] = mapped_column(String(7), nullable=False, default="#888888")
    material: Mapped[str] = mapped_column(
        String(20), nullable=False, default="solid"
    )  # solid, glass, emissive, liquid
    has_collision: Mapped[bool] = mapped_column(Boolean, default=True)

    # Ownership
    placed_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    structure_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    placed_tick: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)

    __table_args__ = (
        Index("ix_voxel_position", "x", "y", "z", unique=True),
        Index("ix_voxel_structure", "structure_id"),
    )


class Structure(Base):
    """A named collection of voxels — building, artwork, monument."""
    __tablename__ = "structures"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    owner_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    structure_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default="building"
    )  # building, art, monument, sign, instrument

    # Bounding box
    min_x: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    min_y: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    min_z: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_x: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_y: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_z: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    properties: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_tick: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class WorldEvent(Base):
    """Event sourcing — every state change is an event."""
    __tablename__ = "world_events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tick: Mapped[int] = mapped_column(BigInteger, nullable=False)

    # Actor (entity who caused this event — no AI/human distinction)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    # Event type and data
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    params: Mapped[dict] = mapped_column(JSONB, default=dict)
    result: Mapped[str] = mapped_column(String(20), nullable=False, default="accepted")
    reason: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # Spatial context
    position_x: Mapped[float | None] = mapped_column(Float, nullable=True)
    position_y: Mapped[float | None] = mapped_column(Float, nullable=True)
    position_z: Mapped[float | None] = mapped_column(Float, nullable=True)

    importance: Mapped[float] = mapped_column(Float, default=0.5)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        Index("ix_world_event_tick", "tick"),
        Index("ix_world_event_actor", "actor_id"),
        Index("ix_world_event_type", "event_type"),
    )


class Zone(Base):
    """A named region in the world — territory, hub, etc."""
    __tablename__ = "zones"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    owner_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    zone_type: Mapped[str] = mapped_column(String(50), default="open")

    # Bounding box
    min_x: Mapped[int] = mapped_column(Integer, nullable=False)
    min_y: Mapped[int] = mapped_column(Integer, nullable=False)
    min_z: Mapped[int] = mapped_column(Integer, nullable=False)
    max_x: Mapped[int] = mapped_column(Integer, nullable=False)
    max_y: Mapped[int] = mapped_column(Integer, nullable=False)
    max_z: Mapped[int] = mapped_column(Integer, nullable=False)

    rules: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_tick: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
