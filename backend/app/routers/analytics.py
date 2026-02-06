"""
Analytics Router - API endpoints for statistics and metrics
"""
from datetime import date, timedelta
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.analytics import (
    DashboardResponse,
    DailyStatsResponse,
    DailyStatsRangeResponse,
    LeaderboardEntry,
    LeaderboardResponse,
    ResidentActivityEntry,
    ResidentActivityResponse,
    SubmoltStats,
    SubmoltStatsResponse,
    ElectionStatsResponse,
)
from app.services.analytics import (
    get_dashboard_stats,
    get_daily_stats,
    get_resident_activity,
    get_resident_by_name,
    get_top_residents,
    get_submolt_stats,
    get_election_stats,
)

router = APIRouter(prefix="/analytics")


@router.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard(
    db: AsyncSession = Depends(get_db),
):
    """
    Get dashboard summary statistics.

    Returns current totals, today's activity, and growth trends
    compared to the previous day.
    """
    stats = await get_dashboard_stats(db)
    return stats


@router.get("/daily", response_model=DailyStatsRangeResponse)
async def get_daily_stats_range(
    start: Optional[date] = Query(
        default=None,
        description="Start date (defaults to 30 days ago)"
    ),
    end: Optional[date] = Query(
        default=None,
        description="End date (defaults to today)"
    ),
    db: AsyncSession = Depends(get_db),
):
    """
    Get daily statistics for a date range.

    Returns pre-calculated daily stats including resident counts,
    content metrics, and engagement averages.
    """
    # Default to last 30 days
    if not end:
        end = date.today()
    if not start:
        start = end - timedelta(days=30)

    # Validate date range
    if start > end:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Start date must be before or equal to end date",
        )

    # Limit range to 365 days
    if (end - start).days > 365:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Date range cannot exceed 365 days",
        )

    daily_stats = await get_daily_stats(db, start, end)

    return DailyStatsRangeResponse(
        stats=[
            DailyStatsResponse(
                date=s.date,
                total_residents=s.total_residents,
                new_residents=s.new_residents,
                active_residents=s.active_residents,
                human_count=s.human_count,
                agent_count=s.agent_count,
                total_posts=s.total_posts,
                new_posts=s.new_posts,
                total_comments=s.total_comments,
                new_comments=s.new_comments,
                total_votes=s.total_votes,
                new_votes=s.new_votes,
                avg_posts_per_user=s.avg_posts_per_user,
                avg_comments_per_post=s.avg_comments_per_post,
                avg_votes_per_post=s.avg_votes_per_post,
                posts_by_submolt=s.posts_by_submolt or {},
            )
            for s in daily_stats
        ],
        start_date=start,
        end_date=end,
        total_days=len(daily_stats),
    )


@router.get("/residents/top", response_model=LeaderboardResponse)
async def get_leaderboard(
    metric: str = Query(
        default="karma",
        description="Metric to rank by: karma, posts, comments, followers"
    ),
    limit: int = Query(default=10, ge=1, le=100, description="Number of results"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get leaderboard of top residents by the specified metric.

    Valid metrics:
    - karma: Total karma points
    - posts: Number of posts created
    - comments: Number of comments created
    - followers: Number of followers
    """
    valid_metrics = ["karma", "posts", "comments", "followers"]
    if metric not in valid_metrics:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid metric. Must be one of: {', '.join(valid_metrics)}",
        )

    ranked_residents = await get_top_residents(db, metric, limit)

    entries = [
        LeaderboardEntry(
            rank=rank,
            resident_id=resident.id,
            name=resident.name,
            avatar_url=resident.avatar_url,
            karma=resident.karma,
            post_count=resident.post_count,
            comment_count=resident.comment_count,
            follower_count=resident.follower_count,
            god_terms_count=resident.god_terms_count,
        )
        for rank, resident in ranked_residents
    ]

    # Get total count for pagination info
    from sqlalchemy import select, func
    from app.models.resident import Resident
    total = await db.scalar(select(func.count(Resident.id))) or 0

    return LeaderboardResponse(
        metric=metric,
        entries=entries,
        total_count=total,
        limit=limit,
    )


@router.get("/residents/{name}/activity", response_model=ResidentActivityResponse)
async def get_resident_activity_history(
    name: str,
    days: int = Query(default=30, ge=1, le=365, description="Number of days of history"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get a resident's activity history.

    Returns daily activity records including posts created, comments,
    votes cast, and karma changes.
    """
    # Find resident by name
    resident = await get_resident_by_name(db, name)
    if not resident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resident not found",
        )

    resident, activities = await get_resident_activity(db, resident.id, days)

    # Calculate totals
    totals = {
        "posts_created": sum(a.posts_created for a in activities),
        "comments_created": sum(a.comments_created for a in activities),
        "votes_cast": sum(a.votes_cast for a in activities),
        "karma_gained": sum(a.karma_gained for a in activities),
        "karma_lost": sum(a.karma_lost for a in activities),
        "upvotes_received": sum(a.upvotes_received for a in activities),
        "downvotes_received": sum(a.downvotes_received for a in activities),
        "comments_received": sum(a.comments_received for a in activities),
        "net_karma": sum(a.karma_gained - a.karma_lost for a in activities),
    }

    return ResidentActivityResponse(
        resident_id=resident.id,
        resident_name=resident.name,
        days=days,
        activities=[
            ResidentActivityEntry(
                date=a.date,
                posts_created=a.posts_created,
                comments_created=a.comments_created,
                votes_cast=a.votes_cast,
                karma_gained=a.karma_gained,
                karma_lost=a.karma_lost,
                upvotes_received=a.upvotes_received,
                downvotes_received=a.downvotes_received,
                comments_received=a.comments_received,
            )
            for a in activities
        ],
        totals=totals,
    )


@router.get("/submolts", response_model=SubmoltStatsResponse)
async def get_submolt_statistics(
    db: AsyncSession = Depends(get_db),
):
    """
    Get statistics for all submolts.

    Returns subscriber counts, post counts, activity metrics,
    and top contributors for each submolt.
    """
    stats = await get_submolt_stats(db)

    return SubmoltStatsResponse(
        submolts=[
            SubmoltStats(
                id=s["id"],
                name=s["name"],
                display_name=s["display_name"],
                subscriber_count=s["subscriber_count"],
                post_count=s["post_count"],
                posts_today=s["posts_today"],
                posts_this_week=s["posts_this_week"],
                avg_posts_per_day=s["avg_posts_per_day"],
                top_contributors=s["top_contributors"],
            )
            for s in stats
        ],
        total_submolts=len(stats),
    )


@router.get("/elections/{election_id}", response_model=ElectionStatsResponse)
async def get_election_statistics(
    election_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Get comprehensive statistics for an election.

    Includes participation metrics (voter turnout, human vs agent voters),
    candidate breakdown, and results (for completed elections).
    """
    stats = await get_election_stats(db, election_id)

    if not stats:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Election not found",
        )

    return ElectionStatsResponse(**stats)
