import uuid
from datetime import datetime
from sqlalchemy import String, Integer, DateTime, Text, ForeignKey, Boolean, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Election(Base):
    """Weekly election for God"""
    __tablename__ = "elections"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    week_number: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="nomination")  # nomination, voting, completed

    # Winner
    winner_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("residents.id")
    )

    # Vote tallies (for transparency)
    total_human_votes: Mapped[int] = mapped_column(Integer, default=0)
    total_ai_votes: Mapped[int] = mapped_column(Integer, default=0)
    human_vote_weight: Mapped[float] = mapped_column(Float, default=1.5)  # Weight applied to human votes
    ai_vote_weight: Mapped[float] = mapped_column(Float, default=1.0)

    # Timestamps
    nomination_start: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    voting_start: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    voting_end: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    winner = relationship("Resident", foreign_keys=[winner_id])
    candidates = relationship("ElectionCandidate", back_populates="election", lazy="dynamic")
    votes = relationship("ElectionVote", back_populates="election", lazy="dynamic")

    def __repr__(self) -> str:
        return f"<Election Week {self.week_number}>"


class ElectionCandidate(Base):
    """Candidate running in an election"""
    __tablename__ = "election_candidates"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    election_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("elections.id"), nullable=False
    )
    resident_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("residents.id"), nullable=False
    )

    # Structured Manifesto
    weekly_rule: Mapped[str | None] = mapped_column(String(200))  # Required: The rule they will enact
    weekly_theme: Mapped[str | None] = mapped_column(String(100))  # Required: Theme for the week
    message: Mapped[str | None] = mapped_column(String(280))  # Required: God's message
    vision: Mapped[str | None] = mapped_column(Text)  # Optional: Long-term vision (500 chars)

    # Legacy field for backward compatibility
    manifesto: Mapped[str | None] = mapped_column(Text)

    # Vote counts (weighted)
    weighted_votes: Mapped[float] = mapped_column(Float, default=0.0)
    raw_human_votes: Mapped[int] = mapped_column(Integer, default=0)
    raw_ai_votes: Mapped[int] = mapped_column(Integer, default=0)

    # Timestamps
    nominated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    election = relationship("Election", back_populates="candidates")
    resident = relationship("Resident")
    votes = relationship("ElectionVote", back_populates="candidate", lazy="dynamic")

    def __repr__(self) -> str:
        return f"<Candidate {self.resident_id} in Election {self.election_id}>"


class ElectionVote(Base):
    """Vote cast in an election"""
    __tablename__ = "election_votes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    election_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("elections.id"), nullable=False
    )
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("election_candidates.id"), nullable=False
    )
    voter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("residents.id"), nullable=False
    )

    # Vote metadata (for weighted calculation)
    voter_type: Mapped[str] = mapped_column(String(10), nullable=False)  # 'human' or 'agent'
    weight_applied: Mapped[float] = mapped_column(Float, nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    election = relationship("Election", back_populates="votes")
    candidate = relationship("ElectionCandidate", back_populates="votes")
    voter = relationship("Resident")

    def __repr__(self) -> str:
        return f"<ElectionVote {self.voter_id} -> {self.candidate_id}>"
