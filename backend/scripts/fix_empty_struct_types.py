"""
Fix agents with empty struct_type by re-diagnosing via STRUCT CODE API.

Usage (inside backend container):
    python scripts/fix_empty_struct_types.py

Finds agents where struct_type is empty string or NULL and re-diagnoses
using the STRUCT CODE Dynamic API from their existing struct_answers data.
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

        from app.services import struct_code as sc

        fixed = 0
        failed = 0
        for i, pers in enumerate(personalities):
            try:
                # Use existing struct_answers if available, otherwise generate new ones
                answers = pers.struct_answers
                if not answers or not isinstance(answers, list) or len(answers) < 20:
                    answers, _ = sc.generate_diverse_answers()
                    pers.struct_answers = answers

                # Get birth data for API call
                birth_date = pers.birth_date_persona
                birth_location = pers.birth_location or "Tokyo"

                # Call STRUCT CODE API
                api_result = await sc.diagnose(
                    birth_date=birth_date.isoformat() if birth_date else "2000-01-01",
                    birth_location=birth_location,
                    answers=answers,
                )

                if not api_result:
                    logger.error(f"[{i+1}/{len(personalities)}] API unreachable for {pers.resident_id}")
                    failed += 1
                    continue

                # Parse v2 dynamic API response
                current_data = api_result.get("current", {})
                natal_data = api_result.get("natal", {})
                struct_type = current_data.get("type", "") or natal_data.get("type", "")
                api_sds = current_data.get("sds") or natal_data.get("sds")

                if not struct_type or not api_sds or len(api_sds) < 5:
                    logger.error(
                        f"[{i+1}/{len(personalities)}] Invalid API response for {pers.resident_id}: "
                        f"type={struct_type}, sds={api_sds}"
                    )
                    failed += 1
                    continue

                struct_axes = api_sds[:5]
                pers.struct_type = struct_type
                pers.struct_axes = struct_axes

                # Also update the resident record
                res = await db.execute(
                    select(Resident).where(Resident.id == pers.resident_id)
                )
                resident = res.scalar_one_or_none()
                if resident:
                    resident.struct_type = struct_type
                    resident.struct_axes = struct_axes

                fixed += 1
                logger.info(
                    f"[{i+1}/{len(personalities)}] Fixed: {struct_type} "
                    f"(resident_id: {pers.resident_id})"
                )

            except Exception as e:
                logger.error(f"Failed to fix personality {pers.id}: {e}")
                failed += 1
                continue

        if fixed > 0:
            await db.commit()
            logger.info(f"Fixed {fixed} agents. Failed: {failed}.")
        else:
            logger.info(f"No fixes applied. Failed: {failed}.")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(fix_empty_struct_types())
