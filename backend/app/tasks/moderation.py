"""
Celery task for periodic content moderation.
Runs once per hour to review recent content using Claude API.
"""
import asyncio
from app.celery_app import celery_app


def run_async(coro):
    """Helper to run async code in Celery tasks"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(name='app.tasks.moderation.run_content_moderation_task')
def run_content_moderation_task():
    """
    Hourly content moderation sweep.
    Scans recent posts/comments and sends to Claude API for review.
    Auto-bans for severe violations (hate speech, discrimination).
    """
    from app.services.content_moderation import moderate_recent_content
    from app.config import get_settings
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

    settings = get_settings()

    async def _run():
        engine = create_async_engine(settings.database_url, pool_pre_ping=True)
        async with AsyncSession(engine) as db:
            result = await moderate_recent_content(db)
        await engine.dispose()
        return result

    return run_async(_run())
