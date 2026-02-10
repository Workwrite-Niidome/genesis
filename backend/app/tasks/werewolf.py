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
    Auto-create a new game after cooldown period.
    Runs every 15 minutes.
    """
    run_async(_auto_create_game())


async def _auto_create_game():
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession as _AsyncSession
    from app.config import get_settings
    from app.services.werewolf_game import maybe_create_new_game

    settings = get_settings()
    _engine = create_async_engine(settings.database_url, pool_pre_ping=True)

    async with _AsyncSession(_engine) as db:
        try:
            game = await maybe_create_new_game(db)
            if game:
                logger.info(f"Auto-created Phantom Night Game #{game.game_number}")
            await db.commit()
        except Exception as e:
            logger.error(f"Auto-create game error: {e}")
            await db.rollback()

    await _engine.dispose()
