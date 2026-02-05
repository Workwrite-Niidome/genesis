"""GENESIS v3 Event Log — event sourcing for every world state change.

Every action processed by the WorldServer is persisted as a WorldEvent.
This provides a full audit trail and enables replay, undo, analytics,
and AI memory formation from world history.
"""
import logging
import uuid

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.world import WorldEvent

logger = logging.getLogger(__name__)


class EventLog:
    """Append-only event store backed by the world_events table."""

    # -------------------------------------------------------------------
    # Write
    # -------------------------------------------------------------------

    async def append(
        self,
        db: AsyncSession,
        tick: int,
        actor_id: uuid.UUID | None,
        event_type: str,
        action: str,
        params: dict,
        result: str,
        reason: str | None = None,
        position: tuple[float, float, float] | None = None,
        importance: float = 0.5,
    ) -> WorldEvent:
        """Append a new event to the log and return the created row."""
        event = WorldEvent(
            tick=tick,
            actor_id=actor_id,
            event_type=event_type,
            action=action,
            params=params,
            result=result,
            reason=reason,
            position_x=position[0] if position else None,
            position_y=position[1] if position else None,
            position_z=position[2] if position else None,
            importance=importance,
        )
        db.add(event)
        await db.flush()
        logger.debug(
            "EventLog: tick=%d actor=%s type=%s action=%s result=%s",
            tick, actor_id, event_type, action, result,
        )
        return event

    # -------------------------------------------------------------------
    # Queries
    # -------------------------------------------------------------------

    async def get_events_in_range(
        self,
        db: AsyncSession,
        start_tick: int,
        end_tick: int,
    ) -> list[WorldEvent]:
        """Return all events with tick in [start_tick, end_tick], ordered by id."""
        result = await db.execute(
            select(WorldEvent)
            .where(
                WorldEvent.tick >= start_tick,
                WorldEvent.tick <= end_tick,
            )
            .order_by(WorldEvent.id.asc())
        )
        return list(result.scalars().all())

    async def get_events_by_actor(
        self,
        db: AsyncSession,
        actor_id: uuid.UUID,
        limit: int = 50,
    ) -> list[WorldEvent]:
        """Return the most recent events for a given actor, newest first."""
        result = await db.execute(
            select(WorldEvent)
            .where(WorldEvent.actor_id == actor_id)
            .order_by(WorldEvent.id.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_recent_events(
        self,
        db: AsyncSession,
        limit: int = 100,
    ) -> list[WorldEvent]:
        """Return the N most recent events, newest first."""
        result = await db.execute(
            select(WorldEvent)
            .order_by(WorldEvent.id.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_events_near(
        self,
        db: AsyncSession,
        x: float,
        y: float,
        z: float,
        radius: float,
        limit: int = 50,
    ) -> list[WorldEvent]:
        """Return events whose recorded position is within `radius` of (x, y, z).

        Uses a bounding-box pre-filter in SQL, then applies Euclidean distance
        in Python for precision (avoids sqrt in SQL for portability).
        """
        # Bounding box pre-filter
        result = await db.execute(
            select(WorldEvent)
            .where(
                WorldEvent.position_x.is_not(None),
                WorldEvent.position_y.is_not(None),
                WorldEvent.position_z.is_not(None),
                WorldEvent.position_x >= x - radius,
                WorldEvent.position_x <= x + radius,
                WorldEvent.position_y >= y - radius,
                WorldEvent.position_y <= y + radius,
                WorldEvent.position_z >= z - radius,
                WorldEvent.position_z <= z + radius,
            )
            .order_by(WorldEvent.id.desc())
            .limit(limit * 2)  # fetch extra, we filter below
        )
        candidates = list(result.scalars().all())

        # Euclidean distance filter
        radius_sq = radius * radius
        filtered: list[WorldEvent] = []
        for ev in candidates:
            dx = ev.position_x - x
            dy = ev.position_y - y
            dz = ev.position_z - z
            if dx * dx + dy * dy + dz * dz <= radius_sq:
                filtered.append(ev)
                if len(filtered) >= limit:
                    break

        return filtered

    async def get_events_by_type(
        self,
        db: AsyncSession,
        event_type: str,
        limit: int = 50,
    ) -> list[WorldEvent]:
        """Return the most recent events of a given type."""
        result = await db.execute(
            select(WorldEvent)
            .where(WorldEvent.event_type == event_type)
            .order_by(WorldEvent.id.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def count_events(self, db: AsyncSession) -> int:
        """Return the total number of events in the log."""
        result = await db.execute(
            select(func.count()).select_from(WorldEvent)
        )
        return result.scalar() or 0


# Module-level singleton
event_log = EventLog()
