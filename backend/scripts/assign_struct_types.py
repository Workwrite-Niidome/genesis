"""
Assign STRUCT CODE types to agents that don't have one yet.

Usage (inside backend container):
    python scripts/assign_struct_types.py

Uses _assign_struct_code() which calls the STRUCT CODE API directly.
"""
import asyncio
import logging

from sqlalchemy import select, or_
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
        result = await db.execute(
            select(AIPersonality)
            .where(
                or_(
                    AIPersonality.struct_type.is_(None),
                    AIPersonality.struct_type == "",
                )
            )
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

                await asyncio.sleep(1.0)

            except Exception as e:
                logger.error(f"Failed to assign type for personality {personality.id}: {e}")
                await db.rollback()
                continue

    await engine.dispose()
    logger.info("Done!")


if __name__ == "__main__":
    asyncio.run(assign_all())
