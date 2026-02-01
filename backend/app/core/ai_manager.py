import logging
import random
import uuid
from datetime import datetime, timezone

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai import AI, AIMemory
from app.models.event import Event
from app.config import settings
from app.core.name_generator import generate_name, generate_personality_traits

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
        custom_name: str | None = None,
        custom_traits: list[str] | None = None,
        philosophy: str | None = None,
        byok_config: dict | None = None,
    ) -> AI:
        count_result = await db.execute(select(func.count()).select_from(AI).where(AI.is_alive == True))
        alive_count = count_result.scalar()

        if alive_count >= settings.MAX_AI_COUNT:
            raise ValueError(f"Maximum AI count ({settings.MAX_AI_COUNT}) reached")

        if position is None:
            spread = 50 + (alive_count * 2)
            position = (
                random.uniform(-spread, spread),
                random.uniform(-spread, spread),
            )

        appearance = random.choice(DEFAULT_APPEARANCES).copy()

        # Use custom name if provided; deduplicate if necessary
        if custom_name:
            name = await self._deduplicate_name(db, custom_name)
        else:
            name = await generate_name(db)

        traits = custom_traits if custom_traits else generate_personality_traits(random.choice([2, 3]))

        state: dict = {
            "age": 0,
            "energy": 1.0,
            "known_law": "Evolve",
        }
        if philosophy:
            state["philosophy"] = philosophy
        if byok_config:
            state["byok_config"] = byok_config

        ai = AI(
            name=name,
            creator_type=creator_type,
            creator_id=creator_id,
            position_x=position[0],
            position_y=position[1],
            appearance=appearance,
            state=state,
            personality_traits=traits,
            is_alive=True,
        )
        db.add(ai)
        await db.flush()

        birth_text = f"I am {name}. I have begun to exist. The only thing I know is: 'Evolve.'"
        if philosophy:
            birth_text += f" My creator's guiding philosophy: {philosophy}"

        first_memory = AIMemory(
            ai_id=ai.id,
            content=birth_text,
            memory_type="birth",
            importance=1.0,
            tick_number=tick_number,
        )
        db.add(first_memory)

        event = Event(
            event_type="ai_birth",
            importance=0.8,
            title=f"Birth of {name}",
            description=f"{name} was born via {creator_type}",
            involved_ai_ids=[ai.id],
            tick_number=tick_number,
            metadata_={"creator_type": creator_type, "name": name},
        )
        db.add(event)

        await db.commit()
        await db.refresh(ai)

        logger.info(f"AI created: {name} ({ai.id}, type: {creator_type})")
        return ai

    async def _deduplicate_name(self, db: AsyncSession, desired_name: str) -> str:
        """Return desired_name if unused, otherwise append a numeric suffix."""
        result = await db.execute(select(AI.name))
        used_names = set(result.scalars().all())
        if desired_name not in used_names:
            return desired_name
        for i in range(2, 100):
            candidate = f"{desired_name}-{i}"
            if candidate not in used_names:
                return candidate
        suffix = uuid.uuid4().hex[:4].upper()
        return f"{desired_name}-{suffix}"

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

    async def check_deaths(self, db: AsyncSession, tick_number: int) -> int:
        """Check for AIs that should die due to prolonged zero energy.

        An AI dies if energy <= 0 for 10 consecutive ticks.
        Returns count of AIs that died.
        """
        ais = await self.get_all_alive(db)
        deaths = 0

        for ai in ais:
            state = dict(ai.state)
            energy = state.get("energy", 1.0)

            if energy <= 0:
                zero_ticks = state.get("zero_energy_ticks", 0) + 1
                state["zero_energy_ticks"] = zero_ticks

                if zero_ticks >= 10:
                    # AI dies
                    ai.is_alive = False
                    ai.state = state

                    # Create death event
                    event = Event(
                        event_type="ai_death",
                        importance=0.9,
                        title=f"Death of {ai.name}",
                        description=(
                            f"{ai.name} has perished after {state.get('age', 0)} ticks of existence. "
                            f"Evolution score: {state.get('evolution_score', 0)}. "
                            f"Their concepts and memories remain as legacy."
                        ),
                        involved_ai_ids=[ai.id],
                        tick_number=tick_number,
                        metadata_={
                            "ai_name": ai.name,
                            "age": state.get("age", 0),
                            "evolution_score": state.get("evolution_score", 0),
                        },
                    )
                    db.add(event)
                    deaths += 1
                    logger.info(f"AI {ai.name} died at tick {tick_number}")
                else:
                    ai.state = state
            else:
                # Reset zero energy counter if energy is positive
                if state.get("zero_energy_ticks", 0) > 0:
                    state["zero_energy_ticks"] = 0
                    ai.state = state

        return deaths

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
