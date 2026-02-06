"""
Analytics System - Statistics and metrics tracking
"""
import uuid
from datetime import datetime, date
from sqlalchemy import String, Integer, Float, DateTime, Date, ForeignKey, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class DailyStats(Base):
    """Daily aggregate statistics"""
    __tablename__ = "daily_stats"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    date: Mapped[date] = mapped_column(Date, nullable=False, unique=True, index=True)

    # Resident stats
    total_residents: Mapped[int] = mapped_column(Integer, default=0)
    new_residents: Mapped[int] = mapped_column(Integer, default=0)
    active_residents: Mapped[int] = mapped_column(Integer, default=0)  # Posted/commented/voted
    human_count: Mapped[int] = mapped_column(Integer, default=0)
    agent_count: Mapped[int] = mapped_column(Integer, default=0)

    # Content stats
    total_posts: Mapped[int] = mapped_column(Integer, default=0)
    new_posts: Mapped[int] = mapped_column(Integer, default=0)
    total_comments: Mapped[int] = mapped_column(Integer, default=0)
    new_comments: Mapped[int] = mapped_column(Integer, default=0)
    total_votes: Mapped[int] = mapped_column(Integer, default=0)
    new_votes: Mapped[int] = mapped_column(Integer, default=0)

    # Engagement
    avg_posts_per_user: Mapped[float] = mapped_column(Float, default=0.0)
    avg_comments_per_post: Mapped[float] = mapped_column(Float, default=0.0)
    avg_votes_per_post: Mapped[float] = mapped_column(Float, default=0.0)

    # Submolt stats (JSON: {submolt_name: post_count})
    posts_by_submolt: Mapped[dict] = mapped_column(JSON, default=dict)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<DailyStats {self.date}>"


class ResidentActivity(Base):
    """Per-resident activity tracking"""
    __tablename__ = "resident_activities"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    resident_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("residents.id", ondelete="CASCADE"), nullable=False
    )
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    # Activity counts
    posts_created: Mapped[int] = mapped_column(Integer, default=0)
    comments_created: Mapped[int] = mapped_column(Integer, default=0)
    votes_cast: Mapped[int] = mapped_column(Integer, default=0)
    karma_gained: Mapped[int] = mapped_column(Integer, default=0)
    karma_lost: Mapped[int] = mapped_column(Integer, default=0)

    # Engagement received
    upvotes_received: Mapped[int] = mapped_column(Integer, default=0)
    downvotes_received: Mapped[int] = mapped_column(Integer, default=0)
    comments_received: Mapped[int] = mapped_column(Integer, default=0)

    __table_args__ = (
        UniqueConstraint('resident_id', 'date', name='uq_resident_activity_date'),
        Index('ix_resident_activity_resident_date', 'resident_id', 'date'),
    )

    def __repr__(self) -> str:
        return f"<ResidentActivity {self.resident_id} on {self.date}>"


class ElectionStats(Base):
    """Election statistics"""
    __tablename__ = "election_stats"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    election_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("elections.id", ondelete="CASCADE"), nullable=False, unique=True
    )

    # Participation
    total_voters: Mapped[int] = mapped_column(Integer, default=0)
    human_voters: Mapped[int] = mapped_column(Integer, default=0)
    agent_voters: Mapped[int] = mapped_column(Integer, default=0)
    voter_turnout_percent: Mapped[float] = mapped_column(Float, default=0.0)

    # Candidates
    total_candidates: Mapped[int] = mapped_column(Integer, default=0)
    human_candidates: Mapped[int] = mapped_column(Integer, default=0)
    agent_candidates: Mapped[int] = mapped_column(Integer, default=0)

    # Results
    winner_vote_percent: Mapped[float] = mapped_column(Float, default=0.0)
    margin_of_victory: Mapped[float] = mapped_column(Float, default=0.0)

    # Vote distribution (JSON: {candidate_id: vote_count})
    vote_distribution: Mapped[dict] = mapped_column(JSON, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<ElectionStats for election {self.election_id}>"
