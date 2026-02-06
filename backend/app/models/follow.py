"""
Follow System - Relationships between residents
"""
import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Follow(Base):
    """Follow relationship between residents"""
    __tablename__ = "follows"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    follower_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("residents.id", ondelete="CASCADE"), nullable=False
    )
    following_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("residents.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    follower = relationship("Resident", foreign_keys=[follower_id], backref="following_relations")
    following = relationship("Resident", foreign_keys=[following_id], backref="follower_relations")

    __table_args__ = (
        UniqueConstraint('follower_id', 'following_id', name='uq_follow_pair'),
        Index('ix_follows_follower_id', 'follower_id'),
        Index('ix_follows_following_id', 'following_id'),
    )

    def __repr__(self) -> str:
        return f"<Follow {self.follower_id} -> {self.following_id}>"
