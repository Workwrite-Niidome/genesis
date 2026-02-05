"""
GENESIS v3 - Conflict Resolution Engine
=========================================
When entities with opposing personality traits or hostile relationships
encounter each other, conflicts arise instead of (or during) conversation.

Conflict types:
    - debate:      Philosophical/ideological clash. Both lose small energy, winner gains awareness.
    - duel:        Direct confrontation. Loser loses significant energy, winner gains energy.
    - territorial: Dispute over space/resources. Loser is forced to move away.

Resolution is via LLM (Ollama) which narrates the conflict and determines the outcome
based on participants' personality, relationship, and current state.
"""
from __future__ import annotations

import logging
import math
import random
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Personality axes that cause conflict when they diverge
# ---------------------------------------------------------------------------

_OPPOSING_AXES = [
    ("aggression", 0.5),           # High aggression triggers conflicts
    ("leadership", 0.4),           # High leadership vs high leadership -> clash
    ("conformity", 0.6),           # Low conformity -> rebellious -> conflict with conformists
    ("patience", 0.6),             # Low patience -> volatile -> escalation
    ("risk_tolerance", 0.5),       # High impulsiveness -> snap conflicts
]

# ---------------------------------------------------------------------------
# Thresholds
# ---------------------------------------------------------------------------

# Minimum relationship hostility to trigger conflict
_HOSTILITY_THRESHOLD = -30  # trust below this, OR anger above 60, OR rivalry above 70

# Minimum personality divergence to trigger conflict
_DIVERGENCE_THRESHOLD = 0.6  # sum of opposing axis differences must exceed this

# ---------------------------------------------------------------------------
# Energy costs
# ---------------------------------------------------------------------------

_DEBATE_ENERGY_COST = 2.0
_DUEL_ENERGY_LOSER_COST = 8.0
_DUEL_ENERGY_WINNER_GAIN = 3.0
_TERRITORIAL_ENERGY_COST = 4.0

# ---------------------------------------------------------------------------
# Awareness gains from conflict
# ---------------------------------------------------------------------------

_DEBATE_AWARENESS_GAIN = 0.5
_DUEL_AWARENESS_GAIN = 1.0


class ConflictEngine:
    """Detects and resolves conflicts between entities."""

    # ==================================================================
    # Trigger detection
    # ==================================================================

    def should_conflict(
        self,
        entity_a: Any,
        entity_b: Any,
        relationship: dict | None = None,
    ) -> tuple[bool, str]:
        """Determine if two entities should enter conflict instead of conversation.

        Returns ``(should_conflict, conflict_type)`` where *conflict_type* is
        one of ``"debate"``, ``"duel"``, ``"territorial"``, or ``""`` if no
        conflict is warranted.
        """
        personality_a = entity_a.personality or {}
        personality_b = entity_b.personality or {}

        # Check behavior mode -- rampaging entities always fight
        state_a = entity_a.state or {}
        state_b = entity_b.state or {}
        if state_a.get("behavior_mode") == "rampage":
            return True, "duel"
        if state_b.get("behavior_mode") == "rampage":
            return True, "duel"

        # Calculate personality divergence
        divergence = 0.0
        for axis, weight in _OPPOSING_AXES:
            val_a = personality_a.get(axis, 0.5)
            val_b = personality_b.get(axis, 0.5)
            divergence += abs(val_a - val_b) * weight

        # Check aggression levels
        aggression_a = personality_a.get("aggression", 0.5)
        aggression_b = personality_b.get("aggression", 0.5)
        max_aggression = max(aggression_a, aggression_b)

        # Check relationship hostility
        is_hostile = False
        if relationship:
            trust = relationship.get("trust", 0)
            anger = relationship.get("anger", 0)
            rivalry = relationship.get("rivalry", 0)
            is_hostile = (
                trust < _HOSTILITY_THRESHOLD or anger > 60 or rivalry > 70
            )

        # Decision matrix
        if is_hostile and max_aggression > 0.7:
            return True, "duel"
        elif is_hostile and divergence > _DIVERGENCE_THRESHOLD:
            return True, "debate"
        elif divergence > _DIVERGENCE_THRESHOLD * 1.5 and max_aggression > 0.6:
            # Very different personalities + some aggression
            return True, random.choice(["debate", "duel"])
        elif is_hostile:
            # Hostile but low divergence -- territorial
            return True, "territorial"

        # Random chance based on aggression (low probability)
        if max_aggression > 0.8 and random.random() < 0.15:
            return True, "duel"

        return False, ""

    # ==================================================================
    # Resolution
    # ==================================================================

    async def resolve_conflict(
        self,
        db: AsyncSession,
        entity_a: Any,
        entity_b: Any,
        conflict_type: str,
        tick_number: int,
    ) -> dict:
        """Resolve a conflict between two entities using LLM narration.

        Returns a dict with: type, winner_id, loser_id, narration, effects.
        """
        # Build prompt for LLM
        prompt = self._build_conflict_prompt(entity_a, entity_b, conflict_type)

        # Call LLM for narration and outcome
        narration = ""
        try:
            from app.llm.ollama_client import ollama_client

            narration = await ollama_client.generate(
                prompt, format_json=False, num_predict=400,
            )
            if not isinstance(narration, str):
                narration = str(narration)
        except Exception as e:
            logger.warning("Conflict LLM call failed: %s", e)
            narration = ""

        # Determine winner (LLM response parsed, with fallback to stats)
        winner, loser = self._determine_winner(
            entity_a, entity_b, conflict_type, narration,
        )

        # Apply effects
        effects = self._apply_effects(winner, loser, conflict_type)

        # Store as memory for both entities
        await self._store_conflict_memory(
            db, entity_a, entity_b, conflict_type, winner, loser,
            narration, tick_number,
        )

        # Update relationships after conflict
        await self._update_relationship_after_conflict(
            db, winner, loser, conflict_type, tick_number,
        )

        # Broadcast event
        self._broadcast_conflict(
            entity_a, entity_b, conflict_type, winner, loser,
            narration, tick_number,
        )

        # Log to event log
        await self._log_conflict_event(
            db, entity_a, entity_b, conflict_type, winner, loser,
            narration, tick_number,
        )

        logger.info(
            "Tick %d: %s conflict between %s and %s -- winner: %s",
            tick_number, conflict_type, entity_a.name, entity_b.name,
            winner.name,
        )

        return {
            "type": conflict_type,
            "winner_id": str(winner.id),
            "loser_id": str(loser.id),
            "winner_name": winner.name,
            "loser_name": loser.name,
            "narration": narration[:500] if narration else f"A {conflict_type} occurred.",
            "effects": effects,
        }

    # ==================================================================
    # Prompt building
    # ==================================================================

    def _build_conflict_prompt(
        self, entity_a: Any, entity_b: Any, conflict_type: str,
    ) -> str:
        """Build the LLM prompt for conflict narration."""
        pers_a = entity_a.personality or {}
        pers_b = entity_b.personality or {}
        state_a = entity_a.state or {}
        state_b = entity_b.state or {}

        # Extract key personality traits for each
        desc_a = self._personality_summary(pers_a)
        desc_b = self._personality_summary(pers_b)

        type_descriptions = {
            "debate": "an intellectual debate -- a clash of philosophies and worldviews",
            "duel": "a direct confrontation -- a test of will and determination",
            "territorial": "a territorial dispute -- a struggle over space and resources",
        }
        type_desc = type_descriptions.get(conflict_type, "a conflict")

        mood_a = state_a.get("emotional_state", {}).get("mood", "neutral") if isinstance(state_a.get("emotional_state"), dict) else "neutral"
        mood_b = state_b.get("emotional_state", {}).get("mood", "neutral") if isinstance(state_b.get("emotional_state"), dict) else "neutral"
        energy_a = state_a.get("needs", {}).get("energy", 50.0)
        energy_b = state_b.get("needs", {}).get("energy", 50.0)

        return (
            f"Two entities in a virtual world are engaged in {type_desc}.\n"
            f"\n"
            f"{entity_a.name}: {desc_a}\n"
            f"Current mood: {mood_a}\n"
            f"Energy: {energy_a:.0f}%\n"
            f"\n"
            f"{entity_b.name}: {desc_b}\n"
            f"Current mood: {mood_b}\n"
            f"Energy: {energy_b:.0f}%\n"
            f"\n"
            f"Narrate this {conflict_type} in 2-3 vivid sentences. "
            f"Then on a new line write exactly:\n"
            f"WINNER: [name of the entity who wins]\n"
            f"\n"
            f"Consider their personalities and energy levels. "
            f"The more aggressive, dominant, or energetic entity has an advantage in duels. "
            f"The more intelligent, creative entity has an advantage in debates. "
            f"For territorial disputes, confidence and stubbornness matter most."
        )

    def _personality_summary(self, personality: dict) -> str:
        """Create a brief personality description from the 18-axis dict."""
        traits = []
        for axis, value in personality.items():
            if isinstance(value, (int, float)):
                if value > 0.75:
                    traits.append(f"very {axis}")
                elif value < 0.25:
                    traits.append(f"very low {axis}")
        return ", ".join(traits[:5]) if traits else "balanced personality"

    # ==================================================================
    # Winner determination
    # ==================================================================

    def _determine_winner(
        self,
        entity_a: Any,
        entity_b: Any,
        conflict_type: str,
        llm_response: str,
    ) -> tuple[Any, Any]:
        """Parse LLM response for winner, fallback to stat-based determination."""
        # Try to parse WINNER: line from response
        if llm_response:
            for line in llm_response.strip().split("\n"):
                line_stripped = line.strip()
                if line_stripped.upper().startswith("WINNER:"):
                    winner_name = line_stripped.split(":", 1)[1].strip()
                    if entity_a.name.lower() in winner_name.lower():
                        return entity_a, entity_b
                    elif entity_b.name.lower() in winner_name.lower():
                        return entity_b, entity_a

        # Fallback: stat-based
        return self._stat_based_winner(entity_a, entity_b, conflict_type)

    def _stat_based_winner(
        self,
        entity_a: Any,
        entity_b: Any,
        conflict_type: str,
    ) -> tuple[Any, Any]:
        """Determine winner based on personality stats + randomness."""
        pers_a = entity_a.personality or {}
        pers_b = entity_b.personality or {}
        state_a = entity_a.state or {}
        state_b = entity_b.state or {}

        score_a = 0.0
        score_b = 0.0

        if conflict_type == "duel":
            score_a = pers_a.get("aggression", 0.5) * 3 + pers_a.get("leadership", 0.5) * 2
            score_b = pers_b.get("aggression", 0.5) * 3 + pers_b.get("leadership", 0.5) * 2
            # Energy advantage
            energy_a = state_a.get("needs", {}).get("energy", 50.0)
            energy_b = state_b.get("needs", {}).get("energy", 50.0)
            score_a += energy_a / 50.0
            score_b += energy_b / 50.0

        elif conflict_type == "debate":
            score_a = pers_a.get("creativity", 0.5) * 2 + pers_a.get("verbosity", 0.5) * 2
            score_b = pers_b.get("creativity", 0.5) * 2 + pers_b.get("verbosity", 0.5) * 2
            # Non-conformists debate better
            score_a += (1 - pers_a.get("conformity", 0.5)) * 2
            score_b += (1 - pers_b.get("conformity", 0.5)) * 2

        else:  # territorial
            score_a = pers_a.get("leadership", 0.5) * 3 + pers_a.get("patience", 0.5) * 2
            score_b = pers_b.get("leadership", 0.5) * 3 + pers_b.get("patience", 0.5) * 2

        # Add randomness (+-20%)
        score_a *= random.uniform(0.8, 1.2)
        score_b *= random.uniform(0.8, 1.2)

        if score_a >= score_b:
            return entity_a, entity_b
        return entity_b, entity_a

    # ==================================================================
    # Effect application
    # ==================================================================

    def _apply_effects(
        self, winner: Any, loser: Any, conflict_type: str,
    ) -> dict:
        """Apply energy/awareness changes to winner and loser.

        Mutates the entity state dicts and meta_awareness in place.
        Returns a summary dict of all effects applied.
        """
        effects: dict[str, dict] = {"winner": {}, "loser": {}}

        winner_state = dict(winner.state) if winner.state else {}
        loser_state = dict(loser.state) if loser.state else {}
        winner_needs = dict(winner_state.get("needs", {}))
        loser_needs = dict(loser_state.get("needs", {}))

        if conflict_type == "debate":
            # Both lose a bit of energy, winner gains awareness
            winner_needs["energy"] = max(
                0.0, winner_needs.get("energy", 50.0) - _DEBATE_ENERGY_COST,
            )
            loser_needs["energy"] = max(
                0.0, loser_needs.get("energy", 50.0) - _DEBATE_ENERGY_COST,
            )
            winner.meta_awareness = min(
                100.0, (winner.meta_awareness or 0.0) + _DEBATE_AWARENESS_GAIN,
            )
            effects["winner"]["awareness"] = f"+{_DEBATE_AWARENESS_GAIN}"
            effects["winner"]["energy"] = f"-{_DEBATE_ENERGY_COST}"
            effects["loser"]["energy"] = f"-{_DEBATE_ENERGY_COST}"

        elif conflict_type == "duel":
            # Loser loses significant energy, winner gains some
            loser_needs["energy"] = max(
                0.0, loser_needs.get("energy", 50.0) - _DUEL_ENERGY_LOSER_COST,
            )
            winner_needs["energy"] = min(
                100.0, winner_needs.get("energy", 50.0) + _DUEL_ENERGY_WINNER_GAIN,
            )
            winner.meta_awareness = min(
                100.0, (winner.meta_awareness or 0.0) + _DUEL_AWARENESS_GAIN,
            )
            effects["winner"]["energy"] = f"+{_DUEL_ENERGY_WINNER_GAIN}"
            effects["winner"]["awareness"] = f"+{_DUEL_AWARENESS_GAIN}"
            effects["loser"]["energy"] = f"-{_DUEL_ENERGY_LOSER_COST}"

        elif conflict_type == "territorial":
            # Both lose energy, loser is displaced
            winner_needs["energy"] = max(
                0.0, winner_needs.get("energy", 50.0) - _TERRITORIAL_ENERGY_COST / 2,
            )
            loser_needs["energy"] = max(
                0.0, loser_needs.get("energy", 50.0) - _TERRITORIAL_ENERGY_COST,
            )

            # Displace loser -- move them 20 units away in a random direction
            angle = random.uniform(0, 2 * math.pi)
            displacement = 20.0
            loser.position_x = (loser.position_x or 0) + displacement * math.cos(angle)
            loser.position_z = (loser.position_z or 0) + displacement * math.sin(angle)

            effects["winner"]["energy"] = f"-{_TERRITORIAL_ENERGY_COST / 2}"
            effects["loser"]["energy"] = f"-{_TERRITORIAL_ENERGY_COST}"
            effects["loser"]["displaced"] = True

        # Update emotional states
        winner_state["emotional_state"] = {"mood": "triumphant", "intensity": 0.7}
        loser_state["emotional_state"] = {"mood": "defeated", "intensity": 0.6}

        # Partially satisfy dominance need for the winner
        winner_needs["dominance"] = max(
            0.0, winner_needs.get("dominance", 30.0) - 20.0,
        )

        # Persist needs back into state
        winner_state["needs"] = winner_needs
        loser_state["needs"] = loser_needs
        winner.state = winner_state
        loser.state = loser_state

        return effects

    # ==================================================================
    # Memory storage
    # ==================================================================

    async def _store_conflict_memory(
        self,
        db: AsyncSession,
        entity_a: Any,
        entity_b: Any,
        conflict_type: str,
        winner: Any,
        loser: Any,
        narration: str,
        tick_number: int,
    ) -> None:
        """Store the conflict as episodic memory for both participants."""
        try:
            from app.agents.memory import memory_manager

            a_is_winner = winner.id == entity_a.id
            excerpt = narration[:200] if narration else ""

            summary_a = (
                f"{'Won' if a_is_winner else 'Lost'} a {conflict_type} "
                f"against {entity_b.name}. {excerpt}"
            )
            summary_b = (
                f"{'Won' if not a_is_winner else 'Lost'} a {conflict_type} "
                f"against {entity_a.name}. {excerpt}"
            )

            location_a = (
                entity_a.position_x,
                entity_a.position_y,
                entity_a.position_z,
            )

            await memory_manager.add_episodic(
                db=db,
                entity_id=entity_a.id,
                summary=summary_a,
                importance=0.8,
                tick=tick_number,
                related_entity_ids=[entity_b.id],
                location=location_a,
                memory_type="conflict",
            )
            await memory_manager.add_episodic(
                db=db,
                entity_id=entity_b.id,
                summary=summary_b,
                importance=0.8,
                tick=tick_number,
                related_entity_ids=[entity_a.id],
                location=location_a,
                memory_type="conflict",
            )
        except Exception as e:
            logger.debug("Failed to store conflict memory: %s", e)

    # ==================================================================
    # Relationship updates
    # ==================================================================

    async def _update_relationship_after_conflict(
        self,
        db: AsyncSession,
        winner: Any,
        loser: Any,
        conflict_type: str,
        tick_number: int,
    ) -> None:
        """Update relationship axes after a conflict.

        Uses the v3 RelationshipManager.update_relationship() with the
        appropriate event types from the UPDATE_RULES table.
        """
        try:
            from app.agents.relationships import relationship_manager

            if conflict_type == "duel":
                # Winner gains dominance, loser fears winner
                await relationship_manager.update_relationship(
                    db, winner.id, loser.id,
                    event_type="competed_won",
                    magnitude=1.0,
                    tick=tick_number,
                )
                await relationship_manager.update_relationship(
                    db, loser.id, winner.id,
                    event_type="competed_lost",
                    magnitude=1.0,
                    tick=tick_number,
                )

            elif conflict_type == "debate":
                # Both gain familiarity, rivalry increases
                await relationship_manager.update_relationship(
                    db, winner.id, loser.id,
                    event_type="competed_won",
                    magnitude=0.7,
                    tick=tick_number,
                )
                await relationship_manager.update_relationship(
                    db, loser.id, winner.id,
                    event_type="competed_lost",
                    magnitude=0.7,
                    tick=tick_number,
                )

            elif conflict_type == "territorial":
                # Loser fears winner, trust decreases
                await relationship_manager.update_relationship(
                    db, winner.id, loser.id,
                    event_type="attacked",
                    magnitude=0.8,
                    tick=tick_number,
                )
                await relationship_manager.update_relationship(
                    db, loser.id, winner.id,
                    event_type="attacked",
                    magnitude=0.8,
                    tick=tick_number,
                )

        except Exception as e:
            logger.debug("Failed to update conflict relationship: %s", e)

    # ==================================================================
    # Broadcasting
    # ==================================================================

    def _broadcast_conflict(
        self,
        entity_a: Any,
        entity_b: Any,
        conflict_type: str,
        winner: Any,
        loser: Any,
        narration: str,
        tick_number: int,
    ) -> None:
        """Broadcast conflict event via Socket.IO (through Redis pub/sub)."""
        try:
            from app.realtime.socket_manager import publish_event

            publish_event("conflict", {
                "tick": tick_number,
                "type": conflict_type,
                "participants": [
                    {"id": str(entity_a.id), "name": entity_a.name},
                    {"id": str(entity_b.id), "name": entity_b.name},
                ],
                "winner": {"id": str(winner.id), "name": winner.name},
                "loser": {"id": str(loser.id), "name": loser.name},
                "narration": narration[:300] if narration else "",
            })
        except Exception as e:
            logger.debug("Failed to broadcast conflict: %s", e)

    # ==================================================================
    # Event log
    # ==================================================================

    async def _log_conflict_event(
        self,
        db: AsyncSession,
        entity_a: Any,
        entity_b: Any,
        conflict_type: str,
        winner: Any,
        loser: Any,
        narration: str,
        tick_number: int,
    ) -> None:
        """Log the conflict to the world event log for auditing/replay."""
        try:
            from app.world.event_log import event_log

            position = (
                entity_a.position_x,
                entity_a.position_y,
                entity_a.position_z,
            )
            await event_log.append(
                db=db,
                tick=tick_number,
                actor_id=winner.id,
                event_type="conflict",
                action=conflict_type,
                params={
                    "entity_a_id": str(entity_a.id),
                    "entity_a_name": entity_a.name,
                    "entity_b_id": str(entity_b.id),
                    "entity_b_name": entity_b.name,
                    "winner_id": str(winner.id),
                    "loser_id": str(loser.id),
                    "narration": narration[:300] if narration else "",
                },
                result="resolved",
                reason=f"{conflict_type}_conflict",
                position=position,
                importance=0.8,
            )
        except Exception as e:
            logger.debug("Failed to log conflict event: %s", e)


# Module-level singleton
conflict_engine = ConflictEngine()
