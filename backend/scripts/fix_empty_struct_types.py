"""
Re-diagnose AI agents via STRUCT CODE API.

Usage (inside backend container):
    python scripts/fix_empty_struct_types.py          # Only agents without struct_type
    python scripts/fix_empty_struct_types.py --all    # ALL agents

Handles struct-code container OOM by detecting failures and waiting
for Docker to restart the container before continuing.
"""
import asyncio
import argparse
import logging
import random

import httpx
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

from app.config import get_settings
from app.models.resident import Resident
from app.models.ai_personality import AIPersonality

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()

DELAY_BETWEEN_CALLS = 3.0
CONTAINER_RESTART_WAIT = 90


async def wait_for_api():
    """Wait until the STRUCT CODE API is responsive."""
    url = f"{settings.struct_code_url}/health"
    for attempt in range(10):
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    logger.info("STRUCT CODE API is ready.")
                    return True
        except Exception:
            pass
        wait = min(15 * (attempt + 1), CONTAINER_RESTART_WAIT)
        logger.warning(f"API not ready, waiting {wait}s (attempt {attempt+1}/10)")
        await asyncio.sleep(wait)
    return False


async def diagnose_one(sc, pers):
    """Diagnose a single agent. Returns (struct_type, axes) or None."""
    answers = pers.struct_answers
    if not answers or not isinstance(answers, list) or len(answers) < 20:
        answers, _ = sc.generate_diverse_answers()
        pers.struct_answers = answers

    birth_date = pers.birth_date_persona
    birth_location = pers.birth_location or "Tokyo"

    result = await sc.diagnose(
        birth_date=birth_date.isoformat() if birth_date else "2000-01-01",
        birth_location=birth_location,
        answers=answers,
    )
    if not result:
        return None

    current_data = result.get("current", {})
    natal_data = result.get("natal", {})
    struct_type = current_data.get("type", "") or natal_data.get("type", "")
    api_sds = current_data.get("sds") or natal_data.get("sds")

    if not struct_type or not api_sds or len(api_sds) < 5:
        return None

    return struct_type, api_sds[:5]


async def reassign(process_all: bool = False):
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)

    async with AsyncSession(engine, expire_on_commit=False) as db:
        query = (
            select(AIPersonality)
            .join(Resident, Resident.id == AIPersonality.resident_id)
            .where(Resident._type == 'agent')
        )
        if not process_all:
            query = query.where(
                or_(
                    AIPersonality.struct_type.is_(None),
                    AIPersonality.struct_type == "",
                )
            )

        result = await db.execute(query)
        personalities = result.scalars().all()

        if not personalities:
            logger.info("No agents to process.")
            return

        # Shuffle so each run processes different agents first
        personalities = list(personalities)
        random.shuffle(personalities)

        mode = "ALL" if process_all else "empty-only"
        logger.info(f"Processing {len(personalities)} agents ({mode}).")

        # Wait for API before starting
        if not await wait_for_api():
            logger.error("STRUCT CODE API never became ready. Aborting.")
            return

        from app.services import struct_code as sc

        fixed = 0
        failed = 0
        consecutive_failures = 0

        for i, pers in enumerate(personalities):
            try:
                diagnosis = await diagnose_one(sc, pers)

                if diagnosis is None:
                    consecutive_failures += 1
                    failed += 1
                    logger.error(f"[{i+1}/{len(personalities)}] Failed: {pers.resident_id}")

                    if consecutive_failures >= 2:
                        logger.warning(
                            f"API appears down. Waiting {CONTAINER_RESTART_WAIT}s "
                            f"for container restart..."
                        )
                        await asyncio.sleep(CONTAINER_RESTART_WAIT)
                        if not await wait_for_api():
                            logger.error("API did not recover. Saving progress and aborting.")
                            break
                        consecutive_failures = 0
                    continue

                consecutive_failures = 0
                struct_type, struct_axes = diagnosis

                old_type = pers.struct_type or "(empty)"
                pers.struct_type = struct_type
                pers.struct_axes = struct_axes

                res = await db.execute(
                    select(Resident).where(Resident.id == pers.resident_id)
                )
                resident = res.scalar_one_or_none()
                if resident:
                    resident.struct_type = struct_type
                    resident.struct_axes = struct_axes

                fixed += 1
                # Commit immediately so progress isn't lost on timeout/kill
                await db.commit()
                logger.info(
                    f"[{i+1}/{len(personalities)}] {old_type} -> {struct_type} "
                    f"(resident_id: {pers.resident_id})"
                )

                await asyncio.sleep(DELAY_BETWEEN_CALLS)

            except Exception as e:
                logger.error(f"Exception for {pers.id}: {e}")
                failed += 1
                continue

        logger.info(f"Done. Fixed: {fixed}, Failed: {failed}")

    await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--all", action="store_true", help="Re-diagnose ALL agents")
    args = parser.parse_args()
    asyncio.run(reassign(process_all=args.all))
