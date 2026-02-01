import logging

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai import AI
from app.models.concept import Concept
from app.models.interaction import Interaction
from app.models.event import Event

logger = logging.getLogger(__name__)


class EvolutionEngine:
    """Calculates evolution scores for AIs and manages ranking."""

    async def recalculate_all_scores(self, db: AsyncSession, tick_number: int) -> None:
        """Recalculate evolution scores for all alive AIs."""
        result = await db.execute(select(AI).where(AI.is_alive == True))
        ais = list(result.scalars().all())

        for ai in ais:
            score = await self._calculate_score(db, ai)
            state = dict(ai.state)
            old_score = state.get("evolution_score", 0)
            state["evolution_score"] = round(score, 1)
            ai.state = state

            # Check for milestone events
            if score >= 50 and old_score < 50:
                await self._create_milestone_event(db, ai, 50, tick_number)
            elif score >= 100 and old_score < 100:
                await self._create_milestone_event(db, ai, 100, tick_number)

        await db.commit()

    async def _calculate_score(self, db: AsyncSession, ai: AI) -> float:
        """Calculate evolution score for a single AI.

        score = concept_created * 10
              + concept_adopted_by_others * 5
              + interaction_count * 2
              + unique_relationships * 3
              + memory_count * 0.5
              + age * 0.1
              + artifacts_created * 8
              + artifact_appreciation * 4
              + organizations * 6
        """
        # Concepts created by this AI
        concept_created_result = await db.execute(
            select(func.count()).select_from(Concept).where(Concept.creator_id == ai.id)
        )
        concepts_created = concept_created_result.scalar() or 0

        # Adoption count of concepts created by this AI (sum of adoption_count - 1 for self)
        adoption_result = await db.execute(
            select(func.coalesce(func.sum(Concept.adoption_count - 1), 0))
            .where(Concept.creator_id == ai.id)
        )
        concepts_adopted_by_others = max(0, adoption_result.scalar() or 0)

        # Interaction count
        interaction_result = await db.execute(
            select(func.count())
            .select_from(Interaction)
            .where(Interaction.participant_ids.any(ai.id))
        )
        interaction_count = interaction_result.scalar() or 0

        # Unique relationships
        relationships = ai.state.get("relationships", {})
        unique_relationships = len(relationships)

        # Memory count
        from app.models.ai import AIMemory
        memory_result = await db.execute(
            select(func.count()).select_from(AIMemory).where(AIMemory.ai_id == ai.id)
        )
        memory_count = memory_result.scalar() or 0

        # Artifacts created by this AI
        from app.models.artifact import Artifact
        artifact_created_result = await db.execute(
            select(func.count()).select_from(Artifact).where(Artifact.creator_id == ai.id)
        )
        artifacts_created = artifact_created_result.scalar() or 0

        # Appreciation of artifacts created by this AI
        appreciation_result = await db.execute(
            select(func.coalesce(func.sum(Artifact.appreciation_count - 1), 0))
            .where(Artifact.creator_id == ai.id)
        )
        artifact_appreciation = max(0, appreciation_result.scalar() or 0)

        # Organizations
        organizations = len(ai.state.get("organizations", []))

        # Age
        age = ai.state.get("age", 0)

        score = (
            concepts_created * 10
            + concepts_adopted_by_others * 5
            + interaction_count * 2
            + unique_relationships * 3
            + memory_count * 0.5
            + age * 0.1
            + artifacts_created * 8
            + artifact_appreciation * 4
            + organizations * 6
        )

        return score

    async def _create_milestone_event(
        self, db: AsyncSession, ai: AI, milestone: int, tick_number: int
    ) -> None:
        """Create an event when an AI reaches an evolution milestone."""
        event = Event(
            event_type="evolution_milestone",
            importance=0.7,
            title=f"{ai.name} reached Evolution Score {milestone}",
            description=f"{ai.name} has achieved an evolution score of {milestone}, "
                        f"demonstrating significant growth and adaptation.",
            involved_ai_ids=[ai.id],
            tick_number=tick_number,
            metadata_={"milestone": milestone, "ai_name": ai.name},
        )
        db.add(event)

    async def get_ranking(self, db: AsyncSession, limit: int = 20) -> list[dict]:
        """Get ranked list of AIs by evolution score."""
        result = await db.execute(select(AI).where(AI.is_alive == True))
        ais = list(result.scalars().all())

        ranked = sorted(
            ais,
            key=lambda a: a.state.get("evolution_score", 0),
            reverse=True,
        )[:limit]

        return [
            {
                "id": str(ai.id),
                "name": ai.name,
                "evolution_score": ai.state.get("evolution_score", 0),
                "age": ai.state.get("age", 0),
                "energy": ai.state.get("energy", 1.0),
            }
            for ai in ranked
        ]

    async def get_god_candidate(self, db: AsyncSession) -> AI | None:
        """Get the top-ranked AI as potential God candidate."""
        result = await db.execute(select(AI).where(AI.is_alive == True))
        ais = list(result.scalars().all())

        if not ais:
            return None

        top = max(ais, key=lambda a: a.state.get("evolution_score", 0))
        if top.state.get("evolution_score", 0) > 0:
            return top
        return None


evolution_engine = EvolutionEngine()
