import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Integer, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class Tick(Base):
    __tablename__ = "ticks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tick_number: Mapped[int] = mapped_column(BigInteger, nullable=False, unique=True)
    world_snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False)
    ai_count: Mapped[int] = mapped_column(Integer, nullable=False)
    concept_count: Mapped[int] = mapped_column(Integer, nullable=False)
    significant_events: Mapped[list] = mapped_column(JSONB, default=list)
    processing_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
