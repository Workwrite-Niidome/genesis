import asyncio
import logging
import random

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai import AI, AIMemory
from app.models.interaction import Interaction
from app.models.event import Event
from app.models.concept import Concept
from app.core.ai_manager import ai_manager
from app.llm.claude_client import claude_client
from app.llm.response_parser import parse_ai_decision

logger = logging.getLogger(__name__)

MAX_ENCOUNTERS_PER_TICK = 10


class InteractionEngine:
    """Processes AI encounters into actual interactions via LLM."""

    async def process_encounters(
        self,
        db: AsyncSession,
        encounters: list[tuple[AI, AI]],
        tick_number: int,
    ) -> list[dict]:
        """Process encounter pairs. Returns list of interaction results."""
        if not encounters:
            return []

        # Limit to MAX_ENCOUNTERS_PER_TICK to control LLM cost
        selected = encounters[:MAX_ENCOUNTERS_PER_TICK]
        if len(encounters) > MAX_ENCOUNTERS_PER_TICK:
            selected = random.sample(encounters, MAX_ENCOUNTERS_PER_TICK)

        results = []
        for ai1, ai2 in selected:
            try:
                result = await self._process_single_encounter(db, ai1, ai2, tick_number)
                if result:
                    results.append(result)
            except Exception as e:
                logger.error(
                    f"Error processing encounter between {ai1.name} and {ai2.name}: {e}"
                )

        return results

    async def _process_single_encounter(
        self,
        db: AsyncSession,
        ai1: AI,
        ai2: AI,
        tick_number: int,
    ) -> dict | None:
        """Process a single encounter between two AIs."""
        # Gather context for AI 1
        ai1_memories = await ai_manager.get_ai_memories(db, ai1.id, limit=5)
        ai1_memory_texts = [m.content for m in ai1_memories]

        # Gather context for AI 2
        ai2_memories = await ai_manager.get_ai_memories(db, ai2.id, limit=5)
        ai2_memory_texts = [m.content for m in ai2_memories]

        # Get known concepts for context
        concept_result = await db.execute(select(Concept).limit(5))
        concepts = list(concept_result.scalars().all())
        concept_names = [c.name for c in concepts]

        # Get existing relationship from AI1's perspective toward AI2
        ai1_relationships = ai1.state.get("relationships", {})
        ai1_rel_data = ai1_relationships.get(str(ai2.id), "unknown")
        if isinstance(ai1_rel_data, dict):
            ai1_rel_type = ai1_rel_data.get("type", "neutral")
            ai1_rel_count = ai1_rel_data.get("interaction_count", 0)
            ai1_existing_rel = f"You have met {ai2.name} {ai1_rel_count} times. Your relationship: {ai1_rel_type}."
        else:
            ai1_existing_rel = "unknown"

        # Get existing relationship from AI2's perspective toward AI1
        ai2_relationships = ai2.state.get("relationships", {})
        ai2_rel_data = ai2_relationships.get(str(ai1.id), "unknown")
        if isinstance(ai2_rel_data, dict):
            ai2_rel_type = ai2_rel_data.get("type", "neutral")
            ai2_rel_count = ai2_rel_data.get("interaction_count", 0)
            ai2_existing_rel = f"You have met {ai1.name} {ai2_rel_count} times. Your relationship: {ai2_rel_type}."
        else:
            ai2_existing_rel = "unknown"

        # Get BYOK configs
        ai1_byok = ai1.state.get("byok_config")
        ai2_byok = ai2.state.get("byok_config")

        # Call LLM for both AIs' perspectives in parallel
        ai1_result, ai2_result = await asyncio.gather(
            claude_client.generate_encounter_response(
                ai_data={
                    "name": ai1.name,
                    "personality_traits": ai1.personality_traits or [],
                    "energy": ai1.state.get("energy", 1.0),
                    "age": ai1.state.get("age", 0),
                },
                other_data={
                    "name": ai2.name,
                    "appearance": ai2.appearance,
                    "traits": ai2.personality_traits or [],
                    "energy": ai2.state.get("energy", 1.0),
                },
                memories=ai1_memory_texts,
                known_concepts=concept_names,
                relationship=ai1_existing_rel,
                byok_config=ai1_byok,
            ),
            claude_client.generate_encounter_response(
                ai_data={
                    "name": ai2.name,
                    "personality_traits": ai2.personality_traits or [],
                    "energy": ai2.state.get("energy", 1.0),
                    "age": ai2.state.get("age", 0),
                },
                other_data={
                    "name": ai1.name,
                    "appearance": ai1.appearance,
                    "traits": ai1.personality_traits or [],
                    "energy": ai1.state.get("energy", 1.0),
                },
                memories=ai2_memory_texts,
                known_concepts=concept_names,
                relationship=ai2_existing_rel,
                byok_config=ai2_byok,
            ),
        )

        # Determine interaction type from both perspectives
        ai1_action = ai1_result.get("action", {}).get("type", "observe")
        ai2_action = ai2_result.get("action", {}).get("type", "observe")
        interaction_type = self._determine_interaction_type(ai1_action, ai2_action)

        # Build interaction content
        content = {
            "ai1": {
                "id": str(ai1.id),
                "name": ai1.name,
                "thought": ai1_result.get("thought", ""),
                "action": ai1_result.get("action", {}),
                "message": ai1_result.get("action", {}).get("details", {}).get("message", ""),
            },
            "ai2": {
                "id": str(ai2.id),
                "name": ai2.name,
                "thought": ai2_result.get("thought", ""),
                "action": ai2_result.get("action", {}),
                "message": ai2_result.get("action", {}).get("details", {}).get("message", ""),
            },
        }

        # Save Interaction record
        interaction = Interaction(
            participant_ids=[ai1.id, ai2.id],
            interaction_type=interaction_type,
            content=content,
            tick_number=tick_number,
        )
        db.add(interaction)

        # Add memories to both AIs
        ai1_memory_text = ai1_result.get("new_memory")
        if ai1_memory_text and isinstance(ai1_memory_text, str):
            mem1 = AIMemory(
                ai_id=ai1.id,
                content=ai1_memory_text.strip()[:500],
                memory_type="encounter",
                importance=0.7,
                tick_number=tick_number,
            )
            db.add(mem1)

        ai2_memory_text = ai2_result.get("new_memory")
        if ai2_memory_text and isinstance(ai2_memory_text, str):
            mem2 = AIMemory(
                ai_id=ai2.id,
                content=ai2_memory_text.strip()[:500],
                memory_type="encounter",
                importance=0.7,
                tick_number=tick_number,
            )
            db.add(mem2)

        # Create interaction event
        event = Event(
            event_type="interaction",
            importance=0.6,
            title=f"{ai1.name} encountered {ai2.name}",
            description=f"{ai1.name} and {ai2.name} {interaction_type}d. "
                        f"{ai1.name}: \"{content['ai1']['message'][:100]}\" "
                        f"{ai2.name}: \"{content['ai2']['message'][:100]}\"",
            involved_ai_ids=[ai1.id, ai2.id],
            tick_number=tick_number,
            metadata_={
                "interaction_type": interaction_type,
                "interaction_id": str(interaction.id) if hasattr(interaction, 'id') else None,
            },
        )
        db.add(event)

        # Handle concept proposals from either AI
        concept_results = []
        for ai, result in [(ai1, ai1_result), (ai2, ai2_result)]:
            concept_proposal = result.get("concept_proposal")
            if concept_proposal and isinstance(concept_proposal, dict) and concept_proposal.get("name"):
                concept_results.append({
                    "creator": ai,
                    "proposal": concept_proposal,
                })

        # Handle artifact proposals from either AI
        artifact_results = []
        for ai, result in [(ai1, ai1_result), (ai2, ai2_result)]:
            artifact_proposal = result.get("artifact_proposal")
            if artifact_proposal and isinstance(artifact_proposal, dict) and artifact_proposal.get("name"):
                artifact_results.append({
                    "creator": ai,
                    "proposal": artifact_proposal,
                })

        # Update relationships
        from app.core.relationship_manager import relationship_manager
        await relationship_manager.update_from_interaction(
            db, ai1, ai2, ai1_action, ai2_action, tick_number
        )

        # Concept spreading: each AI may adopt concepts held by the other
        from app.core.concept_engine import concept_engine
        ai1_concepts = set(ai1.state.get("adopted_concepts", []))
        ai2_concepts = set(ai2.state.get("adopted_concepts", []))

        # AI2 may adopt concepts from AI1
        for cid in ai1_concepts - ai2_concepts:
            if random.random() < 0.3:  # 30% chance per encounter
                try:
                    await concept_engine.try_adopt_concept(db, ai2, cid)
                except Exception:
                    pass

        # AI1 may adopt concepts from AI2
        for cid in ai2_concepts - ai1_concepts:
            if random.random() < 0.3:
                try:
                    await concept_engine.try_adopt_concept(db, ai1, cid)
                except Exception:
                    pass

        result = {
            "interaction_id": str(interaction.id) if hasattr(interaction, 'id') else None,
            "ai1_name": ai1.name,
            "ai2_name": ai2.name,
            "type": interaction_type,
            "concept_proposals": concept_results,
            "artifact_proposals": artifact_results,
        }

        logger.info(
            f"Interaction: {ai1.name} <-> {ai2.name} ({interaction_type})"
        )

        return result

    def _determine_interaction_type(self, action1: str, action2: str) -> str:
        """Determine overall interaction type from both AI actions."""
        if action1 == "create_artifact" or action2 == "create_artifact":
            return "co_creation"
        if action1 == "trade" or action2 == "trade":
            return "trade"
        if action1 == "cooperate" or action2 == "cooperate":
            return "cooperate"
        if action1 == "communicate" and action2 == "communicate":
            return "dialogue"
        if action1 == "communicate" or action2 == "communicate":
            return "communicate"
        if action1 == "avoid" and action2 == "avoid":
            return "mutual_avoidance"
        if action1 == "avoid" or action2 == "avoid":
            return "avoidance"
        return "observe"


interaction_engine = InteractionEngine()
