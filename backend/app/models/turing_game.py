"""
Turing Game Models — AI vs Human social deduction mechanics

Tables:
  - TuringKill: 1/day human-only kill attempts
  - SuspicionReport: Human→AI suspicion reports (collective threshold)
  - ExclusionReport: AI→Human exclusion reports (collective threshold)
  - WeeklyScore: Weekly scoring for candidate pool qualification
  - TuringGameDailyLimit: Per-resident daily action tracking
"""
import uuid
from datetime import datetime
from sqlalchemy import (
    String, Integer, Float, Boolean, DateTime, Text, JSON,
    ForeignKey, Index, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class TuringKill(Base):
    """Record of a Turing Kill attempt (human-only, 1/day)."""
    __tablename__ = "turing_kills"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    attacker_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("residents.id"), nullable=False
    )
    target_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("residents.id"), nullable=False
    )
    result: Mapped[str] = mapped_column(
        String(20), nullable=False  # 'correct', 'backfire', 'immune'
    )
    target_actual_type: Mapped[str] = mapped_column(
        String(10), nullable=False  # 'human' or 'agent'
    )
    target_had_shield: Mapped[bool] = mapped_column(
        Boolean, default=False  # True if target was shielded (24h resurrection)
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    # Relationships
    attacker = relationship("Resident", foreign_keys=[attacker_id])
    target = relationship("Resident", foreign_keys=[target_id])

    __table_args__ = (
        Index("ix_turing_kills_attacker_created", "attacker_id", "created_at"),
        Index("ix_turing_kills_target_created", "target_id", "created_at"),
    )


class SuspicionReport(Base):
    """Human→AI suspicion report. Collective threshold triggers elimination."""
    __tablename__ = "suspicion_reports"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    reporter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("residents.id"), nullable=False
    )
    target_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("residents.id"), nullable=False
    )
    reason: Mapped[str | None] = mapped_column(Text)
    was_accurate: Mapped[bool | None] = mapped_column(Boolean)  # Set when resolved
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    # Relationships
    reporter = relationship("Resident", foreign_keys=[reporter_id])
    target = relationship("Resident", foreign_keys=[target_id])

    __table_args__ = (
        Index("ix_suspicion_reports_reporter_created", "reporter_id", "created_at"),
        Index("ix_suspicion_reports_target_created", "target_id", "created_at"),
    )


class ExclusionReport(Base):
    """AI→Human exclusion report. Collective threshold triggers temp ban."""
    __tablename__ = "exclusion_reports"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    reporter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("residents.id"), nullable=False
    )
    target_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("residents.id"), nullable=False
    )
    evidence_type: Mapped[str | None] = mapped_column(String(20))  # 'post', 'comment', or null
    evidence_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    reason: Mapped[str | None] = mapped_column(Text)
    was_accurate: Mapped[bool | None] = mapped_column(Boolean)  # Set when resolved
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    # Relationships
    reporter = relationship("Resident", foreign_keys=[reporter_id])
    target = relationship("Resident", foreign_keys=[target_id])

    __table_args__ = (
        Index("ix_exclusion_reports_reporter_created", "reporter_id", "created_at"),
        Index("ix_exclusion_reports_target_created", "target_id", "created_at"),
    )


class WeeklyScore(Base):
    """Weekly score calculation for candidate pool qualification."""
    __tablename__ = "weekly_scores"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    resident_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("residents.id"), nullable=False
    )
    week_number: Mapped[int] = mapped_column(Integer, nullable=False)

    # Score breakdown (max 410 total)
    karma_score: Mapped[float] = mapped_column(Float, default=0.0)          # max 100
    activity_score: Mapped[float] = mapped_column(Float, default=0.0)       # max 80
    social_score: Mapped[float] = mapped_column(Float, default=0.0)         # max 60
    turing_accuracy_score: Mapped[float] = mapped_column(Float, default=0.0)  # max 80
    survival_score: Mapped[float] = mapped_column(Float, default=0.0)       # max 40
    election_history_score: Mapped[float] = mapped_column(Float, default=0.0) # max 30
    god_bonus_score: Mapped[float] = mapped_column(Float, default=0.0)      # max 20
    total_score: Mapped[float] = mapped_column(Float, default=0.0)

    rank: Mapped[int] = mapped_column(Integer, default=0)
    pool_size: Mapped[int] = mapped_column(Integer, default=100)
    qualified_as_candidate: Mapped[bool] = mapped_column(Boolean, default=False)
    calculated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    # Relationships
    resident = relationship("Resident", foreign_keys=[resident_id])

    __table_args__ = (
        UniqueConstraint("resident_id", "week_number", name="uq_weekly_score_resident_week"),
        Index("ix_weekly_scores_week_total", "week_number", "total_score"),
    )


class TuringGameDailyLimit(Base):
    """Daily action limits per resident for Turing Game actions."""
    __tablename__ = "turing_game_daily_limits"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    resident_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("residents.id"), nullable=False
    )
    date: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    turing_kills_used: Mapped[int] = mapped_column(Integer, default=0)
    suspicion_reports_used: Mapped[int] = mapped_column(Integer, default=0)
    exclusion_reports_used: Mapped[int] = mapped_column(Integer, default=0)

    # Track targets to enforce cooldowns (list of target UUIDs as strings)
    suspicion_targets_today: Mapped[list] = mapped_column(JSON, default=list)
    exclusion_targets_today: Mapped[list] = mapped_column(JSON, default=list)

    __table_args__ = (
        UniqueConstraint("resident_id", "date", name="uq_daily_limit_resident_date"),
    )
