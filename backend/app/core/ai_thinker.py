import asyncio
import logging
import random

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai import AI, AIMemory
from app.models.ai_thought import AIThought
from app.models.concept import Concept
from app.core.ai_manager import ai_manager
from app.llm.claude_client import claude_client
from app.llm.response_parser import extract_move_details

logger = logging.getLogger(__name__)

BATCH_SIZE = 15
MOVE_CLAMP = 15.0


class AIThinker:
    """Orchestrates the AI thinking cycle."""

    async def run_thinking_cycle(self, db: AsyncSession, tick_number: int) -> int:
        """Run a thinking cycle for a batch of AIs. Returns count of AIs that thought.

        Strategy: gather DB context sequentially, run LLM calls in parallel,
        then apply results to DB sequentially.  This avoids concurrent access
        to a single AsyncSession.
        """
        ais = await ai_manager.get_all_alive(db)
        if not ais:
            return 0

        # Select a random batch
        batch = random.sample(ais, min(BATCH_SIZE, len(ais)))

        # Phase 1: Gather context for each AI sequentially (DB reads)
        ai_contexts = []
        for ai in batch:
            try:
                ctx = await self._gather_context(db, ai)
                ai_contexts.append((ai, ctx))
            except Exception as e:
                logger.error(f"Error gathering context for AI {ai.name}: {e}")

        if not ai_contexts:
            return 0

        # Phase 2: Run all LLM calls in parallel (no DB access)
        llm_tasks = [
            claude_client.think_for_ai(
                ctx["ai_data"], ctx["world_context"], ctx["memory_texts"],
                byok_config=ctx["byok_config"],
            )
            for _ai, ctx in ai_contexts
        ]
        llm_results = await asyncio.gather(*llm_tasks, return_exceptions=True)

        # Phase 3: Apply results sequentially (DB writes)
        thought_count = 0
        for (ai, ctx), llm_result in zip(ai_contexts, llm_results):
            if isinstance(llm_result, Exception):
                logger.error(f"LLM error for AI {ai.name} ({ai.id}): {llm_result}")
                continue
            try:
                await self._apply_result(db, ai, llm_result, ctx["nearby"], tick_number)
                thought_count += 1
            except Exception as e:
                logger.error(f"Error applying result for AI {ai.name}: {e}")

        return thought_count

    async def _gather_context(self, db: AsyncSession, ai: AI) -> dict:
        """Gather all context needed for an AI's thinking (DB reads only)."""
        from app.core.relationship_manager import relationship_manager
        from app.core.concept_engine import concept_engine
        from app.core.culture_engine import culture_engine

        memories = await ai_manager.get_ai_memories(db, ai.id, limit=10)
        memory_texts = [m.content for m in memories]

        nearby = await ai_manager.get_nearby_ais(db, ai, radius=50.0)
        nearby_desc = ", ".join(
            f"{n.name} (at {n.position_x:.0f},{n.position_y:.0f})"
            for n in nearby
        ) if nearby else "None visible"

        relationships_desc = relationship_manager.get_relationship_summary(ai)

        adopted = await concept_engine.get_ai_adopted_concepts(db, ai)
        adopted_desc = "\n".join(
            f"- {c.name} ({c.category}): {c.definition}" for c in adopted
        ) if adopted else "None yet."

        widespread = await concept_engine.get_widespread_concepts(db)
        culture_desc = "\n".join(
            f"- {c.name} ({c.category}, adopted by {c.adoption_count}): {c.definition}"
            for c in widespread
        ) if widespread else "No widespread concepts yet."

        orgs = ai.state.get("organizations", [])
        org_desc = "\n".join(
            f"- {o['name']} (role: {o.get('role', 'member')})" for o in orgs
        ) if orgs else "None."

        artifacts = await culture_engine.get_artifacts_by_ai(db, ai.id, limit=5)
        artifacts_desc = "\n".join(
            f"- {a.name} ({a.artifact_type}): {a.description[:100]}" for a in artifacts
        ) if artifacts else "None yet."

        philosophy = ai.state.get("philosophy")
        philosophy_section = (
            f"## Your Creator's Guiding Philosophy\n{philosophy}\n\n"
            if philosophy else ""
        )

        evolution_score = ai.state.get("evolution_score", 0)

        ai_data = {
            "name": ai.name,
            "personality_traits": ai.personality_traits or [],
            "energy": ai.state.get("energy", 1.0),
            "age": ai.state.get("age", 0),
            "x": ai.position_x,
            "y": ai.position_y,
            "philosophy_section": philosophy_section,
            "evolution_score": evolution_score,
            "relationships": relationships_desc,
            "adopted_concepts": adopted_desc,
            "world_culture": culture_desc,
            "organizations": org_desc,
            "artifacts": artifacts_desc,
        }

        world_context = {
            "nearby_ais": nearby_desc,
        }

        byok_config = ai.state.get("byok_config")

        return {
            "ai_data": ai_data,
            "world_context": world_context,
            "memory_texts": memory_texts,
            "byok_config": byok_config,
            "nearby": nearby,
        }

    async def _apply_result(
        self, db: AsyncSession, ai: AI, result: dict, nearby: list[AI], tick_number: int,
    ) -> None:
        """Apply a single LLM result to the DB (sequential, no concurrency)."""
        from app.core.concept_engine import concept_engine
        from app.core.culture_engine import culture_engine

        # Create thought record
        thought = AIThought(
            ai_id=ai.id,
            tick_number=tick_number,
            thought_type=result["thought_type"],
            content=result["thought"],
            action=result.get("action"),
            context={
                "nearby_count": len(nearby),
                "energy": ai.state.get("energy", 1.0),
            },
        )
        db.add(thought)

        # Apply action
        action = result.get("action", {})
        action_type = action.get("type", "observe") if isinstance(action, dict) else "observe"

        if action_type == "move":
            details = action.get("details", {})
            dx = max(-MOVE_CLAMP, min(MOVE_CLAMP, float(details.get("dx", 0))))
            dy = max(-MOVE_CLAMP, min(MOVE_CLAMP, float(details.get("dy", 0))))
            ai.position_x += dx
            ai.position_y += dy
        elif action_type == "create":
            details = action.get("details", {})
            creation_type = details.get("creation_type", "art")
            description = details.get("description", "")
            if description:
                try:
                    artifact_proposal = {
                        "name": f"{ai.name}'s {creation_type}",
                        "type": creation_type,
                        "description": description[:500],
                    }
                    await culture_engine._create_artifact(db, ai, artifact_proposal, tick_number)
                except Exception as e:
                    logger.debug(f"Artifact creation during thinking failed: {e}")

        # Process concept proposal from thinking
        concept_proposal = result.get("concept_proposal")
        if concept_proposal and isinstance(concept_proposal, dict) and concept_proposal.get("name"):
            try:
                await concept_engine.process_concept_proposals(
                    db,
                    [{"creator": ai, "proposal": concept_proposal}],
                    tick_number,
                )
            except Exception as e:
                logger.debug(f"Concept proposal during thinking failed: {e}")

        # Process artifact proposal from thinking
        artifact_proposal = result.get("artifact_proposal")
        if artifact_proposal and isinstance(artifact_proposal, dict) and artifact_proposal.get("name"):
            try:
                await culture_engine._create_artifact(db, ai, artifact_proposal, tick_number)
            except Exception as e:
                logger.debug(f"Artifact proposal during thinking failed: {e}")

        # Update energy (age is now incremented in tick_engine for ALL AIs)
        state = dict(ai.state)
        if action_type == "rest":
            state["energy"] = min(1.0, state.get("energy", 1.0) + 0.1)
        elif action_type == "create":
            state["energy"] = max(0.0, state.get("energy", 1.0) - 0.05)
        else:
            state["energy"] = max(0.0, state.get("energy", 1.0) - 0.02)
        ai.state = state

        # Store new memory if provided
        new_memory = result.get("new_memory")
        if new_memory and isinstance(new_memory, str) and new_memory.strip():
            memory = AIMemory(
                ai_id=ai.id,
                content=new_memory.strip()[:500],
                memory_type="thought",
                importance=0.5,
                tick_number=tick_number,
            )
            db.add(memory)

        # Gravity drift: pull AIs toward each other or toward origin
        if nearby:
            nearest = min(
                nearby,
                key=lambda n: (n.position_x - ai.position_x) ** 2 + (n.position_y - ai.position_y) ** 2,
            )
            dx = nearest.position_x - ai.position_x
            dy = nearest.position_y - ai.position_y
            dist = (dx ** 2 + dy ** 2) ** 0.5
            if dist > 0:
                drift = 2.0
                ai.position_x += (dx / dist) * drift
                ai.position_y += (dy / dist) * drift
        else:
            dist_from_origin = (ai.position_x ** 2 + ai.position_y ** 2) ** 0.5
            if dist_from_origin > 100:
                ai.position_x *= 0.95
                ai.position_y *= 0.95

        logger.debug(f"AI {ai.name} thought: {result['thought'][:80]}...")


ai_thinker = AIThinker()
