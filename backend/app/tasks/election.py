"""
Election-related Celery tasks
"""
import asyncio
from app.celery_app import celery_app
from app.database import AsyncSessionLocal
from app.services.election import (
    update_election_status,
    check_and_expire_rules,
    get_or_create_current_election,
)


def run_async(coro):
    """Helper to run async code in sync context"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(name="app.tasks.election.update_election_status_task")
def update_election_status_task():
    """
    Periodic task to check and update election status.
    Runs every minute to ensure timely transitions:
    - nomination -> voting (Friday 00:00 UTC)
    - voting -> completed (Sunday 00:00 UTC)
    """
    async def _update():
        async with AsyncSessionLocal() as db:
            try:
                # Ensure current election exists
                await get_or_create_current_election(db)

                # Update status if needed
                election = await update_election_status(db)
                if election:
                    return f"Election week {election.week_number} status updated to: {election.status}"
                return "No status change needed"
            except Exception as e:
                return f"Error: {str(e)}"

    return run_async(_update())


@celery_app.task(name="app.tasks.election.expire_old_rules_task")
def expire_old_rules_task():
    """
    Periodic task to expire rules older than 1 week.
    Runs every hour.
    """
    async def _expire():
        async with AsyncSessionLocal() as db:
            try:
                await check_and_expire_rules(db)
                return "Rules expiration check completed"
            except Exception as e:
                return f"Error: {str(e)}"

    return run_async(_expire())


@celery_app.task(name="app.tasks.election.finalize_election_task")
def finalize_election_task(election_id: str):
    """
    Task to finalize an election and inaugurate the new God.
    Called when voting period ends.
    """
    from uuid import UUID
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    from app.models.election import Election
    from app.services.election import finalize_election

    async def _finalize():
        async with AsyncSessionLocal() as db:
            try:
                result = await db.execute(
                    select(Election)
                    .options(selectinload(Election.candidates))
                    .where(Election.id == UUID(election_id))
                )
                election = result.scalar_one_or_none()

                if not election:
                    return f"Election {election_id} not found"

                if election.status == "completed":
                    return f"Election {election_id} already completed"

                await finalize_election(db, election)
                return f"Election week {election.week_number} finalized. Winner: {election.winner_id}"
            except Exception as e:
                return f"Error: {str(e)}"

    return run_async(_finalize())


@celery_app.task(name="app.tasks.election.create_next_election_task")
def create_next_election_task():
    """
    Task to create the next week's election.
    Called after current election is finalized.
    """
    from app.services.election import create_election, get_current_week_number

    async def _create():
        async with AsyncSessionLocal() as db:
            try:
                next_week = get_current_week_number() + 1
                election = await create_election(db, next_week)
                return f"Created election for week {election.week_number}"
            except Exception as e:
                return f"Error: {str(e)}"

    return run_async(_create())
