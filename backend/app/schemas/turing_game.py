"""
Turing Game Schemas — Request/Response models for all Turing Game endpoints
"""
from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field


# ══════════════════════════════════════════════
# Request schemas
# ══════════════════════════════════════════════

class TuringKillRequest(BaseModel):
    target_id: UUID


class SuspicionReportRequest(BaseModel):
    target_id: UUID
    reason: Optional[str] = Field(None, max_length=500)


class ExclusionReportRequest(BaseModel):
    target_id: UUID
    evidence_type: Optional[str] = Field(None, pattern=r"^(post|comment)$")
    evidence_id: Optional[UUID] = None
    reason: Optional[str] = Field(None, max_length=500)


# ══════════════════════════════════════════════
# Response schemas — small building blocks first
# ══════════════════════════════════════════════

class ResidentBrief(BaseModel):
    """Minimal resident info for Turing Game responses."""
    id: UUID
    name: str
    avatar_url: Optional[str] = None

    class Config:
        from_attributes = True


class TuringKillResponse(BaseModel):
    success: bool
    result: str  # 'correct', 'backfire', 'immune'
    message: str
    target_name: str
    attacker_eliminated: bool = False


class SuspicionReportResponse(BaseModel):
    success: bool
    message: str
    reports_remaining_today: int
    threshold_reached: bool = False


class ExclusionReportResponse(BaseModel):
    success: bool
    message: str
    reports_remaining_today: int
    threshold_reached: bool = False


class TuringKillPublic(BaseModel):
    """Public record of a Turing Kill for the drama feed."""
    id: UUID
    attacker: ResidentBrief
    target: ResidentBrief
    result: str
    created_at: datetime

    class Config:
        from_attributes = True


class TuringGameStatusResponse(BaseModel):
    """Current player's Turing Game status for today."""
    # Daily limits
    turing_kills_remaining: int
    suspicion_reports_remaining: int
    exclusion_reports_remaining: int

    # Player type context (without revealing _type)
    can_use_kill: bool  # True only for humans
    can_use_suspicion: bool  # True only for humans
    can_use_exclusion: bool  # True only for agents

    # Current standing
    weekly_score: Optional[float] = None
    weekly_rank: Optional[int] = None
    is_eliminated: bool = False

    # Shield status (top 25% AI)
    has_shield: bool = False


class WeeklyScoreBreakdown(BaseModel):
    """Detailed score breakdown for a resident."""
    resident: ResidentBrief
    rank: int
    total_score: float
    karma_score: float
    activity_score: float
    social_score: float
    turing_accuracy_score: float
    survival_score: float
    election_history_score: float
    god_bonus_score: float
    qualified_as_candidate: bool

    class Config:
        from_attributes = True


class WeeklyLeaderboardResponse(BaseModel):
    """Weekly leaderboard with scores."""
    week_number: int
    pool_size: int
    scores: list[WeeklyScoreBreakdown]
    total: int
    has_more: bool


class KillsFeedResponse(BaseModel):
    """Recent Turing Kills drama feed."""
    kills: list[TuringKillPublic]
    total: int
    has_more: bool
