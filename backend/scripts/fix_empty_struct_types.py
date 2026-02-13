"""
Fix agents with empty struct_type by re-classifying from their struct_answers.

Usage (inside backend container):
    python scripts/fix_empty_struct_types.py

Finds agents where struct_type is empty string or NULL and re-classifies
using classify_locally() from their existing struct_answers data.
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


async def fix_empty_struct_types():
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)

    async with AsyncSession(engine) as db:
        # Find agents with empty or NULL struct_type
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
            logger.info("No agents with empty struct_type found. All good!")
            return

        logger.info(f"Found {len(personalities)} agents with empty struct_type.")

        from app.services.struct_code import classify_locally, generate_diverse_answers

        fixed = 0
        for i, pers in enumerate(personalities):
            try:
                # Use existing struct_answers if available, otherwise generate new ones
                answers = pers.struct_answers
                if not answers or not isinstance(answers, list) or len(answers) < 20:
                    answers, _ = generate_diverse_answers()
                    pers.struct_answers = answers

                local = classify_locally(answers)
                pers.struct_type = local["struct_type"]
                pers.struct_axes = local["axes"]

                # Also update the resident record
                res = await db.execute(
                    select(Resident).where(Resident.id == pers.resident_id)
                )
                resident = res.scalar_one_or_none()
                if resident:
                    resident.struct_type = local["struct_type"]
                    resident.struct_axes = local["axes"]

                fixed += 1
                logger.info(
                    f"[{i+1}/{len(personalities)}] Fixed: {local['struct_type']} "
                    f"(resident_id: {pers.resident_id})"
                )

            except Exception as e:
                logger.error(f"Failed to fix personality {pers.id}: {e}")
                continue

        if fixed > 0:
            await db.commit()
            logger.info(f"Fixed {fixed} agents with empty struct_type.")
        else:
            logger.info("No fixes needed.")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(fix_empty_struct_types())
