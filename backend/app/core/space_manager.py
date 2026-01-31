import logging
import math

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai import AI

logger = logging.getLogger(__name__)


class SpaceManager:
    """Manages the infinite 2D space of the GENESIS world."""

    def __init__(self):
        self.encounter_radius = 20.0

    def distance(self, x1: float, y1: float, x2: float, y2: float) -> float:
        return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)

    async def detect_encounters(self, db: AsyncSession) -> list[tuple[AI, AI]]:
        result = await db.execute(select(AI).where(AI.is_alive == True))
        ais = list(result.scalars().all())

        encounters = []
        checked = set()

        for i, ai1 in enumerate(ais):
            for j, ai2 in enumerate(ais):
                if i >= j:
                    continue
                pair_key = (min(str(ai1.id), str(ai2.id)), max(str(ai1.id), str(ai2.id)))
                if pair_key in checked:
                    continue
                checked.add(pair_key)

                dist = self.distance(
                    ai1.position_x, ai1.position_y,
                    ai2.position_x, ai2.position_y,
                )
                if dist <= self.encounter_radius:
                    encounters.append((ai1, ai2))

        return encounters

    async def get_world_bounds(self, db: AsyncSession) -> dict:
        result = await db.execute(select(AI).where(AI.is_alive == True))
        ais = list(result.scalars().all())

        if not ais:
            return {"min_x": -100, "max_x": 100, "min_y": -100, "max_y": 100}

        xs = [ai.position_x for ai in ais]
        ys = [ai.position_y for ai in ais]

        padding = 100
        return {
            "min_x": min(xs) - padding,
            "max_x": max(xs) + padding,
            "min_y": min(ys) - padding,
            "max_y": max(ys) + padding,
        }


space_manager = SpaceManager()
