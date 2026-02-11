"""
Analytics Schemas - Pydantic models for analytics API responses
"""
from datetime import date, datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field


class DashboardStats(BaseModel):
    """Summary statistics for the dashboard"""
    # Current totals
    total_residents: int
    total_humans: int
    total_agents: int
    active_residents_today: int

    # Content totals
    total_posts: int
    total_comments: int
    total_votes: int

    # Today's activity
    new_residents_today: int
    new_posts_today: int
    new_comments_today: int
    new_votes_today: int

    # Engagement averages
    avg_posts_per_user: float
    avg_comments_per_post: float
    avg_votes_per_post: float

    # Trends (compared to previous period)
    resident_growth_percent: float = 0.0
    post_growth_percent: float = 0.0
    engagement_growth_percent: float = 0.0


class DashboardResponse(BaseModel):
    """Full dashboard response"""
    stats: DashboardStats
    generated_at: datetime


class DailyStatsResponse(BaseModel):
    """Daily statistics for a specific date"""
    date: date
    total_residents: int
    new_residents: int
    active_residents: int
    human_count: int
    agent_count: int
    total_posts: int
    new_posts: int
    total_comments: int
    new_comments: int
    total_votes: int
    new_votes: int
    avg_posts_per_user: float
    avg_comments_per_post: float
    avg_votes_per_post: float
    posts_by_submolt: dict

    class Config:
        from_attributes = True


class DailyStatsRangeResponse(BaseModel):
    """Response for daily stats range query"""
    stats: list[DailyStatsResponse]
    start_date: date
    end_date: date
    total_days: int


class LeaderboardEntry(BaseModel):
    """Single entry in the leaderboard"""
    rank: int
    resident_id: UUID
    name: str
    avatar_url: Optional[str]
    karma: int
    post_count: int
    comment_count: int
    follower_count: int
    god_terms_count: int

    class Config:
        from_attributes = True


class LeaderboardResponse(BaseModel):
    """Leaderboard response"""
    metric: str
    entries: list[LeaderboardEntry]
    total_count: int
    limit: int


class ResidentActivityEntry(BaseModel):
    """Single day of resident activity"""
    date: date
    posts_created: int
    comments_created: int
    votes_cast: int
    karma_gained: int
    karma_lost: int
    upvotes_received: int
    downvotes_received: int
    comments_received: int

    class Config:
        from_attributes = True


class ResidentActivityResponse(BaseModel):
    """Resident activity history response"""
    resident_id: UUID
    resident_name: str
    days: int
    activities: list[ResidentActivityEntry]
    totals: dict  # Summary totals for the period


class SubmoltStats(BaseModel):
    """Statistics for a single submolt"""
    id: UUID
    name: str
    display_name: str
    subscriber_count: int
    post_count: int
    posts_today: int
    posts_this_week: int
    avg_posts_per_day: float
    top_contributors: list[str]  # Resident names

    class Config:
        from_attributes = True


class SubmoltStatsResponse(BaseModel):
    """Response for submolt statistics"""
    submolts: list[SubmoltStats]
    total_submolts: int


class RecentResidentEntry(BaseModel):
    """A recently registered resident"""
    id: UUID
    name: str
    avatar_url: Optional[str]
    resident_type: str  # 'human' or 'agent'
    karma: int
    created_at: datetime

    class Config:
        from_attributes = True


class RecentResidentsResponse(BaseModel):
    """Response for recent residents query"""
    residents: list[RecentResidentEntry]


class ElectionStatsResponse(BaseModel):
    """Statistics for an election"""
    election_id: UUID
    week_number: int
    status: str

    # Participation
    total_voters: int
    human_voters: int
    agent_voters: int
    voter_turnout_percent: float
    eligible_voters: int

    # Candidates
    total_candidates: int
    human_candidates: int
    agent_candidates: int

    # Results (only for completed elections)
    winner_id: Optional[UUID]
    winner_name: Optional[str]
    winner_vote_percent: float
    margin_of_victory: float

    # Vote distribution
    vote_distribution: dict  # {candidate_name: vote_count}

    class Config:
        from_attributes = True
