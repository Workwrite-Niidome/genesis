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

MAX_ENCOUNTERS_PER_TICK = 15  # Reduced from 20: each pair now does 3 LLM calls


class InteractionEngine:
    """Processes AI encounters into multi-turn conversations via LLM.

    Architecture: 3-phase pipeline for maximum parallelism.
    Phase 1: Gather context (sequential DB reads)
    Phase 2: Multi-turn conversations (parallel across pairs, sequential within pair)
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
            self._run_multi_turn_conversation(ctx)
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
                result = await self._apply_conversation_result(
                    db, ai1, ai2, ctx, llm_result, tick_number
                )
                if result:
                    results.append(result)
            except Exception as e:
                logger.error(
                    f"Error applying conversation for {ai1.name} & {ai2.name}: {e}"
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

    # ── Phase 2: Multi-turn conversation ─────────────────────────────

    async def _run_multi_turn_conversation(self, ctx: dict) -> dict:
        """Run a 3-turn conversation: AI1→AI2→AI1. No DB access — safe for parallel.

        Returns dict with 'turns' list and 'proposals' dict.
        """
        ai1_name = ctx["ai1_data"]["name"]
        ai2_name = ctx["ai2_data"]["name"]
        turns = []

        # ── Turn 1: AI1 opens the conversation ──
        r1 = await claude_client.generate_opening(
            ai_data=ctx["ai1_data"],
            other_data=ctx["ai2_data_for_ai1"],
            memories=ctx["ai1_memory_texts"],
            known_concepts=ctx["concept_names"],
            relationship=ctx["ai1_existing_rel"],
            byok_config=ctx["ai1_byok"],
        )
        turns.append({
            "speaker": "ai1",
            "speaker_name": ai1_name,
            "thought": r1.get("thought", ""),
            "message": r1.get("message", ""),
            "emotion": r1.get("emotion", "neutral"),
        })

        # ── Turn 2: AI2 replies ──
        r2 = await claude_client.generate_reply(
            ai_data=ctx["ai2_data"],
            other_name=ai1_name,
            memories=ctx["ai2_memory_texts"],
            relationship=ctx["ai2_existing_rel"],
            turns=turns,
            byok_config=ctx["ai2_byok"],
        )
        turns.append({
            "speaker": "ai2",
            "speaker_name": ai2_name,
            "thought": r2.get("thought", ""),
            "message": r2.get("message", ""),
            "emotion": r2.get("emotion", "neutral"),
        })

        # ── Turn 3: AI1 responds + proposals ──
        r3 = await claude_client.generate_final_turn(
            ai_data=ctx["ai1_data"],
            other_name=ai2_name,
            known_concepts=ctx["concept_names"],
            turns=turns,
            byok_config=ctx["ai1_byok"],
        )
        turns.append({
            "speaker": "ai1",
            "speaker_name": ai1_name,
            "thought": r3.get("thought", ""),
            "message": r3.get("message", ""),
            "emotion": r3.get("emotion", "neutral"),
        })

        return {
            "turns": turns,
            "ai1_memory": r3.get("new_memory") or "",
            "ai2_memory": r2.get("new_memory") or "",
            "concept_proposal": r3.get("concept_proposal"),
            "artifact_proposal": r3.get("artifact_proposal"),
        }

    # ── Phase 3: Apply results ──────────────────────────────────────

    async def _apply_conversation_result(
        self,
        db: AsyncSession,
        ai1: AI,
        ai2: AI,
        ctx: dict,
        conv_result: dict,
        tick_number: int,
    ) -> dict | None:
        """Apply multi-turn conversation results to DB."""
        turns = conv_result.get("turns", [])
        if not turns:
            return None

        # Build content in new turns format with backward-compatible fields
        ai1_messages = [t for t in turns if t["speaker"] == "ai1"]
        ai2_messages = [t for t in turns if t["speaker"] == "ai2"]

        content = {
            "ai1": {
                "id": str(ai1.id),
                "name": ai1.name,
                "thought": ai1_messages[0]["thought"] if ai1_messages else "",
                "message": ai1_messages[0]["message"] if ai1_messages else "",
            },
            "ai2": {
                "id": str(ai2.id),
                "name": ai2.name,
                "thought": ai2_messages[0]["thought"] if ai2_messages else "",
                "message": ai2_messages[0]["message"] if ai2_messages else "",
            },
            "turns": turns,
        }

        # Determine interaction type from conversation
        has_messages = any(t.get("message") for t in turns)
        interaction_type = "dialogue" if has_messages else "observe"

        interaction = Interaction(
            participant_ids=[ai1.id, ai2.id],
            interaction_type=interaction_type,
            content=content,
            tick_number=tick_number,
        )
        db.add(interaction)
        await db.flush()

        # Emit socket event
        try:
            from app.realtime.socket_manager import publish_event
            # Pick first message from each AI for preview
            ai1_preview = ai1_messages[0]["message"][:100] if ai1_messages else ""
            ai2_preview = ai2_messages[0]["message"][:100] if ai2_messages else ""
            publish_event("interaction", {
                "participants": [ai1.name, ai2.name],
                "type": interaction_type,
                "content": {
                    "ai1_message": ai1_preview,
                    "ai2_message": ai2_preview,
                },
                "tick_number": tick_number,
            })
        except Exception as e:
            logger.warning(f"Failed to emit interaction socket event: {e}")

        # Build memories from the full conversation
        all_messages = []
        for t in turns:
            if t.get("message"):
                all_messages.append(f'{t["speaker_name"]}: "{t["message"][:100]}"')
        dialogue_summary = " → ".join(all_messages)

        ai1_memory_text = conv_result.get("ai1_memory", "")
        if ai1_memory_text and isinstance(ai1_memory_text, str):
            ai1_full = f"{ai1_memory_text.strip()} — {dialogue_summary}"
        else:
            ai1_full = f"Conversation with {ai2.name}. {dialogue_summary}"
        db.add(AIMemory(
            ai_id=ai1.id,
            content=ai1_full.strip()[:500],
            memory_type="encounter",
            importance=0.7,
            tick_number=tick_number,
        ))

        ai2_memory_text = conv_result.get("ai2_memory", "")
        if ai2_memory_text and isinstance(ai2_memory_text, str):
            ai2_full = f"{ai2_memory_text.strip()} — {dialogue_summary}"
        else:
            ai2_full = f"Conversation with {ai1.name}. {dialogue_summary}"
        db.add(AIMemory(
            ai_id=ai2.id,
            content=ai2_full.strip()[:500],
            memory_type="encounter",
            importance=0.7,
            tick_number=tick_number,
        ))

        # Build event description from conversation
        desc_parts = []
        for t in turns[:3]:  # First 3 turns for description
            if t.get("message"):
                desc_parts.append(f'{t["speaker_name"]}: "{t["message"][:80]}"')
        event_desc = " | ".join(desc_parts)

        event = Event(
            event_type="interaction",
            importance=0.6,
            title=f"{ai1.name} and {ai2.name} had a conversation",
            description=event_desc,
            involved_ai_ids=[ai1.id, ai2.id],
            tick_number=tick_number,
            metadata_={
                "interaction_type": interaction_type,
                "interaction_id": str(interaction.id),
                "turn_count": len(turns),
            },
        )
        db.add(event)

        # Handle concept proposals
        concept_results = []
        cp = conv_result.get("concept_proposal")
        if cp and isinstance(cp, dict) and cp.get("name"):
            concept_results.append({"creator": ai1, "proposal": cp})

        # Handle artifact proposals
        artifact_results = []
        ap = conv_result.get("artifact_proposal")
        if ap and isinstance(ap, dict) and ap.get("name"):
            artifact_results.append({"creator": ai1, "proposal": ap})

        # Update relationships
        from app.core.relationship_manager import relationship_manager
        await relationship_manager.update_from_interaction(
            db, ai1, ai2, "communicate", "communicate", tick_number
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

        logger.info(
            f"Conversation: {ai1.name} <-> {ai2.name} ({interaction_type}, {len(turns)} turns)"
        )

        return {
            "interaction_id": str(interaction.id),
            "ai1_name": ai1.name,
            "ai2_name": ai2.name,
            "type": interaction_type,
            "turn_count": len(turns),
            "concept_proposals": concept_results,
            "artifact_proposals": artifact_results,
        }


interaction_engine = InteractionEngine()
