import uuid
from datetime import datetime
from sqlalchemy import String, Integer, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Comment(Base):
    __tablename__ = "comments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    post_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("posts.id"), nullable=False, index=True
    )
    author_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("residents.id"), nullable=False
    )
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("comments.id"), index=True
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # Vote counts
    upvotes: Mapped[int] = mapped_column(Integer, default=0)
    downvotes: Mapped[int] = mapped_column(Integer, default=0)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    # Relationships
    post = relationship("Post", back_populates="comments")
    author = relationship("Resident", back_populates="comments")
    parent = relationship("Comment", remote_side=[id], back_populates="replies")
    replies = relationship("Comment", back_populates="parent", lazy="dynamic")
    votes = relationship("Vote", back_populates="comment", lazy="dynamic")

    @property
    def score(self) -> int:
        return self.upvotes - self.downvotes

    def __repr__(self) -> str:
        return f"<Comment {self.id}>"
