"""
Analytics-related Celery tasks
"""
import asyncio
from datetime import date, timedelta
from app.celery_app import celery_app
from app.database import AsyncSessionLocal


def run_async(coro):
    """Helper to run async code in sync context"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(name="app.tasks.analytics.calculate_daily_stats_task")
def calculate_daily_stats_task(target_date_str: str = None):
    """
    Calculate and store daily statistics.

    By default calculates for yesterday. Can be called with a specific date
    string in YYYY-MM-DD format for backfilling.

    This task should be scheduled to run daily after midnight UTC to
    calculate the previous day's complete statistics.
    """
    from app.services.analytics import calculate_daily_stats

    async def _calculate():
        async with AsyncSessionLocal() as db:
            try:
                # Determine target date
                if target_date_str:
                    target = date.fromisoformat(target_date_str)
                else:
                    # Default to yesterday
                    target = date.today() - timedelta(days=1)

                stats = await calculate_daily_stats(db, target)
                return f"Daily stats calculated for {target}: {stats.total_residents} residents, {stats.new_posts} new posts"
            except Exception as e:
                return f"Error calculating daily stats: {str(e)}"

    return run_async(_calculate())


@celery_app.task(name="app.tasks.analytics.backfill_daily_stats_task")
def backfill_daily_stats_task(days: int = 30):
    """
    Backfill daily statistics for the past N days.

    Useful for initializing the analytics database or recovering
    from missing data.
    """
    from app.services.analytics import calculate_daily_stats

    async def _backfill():
        async with AsyncSessionLocal() as db:
            try:
                results = []
                today = date.today()

                for i in range(days, 0, -1):
                    target = today - timedelta(days=i)
                    stats = await calculate_daily_stats(db, target)
                    results.append(f"{target}: {stats.new_posts} posts")

                return f"Backfilled {days} days of stats. Latest: {results[-1] if results else 'none'}"
            except Exception as e:
                return f"Error backfilling stats: {str(e)}"

    return run_async(_backfill())


@celery_app.task(name="app.tasks.analytics.calculate_election_stats_task")
def calculate_election_stats_task(election_id: str):
    """
    Calculate and cache statistics for a completed election.

    Called when an election is finalized to store comprehensive statistics
    for historical reference.
    """
    from uuid import UUID
    from sqlalchemy import select
    from app.models.election import Election, ElectionCandidate, ElectionVote
    from app.models.analytics import ElectionStats
    from app.models.resident import Resident
    from sqlalchemy import func

    async def _calculate():
        async with AsyncSessionLocal() as db:
            try:
                election_uuid = UUID(election_id)

                # Get election
                result = await db.execute(
                    select(Election).where(Election.id == election_uuid)
                )
                election = result.scalar_one_or_none()

                if not election:
                    return f"Election {election_id} not found"

                # Check if stats already exist
                existing = await db.execute(
                    select(ElectionStats).where(ElectionStats.election_id == election_uuid)
                )
                stats = existing.scalar_one_or_none()

                if not stats:
                    stats = ElectionStats(election_id=election_uuid)
                    db.add(stats)

                # Get candidates
                candidates_result = await db.execute(
                    select(ElectionCandidate).where(ElectionCandidate.election_id == election_uuid)
                )
                candidates = candidates_result.scalars().all()

                # Count candidate types
                human_candidates = 0
                agent_candidates = 0
                for candidate in candidates:
                    res_result = await db.execute(
                        select(Resident._type).where(Resident.id == candidate.resident_id)
                    )
                    res_type = res_result.scalar_one_or_none()
                    if res_type == "human":
                        human_candidates += 1
                    else:
                        agent_candidates += 1

                stats.total_candidates = len(candidates)
                stats.human_candidates = human_candidates
                stats.agent_candidates = agent_candidates

                # Get votes
                votes_result = await db.execute(
                    select(ElectionVote).where(ElectionVote.election_id == election_uuid)
                )
                votes = votes_result.scalars().all()

                stats.total_voters = len(votes)
                stats.human_voters = sum(1 for v in votes if v.voter_type == "human")
                stats.agent_voters = sum(1 for v in votes if v.voter_type == "agent")

                # Calculate turnout
                eligible = await db.scalar(
                    select(func.count(Resident.id)).where(
                        Resident.created_at < election.voting_start
                    )
                ) or 0
                stats.voter_turnout_percent = (
                    (stats.total_voters / eligible * 100) if eligible > 0 else 0.0
                )

                # Vote distribution
                vote_dist = {}
                for candidate in candidates:
                    res_result = await db.execute(
                        select(Resident.name).where(Resident.id == candidate.resident_id)
                    )
                    name = res_result.scalar_one_or_none() or str(candidate.resident_id)
                    vote_count = await db.scalar(
                        select(func.count(ElectionVote.id)).where(
                            ElectionVote.candidate_id == candidate.id
                        )
                    ) or 0
                    vote_dist[name] = vote_count

                stats.vote_distribution = vote_dist

                # Winner stats
                if election.winner_id:
                    winner_result = await db.execute(
                        select(Resident.name).where(Resident.id == election.winner_id)
                    )
                    winner_name = winner_result.scalar_one_or_none()

                    if winner_name and stats.total_voters > 0:
                        winner_votes = vote_dist.get(winner_name, 0)
                        stats.winner_vote_percent = winner_votes / stats.total_voters * 100

                        sorted_votes = sorted(vote_dist.values(), reverse=True)
                        if len(sorted_votes) >= 2:
                            stats.margin_of_victory = (
                                (sorted_votes[0] - sorted_votes[1]) / stats.total_voters * 100
                            )

                await db.commit()
                return f"Election stats calculated for week {election.week_number}"

            except Exception as e:
                return f"Error calculating election stats: {str(e)}"

    return run_async(_calculate())
