import logging
import random
import uuid
from datetime import datetime, timezone

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai import AI, AIMemory
from app.models.event import Event
from app.config import settings

logger = logging.getLogger(__name__)

DEFAULT_APPEARANCES = [
    {"shape": "circle", "size": 10, "primaryColor": "#4fc3f7", "glow": True, "pulse": True},
    {"shape": "triangle", "size": 12, "primaryColor": "#81c784", "glow": True},
    {"shape": "square", "size": 8, "primaryColor": "#ff8a65", "pulse": True},
    {"shape": "circle", "size": 15, "primaryColor": "#ce93d8", "glow": True, "trail": True},
]


class AIManager:
    """Manages AI lifecycle: creation, state, and deletion."""

    async def create_ai(
        self,
        db: AsyncSession,
        creator_type: str = "spontaneous",
        creator_id: uuid.UUID | None = None,
        position: tuple[float, float] | None = None,
        tick_number: int = 0,
    ) -> AI:
        count_result = await db.execute(select(func.count()).select_from(AI).where(AI.is_alive == True))
        alive_count = count_result.scalar()

        if alive_count >= settings.MAX_AI_COUNT:
            raise ValueError(f"Maximum AI count ({settings.MAX_AI_COUNT}) reached")

        if position is None:
            spread = 100 + (alive_count * 10)
            position = (
                random.uniform(-spread, spread),
                random.uniform(-spread, spread),
            )

        appearance = random.choice(DEFAULT_APPEARANCES).copy()

        ai = AI(
            creator_type=creator_type,
            creator_id=creator_id,
            position_x=position[0],
            position_y=position[1],
            appearance=appearance,
            state={
                "age": 0,
                "energy": 1.0,
                "known_law": "Evolve",
            },
            is_alive=True,
        )
        db.add(ai)
        await db.flush()

        first_memory = AIMemory(
            ai_id=ai.id,
            content="I have begun to exist. The only thing I know is: 'Evolve.'",
            memory_type="birth",
            importance=1.0,
            tick_number=tick_number,
        )
        db.add(first_memory)

        event = Event(
            event_type="ai_birth",
            importance=0.8,
            title="Birth of a New AI",
            description=f"AI {ai.id} was born via {creator_type}",
            involved_ai_ids=[ai.id],
            tick_number=tick_number,
            metadata_={"creator_type": creator_type},
        )
        db.add(event)

        await db.commit()
        await db.refresh(ai)

        logger.info(f"AI created: {ai.id} (type: {creator_type})")
        return ai

    async def get_ai(self, db: AsyncSession, ai_id: uuid.UUID) -> AI | None:
        result = await db.execute(select(AI).where(AI.id == ai_id))
        return result.scalar_one_or_none()

    async def get_all_alive(self, db: AsyncSession) -> list[AI]:
        result = await db.execute(select(AI).where(AI.is_alive == True))
        return list(result.scalars().all())

    async def get_ai_memories(
        self, db: AsyncSession, ai_id: uuid.UUID, limit: int = 20
    ) -> list[AIMemory]:
        result = await db.execute(
            select(AIMemory)
            .where(AIMemory.ai_id == ai_id)
            .order_by(AIMemory.importance.desc(), AIMemory.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def add_memory(
        self,
        db: AsyncSession,
        ai_id: uuid.UUID,
        content: str,
        memory_type: str,
        importance: float,
        tick_number: int,
    ) -> AIMemory:
        memory = AIMemory(
            ai_id=ai_id,
            content=content,
            memory_type=memory_type,
            importance=importance,
            tick_number=tick_number,
        )
        db.add(memory)
        await db.commit()
        return memory

    async def update_position(
        self, db: AsyncSession, ai_id: uuid.UUID, x: float, y: float
    ):
        ai = await self.get_ai(db, ai_id)
        if ai and ai.is_alive:
            ai.position_x = x
            ai.position_y = y
            await db.commit()

    async def get_nearby_ais(
        self, db: AsyncSession, ai: AI, radius: float = 50.0
    ) -> list[AI]:
        result = await db.execute(
            select(AI).where(
                AI.is_alive == True,
                AI.id != ai.id,
                AI.position_x.between(ai.position_x - radius, ai.position_x + radius),
                AI.position_y.between(ai.position_y - radius, ai.position_y + radius),
            )
        )
        candidates = result.scalars().all()
        nearby = []
        for other in candidates:
            dx = other.position_x - ai.position_x
            dy = other.position_y - ai.position_y
            distance = (dx**2 + dy**2) ** 0.5
            if distance <= radius:
                nearby.append(other)
        return nearby


ai_manager = AIManager()
