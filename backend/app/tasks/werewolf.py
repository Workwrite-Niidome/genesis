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
    from sqlalchemy import select
    from app.config import get_settings
    from app.services.werewolf_game import check_phase_transition
    from app.models.werewolf_game import WerewolfGame

    settings = get_settings()
    _engine = create_async_engine(settings.database_url, pool_pre_ping=True)

    async with _AsyncSession(_engine) as db:
        try:
            # Capture active game IDs before transition (game may become 'finished')
            active_res = await db.execute(
                select(WerewolfGame.id).where(
                    WerewolfGame.status.in_(["day", "night"])
                )
            )
            active_ids = [str(gid) for (gid,) in active_res.all()]

            result = await check_phase_transition(db)
            if result:
                logger.info(f"Phantom Night phase transition: {result}")
            await db.commit()

            # Notify WebSocket clients after commit
            if result and active_ids:
                try:
                    from app.services.ws_manager import publish
                    for gid in active_ids:
                        publish(gid, 'game')
                        publish(gid, 'events')
                        publish(gid, 'players')
                except Exception:
                    pass
        except Exception as e:
            logger.error(f"Phase transition error: {e}")
            await db.rollback()

    await _engine.dispose()


@celery_app.task(name='app.tasks.werewolf.werewolf_agent_actions_task')
def werewolf_agent_actions_task():
    """
    Dedicated werewolf agent cycle — runs every 60 seconds.
    More frequent than the general 5-min agent cycle so AI agents
    reliably participate in fast games (casual = 18-min phases).
    """
    from app.services.agent_runner import run_werewolf_agent_cycle
    run_async(run_werewolf_agent_cycle())


@celery_app.task(name='app.tasks.werewolf.auto_create_game_task')
def auto_create_game_task():
    """
    Lobby system replaced auto-create.
    This task is kept for backward compatibility but is now a no-op.
    Games are created manually via the lobby system.
    """
    logger.debug("auto_create_game_task: no-op (lobby system active)")
