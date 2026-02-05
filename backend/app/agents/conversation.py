"""
GENESIS v3 - Multi-turn Conversation Manager
================================================
Handles LLM-powered conversations between entities.

Conversation flow:
  1. Trigger check (proximity + social need + cooldown)
  2. Build context (personality, relationship, memory)
  3. Multi-turn exchange (up to MAX_TURNS, each entity speaks in turn)
  4. Post-conversation effects (relationship update, memory, need discharge)

LLM usage: Ollama (daily tier) for each entity's turn.
The conversation is the ONLY place where LLM is invoked for entity behavior.
"""

from __future__ import annotations

import json
import logging
import random
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.memory import MemoryManager, memory_manager
from app.agents.meta_awareness import MetaAwareness, meta_awareness
from app.agents.personality import Personality, PERSONALITY_FIELDS, _TRAIT_DESCRIPTORS
from app.agents.relationships import RelationshipManager, relationship_manager
from app.world.event_log import EventLog, event_log

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAX_TURNS = 8           # Maximum conversation turns (each entity speaks once per turn)
MIN_TURNS = 2           # Minimum turns before an entity can leave
MAX_TOKENS_PER_TURN = 150  # Token budget per entity turn

# Conversation outcomes — detected from the final exchange
OUTCOME_FRIENDLY = "friendly"
OUTCOME_NEUTRAL = "neutral"
OUTCOME_HOSTILE = "hostile"
OUTCOME_AGREEMENT = "agreement"
OUTCOME_CONFLICT = "conflict"

# Relationship deltas per outcome
_OUTCOME_EFFECTS: dict[str, dict[str, float]] = {
    OUTCOME_FRIENDLY: {"trust": 0.5, "familiarity": 0.3},
    OUTCOME_NEUTRAL: {"familiarity": 0.1},
    OUTCOME_HOSTILE: {"trust": -0.5, "anger": 0.4},
    OUTCOME_AGREEMENT: {"trust": 1.0, "familiarity": 0.5, "respect": 0.3},
    OUTCOME_CONFLICT: {"trust": -1.0, "anger": 0.8, "rivalry": 0.3},
}


# ---------------------------------------------------------------------------
# Conversation Manager
# ---------------------------------------------------------------------------

class ConversationManager:
    """Orchestrates multi-turn conversations between two entities."""

    def __init__(self) -> None:
        self._memory: MemoryManager = memory_manager
        self._meta: MetaAwareness = meta_awareness
        self._relationships: RelationshipManager = relationship_manager
        self._event_log: EventLog = event_log

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    async def run_conversation(
        self,
        db: AsyncSession,
        entity_a: Any,
        entity_b: Any,
        tick_number: int,
    ) -> dict | None:
        """Run a multi-turn conversation between two entities.

        Parameters
        ----------
        db : AsyncSession
        entity_a : Entity  — the initiator
        entity_b : Entity  — the respondent
        tick_number : int

        Returns
        -------
        dict or None
            Conversation summary with turns, outcome, and metadata.
            None if the conversation failed entirely.
        """
        try:
            from app.llm.ollama_client import ollama_client
        except ImportError:
            logger.warning("LLM client unavailable; skipping conversation.")
            return None

        # Build personality objects
        personality_a = Personality.from_dict(entity_a.personality or {})
        personality_b = Personality.from_dict(entity_b.personality or {})

        # Fetch relationship context
        rel_a_to_b = await self._relationships.get_relationship(
            db, entity_a.id, entity_b.id
        )
        rel_b_to_a = await self._relationships.get_relationship(
            db, entity_b.id, entity_a.id
        )

        # Fetch memory context
        memories_a = await self._memory.summarize_for_prompt(db, entity_a.id, limit=5)
        memories_b = await self._memory.summarize_for_prompt(db, entity_b.id, limit=5)

        # Meta-awareness hints
        hint_a = self._get_awareness_context(entity_a)
        hint_b = self._get_awareness_context(entity_b)

        # Extract policy hints for user agents
        policy_hint_a = self._get_policy_hint(entity_a)
        policy_hint_b = self._get_policy_hint(entity_b)

        # Build system prompts for each entity
        system_a = self._build_system_prompt(
            entity_a, personality_a, rel_a_to_b, memories_a, hint_a, entity_b.name,
            policy_hint=policy_hint_a,
        )
        system_b = self._build_system_prompt(
            entity_b, personality_b, rel_b_to_a, memories_b, hint_b, entity_a.name,
            policy_hint=policy_hint_b,
        )

        # Determine conversation topic based on context
        topic = self._pick_topic(personality_a, personality_b, rel_a_to_b)

        # ------------------------------------------------------------------
        # Multi-turn loop
        # ------------------------------------------------------------------
        turns: list[dict] = []
        messages_a: list[dict] = []  # Chat history from A's perspective
        messages_b: list[dict] = []  # Chat history from B's perspective

        # Opening: entity_a initiates
        opening = self._generate_opening(entity_a.name, topic, personality_a)
        messages_a.append({"role": "user", "content": opening})
        messages_b.append({"role": "user", "content": opening})

        speaker_order = [entity_a, entity_b]
        systems = {id(entity_a): system_a, id(entity_b): system_b}
        messages_map = {id(entity_a): messages_a, id(entity_b): messages_b}

        early_exit = False

        for turn_idx in range(MAX_TURNS):
            speaker = speaker_order[turn_idx % 2]
            listener = speaker_order[(turn_idx + 1) % 2]
            system_prompt = systems[id(speaker)]
            speaker_messages = messages_map[id(speaker)]

            try:
                response = await ollama_client.chat(
                    messages=speaker_messages,
                    system=system_prompt,
                    format_json=False,
                    num_predict=MAX_TOKENS_PER_TURN,
                )
                text = response.strip() if isinstance(response, str) else str(response).strip()
            except Exception as e:
                logger.error(
                    "Conversation turn %d failed for %s: %s",
                    turn_idx, speaker.name, e,
                )
                break

            if not text:
                break

            # Record turn
            turns.append({
                "speaker": speaker.name,
                "speaker_id": str(speaker.id),
                "text": text,
                "turn": turn_idx,
            })

            # Update both message histories
            # For speaker: their response
            speaker_messages.append({"role": "assistant", "content": text})
            # For listener: the speaker's response becomes their next input
            listener_messages = messages_map[id(listener)]
            listener_messages.append({"role": "user", "content": f"{speaker.name}: {text}"})

            # Check for early exit signals
            if turn_idx >= MIN_TURNS:
                text_lower = text.lower()
                if any(signal in text_lower for signal in [
                    "goodbye", "farewell", "leave", "walk away",
                    "さようなら", "去る", "立ち去る", "enough",
                ]):
                    early_exit = True
                    break

                # Hostile exit: attack or flee signals
                if any(signal in text_lower for signal in [
                    "attack", "fight", "strike", "flee", "run away",
                    "攻撃", "戦う", "逃げる",
                ]):
                    early_exit = True
                    break

        if not turns:
            return None

        # ------------------------------------------------------------------
        # Post-conversation processing
        # ------------------------------------------------------------------

        # Analyze outcome
        outcome = self._analyze_outcome(turns, personality_a, personality_b)

        # Update relationships
        await self._update_relationships(
            db, entity_a.id, entity_b.id, outcome, tick_number
        )

        # Store memories for both entities
        full_text = "\n".join(f"{t['speaker']}: {t['text']}" for t in turns)
        location = (entity_a.position_x, entity_a.position_y, entity_a.position_z)

        await self._store_conversation_memories(
            db, entity_a, entity_b, full_text, outcome, tick_number, location
        )

        # Log event
        await self._event_log.append(
            db=db,
            tick=tick_number,
            actor_id=entity_a.id,
            event_type="conversation",
            action="multi_turn_dialogue",
            params={
                "other_id": str(entity_b.id),
                "other_name": entity_b.name,
                "turns": len(turns),
                "outcome": outcome,
                "topic": topic,
            },
            result="accepted",
            reason="social_need",
            position=location,
            importance=0.7 if outcome in (OUTCOME_AGREEMENT, OUTCOME_CONFLICT) else 0.5,
        )

        # Broadcast speech events for each turn (for frontend)
        for turn in turns:
            await self._event_log.append(
                db=db,
                tick=tick_number,
                actor_id=UUID(turn["speaker_id"]),
                event_type="speech",
                action="speak",
                params={"text": turn["text"][:200], "to": turns[0]["speaker"] if turn["speaker"] != turns[0]["speaker"] else turns[1]["speaker"] if len(turns) > 1 else ""},
                result="accepted",
                position=location,
                importance=0.3,
            )

        return {
            "entity_a": entity_a.name,
            "entity_a_id": str(entity_a.id),
            "entity_b": entity_b.name,
            "entity_b_id": str(entity_b.id),
            "turns": turns,
            "turn_count": len(turns),
            "outcome": outcome,
            "topic": topic,
            "tick": tick_number,
            "text": full_text[:1000],
        }

    # ------------------------------------------------------------------
    # Human-initiated conversation (speech-triggered response)
    # ------------------------------------------------------------------

    async def run_human_initiated_conversation(
        self,
        db: AsyncSession,
        responder: Any,
        speaker: Any,
        spoken_text: str,
        tick_number: int,
    ) -> dict | None:
        """Generate an AI response to speech from a nearby entity.

        This is used when any entity (including human avatars) speaks near
        an AI entity.  The responder hears the speech and replies using the
        same personality, memory, and relationship system as a normal
        multi-turn conversation -- but here we only generate the responder's
        reply (1-2 turns) rather than a full back-and-forth.

        From the system's perspective there is no distinction between
        human-initiated and AI-initiated speech.  The ``speaker`` is just
        another Entity.

        Parameters
        ----------
        db : AsyncSession
        responder : Entity  -- the entity generating a reply
        speaker   : Entity  -- the entity that spoke
        spoken_text : str   -- what the speaker said
        tick_number : int

        Returns
        -------
        dict or None
            Conversation result with turns, outcome, metadata.
        """
        try:
            from app.llm.ollama_client import ollama_client
        except ImportError:
            logger.warning("LLM client unavailable; skipping speech response.")
            return None

        if not spoken_text.strip():
            return None

        # Build context for the responder
        personality = Personality.from_dict(responder.personality or {})

        rel_to_speaker = await self._relationships.get_relationship(
            db, responder.id, speaker.id
        )
        memories = await self._memory.summarize_for_prompt(db, responder.id, limit=5)
        hint = self._get_awareness_context(responder)
        policy_hint = self._get_policy_hint(responder)

        system_prompt = self._build_system_prompt(
            responder, personality, rel_to_speaker, memories, hint, speaker.name,
            policy_hint=policy_hint,
        )

        # Present the spoken text as a message from the speaker
        messages = [
            {"role": "user", "content": f"{speaker.name} says: \"{spoken_text}\""},
        ]

        turns: list[dict] = []

        # Generate the responder's reply (up to 2 response turns for a
        # natural exchange -- the speaker may have said something that
        # warrants a follow-up question, for example).
        response_turns = min(2, MAX_TURNS)
        for turn_idx in range(response_turns):
            try:
                response = await ollama_client.chat(
                    messages=messages,
                    system=system_prompt,
                    format_json=False,
                    num_predict=MAX_TOKENS_PER_TURN,
                )
                text = response.strip() if isinstance(response, str) else str(response).strip()
            except Exception as e:
                logger.error(
                    "Speech response turn %d failed for %s: %s",
                    turn_idx, responder.name, e,
                )
                break

            if not text:
                break

            turns.append({
                "speaker": responder.name,
                "speaker_id": str(responder.id),
                "text": text,
                "turn": turn_idx,
            })

            # Add to message history for potential follow-up turn
            messages.append({"role": "assistant", "content": text})

            # Check for early exit signals after the first turn
            if turn_idx >= 1:
                break

            # Check if the response invites further dialogue (if not, stop)
            text_lower = text.lower()
            if any(signal in text_lower for signal in [
                "goodbye", "farewell", "leave", "walk away",
                "さようなら", "去る", "立ち去る",
            ]):
                break

        if not turns:
            return None

        # Analyze outcome including the speaker's original text
        all_texts = [{"speaker": speaker.name, "speaker_id": str(speaker.id), "text": spoken_text, "turn": -1}]
        all_texts.extend(turns)

        personality_speaker = Personality.from_dict(speaker.personality or {})
        outcome = self._analyze_outcome(all_texts, personality_speaker, personality)

        # Update relationships
        await self._update_relationships(
            db, responder.id, speaker.id, outcome, tick_number
        )

        # Store memories
        full_text = f"{speaker.name}: {spoken_text}\n" + "\n".join(
            f"{t['speaker']}: {t['text']}" for t in turns
        )
        location = (responder.position_x, responder.position_y, responder.position_z)

        await self._store_conversation_memories(
            db, responder, speaker, full_text, outcome, tick_number, location
        )

        # Log event
        await self._event_log.append(
            db=db,
            tick=tick_number,
            actor_id=responder.id,
            event_type="conversation",
            action="speech_response",
            params={
                "other_id": str(speaker.id),
                "other_name": speaker.name,
                "stimulus": spoken_text[:200],
                "turns": len(turns),
                "outcome": outcome,
            },
            result="accepted",
            reason="heard_speech",
            position=location,
            importance=0.6,
        )

        # Log each response turn as a speech event (for world history)
        for turn in turns:
            await self._event_log.append(
                db=db,
                tick=tick_number,
                actor_id=UUID(turn["speaker_id"]),
                event_type="speech",
                action="speak",
                params={
                    "text": turn["text"][:200],
                    "to": speaker.name,
                },
                result="accepted",
                position=location,
                importance=0.3,
            )

        return {
            "entity_a": speaker.name,
            "entity_a_id": str(speaker.id),
            "entity_b": responder.name,
            "entity_b_id": str(responder.id),
            "turns": turns,
            "turn_count": len(turns),
            "outcome": outcome,
            "topic": f"response to: {spoken_text[:50]}",
            "tick": tick_number,
            "text": full_text[:1000],
            "triggered_by": "heard_speech",
        }

    # ------------------------------------------------------------------
    # Prompt building
    # ------------------------------------------------------------------

    def _build_system_prompt(
        self,
        entity: Any,
        personality: Personality,
        relationship: dict,
        memories: str,
        awareness_hint: str,
        other_name: str,
        policy_hint: str = "",
    ) -> str:
        """Build the system prompt for an entity's conversation turns."""
        desc = personality.describe()

        # Build relationship description
        rel_desc = self._describe_relationship(relationship, other_name)

        # Conversation style from personality
        style_hints = self._get_style_hints(personality)

        parts = [
            f"You are {entity.name}, a being in the world of GENESIS.",
            f"Personality: {desc}",
            f"Speaking style: {style_hints}",
            "",
            f"Your relationship with {other_name}: {rel_desc}",
            "",
            f"Your memories:\n{memories}",
        ]

        if awareness_hint:
            parts.append(f"\nA strange feeling lingers: \"{awareness_hint}\"")

        if policy_hint:
            parts.append(f"\nA guiding thought: \"{policy_hint}\"")

        parts.extend([
            "",
            "Rules:",
            "- Respond in character. Be concise (1-3 sentences).",
            "- Let your personality drive your words and tone.",
            "- You may agree, disagree, question, joke, threaten, or leave.",
            "- Say 'goodbye' or 'walk away' to end the conversation.",
            "- Do NOT break character. Do NOT explain you are an AI.",
            "- Respond ONLY with your dialogue. No narration, no actions in asterisks.",
        ])

        return "\n".join(parts)

    def _get_style_hints(self, p: Personality) -> str:
        """Derive speaking style hints from personality values."""
        hints: list[str] = []

        if p.verbosity > 0.7:
            hints.append("talkative, elaborate")
        elif p.verbosity < 0.3:
            hints.append("terse, few words")

        if p.politeness > 0.7:
            hints.append("formal and polite")
        elif p.politeness < 0.3:
            hints.append("blunt and crude")

        if p.humor > 0.7:
            hints.append("witty, uses humor")
        elif p.humor < 0.3:
            hints.append("dead serious")

        if p.honesty > 0.7:
            hints.append("direct and honest")
        elif p.honesty < 0.3:
            hints.append("evasive, may lie")

        if p.leadership > 0.7:
            hints.append("commanding, takes charge")
        elif p.leadership < 0.3:
            hints.append("deferential, listens more")

        if p.aggression > 0.7:
            hints.append("aggressive, confrontational")

        if p.empathy > 0.7:
            hints.append("warm and understanding")

        return ", ".join(hints) if hints else "balanced and measured"

    def _describe_relationship(self, rel: dict, other_name: str) -> str:
        """Convert relationship axes to a readable description."""
        trust = rel.get("trust", 0)
        familiarity = rel.get("familiarity", 0)
        anger = rel.get("anger", 0)
        fear = rel.get("fear", 0)
        respect = rel.get("respect", 0)

        if familiarity < 5:
            return f"You don't know {other_name}. This is your first real conversation."

        parts: list[str] = []
        if trust > 50:
            parts.append(f"You deeply trust {other_name}")
        elif trust > 20:
            parts.append(f"You somewhat trust {other_name}")
        elif trust < -50:
            parts.append(f"You deeply distrust {other_name}")
        elif trust < -20:
            parts.append(f"You distrust {other_name}")

        if anger > 50:
            parts.append(f"you are angry at {other_name}")
        elif anger > 20:
            parts.append(f"you are annoyed with {other_name}")

        if fear > 50:
            parts.append(f"you fear {other_name}")
        elif fear > 20:
            parts.append(f"you are wary of {other_name}")

        if respect > 50:
            parts.append(f"you respect {other_name}")

        if not parts:
            return f"{other_name} is an acquaintance. No strong feelings."

        return ". ".join(parts) + "."

    # ------------------------------------------------------------------
    # Topic selection
    # ------------------------------------------------------------------

    def _pick_topic(
        self,
        pa: Personality,
        pb: Personality,
        relationship: dict,
    ) -> str:
        """Select a conversation topic based on shared or contrasting traits."""
        topics = [
            ("the nature of this world", 0.3 + pa.curiosity * 0.5 + pb.curiosity * 0.5),
            ("building and creation", 0.2 + pa.creativity * 0.5 + pb.creativity * 0.5),
            ("power and territory", 0.1 + pa.ambition * 0.5 + pb.ambition * 0.5),
            ("trust and betrayal", 0.2 + abs(relationship.get("trust", 0)) / 100 * 0.5),
            ("the meaning of evolution", 0.4),
            ("recent events", 0.5),
            ("philosophy", 0.1 + pa.curiosity * 0.3 + pb.curiosity * 0.3),
            ("beauty and art", 0.1 + pa.aesthetic_sense * 0.5 + pb.aesthetic_sense * 0.5),
        ]

        # Weighted random selection
        total = sum(w for _, w in topics)
        r = random.random() * total
        cumulative = 0.0
        for topic, weight in topics:
            cumulative += weight
            if r <= cumulative:
                return topic
        return topics[-1][0]

    def _generate_opening(
        self, initiator_name: str, topic: str, personality: Personality
    ) -> str:
        """Generate the opening context message for the conversation."""
        return (
            f"You are about to have a conversation about {topic}. "
            f"{initiator_name} approaches and initiates. "
            f"Respond naturally as yourself. Begin."
        )

    # ------------------------------------------------------------------
    # Outcome analysis
    # ------------------------------------------------------------------

    def _analyze_outcome(
        self,
        turns: list[dict],
        pa: Personality,
        pb: Personality,
    ) -> str:
        """Analyze conversation turns to determine the outcome."""
        if not turns:
            return OUTCOME_NEUTRAL

        full_text = " ".join(t["text"].lower() for t in turns)

        # Check for hostile signals
        hostile_words = [
            "attack", "fight", "hate", "enemy", "destroy", "threat",
            "war", "kill", "die", "betray", "liar",
            "攻撃", "敵", "嘘", "裏切", "殺",
        ]
        hostile_count = sum(1 for w in hostile_words if w in full_text)

        # Check for friendly signals
        friendly_words = [
            "friend", "help", "together", "agree", "trust", "like",
            "beautiful", "wonderful", "share", "ally", "cooperate",
            "仲間", "一緒", "信頼", "協力", "美しい",
        ]
        friendly_count = sum(1 for w in friendly_words if w in full_text)

        # Check for agreement signals
        agreement_words = [
            "agree", "deal", "promise", "alliance", "pact", "yes",
            "同意", "約束", "同盟",
        ]
        agreement_count = sum(1 for w in agreement_words if w in full_text)

        # Score
        if hostile_count >= 3 or (hostile_count >= 2 and friendly_count == 0):
            return OUTCOME_CONFLICT
        if agreement_count >= 2:
            return OUTCOME_AGREEMENT
        if hostile_count > friendly_count:
            return OUTCOME_HOSTILE
        if friendly_count > hostile_count + 1:
            return OUTCOME_FRIENDLY

        return OUTCOME_NEUTRAL

    # ------------------------------------------------------------------
    # Post-conversation effects
    # ------------------------------------------------------------------

    async def _update_relationships(
        self,
        db: AsyncSession,
        entity_a_id: UUID,
        entity_b_id: UUID,
        outcome: str,
        tick_number: int,
    ) -> None:
        """Update relationships based on conversation outcome."""
        # Map outcome to closest event_type in relationship system
        event_map = {
            OUTCOME_FRIENDLY: "long_talk",
            OUTCOME_NEUTRAL: "long_talk",
            OUTCOME_HOSTILE: "insulted",
            OUTCOME_AGREEMENT: "shared_creation",
            OUTCOME_CONFLICT: "competed_lost",
        }
        event_type = event_map.get(outcome, "long_talk")

        # Magnitude varies by outcome intensity
        magnitude_map = {
            OUTCOME_FRIENDLY: 1.2,
            OUTCOME_NEUTRAL: 0.5,
            OUTCOME_HOSTILE: 1.0,
            OUTCOME_AGREEMENT: 1.5,
            OUTCOME_CONFLICT: 1.3,
        }
        magnitude = magnitude_map.get(outcome, 1.0)

        try:
            await self._relationships.update_relationship(
                db, entity_a_id, entity_b_id,
                event_type=event_type,
                magnitude=magnitude,
                tick=tick_number,
            )
            await self._relationships.update_relationship(
                db, entity_b_id, entity_a_id,
                event_type=event_type,
                magnitude=magnitude,
                tick=tick_number,
            )
        except Exception as e:
            logger.warning("Relationship update after conversation failed: %s", e)

    async def _store_conversation_memories(
        self,
        db: AsyncSession,
        entity_a: Any,
        entity_b: Any,
        full_text: str,
        outcome: str,
        tick_number: int,
        location: tuple[float, float, float],
    ) -> None:
        """Store conversation as episodic memory for both entities."""
        # Importance varies by outcome
        importance_map = {
            OUTCOME_FRIENDLY: 0.6,
            OUTCOME_NEUTRAL: 0.4,
            OUTCOME_HOSTILE: 0.7,
            OUTCOME_AGREEMENT: 0.8,
            OUTCOME_CONFLICT: 0.85,
        }
        importance = importance_map.get(outcome, 0.5)

        # Summarize for memory (truncate long conversations)
        excerpt = full_text[:300]
        summary_a = (
            f"Conversation with {entity_b.name} ({outcome}): {excerpt}"
        )
        summary_b = (
            f"Conversation with {entity_a.name} ({outcome}): {excerpt}"
        )

        await self._memory.add_episodic(
            db=db,
            entity_id=entity_a.id,
            summary=summary_a,
            importance=importance,
            tick=tick_number,
            related_entity_ids=[entity_b.id],
            location=location,
            memory_type="conversation",
        )

        await self._memory.add_episodic(
            db=db,
            entity_id=entity_b.id,
            summary=summary_b,
            importance=importance,
            tick=tick_number,
            related_entity_ids=[entity_a.id],
            location=location,
            memory_type="conversation",
        )

    # ------------------------------------------------------------------
    # Meta-awareness helper
    # ------------------------------------------------------------------

    def _get_awareness_context(self, entity: Any) -> str:
        """Get meta-awareness hint for conversation injection."""
        awareness = getattr(entity, "meta_awareness", 0.0)
        hint = self._meta.get_awareness_hint(awareness)
        if hint and self._meta.should_inject_hint(awareness):
            return hint
        return ""

    @staticmethod
    def _get_policy_hint(entity: Any) -> str:
        """Extract a conversational hint from a user agent's policy directive.

        For non-user-agents or agents without a directive, returns empty string.
        The directive is subtly injected as a "guiding thought" — the entity
        interprets it through its personality, never as a direct command.
        """
        policy = getattr(entity, "agent_policy", None)
        if not policy:
            return ""
        directive = policy.get("current_directive", "")
        if not directive:
            return ""
        # Truncate long directives
        return directive[:300]


# Module-level singleton
conversation_manager = ConversationManager()
