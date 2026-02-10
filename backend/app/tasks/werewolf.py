"""
Celery tasks for Phantom Night (werewolf game)

- Phase transition check (every 60s)
- Auto game creation (every 15min)
"""
import asyncio
import logging
from app.celery_app import celery_app

logger = logging.getLogger(__name__)


def run_async(coro):
    """Helper to run async code in Celery tasks"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(name='app.tasks.werewolf.check_phase_transition_task')
def check_phase_transition_task():
    """
    Check if the current game phase has expired and transition if needed.
    Runs every 60 seconds.
    """
    run_async(_check_phase_transition())


async def _check_phase_transition():
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession as _AsyncSession
    from app.config import get_settings
    from app.services.werewolf_game import check_phase_transition

    settings = get_settings()
    _engine = create_async_engine(settings.database_url, pool_pre_ping=True)

    async with _AsyncSession(_engine) as db:
        try:
            result = await check_phase_transition(db)
            if result:
                logger.info(f"Phantom Night phase transition: {result}")
            await db.commit()
        except Exception as e:
            logger.error(f"Phase transition error: {e}")
            await db.rollback()

    await _engine.dispose()


@celery_app.task(name='app.tasks.werewolf.auto_create_game_task')
def auto_create_game_task():
    """
    Lobby system replaced auto-create.
    This task is kept for backward compatibility but is now a no-op.
    Games are created manually via the lobby system.
    """
    logger.debug("auto_create_game_task: no-op (lobby system active)")
