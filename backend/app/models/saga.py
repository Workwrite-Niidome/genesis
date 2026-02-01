import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class WorldSaga(Base):
    __tablename__ = "world_saga"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    era_number: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    start_tick: Mapped[int] = mapped_column(BigInteger, nullable=False)
    end_tick: Mapped[int] = mapped_column(BigInteger, nullable=False)
    chapter_title: Mapped[str] = mapped_column(String(500), nullable=False)
    narrative: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    era_statistics: Mapped[dict] = mapped_column(JSONB, default=dict)
    key_events: Mapped[list] = mapped_column(JSONB, default=list)
    key_characters: Mapped[list] = mapped_column(JSONB, default=list)
    mood: Mapped[str | None] = mapped_column(String(100), nullable=True)
    generation_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
