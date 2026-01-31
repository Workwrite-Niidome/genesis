import logging

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tick import Tick
from app.models.event import Event
from app.models.ai import AI
from app.models.concept import Concept

logger = logging.getLogger(__name__)


class HistoryManager:
    """Records and retrieves world history."""

    async def record_tick(
        self,
        db: AsyncSession,
        tick_number: int,
        world_snapshot: dict,
        ai_count: int,
        concept_count: int,
        events: list[dict],
        processing_time_ms: int | None = None,
    ) -> Tick:
        tick = Tick(
            tick_number=tick_number,
            world_snapshot=world_snapshot,
            ai_count=ai_count,
            concept_count=concept_count,
            significant_events=events,
            processing_time_ms=processing_time_ms,
        )
        db.add(tick)
        await db.commit()
        await db.refresh(tick)
        return tick

    async def get_latest_tick_number(self, db: AsyncSession) -> int:
        result = await db.execute(
            select(Tick.tick_number).order_by(Tick.tick_number.desc()).limit(1)
        )
        tick_num = result.scalar_one_or_none()
        return tick_num or 0

    async def get_tick(self, db: AsyncSession, tick_number: int) -> Tick | None:
        result = await db.execute(
            select(Tick).where(Tick.tick_number == tick_number)
        )
        return result.scalar_one_or_none()

    async def get_ticks(
        self, db: AsyncSession, offset: int = 0, limit: int = 50
    ) -> list[Tick]:
        result = await db.execute(
            select(Tick)
            .order_by(Tick.tick_number.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_events(
        self,
        db: AsyncSession,
        event_type: str | None = None,
        min_importance: float = 0.0,
        offset: int = 0,
        limit: int = 50,
    ) -> list[Event]:
        query = select(Event).where(Event.importance >= min_importance)
        if event_type:
            query = query.where(Event.event_type == event_type)
        query = query.order_by(Event.created_at.desc()).offset(offset).limit(limit)

        result = await db.execute(query)
        return list(result.scalars().all())

    async def get_timeline(
        self, db: AsyncSession, limit: int = 100
    ) -> list[dict]:
        events = await self.get_events(db, min_importance=0.3, limit=limit)
        return [
            {
                "id": str(e.id),
                "type": e.event_type,
                "importance": e.importance,
                "title": e.title,
                "description": e.description,
                "tick_number": e.tick_number,
                "timestamp": e.created_at.isoformat(),
            }
            for e in events
        ]


history_manager = HistoryManager()
