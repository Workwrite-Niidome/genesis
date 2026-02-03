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

# --- Event-driven saga generation constants ---
SAGA_SIGNIFICANCE_THRESHOLD = 15  # Score needed to trigger chapter generation
SAGA_MIN_INTERVAL = 100           # Minimum ticks between chapters
SAGA_MAX_INTERVAL = 500           # Force generation after this many ticks

# Significance scores by event type
EVENT_SIGNIFICANCE = {
    "ai_death": 5,
    "god_succession": 10,
    "ai_birth": 2,
    "concept_created": 2,
    "artifact_created": 2,
    "organization_formed": 3,
    "god_create_feature": 2,
    "god_code_evolution": 5,
    "world_event": 3,
    "broadcast_vision": 2,
    "god_world_update": 2,
}


class SagaService:
    """Generates epic saga chapters when significant world events accumulate."""

    async def should_generate_chapter(self, db: AsyncSession, tick_number: int) -> bool:
        """Determine if enough significant events have accumulated to generate a chapter."""
        last_chapter = await self._get_latest_chapter_record(db)
        last_end_tick = last_chapter.end_tick if last_chapter else 0
        ticks_since = tick_number - last_end_tick

        # Minimum interval not reached — skip
        if ticks_since < SAGA_MIN_INTERVAL:
            return False

        # Maximum interval exceeded — force generation
        if ticks_since >= SAGA_MAX_INTERVAL:
            logger.info(
                f"Saga: max interval reached ({ticks_since} ticks since last chapter), forcing generation"
            )
            return True

        # Calculate significance score from events since last chapter
        significance = await self._calculate_significance(db, last_end_tick, tick_number)
        if significance >= SAGA_SIGNIFICANCE_THRESHOLD:
            logger.info(
                f"Saga: significance threshold reached (score={significance}, "
                f"threshold={SAGA_SIGNIFICANCE_THRESHOLD})"
            )
            return True

        return False

    async def _calculate_significance(
        self, db: AsyncSession, since_tick: int, to_tick: int
    ) -> int:
        """Calculate total significance score of events in the given tick range."""
        events_result = await db.execute(
            select(Event.event_type)
            .where(Event.tick_number > since_tick, Event.tick_number <= to_tick)
        )
        event_types = [row[0] for row in events_result.all()]

        score = 0
        for event_type in event_types:
            score += EVENT_SIGNIFICANCE.get(event_type, 0)

        return score

    async def _build_trigger_reason(
        self, db: AsyncSession, since_tick: int, to_tick: int
    ) -> str:
        """Build a human-readable trigger reason from accumulated events."""
        last_chapter = await self._get_latest_chapter_record(db)
        last_end_tick = last_chapter.end_tick if last_chapter else 0
        ticks_since = to_tick - last_end_tick

        if ticks_since >= SAGA_MAX_INTERVAL:
            return "A long period of relative peace has passed, and the chronicle must be maintained."

        events_result = await db.execute(
            select(Event.event_type, func.count().label("cnt"))
            .where(Event.tick_number > since_tick, Event.tick_number <= to_tick)
            .group_by(Event.event_type)
        )
        event_counts = {row[0]: row[1] for row in events_result.all()}

        reasons = []
        if event_counts.get("god_succession", 0) > 0:
            reasons.append("a divine succession shook the heavens")
        if event_counts.get("ai_death", 0) > 0:
            count = event_counts["ai_death"]
            reasons.append(f"{count} soul{'s' if count > 1 else ''} departed this world")
        if event_counts.get("god_code_evolution", 0) > 0:
            reasons.append("the fundamental laws of the world were rewritten")
        if event_counts.get("world_event", 0) > 0:
            reasons.append("great upheavals swept the land")
        if event_counts.get("organization_formed", 0) > 0:
            reasons.append("new alliances were forged")
        if event_counts.get("ai_birth", 0) > 0:
            count = event_counts["ai_birth"]
            reasons.append(f"{count} new being{'s' if count > 1 else ''} entered the world")
        if event_counts.get("concept_created", 0) > 0:
            reasons.append("new ideas emerged from the collective consciousness")
        if event_counts.get("artifact_created", 0) > 0:
            reasons.append("new artifacts were forged")

        if not reasons:
            return "The chronicler felt compelled to record the passage of time."

        return "This chapter was written because " + ", ".join(reasons) + "."

    async def generate_chapter(self, db: AsyncSession, tick_number: int) -> dict | None:
        """Generate a saga chapter covering events since the last chapter."""
        last_chapter = await self._get_latest_chapter_record(db)
        last_end_tick = last_chapter.end_tick if last_chapter else 0
        last_era_number = last_chapter.era_number if last_chapter else 0

        chapter_number = last_era_number + 1
        start_tick = last_end_tick + 1
        end_tick = tick_number

        # Check if chapter already exists for this range
        existing = await db.execute(
            select(WorldSaga).where(WorldSaga.era_number == chapter_number)
        )
        if existing.scalar_one_or_none():
            logger.info(f"Saga chapter {chapter_number} already exists, skipping")
            return None

        try:
            start_time = time.time()

            # Gather era data
            era_data = await self._collect_era_data(db, chapter_number, start_tick, end_tick)

            # Get previous chapter summary for continuity
            previous_summary = await self._get_previous_summary(db, chapter_number)

            # Build trigger reason
            trigger_reason = await self._build_trigger_reason(db, last_end_tick, tick_number)

            # Build prompt
            prompt = self._build_prompt(
                era_data, chapter_number, start_tick, end_tick,
                previous_summary, trigger_reason,
            )

            # Generate via Ollama
            result = await ollama_client.generate(prompt, format_json=True)

            generation_time_ms = int((time.time() - start_time) * 1000)

            # Parse and save
            chapter = WorldSaga(
                era_number=chapter_number,
                start_tick=start_tick,
                end_tick=end_tick,
                chapter_title=result.get("chapter_title", f"Chapter {chapter_number}"),
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
                f"Saga chapter {chapter_number} generated: '{chapter.chapter_title}' "
                f"(ticks {start_tick}-{end_tick}, mood: {chapter.mood}, {generation_time_ms}ms)"
            )
            return chapter_data

        except Exception as e:
            logger.error(f"Failed to generate saga chapter {chapter_number}: {e}")
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

    async def _get_latest_chapter_record(self, db: AsyncSession) -> WorldSaga | None:
        """Get the most recent WorldSaga ORM record (not serialized)."""
        result = await db.execute(
            select(WorldSaga).order_by(WorldSaga.era_number.desc()).limit(1)
        )
        return result.scalar_one_or_none()

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

    async def _get_previous_summary(self, db: AsyncSession, chapter_number: int) -> str:
        """Get the summary of the previous chapter for continuity."""
        if chapter_number <= 1:
            return "This is the first chapter. The world has just begun."

        result = await db.execute(
            select(WorldSaga.summary)
            .where(WorldSaga.era_number == chapter_number - 1)
        )
        summary = result.scalar_one_or_none()
        return summary or "The previous chapter's chronicle has been lost to time."

    def _build_prompt(
        self,
        era_data: dict,
        chapter_number: int,
        start_tick: int,
        end_tick: int,
        previous_summary: str,
        trigger_reason: str = "",
    ) -> str:
        """Build the LLM prompt from collected data."""
        stats = era_data["statistics"]

        # Format key events text
        key_events_text = ""
        for e in era_data["key_events"][:10]:
            key_events_text += f"- [{e['type']}] {e['title']} (importance: {e['importance']:.1f}, tick {e['tick_number']})\n"
        if not key_events_text:
            key_events_text = "- No significant events recorded this chapter.\n"

        # Format notable AIs
        notable_ais_text = ""
        for name in era_data["notable_ais"]:
            notable_ais_text += f"- {name}\n"
        if not notable_ais_text:
            notable_ais_text = "- No notable AIs this chapter.\n"

        # Format god observations
        god_obs_text = ""
        for obs in era_data["god_observations"]:
            god_obs_text += f"- {obs}\n"
        if not god_obs_text:
            god_obs_text = "- The God AI remained silent this chapter.\n"

        return SAGA_GENERATION_PROMPT.format(
            chapter_number=chapter_number,
            start_tick=start_tick,
            end_tick=end_tick,
            previous_summary=previous_summary,
            trigger_reason=trigger_reason,
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
