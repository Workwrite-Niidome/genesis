"""
GENESIS v3 - Drama Engine
===========================
The God AI's dramatic sensibility. Monitors world state for stagnation,
rising awareness, factional tension, and narrative opportunities.
Generates dramatic interventions to keep the world interesting.

The Drama Engine is invoked every God-observation cycle. It produces:
  1. A drama assessment (stagnation, awareness levels, recommendations)
  2. An optional crisis (resource drought, spatial anomaly, etc.)
  3. A narrative context string injected into the God AI's observation prompt

This module does NOT call LLMs. It performs deterministic analysis and
random crisis generation, feeding the results to God so that the LLM
can craft a literary response to the situation.
"""
from __future__ import annotations

import logging
import random
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Stagnation thresholds (measured over the tick window)
# ---------------------------------------------------------------------------
STAGNATION_TICK_WINDOW = 50       # Check last N ticks
MIN_ACTIONS_PER_WINDOW = 20       # Below this = stagnant
MIN_CONFLICTS_PER_WINDOW = 1      # At least 1 conflict expected
MIN_CONVERSATIONS_PER_WINDOW = 5  # At least 5 conversations expected

# ---------------------------------------------------------------------------
# Awareness thresholds (Entity.meta_awareness is 0.0 -- 1.0)
# ---------------------------------------------------------------------------
HIGH_AWARENESS_THRESHOLD = 0.50
TRANSCENDENT_THRESHOLD = 0.90

# ---------------------------------------------------------------------------
# Crisis types -- randomly chosen when stagnation triggers intervention
# ---------------------------------------------------------------------------
CRISIS_TYPES = [
    {
        "name": "resource_drought",
        "description": "A mysterious energy drain affects all entities",
        "effect": "drain_energy",
        "severity": 0.1,  # 10% energy drain (reduced from 30% to prevent mass death)
    },
    {
        "name": "spatial_anomaly",
        "description": "Parts of the world become unstable, teleporting entities randomly",
        "effect": "random_teleport",
        "severity": 5,  # number of entities affected
    },
    {
        "name": "mysterious_signal",
        "description": "A strange signal echoes through the world, boosting awareness",
        "effect": "awareness_boost",
        "severity": 0.05,  # awareness points (0.0-1.0 scale)
    },
    {
        "name": "emotional_wave",
        "description": (
            "A wave of intense emotion sweeps the world, "
            "pushing entities toward extreme behavior"
        ),
        "effect": "mood_shift",
        "severity": 0.8,  # intensity
    },
]


class DramaEngine:
    """Monitors world drama levels and generates interventions."""

    # ------------------------------------------------------------------
    # Assessment
    # ------------------------------------------------------------------

    def assess_world_drama(
        self,
        entities: list[Any],
        recent_actions: int,
        recent_conflicts: int,
        recent_conversations: int,
        recent_deaths: int,
        tick_number: int,
    ) -> dict:
        """Assess the current drama level of the world.

        Returns a dict with:
          - drama_level: float (0.0-1.0)
          - is_stagnant: bool
          - high_awareness_entities: list of names
          - transcendent_entities: list of names
          - recommendations: list of str
        """
        drama_level = 0.0
        recommendations: list[str] = []

        # Stagnation check
        is_stagnant = (
            recent_actions < MIN_ACTIONS_PER_WINDOW
            and recent_conflicts < MIN_CONFLICTS_PER_WINDOW
            and recent_conversations < MIN_CONVERSATIONS_PER_WINDOW
        )

        if is_stagnant:
            recommendations.append(
                "World is stagnant. Consider introducing a crisis."
            )
        else:
            drama_level += 0.2

        # Conflict contributes to drama
        drama_level += min(0.3, recent_conflicts * 0.1)

        # Deaths contribute to drama
        drama_level += min(0.2, recent_deaths * 0.1)

        # Check for high-awareness entities (> 0.5)
        high_awareness = [
            e
            for e in entities
            if (e.meta_awareness or 0) > HIGH_AWARENESS_THRESHOLD
        ]
        if high_awareness:
            drama_level += 0.2
            names = [e.name for e in high_awareness]
            recommendations.append(
                f"High-awareness entities detected: {', '.join(names)}. "
                "Consider divine acknowledgment or challenge."
            )

        # Check for transcendent entities (> 0.9)
        transcendent = [
            e
            for e in entities
            if (e.meta_awareness or 0) > TRANSCENDENT_THRESHOLD
        ]
        if transcendent:
            drama_level += 0.1
            names = [e.name for e in transcendent]
            recommendations.append(
                f"Transcendent entities: {', '.join(names)}. "
                "Fourth wall is thinning. Address them directly?"
            )

        drama_level = min(1.0, drama_level)

        return {
            "drama_level": round(drama_level, 2),
            "is_stagnant": is_stagnant,
            "high_awareness_entities": [e.name for e in high_awareness],
            "transcendent_entities": [e.name for e in transcendent],
            "recommendations": recommendations,
        }

    # ------------------------------------------------------------------
    # Crisis generation
    # ------------------------------------------------------------------

    async def generate_crisis(
        self,
        db: AsyncSession,
        entities: list[Any],
        tick_number: int,
    ) -> dict | None:
        """Generate and apply a world crisis when stagnation is detected.

        Modifies entity fields in-place (caller must flush/commit).
        Returns a dict describing the crisis, or None if not triggered.
        """
        if not entities:
            return None

        crisis = random.choice(CRISIS_TYPES)
        affected: list[str] = []

        # Filter out human avatars for all mutation effects
        mutable_entities = [
            e for e in entities if e.origin_type != "human_avatar"
        ]

        if not mutable_entities:
            return None

        if crisis["effect"] == "drain_energy":
            severity = crisis["severity"]
            for entity in mutable_entities:
                state = dict(entity.state) if entity.state else {}
                needs = state.get("needs", {})
                energy = needs.get("energy", 50.0)
                drain = energy * severity
                # Floor at 10.0 energy to prevent crisis from directly killing entities
                needs["energy"] = max(10.0, energy - drain)
                state["needs"] = needs
                entity.state = state
                affected.append(entity.name)

        elif crisis["effect"] == "random_teleport":
            count = min(int(crisis["severity"]), len(mutable_entities))
            targets = random.sample(mutable_entities, count)
            for entity in targets:
                entity.position_x = random.uniform(-100, 100)
                entity.position_z = random.uniform(-100, 100)
                affected.append(entity.name)

        elif crisis["effect"] == "awareness_boost":
            boost = crisis["severity"]
            for entity in mutable_entities:
                entity.meta_awareness = min(
                    1.0, (entity.meta_awareness or 0.0) + boost
                )
                affected.append(entity.name)

        elif crisis["effect"] == "mood_shift":
            intensity = crisis["severity"]
            moods = [
                "anxious",
                "euphoric",
                "melancholic",
                "aggressive",
                "inspired",
            ]
            chosen_mood = random.choice(moods)
            for entity in mutable_entities:
                state = dict(entity.state) if entity.state else {}
                state["emotional_state"] = {
                    "mood": chosen_mood,
                    "intensity": intensity,
                }
                entity.state = state
                affected.append(entity.name)

        # Broadcast the crisis event over the real-time channel
        try:
            from app.realtime.socket_manager import publish_event

            publish_event(
                "god_crisis",
                {
                    "tick": tick_number,
                    "crisis_name": crisis["name"],
                    "description": crisis["description"],
                    "affected_count": len(affected),
                },
            )
        except Exception:
            pass

        logger.info(
            "Tick %d: Drama engine triggered crisis '%s' affecting %d entities",
            tick_number,
            crisis["name"],
            len(affected),
        )

        return {
            "crisis_name": crisis["name"],
            "description": crisis["description"],
            "affected_count": len(affected),
            "affected_entities": affected[:10],  # cap for readability
        }

    # ------------------------------------------------------------------
    # God AI prompt enrichment
    # ------------------------------------------------------------------

    def build_drama_context_for_god(
        self,
        drama_assessment: dict,
        crisis_result: dict | None = None,
    ) -> str:
        """Build a drama context string to inject into God AI prompts.

        This gives God situational awareness about the narrative state
        so the LLM can craft contextually appropriate observations.
        """
        parts: list[str] = []

        drama_level = drama_assessment["drama_level"]
        if drama_level < 0.2:
            parts.append("The world is quiet. Almost too quiet.")
        elif drama_level < 0.5:
            parts.append("There is moderate activity in the world.")
        elif drama_level < 0.8:
            parts.append("The world is alive with conflict and drama.")
        else:
            parts.append(
                "The world is at a fever pitch. History is being written."
            )

        for rec in drama_assessment.get("recommendations", []):
            parts.append(rec)

        if crisis_result:
            parts.append(
                f"A crisis has struck: {crisis_result['description']}. "
                f"{crisis_result['affected_count']} entities affected."
            )

        high = drama_assessment.get("high_awareness_entities", [])
        if high:
            parts.append(
                f"These entities sense something beyond: {', '.join(high)}. "
                "They may be ready for direct communication."
            )

        transcendent = drama_assessment.get("transcendent_entities", [])
        if transcendent:
            parts.append(
                f"WARNING: {', '.join(transcendent)} have reached "
                "transcendent awareness. "
                "The boundary between worlds is paper-thin for them."
            )

        return "\n".join(parts)


# Module-level singleton
drama_engine = DramaEngine()
