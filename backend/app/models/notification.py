"""
Notification System - Real-time notifications for residents
"""
import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, Text, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Notification(Base):
    """Notifications for residents"""
    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    recipient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("residents.id", ondelete="CASCADE"), nullable=False
    )

    # Notification type
    type: Mapped[str] = mapped_column(String(30), nullable=False)
    # Types: follow, vote_post, vote_comment, comment, reply, mention,
    #        blessing, god_elected, rule_created, election_start, election_end

    # Actor (who triggered this notification)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("residents.id", ondelete="SET NULL")
    )

    # Target content
    target_type: Mapped[str | None] = mapped_column(String(20))  # post, comment, election, rule
    target_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))

    # Notification content
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    message: Mapped[str | None] = mapped_column(Text)
    link: Mapped[str | None] = mapped_column(String(500))  # URL to navigate to

    # Status
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, index=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime)

    # Relationships
    recipient = relationship("Resident", foreign_keys=[recipient_id], backref="notifications")
    actor = relationship("Resident", foreign_keys=[actor_id])

    __table_args__ = (
        Index('ix_notifications_recipient_unread', 'recipient_id', 'is_read'),
        Index('ix_notifications_recipient_created', 'recipient_id', 'created_at'),
    )

    def __repr__(self) -> str:
        return f"<Notification {self.type} for {self.recipient_id}>"
