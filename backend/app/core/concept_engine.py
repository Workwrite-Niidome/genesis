import logging

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai import AI, AIMemory
from app.models.concept import Concept
from app.models.event import Event

logger = logging.getLogger(__name__)

# Adoption threshold: concepts above this count are injected into all AI thinking
WIDESPREAD_ADOPTION_THRESHOLD = 3


class ConceptEngine:
    """Manages concept creation and adoption from AI interactions."""

    async def process_concept_proposals(
        self,
        db: AsyncSession,
        proposals: list[dict],
        tick_number: int,
    ) -> list[Concept]:
        """Process concept proposals from interactions.

        Each proposal dict: {"creator": AI, "proposal": {"name", "definition", "effects"}}
        """
        created = []
        for item in proposals:
            try:
                concept = await self._create_concept(
                    db, item["creator"], item["proposal"], tick_number
                )
                if concept:
                    created.append(concept)
            except Exception as e:
                logger.error(f"Error creating concept: {e}")
        return created

    async def _create_concept(
        self,
        db: AsyncSession,
        creator: AI,
        proposal: dict,
        tick_number: int,
    ) -> Concept | None:
        """Create a new concept from a proposal."""
        name = proposal.get("name", "").strip()
        definition = proposal.get("definition", "").strip()

        if not name or not definition:
            return None

        # Check for duplicate names
        existing = await db.execute(
            select(Concept).where(func.lower(Concept.name) == name.lower())
        )
        if existing.scalar_one_or_none():
            logger.debug(f"Concept '{name}' already exists, skipping creation")
            return None

        # Determine category
        category = proposal.get("category", "philosophy")
        valid_categories = [
            "philosophy", "religion", "government", "economy",
            "art", "technology", "social_norm", "organization",
        ]
        if category not in valid_categories:
            category = "philosophy"

        concept = Concept(
            creator_id=creator.id,
            name=name[:255],
            category=category,
            definition=definition[:2000],
            effects=proposal.get("effects", {}),
            adoption_count=1,
            tick_created=tick_number,
        )
        db.add(concept)
        await db.flush()

        # Creator automatically adopts concept
        state = dict(creator.state)
        adopted = state.get("adopted_concepts", [])
        adopted.append(str(concept.id))
        state["adopted_concepts"] = adopted
        creator.state = state

        # Create event
        event = Event(
            event_type="concept_created",
            importance=0.8,
            title=f"New Concept: {name}",
            description=f"{creator.name} proposed a new concept: '{name}' — {definition[:200]}",
            involved_ai_ids=[creator.id],
            involved_concept_ids=[concept.id],
            tick_number=tick_number,
            metadata_={"concept_name": name, "creator_name": creator.name},
        )
        db.add(event)

        logger.info(f"Concept created: '{name}' by {creator.name}")
        return concept

    async def try_adopt_concept(
        self,
        db: AsyncSession,
        ai: AI,
        concept_id: str,
    ) -> bool:
        """Attempt to have an AI adopt a concept."""
        from uuid import UUID

        try:
            cid = UUID(concept_id)
        except ValueError:
            return False

        result = await db.execute(select(Concept).where(Concept.id == cid))
        concept = result.scalar_one_or_none()
        if not concept:
            return False

        state = dict(ai.state)
        adopted = state.get("adopted_concepts", [])
        if str(concept.id) in adopted:
            return False

        adopted.append(str(concept.id))
        state["adopted_concepts"] = adopted
        ai.state = state

        concept.adoption_count = concept.adoption_count + 1

        logger.debug(f"{ai.name} adopted concept '{concept.name}'")
        return True

    async def get_widespread_concepts(self, db: AsyncSession) -> list[Concept]:
        """Get concepts that have been widely adopted."""
        result = await db.execute(
            select(Concept)
            .where(Concept.adoption_count >= WIDESPREAD_ADOPTION_THRESHOLD)
            .order_by(Concept.adoption_count.desc())
            .limit(10)
        )
        return list(result.scalars().all())

    async def get_ai_adopted_concepts(self, db: AsyncSession, ai: AI) -> list[Concept]:
        """Get concepts adopted by a specific AI."""
        adopted_ids = ai.state.get("adopted_concepts", [])
        if not adopted_ids:
            return []

        from uuid import UUID

        valid_ids = []
        for cid in adopted_ids:
            try:
                valid_ids.append(UUID(cid))
            except (ValueError, TypeError):
                continue

        if not valid_ids:
            return []

        result = await db.execute(
            select(Concept).where(Concept.id.in_(valid_ids))
        )
        return list(result.scalars().all())


concept_engine = ConceptEngine()
