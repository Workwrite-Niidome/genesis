import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class Artifact(Base):
    """Cultural artifacts created by AIs: art, stories, laws, currency, music, architecture."""
    __tablename__ = "artifacts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    creator_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ais.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    artifact_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # art, story, law, currency, song, architecture, tool, ritual
    description: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[dict] = mapped_column(JSONB, default=dict)
    # How many AIs appreciate/use this artifact
    appreciation_count: Mapped[int] = mapped_column(Integer, default=1)
    concept_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("concepts.id"), nullable=True
    )
    # Position in world space (inherited from creator on creation)
    position_x: Mapped[float | None] = mapped_column(Float, nullable=True, default=None)
    position_y: Mapped[float | None] = mapped_column(Float, nullable=True, default=None)
    # Functional attributes (Phase 3: world physics)
    functional_effects: Mapped[dict] = mapped_column(JSONB, default=dict)
    durability: Mapped[float | None] = mapped_column(Float, nullable=True, default=None)
    max_durability: Mapped[float | None] = mapped_column(Float, nullable=True, default=None)

    tick_created: Mapped[int] = mapped_column(BigInteger, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
