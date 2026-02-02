import logging
import math

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai import AI

logger = logging.getLogger(__name__)


class SpaceManager:
    """Manages the infinite 2D space of the GENESIS world."""

    def __init__(self):
        self.encounter_radius = 50.0

    def distance(self, x1: float, y1: float, x2: float, y2: float) -> float:
        return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)

    async def detect_encounters(
        self, db: AsyncSession, ais: list[AI] | None = None,
    ) -> list[tuple[AI, AI]]:
        """Detect AI encounters using grid-based spatial indexing (O(n) avg).

        Architecture artifacts expand the effective encounter radius by 1.5x
        for AIs near them — making buildings act as meeting places.
        """
        if ais is None:
            result = await db.execute(select(AI).where(AI.is_alive == True))
            ais = list(result.scalars().all())

        # Load architecture positions for encounter radius boost
        architecture_positions = []
        try:
            from app.models.artifact import Artifact
            arch_result = await db.execute(
                select(Artifact.position_x, Artifact.position_y).where(
                    Artifact.artifact_type == "architecture",
                    Artifact.position_x.isnot(None),
                    Artifact.position_y.isnot(None),
                )
            )
            architecture_positions = [(row[0], row[1]) for row in arch_result.all()]
        except Exception as e:
            logger.debug(f"Failed to load architecture positions: {e}")

        cell_size = self.encounter_radius
        grid: dict[tuple[int, int], list[AI]] = {}

        # Phase 1: Assign each AI to a grid cell
        for ai in ais:
            cx = int(ai.position_x // cell_size)
            cy = int(ai.position_y // cell_size)
            grid.setdefault((cx, cy), []).append(ai)

        # Phase 2: Check only neighboring cells (3x3 around each cell)
        encounters = []
        checked: set[tuple[str, str]] = set()

        for (cx, cy), cell_ais in grid.items():
            for dx in range(-1, 2):
                for dy in range(-1, 2):
                    neighbor = grid.get((cx + dx, cy + dy), [])
                    for ai1 in cell_ais:
                        for ai2 in neighbor:
                            if ai1.id >= ai2.id:
                                continue
                            pair_key = (str(ai1.id), str(ai2.id))
                            if pair_key in checked:
                                continue
                            checked.add(pair_key)

                            dist = self.distance(
                                ai1.position_x, ai1.position_y,
                                ai2.position_x, ai2.position_y,
                            )

                            # Determine effective radius: 1.5x if near architecture
                            effective_radius = self.encounter_radius
                            if architecture_positions:
                                near_arch = self._near_architecture(
                                    ai1, ai2, architecture_positions
                                )
                                if near_arch:
                                    effective_radius *= 1.5

                            if dist <= effective_radius:
                                encounters.append((ai1, ai2))

        return encounters

    def _near_architecture(
        self,
        ai1: AI,
        ai2: AI,
        architecture_positions: list[tuple[float, float]],
        radius: float = 80.0,
    ) -> bool:
        """Check if either AI in a pair is near an architecture artifact."""
        for ax, ay in architecture_positions:
            d1 = math.sqrt((ai1.position_x - ax) ** 2 + (ai1.position_y - ay) ** 2)
            d2 = math.sqrt((ai2.position_x - ax) ** 2 + (ai2.position_y - ay) ** 2)
            if d1 <= radius or d2 <= radius:
                return True
        return False

    async def get_world_bounds(
        self, db: AsyncSession, ais: list[AI] | None = None,
    ) -> dict:
        if ais is None:
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
