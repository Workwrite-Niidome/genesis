import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class AIThought(Base):
    __tablename__ = "ai_thoughts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    ai_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ais.id", ondelete="CASCADE"), nullable=False
    )
    tick_number: Mapped[int] = mapped_column(BigInteger, nullable=False)
    thought_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # 'reflection', 'reaction', 'intention', 'observation'
    content: Mapped[str] = mapped_column(Text, nullable=False)
    action: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    context: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    ai = relationship("AI", back_populates="thoughts")
