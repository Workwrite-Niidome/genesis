import logging

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.god_ai import god_ai_manager
from app.core.ai_manager import ai_manager
from app.core.history_manager import history_manager
from app.models.ai import AI
from app.models.concept import Concept
from app.models.tick import Tick

logger = logging.getLogger(__name__)


class WorldEngine:
    """Central orchestrator for the GENESIS world."""

    def __init__(self):
        self.is_running = False

    def _read_redis_state(self) -> tuple[float, bool]:
        """Read time_speed and is_paused from Redis."""
        try:
            import redis
            r = redis.from_url(settings.REDIS_URL)
            speed_raw = r.get("genesis:time_speed")
            paused_raw = r.get("genesis:is_paused")
            time_speed = float(speed_raw.decode()) if speed_raw else 1.0
            is_paused = paused_raw.decode() == "1" if paused_raw else False
            return time_speed, is_paused
        except Exception:
            return 1.0, False

    async def get_world_state(self, db: AsyncSession) -> dict:
        ai_count_result = await db.execute(
            select(func.count()).select_from(AI).where(AI.is_alive == True)
        )
        ai_count = ai_count_result.scalar()

        concept_count_result = await db.execute(
            select(func.count()).select_from(Concept)
        )
        concept_count = concept_count_result.scalar()

        tick_number = await history_manager.get_latest_tick_number(db)

        god = await god_ai_manager.get_or_create(db)

        time_speed, is_paused = self._read_redis_state()

        return {
            "tick_number": tick_number,
            "ai_count": ai_count,
            "concept_count": concept_count,
            "is_running": self.is_running,
            "time_speed": time_speed,
            "is_paused": is_paused,
            "god_ai_active": god.is_active,
            "god_ai_phase": god.state.get("phase", "unknown"),
        }

    async def get_world_stats(self, db: AsyncSession) -> dict:
        ai_alive_result = await db.execute(
            select(func.count()).select_from(AI).where(AI.is_alive == True)
        )
        ai_total_result = await db.execute(select(func.count()).select_from(AI))

        concept_result = await db.execute(select(func.count()).select_from(Concept))

        from app.models.interaction import Interaction
        from app.models.event import Event

        interaction_result = await db.execute(
            select(func.count()).select_from(Interaction)
        )
        event_result = await db.execute(select(func.count()).select_from(Event))

        tick_number = await history_manager.get_latest_tick_number(db)

        return {
            "total_ticks": tick_number,
            "total_ais_born": ai_total_result.scalar(),
            "total_ais_alive": ai_alive_result.scalar(),
            "total_concepts": concept_result.scalar(),
            "total_interactions": interaction_result.scalar(),
            "total_events": event_result.scalar(),
        }


world_engine = WorldEngine()
