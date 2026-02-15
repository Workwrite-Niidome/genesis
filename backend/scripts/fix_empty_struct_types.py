"""
Re-diagnose ALL AI agents via STRUCT CODE API.

Usage (inside backend container):
    python scripts/fix_empty_struct_types.py

Calls the STRUCT CODE Dynamic API for every agent using their existing
struct_answers and birth data, then updates struct_type and struct_axes.
Includes retry with exponential backoff to handle API container restarts.
"""
import asyncio
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

from app.config import get_settings
from app.models.resident import Resident
from app.models.ai_personality import AIPersonality

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()

MAX_RETRIES = 3
BATCH_SIZE = 10
DELAY_BETWEEN_CALLS = 2.0
DELAY_BETWEEN_BATCHES = 10.0


async def diagnose_with_retry(sc, birth_date, birth_location, answers):
    """Call STRUCT CODE API with retry and exponential backoff."""
    for attempt in range(MAX_RETRIES):
        result = await sc.diagnose(
            birth_date=birth_date,
            birth_location=birth_location,
            answers=answers,
        )
        if result:
            return result
        wait = (attempt + 1) * 5
        logger.warning(f"API unreachable, retrying in {wait}s (attempt {attempt+1}/{MAX_RETRIES})")
        await asyncio.sleep(wait)
    return None


async def reassign_all():
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)

    async with AsyncSession(engine) as db:
        result = await db.execute(
            select(AIPersonality)
            .join(Resident, Resident.id == AIPersonality.resident_id)
            .where(Resident._type == 'agent')
        )
        personalities = result.scalars().all()

        if not personalities:
            logger.info("No agent personalities found.")
            return

        logger.info(f"Re-diagnosing {len(personalities)} agents via STRUCT CODE API.")

        from app.services import struct_code as sc

        fixed = 0
        failed = 0
        for i, pers in enumerate(personalities):
            try:
                answers = pers.struct_answers
                if not answers or not isinstance(answers, list) or len(answers) < 20:
                    answers, _ = sc.generate_diverse_answers()
                    pers.struct_answers = answers

                birth_date = pers.birth_date_persona
                birth_location = pers.birth_location or "Tokyo"

                api_result = await diagnose_with_retry(
                    sc,
                    birth_date=birth_date.isoformat() if birth_date else "2000-01-01",
                    birth_location=birth_location,
                    answers=answers,
                )

                if not api_result:
                    logger.error(f"[{i+1}/{len(personalities)}] API failed after retries: {pers.resident_id}")
                    failed += 1
                    continue

                current_data = api_result.get("current", {})
                natal_data = api_result.get("natal", {})
                struct_type = current_data.get("type", "") or natal_data.get("type", "")
                api_sds = current_data.get("sds") or natal_data.get("sds")

                if not struct_type or not api_sds or len(api_sds) < 5:
                    logger.error(f"[{i+1}/{len(personalities)}] Invalid response: {pers.resident_id}")
                    failed += 1
                    continue

                old_type = pers.struct_type or "(empty)"
                pers.struct_type = struct_type
                pers.struct_axes = api_sds[:5]

                res = await db.execute(
                    select(Resident).where(Resident.id == pers.resident_id)
                )
                resident = res.scalar_one_or_none()
                if resident:
                    resident.struct_type = struct_type
                    resident.struct_axes = api_sds[:5]

                fixed += 1
                logger.info(
                    f"[{i+1}/{len(personalities)}] {old_type} -> {struct_type} "
                    f"(resident_id: {pers.resident_id})"
                )

                await asyncio.sleep(DELAY_BETWEEN_CALLS)

                # Batch pause to let API container breathe
                if (i + 1) % BATCH_SIZE == 0:
                    logger.info(f"Batch pause ({DELAY_BETWEEN_BATCHES}s)...")
                    # Commit progress so far
                    if fixed > 0:
                        await db.commit()
                    await asyncio.sleep(DELAY_BETWEEN_BATCHES)

            except Exception as e:
                logger.error(f"Failed for personality {pers.id}: {e}")
                failed += 1
                continue

        if fixed > 0:
            await db.commit()
        logger.info(f"Done. Re-diagnosed: {fixed}, Failed: {failed}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(reassign_all())
