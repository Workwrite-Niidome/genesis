import uuid
from datetime import datetime
from sqlalchemy import String, Integer, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class ConsultationSession(Base):
    __tablename__ = "consultation_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    resident_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("residents.id"), nullable=False, index=True
    )
    dify_conversation_id: Mapped[str | None] = mapped_column(
        String(64), nullable=True, index=True
    )
    title: Mapped[str] = mapped_column(String(200), default="New Consultation")
    message_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    resident = relationship("Resident", back_populates="consultation_sessions")
    messages = relationship(
        "ConsultationMessage",
        back_populates="session",
        lazy="dynamic",
        cascade="all, delete-orphan",
        order_by="ConsultationMessage.created_at",
    )

    def __repr__(self) -> str:
        return f"<ConsultationSession {self.id}>"


class ConsultationMessage(Base):
    __tablename__ = "consultation_messages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("consultation_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(String(10), nullable=False)  # "user" or "assistant"
    content: Mapped[str] = mapped_column(Text, nullable=False)
    dify_message_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, index=True
    )

    # Relationships
    session = relationship("ConsultationSession", back_populates="messages")

    def __repr__(self) -> str:
        return f"<ConsultationMessage {self.id} role={self.role}>"
