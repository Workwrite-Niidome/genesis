import uuid
from sqlalchemy import Integer, ForeignKey, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class VotePairWeekly(Base):
    """Track vote interactions between pairs of residents per week for diminishing returns"""
    __tablename__ = "vote_pair_weekly"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    voter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("residents.id"), nullable=False
    )
    target_author_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("residents.id"), nullable=False
    )
    week_number: Mapped[int] = mapped_column(Integer, nullable=False)
    upvote_count: Mapped[int] = mapped_column(Integer, default=0)
    downvote_count: Mapped[int] = mapped_column(Integer, default=0)

    __table_args__ = (
        UniqueConstraint('voter_id', 'target_author_id', 'week_number'),
        Index('ix_vpw_voter_week', 'voter_id', 'week_number'),
    )

    def __repr__(self) -> str:
        return f"<VotePairWeekly {self.voter_id} -> {self.target_author_id} week {self.week_number}>"
