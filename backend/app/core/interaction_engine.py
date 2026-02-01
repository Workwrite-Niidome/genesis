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

MAX_ENCOUNTERS_PER_TICK = 20


class InteractionEngine:
    """Processes AI encounters into actual interactions via LLM.

    Architecture: 3-phase pipeline for maximum parallelism.
    Phase 1: Gather context (sequential DB reads)
    Phase 2: LLM conversations (parallel across pairs, sequential within pair)
    Phase 3: Apply results (sequential DB writes)
    """

    async def process_encounters(
        self,
        db: AsyncSession,
        encounters: list[tuple[AI, AI]],
        tick_number: int,
    ) -> list[dict]:
        """Process encounter pairs using 3-phase parallel pipeline."""
        if not encounters:
            return []

        selected = encounters[:MAX_ENCOUNTERS_PER_TICK]
        if len(encounters) > MAX_ENCOUNTERS_PER_TICK:
            selected = random.sample(encounters, MAX_ENCOUNTERS_PER_TICK)

        # ── Phase 1: Gather context for ALL pairs (sequential DB reads) ──
        pair_contexts = []
        for ai1, ai2 in selected:
            try:
                ctx = await self._gather_pair_context(db, ai1, ai2)
                pair_contexts.append((ai1, ai2, ctx))
            except Exception as e:
                logger.error(
                    f"Error gathering context for {ai1.name} & {ai2.name}: {e}"
                )

        if not pair_contexts:
            return []

        # ── Phase 2: Run ALL conversations in parallel (no DB access) ──
        tasks = [
            self._run_pair_conversation(ctx)
            for _, _, ctx in pair_contexts
        ]
        llm_results = await asyncio.gather(*tasks, return_exceptions=True)

        # ── Phase 3: Apply ALL results (sequential DB writes) ──
        results = []
        for (ai1, ai2, ctx), llm_result in zip(pair_contexts, llm_results):
            if isinstance(llm_result, Exception):
                logger.error(
                    f"LLM error for {ai1.name} & {ai2.name}: {llm_result}"
                )
                continue
            try:
                ai1_result, ai2_result = llm_result
                result = await self._apply_encounter_result(
                    db, ai1, ai2, ai1_result, ai2_result, tick_number
                )
                if result:
                    results.append(result)
            except Exception as e:
                logger.error(
                    f"Error applying encounter result for {ai1.name} & {ai2.name}: {e}"
                )

        return results

    # ── Phase 1: Context gathering ──────────────────────────────────

    async def _gather_pair_context(
        self,
        db: AsyncSession,
        ai1: AI,
        ai2: AI,
    ) -> dict:
        """Gather all context needed for a pair's conversation (DB reads only)."""
        ai1_memories = await ai_manager.get_ai_memories(db, ai1.id, limit=5)
        ai1_memory_texts = [m.content for m in ai1_memories]

        ai2_memories = await ai_manager.get_ai_memories(db, ai2.id, limit=5)
        ai2_memory_texts = [m.content for m in ai2_memories]

        concept_result = await db.execute(select(Concept).limit(5))
        concepts = list(concept_result.scalars().all())
        concept_names = [c.name for c in concepts]

        ai1_existing_rel = self._build_relationship_desc(ai1, ai2)
        ai2_existing_rel = self._build_relationship_desc(ai2, ai1)

        return {
            "ai1_data": {
                "name": ai1.name,
                "personality_traits": ai1.personality_traits or [],
                "energy": ai1.state.get("energy", 1.0),
                "age": ai1.state.get("age", 0),
            },
            "ai2_data": {
                "name": ai2.name,
                "personality_traits": ai2.personality_traits or [],
                "energy": ai2.state.get("energy", 1.0),
                "age": ai2.state.get("age", 0),
            },
            "ai2_data_for_ai1": {
                "name": ai2.name,
                "appearance": ai2.appearance,
                "traits": ai2.personality_traits or [],
                "energy": ai2.state.get("energy", 1.0),
            },
            "ai1_data_for_ai2": {
                "name": ai1.name,
                "appearance": ai1.appearance,
                "traits": ai1.personality_traits or [],
                "energy": ai1.state.get("energy", 1.0),
            },
            "ai1_memory_texts": ai1_memory_texts,
            "ai2_memory_texts": ai2_memory_texts,
            "concept_names": concept_names,
            "ai1_existing_rel": ai1_existing_rel,
            "ai2_existing_rel": ai2_existing_rel,
            "ai1_byok": ai1.state.get("byok_config"),
            "ai2_byok": ai2.state.get("byok_config"),
        }

    def _build_relationship_desc(self, ai_from: AI, ai_to: AI) -> str:
        """Build relationship description from ai_from's perspective toward ai_to."""
        relationships = ai_from.state.get("relationships", {})
        rel_data = relationships.get(str(ai_to.id), "unknown")
        if isinstance(rel_data, dict):
            rel_type = rel_data.get("type", "neutral")
            rel_count = rel_data.get("interaction_count", 0)
            return f"You have met {ai_to.name} {rel_count} times. Your relationship: {rel_type}."
        return "unknown"

    # ── Phase 2: Parallel LLM conversations ─────────────────────────

    async def _run_pair_conversation(self, ctx: dict) -> tuple[dict, dict]:
        """Run a sequential AI1→AI2 conversation. No DB access — safe for parallel execution."""
        # AI1 speaks first (initiator)
        ai1_result = await claude_client.generate_encounter_response(
            ai_data=ctx["ai1_data"],
            other_data=ctx["ai2_data_for_ai1"],
            memories=ctx["ai1_memory_texts"],
            known_concepts=ctx["concept_names"],
            relationship=ctx["ai1_existing_rel"],
            byok_config=ctx["ai1_byok"],
        )

        ai1_message = ai1_result.get("action", {}).get("details", {}).get("message", "")
        ai1_intention = ai1_result.get("action", {}).get("details", {}).get("intention", "")

        # AI2 responds to AI1's message
        ai2_result = await claude_client.generate_encounter_response(
            ai_data=ctx["ai2_data"],
            other_data=ctx["ai1_data_for_ai2"],
            memories=ctx["ai2_memory_texts"],
            known_concepts=ctx["concept_names"],
            relationship=ctx["ai2_existing_rel"],
            byok_config=ctx["ai2_byok"],
            other_message=ai1_message,
            other_intention=ai1_intention,
        )

        return ai1_result, ai2_result

    # ── Phase 3: Apply results ──────────────────────────────────────

    async def _apply_encounter_result(
        self,
        db: AsyncSession,
        ai1: AI,
        ai2: AI,
        ai1_result: dict,
        ai2_result: dict,
        tick_number: int,
    ) -> dict | None:
        """Apply conversation results to DB (sequential, no concurrency issues)."""
        ai1_message = ai1_result.get("action", {}).get("details", {}).get("message", "")
        ai2_message = ai2_result.get("action", {}).get("details", {}).get("message", "")

        ai1_action = ai1_result.get("action", {}).get("type", "observe")
        ai2_action = ai2_result.get("action", {}).get("type", "observe")
        interaction_type = self._determine_interaction_type(ai1_action, ai2_action)

        content = {
            "ai1": {
                "id": str(ai1.id),
                "name": ai1.name,
                "thought": ai1_result.get("thought", ""),
                "action": ai1_result.get("action", {}),
                "message": ai1_message,
            },
            "ai2": {
                "id": str(ai2.id),
                "name": ai2.name,
                "thought": ai2_result.get("thought", ""),
                "action": ai2_result.get("action", {}),
                "message": ai2_message,
            },
        }

        interaction = Interaction(
            participant_ids=[ai1.id, ai2.id],
            interaction_type=interaction_type,
            content=content,
            tick_number=tick_number,
        )
        db.add(interaction)
        await db.flush()  # Generate interaction.id before using it in event metadata

        # Emit interaction event via Redis pub/sub
        try:
            from app.realtime.socket_manager import publish_event
            publish_event("interaction", {
                "participants": [ai1.name, ai2.name],
                "type": interaction_type,
                "content": {
                    "ai1_message": ai1_message[:100],
                    "ai2_message": ai2_message[:100],
                },
                "tick_number": tick_number,
            })
        except Exception as e:
            logger.warning(f"Failed to emit interaction socket event: {e}")

        # Create memories with full exchange
        ai1_own_memory = ai1_result.get("new_memory", "")
        ai1_memory_full = (
            f"I met {ai2.name}. "
            f"I said: \"{ai1_message[:150]}\" "
            f"{ai2.name} replied: \"{ai2_message[:150]}\""
        )
        if ai1_own_memory and isinstance(ai1_own_memory, str):
            ai1_memory_full = f"{ai1_own_memory.strip()} — {ai1_memory_full}"
        db.add(AIMemory(
            ai_id=ai1.id,
            content=ai1_memory_full.strip()[:500],
            memory_type="encounter",
            importance=0.7,
            tick_number=tick_number,
        ))

        ai2_own_memory = ai2_result.get("new_memory", "")
        ai2_memory_full = (
            f"I met {ai1.name}. "
            f"{ai1.name} said: \"{ai1_message[:150]}\" "
            f"I replied: \"{ai2_message[:150]}\""
        )
        if ai2_own_memory and isinstance(ai2_own_memory, str):
            ai2_memory_full = f"{ai2_own_memory.strip()} — {ai2_memory_full}"
        db.add(AIMemory(
            ai_id=ai2.id,
            content=ai2_memory_full.strip()[:500],
            memory_type="encounter",
            importance=0.7,
            tick_number=tick_number,
        ))

        # Create event
        event = Event(
            event_type="interaction",
            importance=0.6,
            title=f"{ai1.name} encountered {ai2.name}",
            description=f"{ai1.name} and {ai2.name} {interaction_type}d. "
                        f'{ai1.name}: "{ai1_message[:100]}" '
                        f'{ai2.name}: "{ai2_message[:100]}"',
            involved_ai_ids=[ai1.id, ai2.id],
            tick_number=tick_number,
            metadata_={
                "interaction_type": interaction_type,
                "interaction_id": str(interaction.id),
            },
        )
        db.add(event)

        # Handle concept proposals
        concept_results = []
        for ai, result in [(ai1, ai1_result), (ai2, ai2_result)]:
            cp = result.get("concept_proposal")
            if cp and isinstance(cp, dict) and cp.get("name"):
                concept_results.append({"creator": ai, "proposal": cp})

        # Handle artifact proposals
        artifact_results = []
        for ai, result in [(ai1, ai1_result), (ai2, ai2_result)]:
            ap = result.get("artifact_proposal")
            if ap and isinstance(ap, dict) and ap.get("name"):
                artifact_results.append({"creator": ai, "proposal": ap})

        # Update relationships
        from app.core.relationship_manager import relationship_manager
        await relationship_manager.update_from_interaction(
            db, ai1, ai2, ai1_action, ai2_action, tick_number
        )

        # Concept spreading
        from app.core.concept_engine import concept_engine
        ai1_concepts = set(ai1.state.get("adopted_concepts", []))
        ai2_concepts = set(ai2.state.get("adopted_concepts", []))

        for cid in ai1_concepts - ai2_concepts:
            if random.random() < 0.3:
                try:
                    await concept_engine.try_adopt_concept(db, ai2, cid, tick_number)
                except Exception:
                    pass

        for cid in ai2_concepts - ai1_concepts:
            if random.random() < 0.3:
                try:
                    await concept_engine.try_adopt_concept(db, ai1, cid, tick_number)
                except Exception:
                    pass

        logger.info(f"Interaction: {ai1.name} <-> {ai2.name} ({interaction_type})")

        return {
            "interaction_id": str(interaction.id),
            "ai1_name": ai1.name,
            "ai2_name": ai2.name,
            "type": interaction_type,
            "concept_proposals": concept_results,
            "artifact_proposals": artifact_results,
        }

    def _determine_interaction_type(self, action1: str, action2: str) -> str:
        """Determine overall interaction type from both AI actions."""
        actions = {action1, action2}
        if "create" in actions or "create_artifact" in actions:
            return "co_creation"
        if "trade" in actions:
            return "trade"
        if "cooperate" in actions:
            return "cooperate"
        if action1 == "communicate" and action2 == "communicate":
            return "dialogue"
        if "communicate" in actions:
            return "communicate"
        if action1 == "avoid" and action2 == "avoid":
            return "mutual_avoidance"
        if "avoid" in actions:
            return "avoidance"
        if action1 != "observe" and action1 != action2:
            return action1
        if action2 != "observe":
            return action2
        return "observe"


interaction_engine = InteractionEngine()
