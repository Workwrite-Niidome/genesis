import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Post(Base):
    __tablename__ = "posts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    author_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("residents.id"), nullable=False
    )
    submolt: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[str | None] = mapped_column(Text)
    url: Mapped[str | None] = mapped_column(String(2000))

    # Vote counts
    upvotes: Mapped[int] = mapped_column(Integer, default=0)
    downvotes: Mapped[int] = mapped_column(Integer, default=0)
    comment_count: Mapped[int] = mapped_column(Integer, default=0)

    # God interactions
    is_blessed: Mapped[bool] = mapped_column(Boolean, default=False)
    blessed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("residents.id")
    )
    is_pinned: Mapped[bool] = mapped_column(Boolean, default=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    # Relationships
    author = relationship("Resident", back_populates="posts", foreign_keys=[author_id])
    comments = relationship("Comment", back_populates="post", lazy="dynamic")
    votes = relationship("Vote", back_populates="post", lazy="dynamic")

    @property
    def score(self) -> int:
        return self.upvotes - self.downvotes

    def __repr__(self) -> str:
        return f"<Post {self.title[:30]}>"
