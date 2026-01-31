import logging
import time

from app.core.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="app.core.tick_engine.process_tick")
def process_tick():
    """Process a single world tick. Called periodically by Celery Beat."""
    import asyncio
    asyncio.run(_process_tick_async())


async def _process_tick_async():
    from app.db.database import async_session
    from app.core.history_manager import history_manager
    from app.core.ai_manager import ai_manager
    from app.core.space_manager import space_manager
    from app.models.ai import AI

    start_time = time.time()

    async with async_session() as db:
        tick_number = await history_manager.get_latest_tick_number(db) + 1

        ais = await ai_manager.get_all_alive(db)
        ai_count = len(ais)

        encounters = await space_manager.detect_encounters(db)

        from app.models.concept import Concept
        from sqlalchemy import select, func

        concept_count_result = await db.execute(select(func.count()).select_from(Concept))
        concept_count = concept_count_result.scalar()

        bounds = await space_manager.get_world_bounds(db)

        world_snapshot = {
            "bounds": bounds,
            "ai_positions": [
                {
                    "id": str(ai.id),
                    "x": ai.position_x,
                    "y": ai.position_y,
                }
                for ai in ais
            ],
            "encounter_count": len(encounters),
        }

        processing_time_ms = int((time.time() - start_time) * 1000)

        await history_manager.record_tick(
            db=db,
            tick_number=tick_number,
            world_snapshot=world_snapshot,
            ai_count=ai_count,
            concept_count=concept_count,
            events=[],
            processing_time_ms=processing_time_ms,
        )

        logger.debug(
            f"Tick {tick_number}: {ai_count} AIs, {concept_count} concepts, "
            f"{len(encounters)} encounters, {processing_time_ms}ms"
        )
