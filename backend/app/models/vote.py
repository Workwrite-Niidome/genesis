import uuid
from datetime import datetime
from sqlalchemy import String, Integer, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Vote(Base):
    __tablename__ = "votes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    resident_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("residents.id"), nullable=False
    )
    target_type: Mapped[str] = mapped_column(String(10), nullable=False)  # 'post' or 'comment'
    target_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    value: Mapped[int] = mapped_column(Integer, nullable=False)  # 1 or -1

    # For easy querying
    post_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("posts.id"), index=True
    )
    comment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("comments.id"), index=True
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    resident = relationship("Resident", back_populates="votes")
    post = relationship("Post", back_populates="votes")
    comment = relationship("Comment", back_populates="votes")

    __table_args__ = (
        UniqueConstraint("resident_id", "target_type", "target_id", name="uq_vote_unique"),
    )

    def __repr__(self) -> str:
        return f"<Vote {self.target_type}:{self.target_id} = {self.value}>"
