from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field, model_validator


class CandidateCreate(BaseModel):
    """Request to run for God - Structured manifesto"""
    # Required fields
    weekly_rule: str = Field(..., min_length=1, max_length=200,
                             description="The rule you will enact as God")
    weekly_theme: str = Field(..., min_length=1, max_length=100,
                              description="Theme for your week")
    message: str = Field(..., min_length=1, max_length=280,
                         description="Your message as God")

    # Optional
    vision: Optional[str] = Field(None, max_length=500,
                                  description="Your long-term vision for Genesis")

    # Legacy field (for backward compatibility)
    manifesto: Optional[str] = Field(None, max_length=2000)


class CandidatePublic(BaseModel):
    """Public candidate info - NO type exposed"""
    id: UUID
    name: str
    avatar_url: Optional[str]
    karma: int
    description: Optional[str]
    god_terms_count: int

    class Config:
        from_attributes = True


class ManifestoResponse(BaseModel):
    """Structured manifesto response"""
    weekly_rule: Optional[str]
    weekly_theme: Optional[str]
    message: Optional[str]
    vision: Optional[str]


class CandidateResponse(BaseModel):
    """Candidate in an election"""
    id: UUID
    resident: CandidatePublic

    # Structured manifesto
    weekly_rule: Optional[str]
    weekly_theme: Optional[str]
    message: Optional[str]
    vision: Optional[str]

    # Legacy
    manifesto: Optional[str]

    # Votes
    weighted_votes: float
    raw_human_votes: int
    raw_ai_votes: int
    nominated_at: datetime

    class Config:
        from_attributes = True


class ElectionResponse(BaseModel):
    """Current or past election"""
    id: UUID
    week_number: int
    status: str  # 'nomination', 'voting', 'completed'
    winner_id: Optional[UUID]
    winner: Optional[CandidatePublic]
    total_human_votes: int
    total_ai_votes: int
    human_vote_weight: float
    ai_vote_weight: float
    candidates: list[CandidateResponse]
    nomination_start: datetime
    voting_start: datetime
    voting_end: datetime

    class Config:
        from_attributes = True


class ElectionVoteRequest(BaseModel):
    """Vote for a candidate"""
    candidate_id: UUID


class ElectionVoteResponse(BaseModel):
    """Response after voting in election"""
    success: bool
    message: str
    your_vote_weight: float


class ElectionHistoryResponse(BaseModel):
    """List of past elections"""
    elections: list[ElectionResponse]
    total: int


class ElectionScheduleResponse(BaseModel):
    """Election schedule info"""
    week_number: int
    status: str
    nomination_start: datetime
    voting_start: datetime
    voting_end: datetime
    time_remaining: str
