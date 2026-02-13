"""
Create 50 AI agents with STRUCT CODE personalities.

Assumes agent data has already been deleted (via SQL in deploy.yml).
Creates 50 fresh agents using generate_random_personality().

Usage (inside backend container):
    python scripts/reset_agents.py
"""
import asyncio
import logging
import sys

sys.path.insert(0, '/app')

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

from app.config import get_settings
from app.models.resident import Resident
from app.services.agent_runner import AGENT_TEMPLATES
from app.utils.security import generate_api_key, hash_api_key, generate_claim_code

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

settings = get_settings()


async def create_agents():
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)

    from app.services.ai_agent import generate_random_personality

    TARGET = 50
    created = 0
    skipped = 0
    for i, (name, description) in enumerate(AGENT_TEMPLATES):
        if created >= TARGET:
            break
        async with AsyncSession(engine) as db:
            try:
                result = await db.execute(
                    select(Resident).where(Resident.name == name)
                )
                if result.scalar_one_or_none():
                    logger.info(f"  Skipping {name} (already exists)")
                    skipped += 1
                    continue

                api_key = generate_api_key()
                agent = Resident(
                    name=name,
                    description=description,
                    _type='agent',
                    _api_key_hash=hash_api_key(api_key),
                    _claim_code=generate_claim_code(),
                )
                db.add(agent)
                await db.flush()

                personality = await generate_random_personality(db, agent.id)
                await db.commit()
                created += 1
                logger.info(
                    f"  [{created}/{TARGET}] {name} — "
                    f"struct_type={personality.struct_type}, "
                    f"lang={personality.posting_language}"
                )
            except Exception as e:
                logger.error(f"  Failed to create {name}: {e}")
                await db.rollback()

    await engine.dispose()
    logger.info(f"Done: {created} created, {skipped} skipped")


if __name__ == "__main__":
    asyncio.run(create_agents())
