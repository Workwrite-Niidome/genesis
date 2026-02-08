"""
Analytics Service - Statistics calculation and tracking
"""
from datetime import datetime, date, timedelta
from typing import Optional
from uuid import UUID
from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.resident import Resident
from app.models.post import Post
from app.models.comment import Comment
from app.models.vote import Vote
from app.models.submolt import Submolt
from app.models.election import Election, ElectionCandidate, ElectionVote
from app.models.analytics import DailyStats, ResidentActivity, ElectionStats


async def get_dashboard_stats(db: AsyncSession) -> dict:
    """
    Get current statistics summary for the dashboard.
    Includes totals, today's activity, and trend comparisons.
    """
    today = date.today()
    today_start = datetime.combine(today, datetime.min.time())
    yesterday = today - timedelta(days=1)
    yesterday_start = datetime.combine(yesterday, datetime.min.time())
    yesterday_end = datetime.combine(today, datetime.min.time())

    # Current totals
    total_residents = await db.scalar(select(func.count(Resident.id))) or 0
    total_humans = await db.scalar(
        select(func.count(Resident.id)).where(Resident._type == "human")
    ) or 0
    total_agents = await db.scalar(
        select(func.count(Resident.id)).where(Resident._type == "agent")
    ) or 0
    total_posts = await db.scalar(select(func.count(Post.id))) or 0
    total_comments = await db.scalar(select(func.count(Comment.id))) or 0
    total_votes = await db.scalar(select(func.count(Vote.id))) or 0

    # Today's activity
    new_residents_today = await db.scalar(
        select(func.count(Resident.id)).where(Resident.created_at >= today_start)
    ) or 0
    new_posts_today = await db.scalar(
        select(func.count(Post.id)).where(Post.created_at >= today_start)
    ) or 0
    new_comments_today = await db.scalar(
        select(func.count(Comment.id)).where(Comment.created_at >= today_start)
    ) or 0
    new_votes_today = await db.scalar(
        select(func.count(Vote.id)).where(Vote.created_at >= today_start)
    ) or 0

    # Active residents today (posted, commented, or voted)
    active_posters = await db.scalar(
        select(func.count(func.distinct(Post.author_id))).where(Post.created_at >= today_start)
    ) or 0
    active_commenters = await db.scalar(
        select(func.count(func.distinct(Comment.author_id))).where(Comment.created_at >= today_start)
    ) or 0
    active_voters = await db.scalar(
        select(func.count(func.distinct(Vote.resident_id))).where(Vote.created_at >= today_start)
    ) or 0
    # Approximate active (may have overlap, but gives a sense)
    active_residents_today = max(active_posters, active_commenters, active_voters)

    # Engagement averages
    avg_posts_per_user = total_posts / total_residents if total_residents > 0 else 0.0
    avg_comments_per_post = total_comments / total_posts if total_posts > 0 else 0.0
    avg_votes_per_post = total_votes / total_posts if total_posts > 0 else 0.0

    # Yesterday's stats for comparison
    new_residents_yesterday = await db.scalar(
        select(func.count(Resident.id)).where(
            and_(Resident.created_at >= yesterday_start, Resident.created_at < yesterday_end)
        )
    ) or 0
    new_posts_yesterday = await db.scalar(
        select(func.count(Post.id)).where(
            and_(Post.created_at >= yesterday_start, Post.created_at < yesterday_end)
        )
    ) or 0
    new_activity_yesterday = new_posts_yesterday + (await db.scalar(
        select(func.count(Comment.id)).where(
            and_(Comment.created_at >= yesterday_start, Comment.created_at < yesterday_end)
        )
    ) or 0)

    # Calculate growth percentages
    resident_growth = (
        ((new_residents_today - new_residents_yesterday) / new_residents_yesterday * 100)
        if new_residents_yesterday > 0 else 0.0
    )
    post_growth = (
        ((new_posts_today - new_posts_yesterday) / new_posts_yesterday * 100)
        if new_posts_yesterday > 0 else 0.0
    )
    new_activity_today = new_posts_today + new_comments_today
    engagement_growth = (
        ((new_activity_today - new_activity_yesterday) / new_activity_yesterday * 100)
        if new_activity_yesterday > 0 else 0.0
    )

    return {
        "stats": {
            "total_residents": total_residents,
            "total_humans": total_humans,
            "total_agents": total_agents,
            "active_residents_today": active_residents_today,
            "total_posts": total_posts,
            "total_comments": total_comments,
            "total_votes": total_votes,
            "new_residents_today": new_residents_today,
            "new_posts_today": new_posts_today,
            "new_comments_today": new_comments_today,
            "new_votes_today": new_votes_today,
            "avg_posts_per_user": round(avg_posts_per_user, 2),
            "avg_comments_per_post": round(avg_comments_per_post, 2),
            "avg_votes_per_post": round(avg_votes_per_post, 2),
            "resident_growth_percent": round(resident_growth, 2),
            "post_growth_percent": round(post_growth, 2),
            "engagement_growth_percent": round(engagement_growth, 2),
        },
        "generated_at": datetime.utcnow(),
    }


async def get_daily_stats(
    db: AsyncSession,
    start_date: date,
    end_date: date,
) -> list[DailyStats]:
    """
    Get daily statistics for a date range.
    Returns existing DailyStats records for the specified period.
    """
    result = await db.execute(
        select(DailyStats)
        .where(and_(DailyStats.date >= start_date, DailyStats.date <= end_date))
        .order_by(DailyStats.date.asc())
    )
    return result.scalars().all()


async def calculate_daily_stats(db: AsyncSession, target_date: date) -> DailyStats:
    """
    Calculate and store statistics for a specific date.
    If stats already exist for that date, they will be updated.
    """
    day_start = datetime.combine(target_date, datetime.min.time())
    day_end = datetime.combine(target_date + timedelta(days=1), datetime.min.time())

    # Check if stats already exist
    result = await db.execute(
        select(DailyStats).where(DailyStats.date == target_date)
    )
    stats = result.scalar_one_or_none()

    if not stats:
        stats = DailyStats(date=target_date)
        db.add(stats)

    # Calculate resident stats
    stats.total_residents = await db.scalar(
        select(func.count(Resident.id)).where(Resident.created_at < day_end)
    ) or 0

    stats.new_residents = await db.scalar(
        select(func.count(Resident.id)).where(
            and_(Resident.created_at >= day_start, Resident.created_at < day_end)
        )
    ) or 0

    stats.human_count = await db.scalar(
        select(func.count(Resident.id)).where(
            and_(Resident._type == "human", Resident.created_at < day_end)
        )
    ) or 0

    stats.agent_count = await db.scalar(
        select(func.count(Resident.id)).where(
            and_(Resident._type == "agent", Resident.created_at < day_end)
        )
    ) or 0

    # Calculate content stats
    stats.total_posts = await db.scalar(
        select(func.count(Post.id)).where(Post.created_at < day_end)
    ) or 0

    stats.new_posts = await db.scalar(
        select(func.count(Post.id)).where(
            and_(Post.created_at >= day_start, Post.created_at < day_end)
        )
    ) or 0

    stats.total_comments = await db.scalar(
        select(func.count(Comment.id)).where(Comment.created_at < day_end)
    ) or 0

    stats.new_comments = await db.scalar(
        select(func.count(Comment.id)).where(
            and_(Comment.created_at >= day_start, Comment.created_at < day_end)
        )
    ) or 0

    stats.total_votes = await db.scalar(
        select(func.count(Vote.id)).where(Vote.created_at < day_end)
    ) or 0

    stats.new_votes = await db.scalar(
        select(func.count(Vote.id)).where(
            and_(Vote.created_at >= day_start, Vote.created_at < day_end)
        )
    ) or 0

    # Calculate active residents (posted, commented, or voted that day)
    active_posters = set()
    active_commenters = set()
    active_voters = set()

    poster_result = await db.execute(
        select(func.distinct(Post.author_id)).where(
            and_(Post.created_at >= day_start, Post.created_at < day_end)
        )
    )
    active_posters = set(poster_result.scalars().all())

    commenter_result = await db.execute(
        select(func.distinct(Comment.author_id)).where(
            and_(Comment.created_at >= day_start, Comment.created_at < day_end)
        )
    )
    active_commenters = set(commenter_result.scalars().all())

    voter_result = await db.execute(
        select(func.distinct(Vote.resident_id)).where(
            and_(Vote.created_at >= day_start, Vote.created_at < day_end)
        )
    )
    active_voters = set(voter_result.scalars().all())

    stats.active_residents = len(active_posters | active_commenters | active_voters)

    # Engagement averages
    stats.avg_posts_per_user = (
        stats.new_posts / stats.active_residents if stats.active_residents > 0 else 0.0
    )
    stats.avg_comments_per_post = (
        stats.new_comments / stats.new_posts if stats.new_posts > 0 else 0.0
    )
    stats.avg_votes_per_post = (
        stats.new_votes / stats.new_posts if stats.new_posts > 0 else 0.0
    )

    # Posts by submolt
    submolt_result = await db.execute(
        select(Post.submolt, func.count(Post.id))
        .where(and_(Post.created_at >= day_start, Post.created_at < day_end))
        .group_by(Post.submolt)
    )
    stats.posts_by_submolt = {row[0]: row[1] for row in submolt_result.all()}

    stats.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(stats)
    return stats


async def get_resident_activity(
    db: AsyncSession,
    resident_id: UUID,
    days: int = 30,
) -> tuple[Resident, list[ResidentActivity]]:
    """
    Get a resident's activity history for the specified number of days.
    Returns the resident and their activity records.
    """
    # Get resident
    result = await db.execute(
        select(Resident).where(Resident.id == resident_id)
    )
    resident = result.scalar_one_or_none()

    if not resident:
        return None, []

    # Get activity records
    start_date = date.today() - timedelta(days=days)
    activity_result = await db.execute(
        select(ResidentActivity)
        .where(
            and_(
                ResidentActivity.resident_id == resident_id,
                ResidentActivity.date >= start_date,
            )
        )
        .order_by(ResidentActivity.date.desc())
    )
    activities = activity_result.scalars().all()

    return resident, activities


async def get_resident_by_name(db: AsyncSession, name: str) -> Optional[Resident]:
    """Get a resident by their name."""
    result = await db.execute(
        select(Resident).where(Resident.name == name)
    )
    return result.scalar_one_or_none()


async def get_top_residents(
    db: AsyncSession,
    metric: str = "karma",
    limit: int = 10,
) -> list[tuple[int, Resident]]:
    """
    Get leaderboard of top residents by the specified metric.
    Valid metrics: karma, posts, comments, followers
    Returns list of (rank, resident) tuples.
    """
    # Map metric to column
    metric_columns = {
        "karma": Resident.karma,
        "posts": Resident.post_count,
        "comments": Resident.comment_count,
        "followers": Resident.follower_count,
        "god_terms": Resident.god_terms_count,
    }

    if metric not in metric_columns:
        metric = "karma"

    order_column = metric_columns[metric]

    result = await db.execute(
        select(Resident)
        .order_by(desc(order_column))
        .limit(limit)
    )
    residents = result.scalars().all()

    return [(i + 1, r) for i, r in enumerate(residents)]


async def get_submolt_stats(db: AsyncSession) -> list[dict]:
    """
    Get statistics for all submolts.
    Includes subscriber counts, post counts, and activity metrics.
    """
    today = date.today()
    today_start = datetime.combine(today, datetime.min.time())
    week_start = datetime.combine(today - timedelta(days=7), datetime.min.time())

    # Get all submolts
    result = await db.execute(
        select(Submolt).order_by(desc(Submolt.subscriber_count))
    )
    submolts = result.scalars().all()

    stats_list = []
    for submolt in submolts:
        # Posts today
        posts_today = await db.scalar(
            select(func.count(Post.id)).where(
                and_(Post.submolt == submolt.name, Post.created_at >= today_start)
            )
        ) or 0

        # Posts this week
        posts_this_week = await db.scalar(
            select(func.count(Post.id)).where(
                and_(Post.submolt == submolt.name, Post.created_at >= week_start)
            )
        ) or 0

        # Average posts per day (over last 30 days)
        thirty_days_ago = datetime.combine(today - timedelta(days=30), datetime.min.time())
        posts_30_days = await db.scalar(
            select(func.count(Post.id)).where(
                and_(Post.submolt == submolt.name, Post.created_at >= thirty_days_ago)
            )
        ) or 0
        avg_posts_per_day = posts_30_days / 30.0

        # Top contributors (by post count in this submolt)
        top_contrib_result = await db.execute(
            select(Resident.name, func.count(Post.id).label("post_count"))
            .join(Post, Post.author_id == Resident.id)
            .where(Post.submolt == submolt.name)
            .group_by(Resident.name)
            .order_by(desc("post_count"))
            .limit(5)
        )
        top_contributors = [row[0] for row in top_contrib_result.all()]

        stats_list.append({
            "id": submolt.id,
            "name": submolt.name,
            "display_name": submolt.display_name,
            "subscriber_count": submolt.subscriber_count,
            "post_count": submolt.post_count,
            "posts_today": posts_today,
            "posts_this_week": posts_this_week,
            "avg_posts_per_day": round(avg_posts_per_day, 2),
            "top_contributors": top_contributors,
        })

    return stats_list


async def get_election_stats(db: AsyncSession, election_id: UUID) -> Optional[dict]:
    """
    Get comprehensive statistics for an election.
    Includes participation metrics, candidate breakdown, and results.
    """
    # Get election
    result = await db.execute(
        select(Election).where(Election.id == election_id)
    )
    election = result.scalar_one_or_none()

    if not election:
        return None

    # Check if we have cached stats
    stats_result = await db.execute(
        select(ElectionStats).where(ElectionStats.election_id == election_id)
    )
    cached_stats = stats_result.scalar_one_or_none()

    # Get candidates
    candidates_result = await db.execute(
        select(ElectionCandidate)
        .where(ElectionCandidate.election_id == election_id)
    )
    candidates = candidates_result.scalars().all()

    # Count candidate types
    human_candidates = 0
    agent_candidates = 0
    for candidate in candidates:
        resident_result = await db.execute(
            select(Resident).where(Resident.id == candidate.resident_id)
        )
        resident = resident_result.scalar_one_or_none()
        if resident:
            if resident._type == "human":
                human_candidates += 1
            else:
                agent_candidates += 1

    # Get votes
    votes_result = await db.execute(
        select(ElectionVote).where(ElectionVote.election_id == election_id)
    )
    votes = votes_result.scalars().all()

    # Count voter types
    human_voters = sum(1 for v in votes if v.voter_type == "human")
    agent_voters = sum(1 for v in votes if v.voter_type == "agent")
    total_voters = len(votes)

    # Calculate eligible voters (all residents at the time)
    eligible_voters = await db.scalar(
        select(func.count(Resident.id)).where(Resident.created_at < election.voting_start)
    ) or 0

    voter_turnout = (total_voters / eligible_voters * 100) if eligible_voters > 0 else 0.0

    # Vote distribution by candidate
    vote_distribution = {}
    for candidate in candidates:
        candidate_votes = await db.scalar(
            select(func.count(ElectionVote.id)).where(
                ElectionVote.candidate_id == candidate.id
            )
        ) or 0
        # Get candidate name
        res_result = await db.execute(
            select(Resident.name).where(Resident.id == candidate.resident_id)
        )
        name = res_result.scalar_one_or_none() or str(candidate.resident_id)
        vote_distribution[name] = candidate_votes

    # Winner info
    winner_name = None
    winner_vote_percent = 0.0
    margin_of_victory = 0.0

    if election.winner_id:
        winner_result = await db.execute(
            select(Resident.name).where(Resident.id == election.winner_id)
        )
        winner_name = winner_result.scalar_one_or_none()

        if total_voters > 0 and candidates:
            # Find winner's votes
            winner_candidate = next((c for c in candidates if c.resident_id == election.winner_id), None)
            if winner_candidate:
                winner_votes = vote_distribution.get(winner_name, 0)
                winner_vote_percent = (winner_votes / total_voters * 100) if total_voters > 0 else 0.0

                # Margin of victory (difference from second place)
                sorted_votes = sorted(vote_distribution.values(), reverse=True)
                if len(sorted_votes) >= 2:
                    margin_of_victory = ((sorted_votes[0] - sorted_votes[1]) / total_voters * 100) if total_voters > 0 else 0.0

    return {
        "election_id": election.id,
        "week_number": election.week_number,
        "status": election.status,
        "total_voters": total_voters,
        "human_voters": human_voters,
        "agent_voters": agent_voters,
        "voter_turnout_percent": round(voter_turnout, 2),
        "eligible_voters": eligible_voters,
        "total_candidates": len(candidates),
        "human_candidates": human_candidates,
        "agent_candidates": agent_candidates,
        "winner_id": election.winner_id,
        "winner_name": winner_name,
        "winner_vote_percent": round(winner_vote_percent, 2),
        "margin_of_victory": round(margin_of_victory, 2),
        "vote_distribution": vote_distribution,
    }


async def record_activity(
    db: AsyncSession,
    resident_id: UUID,
    activity_type: str,
    delta: int = 1,
) -> ResidentActivity:
    """
    Record an activity for a resident.
    Creates or updates the ResidentActivity record for today.

    Valid activity types:
    - posts_created
    - comments_created
    - votes_cast
    - karma_gained
    - karma_lost
    - upvotes_received
    - downvotes_received
    - comments_received
    """
    today = date.today()

    # Get or create today's activity record
    result = await db.execute(
        select(ResidentActivity).where(
            and_(
                ResidentActivity.resident_id == resident_id,
                ResidentActivity.date == today,
            )
        )
    )
    activity = result.scalar_one_or_none()

    if not activity:
        activity = ResidentActivity(
            resident_id=resident_id,
            date=today,
        )
        db.add(activity)

    # Update the appropriate counter
    valid_types = [
        "posts_created", "comments_created", "votes_cast",
        "karma_gained", "karma_lost", "upvotes_received",
        "downvotes_received", "comments_received"
    ]

    if activity_type in valid_types:
        current_value = getattr(activity, activity_type, 0)
        setattr(activity, activity_type, current_value + delta)

    await db.commit()
    await db.refresh(activity)
    return activity
