import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Float, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class WorldFeature(Base):
    """World features: resource nodes, terrain zones, shelter zones, workshop zones.

    These form the physical layer of the world — they determine what happens
    when AIs rest, create, or move, based on location rather than fixed bonuses.
    """
    __tablename__ = "world_features"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    feature_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # resource_node, terrain_zone, shelter_zone, workshop_zone
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    position_x: Mapped[float] = mapped_column(Float, nullable=False)
    position_y: Mapped[float] = mapped_column(Float, nullable=False)
    radius: Mapped[float] = mapped_column(Float, default=30.0)
    properties: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_by_artifact_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("artifacts.id"), nullable=True
    )
    tick_created: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
