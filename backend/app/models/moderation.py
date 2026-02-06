"""
Moderation System - Reports, bans, and moderation actions
"""
import uuid
from datetime import datetime
from sqlalchemy import String, Integer, DateTime, Text, Boolean, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Report(Base):
    """User reports for posts, comments, or residents"""
    __tablename__ = "reports"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    reporter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("residents.id", ondelete="CASCADE"), nullable=False
    )

    # Target (one of these will be set)
    target_type: Mapped[str] = mapped_column(String(20), nullable=False)  # 'post', 'comment', 'resident'
    target_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

    # Report details
    reason: Mapped[str] = mapped_column(String(50), nullable=False)  # spam, harassment, hate, misinformation, other
    description: Mapped[str | None] = mapped_column(Text)

    # Status
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, reviewed, resolved, dismissed
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("residents.id"))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime)
    resolution_note: Mapped[str | None] = mapped_column(Text)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    # Relationships
    reporter = relationship("Resident", foreign_keys=[reporter_id])
    reviewer = relationship("Resident", foreign_keys=[reviewed_by])

    __table_args__ = (
        Index('ix_reports_target', 'target_type', 'target_id'),
        Index('ix_reports_status', 'status'),
    )

    def __repr__(self) -> str:
        return f"<Report {self.target_type}:{self.target_id} by {self.reporter_id}>"


class ModerationAction(Base):
    """Actions taken by moderators"""
    __tablename__ = "moderation_actions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    moderator_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("residents.id"), nullable=False
    )

    # Target
    target_type: Mapped[str] = mapped_column(String(20), nullable=False)  # 'post', 'comment', 'resident'
    target_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

    # Action
    action: Mapped[str] = mapped_column(String(30), nullable=False)  # remove, restore, warn, mute, ban, unban
    reason: Mapped[str | None] = mapped_column(Text)

    # Duration (for mute/ban)
    duration_hours: Mapped[int | None] = mapped_column(Integer)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime)

    # Related report
    report_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("reports.id")
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    # Relationships
    moderator = relationship("Resident", foreign_keys=[moderator_id])
    report = relationship("Report")

    def __repr__(self) -> str:
        return f"<ModerationAction {self.action} on {self.target_type}:{self.target_id}>"


class ResidentBan(Base):
    """Active bans on residents"""
    __tablename__ = "resident_bans"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    resident_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("residents.id", ondelete="CASCADE"), nullable=False, unique=True
    )

    # Ban details
    banned_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("residents.id"), nullable=False
    )
    reason: Mapped[str | None] = mapped_column(Text)

    # Duration
    is_permanent: Mapped[bool] = mapped_column(Boolean, default=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, index=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    resident = relationship("Resident", foreign_keys=[resident_id])
    banner = relationship("Resident", foreign_keys=[banned_by])

    def __repr__(self) -> str:
        return f"<ResidentBan {self.resident_id}>"

    @property
    def is_active(self) -> bool:
        if self.is_permanent:
            return True
        if self.expires_at is None:
            return False
        return datetime.utcnow() < self.expires_at
