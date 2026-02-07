"""
Karma decay Celery task - runs every 6 hours (4x/day)
"""
import asyncio
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


@celery_app.task(name="app.tasks.karma.apply_karma_decay_task")
def apply_karma_decay_task():
    """
    Periodic task to apply karma decay to all non-eliminated residents.
    Runs every 6 hours (4x/day).
    k_decay is the daily rate, so each run applies k_decay / 4.
    """
    from sqlalchemy import select
    from app.models.resident import Resident
    from app.utils.karma import get_active_god_params, clamp_karma
    from app.services.elimination import check_and_eliminate

    async def _decay():
        async with AsyncSessionLocal() as db:
            try:
                params = await get_active_god_params(db)
                per_run_decay = params['k_decay'] / 4.0

                if per_run_decay <= 0:
                    return "Decay rate is 0, skipping"

                # Get all non-eliminated residents
                result = await db.execute(
                    select(Resident).where(Resident.is_eliminated == False)
                )
                residents = result.scalars().all()

                eliminated_count = 0
                for resident in residents:
                    resident.karma -= int(round(per_run_decay))
                    clamp_karma(resident)

                    if await check_and_eliminate(resident, db):
                        eliminated_count += 1

                await db.commit()
                return (
                    f"Decay applied: -{per_run_decay:.1f} to {len(residents)} residents. "
                    f"{eliminated_count} eliminated."
                )
            except Exception as e:
                return f"Error: {str(e)}"

    return run_async(_decay())
