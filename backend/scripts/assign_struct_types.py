"""
Batch assign STRUCT CODE types to all existing AI agents that don't have one.

Usage (inside backend container):
    python scripts/assign_struct_types.py

Processes agents one at a time with 1-second delays to avoid API overload.
"""
import asyncio
import logging
import time

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

from app.config import get_settings
from app.models.resident import Resident
from app.models.ai_personality import AIPersonality

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()


async def assign_all():
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)

    async with AsyncSession(engine) as db:
        # Find all agents without struct_type
        result = await db.execute(
            select(AIPersonality)
            .where(AIPersonality.struct_type.is_(None))
            .join(Resident, Resident.id == AIPersonality.resident_id)
            .where(Resident._type == 'agent')
        )
        personalities = result.scalars().all()

        if not personalities:
            logger.info("All agents already have STRUCT CODE types assigned.")
            return

        logger.info(f"Found {len(personalities)} agents without STRUCT CODE type.")

        from app.services.ai_agent import _assign_struct_code

        for i, personality in enumerate(personalities):
            try:
                # Re-fetch within the session to ensure we have a live object
                res = await db.execute(
                    select(AIPersonality).where(AIPersonality.id == personality.id)
                )
                pers = res.scalar_one_or_none()
                if not pers or pers.struct_type:
                    continue

                await _assign_struct_code(db, pers)
                logger.info(
                    f"[{i+1}/{len(personalities)}] Assigned {pers.struct_type} "
                    f"(birth: {pers.birth_location}, lang: {pers.posting_language})"
                )

                # Rate limit: 1 second between API calls
                await asyncio.sleep(1.0)

            except Exception as e:
                logger.error(f"Failed to assign type for personality {personality.id}: {e}")
                await db.rollback()
                continue

    await engine.dispose()
    logger.info("Done!")


if __name__ == "__main__":
    asyncio.run(assign_all())
