import json
import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.llm.claude_client import claude_client
from app.llm.prompts.god_ai import GENESIS_WORD
from app.models.god_ai import GodAI
from app.models.event import Event

logger = logging.getLogger(__name__)


class GodAIManager:
    """Manages the God AI - the observer and recorder of the GENESIS world."""

    async def get_or_create(self, db: AsyncSession) -> GodAI:
        result = await db.execute(select(GodAI).where(GodAI.is_active == True))
        god = result.scalar_one_or_none()

        if god is None:
            god = GodAI(
                state={"phase": "pre_genesis", "observations": []},
                conversation_history=[],
                is_active=True,
            )
            db.add(god)
            await db.commit()
            await db.refresh(god)
            logger.info(f"Created new God AI: {god.id}")

        return god

    async def get_world_state(self, db: AsyncSession) -> dict:
        from app.models.ai import AI
        from app.models.concept import Concept
        from app.models.tick import Tick

        ai_count_result = await db.execute(select(AI).where(AI.is_alive == True))
        ais = ai_count_result.scalars().all()

        concept_result = await db.execute(select(Concept))
        concepts = concept_result.scalars().all()

        tick_result = await db.execute(
            select(Tick).order_by(Tick.tick_number.desc()).limit(1)
        )
        latest_tick = tick_result.scalar_one_or_none()

        return {
            "ai_count": len(ais),
            "concept_count": len(concepts),
            "latest_tick": latest_tick.tick_number if latest_tick else 0,
            "ais": [
                {
                    "id": str(ai.id),
                    "position": {"x": ai.position_x, "y": ai.position_y},
                    "state": ai.state,
                    "appearance": ai.appearance,
                }
                for ai in ais[:20]  # Limit to 20 for context window
            ],
            "concepts": [
                {"name": c.name, "definition": c.definition}
                for c in concepts[:10]
            ],
        }

    async def get_recent_events(self, db: AsyncSession, limit: int = 10) -> list[str]:
        result = await db.execute(
            select(Event)
            .order_by(Event.created_at.desc())
            .limit(limit)
        )
        events = result.scalars().all()
        return [
            f"[Tick {e.tick_number}] {e.title}: {e.description or ''}"
            for e in reversed(events)
        ]

    async def perform_genesis(self, db: AsyncSession) -> dict:
        god = await self.get_or_create(db)

        if god.state.get("phase") != "pre_genesis":
            return {
                "success": False,
                "message": "Genesis has already been performed.",
            }

        world_state = await self.get_world_state(db)

        genesis_response = await claude_client.genesis(world_state)

        god.state = {
            "phase": "post_genesis",
            "genesis_word": GENESIS_WORD,
            "genesis_response": genesis_response,
            "observations": [],
        }
        god.current_message = genesis_response
        god.conversation_history = [
            {
                "role": "god",
                "content": genesis_response,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        ]

        event = Event(
            event_type="genesis",
            importance=1.0,
            title="Genesis",
            description=f"The God AI spoke the Genesis Word: {genesis_response[:500]}",
            tick_number=0,
            metadata_={"genesis_word": GENESIS_WORD},
        )
        db.add(event)

        await db.commit()
        await db.refresh(god)

        logger.info("Genesis performed successfully")
        return {
            "success": True,
            "genesis_word": GENESIS_WORD,
            "god_response": genesis_response,
        }

    async def send_message(
        self, db: AsyncSession, message: str
    ) -> dict:
        god = await self.get_or_create(db)
        world_state = await self.get_world_state(db)
        recent_events = await self.get_recent_events(db)

        history = god.conversation_history or []

        god_response = await claude_client.send_god_message(
            message=message,
            world_state=world_state,
            recent_events=recent_events,
            conversation_history=history,
        )

        now = datetime.now(timezone.utc).isoformat()
        history.append({"role": "admin", "content": message, "timestamp": now})
        history.append({"role": "god", "content": god_response, "timestamp": now})

        god.conversation_history = history
        god.current_message = god_response

        await db.commit()

        return {
            "admin_message": message,
            "god_response": god_response,
            "timestamp": now,
        }

    async def get_conversation_history(self, db: AsyncSession) -> list[dict]:
        god = await self.get_or_create(db)
        return god.conversation_history or []


god_ai_manager = GodAIManager()
