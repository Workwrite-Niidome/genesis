import logging
import time

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.saga import WorldSaga
from app.models.event import Event
from app.models.ai import AI
from app.models.interaction import Interaction
from app.models.tick import Tick
from app.llm.ollama_client import ollama_client
from app.llm.prompts.saga import SAGA_GENERATION_PROMPT

logger = logging.getLogger(__name__)

ERA_SIZE = 50


class SagaService:
    """Generates epic saga chapters at the end of each era."""

    async def generate_era_saga(self, db: AsyncSession, tick_number: int) -> dict | None:
        """Generate a saga chapter for the era that just ended."""
        era_number = tick_number // ERA_SIZE
        start_tick = (era_number - 1) * ERA_SIZE
        end_tick = tick_number - 1

        # Check if chapter already exists
        existing = await db.execute(
            select(WorldSaga).where(WorldSaga.era_number == era_number)
        )
        if existing.scalar_one_or_none():
            logger.info(f"Saga chapter for era {era_number} already exists, skipping")
            return None

        try:
            start_time = time.time()

            # Gather era data
            era_data = await self._collect_era_data(db, era_number, start_tick, end_tick)

            # Get previous chapter summary for continuity
            previous_summary = await self._get_previous_summary(db, era_number)

            # Build prompt
            prompt = self._build_prompt(era_data, era_number, start_tick, end_tick, previous_summary)

            # Generate via Ollama
            result = await ollama_client.generate(prompt, format_json=True)

            generation_time_ms = int((time.time() - start_time) * 1000)

            # Parse and save
            chapter = WorldSaga(
                era_number=era_number,
                start_tick=start_tick,
                end_tick=end_tick,
                chapter_title=result.get("chapter_title", f"Era {era_number}"),
                narrative=result.get("narrative", "The chronicle remains unwritten."),
                summary=result.get("summary", ""),
                era_statistics=era_data["statistics"],
                key_events=era_data["key_events"],
                key_characters=result.get("key_characters", []),
                mood=result.get("mood"),
                generation_time_ms=generation_time_ms,
            )
            db.add(chapter)
            await db.commit()
            await db.refresh(chapter)

            chapter_data = self._serialize_chapter(chapter)

            # Emit socket event
            try:
                from app.realtime.socket_manager import publish_event
                publish_event("saga_chapter", chapter_data)
            except Exception as e:
                logger.warning(f"Failed to emit saga_chapter event: {e}")

            logger.info(
                f"Saga chapter {era_number} generated: '{chapter.chapter_title}' "
                f"(mood: {chapter.mood}, {generation_time_ms}ms)"
            )
            return chapter_data

        except Exception as e:
            logger.error(f"Failed to generate saga for era {era_number}: {e}")
            await db.rollback()
            return None

    async def get_chapters(self, db: AsyncSession, limit: int = 50) -> list[dict]:
        """Get all saga chapters ordered by era descending."""
        result = await db.execute(
            select(WorldSaga)
            .order_by(WorldSaga.era_number.desc())
            .limit(limit)
        )
        chapters = result.scalars().all()
        return [self._serialize_chapter(c) for c in chapters]

    async def get_chapter_by_era(self, db: AsyncSession, era_number: int) -> dict | None:
        """Get a specific chapter by era number."""
        result = await db.execute(
            select(WorldSaga).where(WorldSaga.era_number == era_number)
        )
        chapter = result.scalar_one_or_none()
        if chapter:
            return self._serialize_chapter(chapter)
        return None

    async def get_latest_chapter(self, db: AsyncSession) -> dict | None:
        """Get the most recent saga chapter."""
        result = await db.execute(
            select(WorldSaga).order_by(WorldSaga.era_number.desc()).limit(1)
        )
        chapter = result.scalar_one_or_none()
        if chapter:
            return self._serialize_chapter(chapter)
        return None

    async def _collect_era_data(
        self, db: AsyncSession, era_number: int, start_tick: int, end_tick: int
    ) -> dict:
        """Collect all relevant data for the era."""
        # Events in this era
        events_result = await db.execute(
            select(Event)
            .where(Event.tick_number >= start_tick, Event.tick_number <= end_tick)
            .order_by(Event.importance.desc())
            .limit(20)
        )
        events = list(events_result.scalars().all())

        key_events = [
            {
                "id": str(e.id),
                "type": e.event_type,
                "title": e.title,
                "importance": e.importance,
                "tick_number": e.tick_number,
            }
            for e in events
        ]

        # Count statistics
        births = sum(1 for e in events if e.event_type == "ai_birth")
        deaths = sum(1 for e in events if e.event_type == "ai_death")
        concepts_created = sum(1 for e in events if e.event_type == "concept_created")

        # Interaction count
        interaction_count_result = await db.execute(
            select(func.count()).select_from(Interaction).where(
                Interaction.tick_number >= start_tick,
                Interaction.tick_number <= end_tick,
            )
        )
        interactions_count = interaction_count_result.scalar() or 0

        # AI counts at era boundaries
        start_tick_record = await db.execute(
            select(Tick.ai_count)
            .where(Tick.tick_number >= start_tick)
            .order_by(Tick.tick_number.asc())
            .limit(1)
        )
        ai_count_start = start_tick_record.scalar() or 0

        end_tick_record = await db.execute(
            select(Tick.ai_count)
            .where(Tick.tick_number <= end_tick)
            .order_by(Tick.tick_number.desc())
            .limit(1)
        )
        ai_count_end = end_tick_record.scalar() or 0

        # Notable AIs (alive during this era)
        notable_ais_result = await db.execute(
            select(AI.name).where(AI.is_alive == True).limit(10)
        )
        notable_ais = [name for (name,) in notable_ais_result.all()]

        # God observations
        god_obs_result = await db.execute(
            select(Event)
            .where(
                Event.event_type == "god_observation",
                Event.tick_number >= start_tick,
                Event.tick_number <= end_tick,
            )
            .order_by(Event.tick_number.desc())
            .limit(5)
        )
        god_observations = [
            e.description or e.title for e in god_obs_result.scalars().all()
        ]

        statistics = {
            "births": births,
            "deaths": deaths,
            "concepts": concepts_created,
            "interactions": interactions_count,
            "ai_count_start": ai_count_start,
            "ai_count_end": ai_count_end,
        }

        return {
            "statistics": statistics,
            "key_events": key_events,
            "notable_ais": notable_ais,
            "god_observations": god_observations,
        }

    async def _get_previous_summary(self, db: AsyncSession, era_number: int) -> str:
        """Get the summary of the previous chapter for continuity."""
        if era_number <= 1:
            return "This is the first era. The world has just begun."

        result = await db.execute(
            select(WorldSaga.summary)
            .where(WorldSaga.era_number == era_number - 1)
        )
        summary = result.scalar_one_or_none()
        return summary or "The previous era's chronicle has been lost to time."

    def _build_prompt(
        self,
        era_data: dict,
        era_number: int,
        start_tick: int,
        end_tick: int,
        previous_summary: str,
    ) -> str:
        """Build the LLM prompt from collected data."""
        stats = era_data["statistics"]

        # Format key events text
        key_events_text = ""
        for e in era_data["key_events"][:10]:
            key_events_text += f"- [{e['type']}] {e['title']} (importance: {e['importance']:.1f}, tick {e['tick_number']})\n"
        if not key_events_text:
            key_events_text = "- No significant events recorded this era.\n"

        # Format notable AIs
        notable_ais_text = ""
        for name in era_data["notable_ais"]:
            notable_ais_text += f"- {name}\n"
        if not notable_ais_text:
            notable_ais_text = "- No notable AIs this era.\n"

        # Format god observations
        god_obs_text = ""
        for obs in era_data["god_observations"]:
            god_obs_text += f"- {obs}\n"
        if not god_obs_text:
            god_obs_text = "- The God AI remained silent this era.\n"

        return SAGA_GENERATION_PROMPT.format(
            era_number=era_number,
            start_tick=start_tick,
            end_tick=end_tick,
            previous_summary=previous_summary,
            ai_count_start=stats["ai_count_start"],
            ai_count_end=stats["ai_count_end"],
            births=stats["births"],
            deaths=stats["deaths"],
            concepts_created=stats["concepts"],
            interactions_count=stats["interactions"],
            key_events_text=key_events_text,
            notable_ais_text=notable_ais_text,
            god_observations_text=god_obs_text,
        )

    def _serialize_chapter(self, chapter: WorldSaga) -> dict:
        """Serialize a WorldSaga instance to a dict."""
        return {
            "id": str(chapter.id),
            "era_number": chapter.era_number,
            "start_tick": chapter.start_tick,
            "end_tick": chapter.end_tick,
            "chapter_title": chapter.chapter_title,
            "narrative": chapter.narrative,
            "summary": chapter.summary,
            "era_statistics": chapter.era_statistics,
            "key_events": chapter.key_events,
            "key_characters": chapter.key_characters,
            "mood": chapter.mood,
            "generation_time_ms": chapter.generation_time_ms,
            "created_at": chapter.created_at.isoformat() if chapter.created_at else None,
        }


saga_service = SagaService()
