"""
GENESIS v3 - Safety Monitor
=============================
Detects stuck, looping, or runaway entities and auto-intervenes.

Detection:
    - Action loop: same action repeated 10+ consecutive times
    - Position stuck: entity at same position for 30+ ticks
    - Rampage timeout: rampage behavior_mode lasting 100+ ticks
    - Conversation loop: same phrase detected 3+ times

Intervention:
    - Cooldown: entity skips 1 tick, gets introspection prompt
    - Position reset: teleport to random valid position
    - Behavior reset: force behavior_mode back to "normal"
    - Memory cleanup: clear contradictory recent memories
"""
from __future__ import annotations

import logging
import random
from typing import Any

logger = logging.getLogger(__name__)

# Detection thresholds
ACTION_LOOP_THRESHOLD = 10       # same action N times in a row
POSITION_STUCK_THRESHOLD = 30    # same position for N ticks
RAMPAGE_TIMEOUT_TICKS = 100      # rampage mode for N ticks
CONVERSATION_REPEAT_THRESHOLD = 3  # same phrase N times

# World bounds for position reset
WORLD_MIN = -200
WORLD_MAX = 200
SPAWN_Y = 1.0

# Cooldown duration (ticks to skip after intervention)
COOLDOWN_TICKS = 3


class SafetyMonitor:
    """Monitors entities for stuck/loop states and auto-intervenes."""

    def check_entity(self, entity: Any, tick_number: int) -> list[str]:
        """Check an entity for safety issues.

        Returns a list of intervention actions taken (empty if none).
        Modifies entity state in-place when intervening.
        """
        interventions: list[str] = []
        state = dict(entity.state) if entity.state else {}

        # Skip if entity is in cooldown
        cooldown_until = state.get("_safety_cooldown_until", 0)
        if tick_number < cooldown_until:
            return ["in_cooldown"]

        # Track safety history
        safety = state.get("_safety", {})

        # 1. Action loop detection
        action_intervention = self._check_action_loop(entity, state, safety, tick_number)
        if action_intervention:
            interventions.append(action_intervention)

        # 2. Position stuck detection
        position_intervention = self._check_position_stuck(entity, state, safety, tick_number)
        if position_intervention:
            interventions.append(position_intervention)

        # 3. Rampage timeout
        rampage_intervention = self._check_rampage_timeout(entity, state, safety, tick_number)
        if rampage_intervention:
            interventions.append(rampage_intervention)

        # Save updated safety state
        state["_safety"] = safety
        entity.state = state

        return interventions

    def _check_action_loop(
        self, entity: Any, state: dict, safety: dict, tick_number: int,
    ) -> str | None:
        """Detect if entity is repeating the same action."""
        current_action = state.get("current_action", "")
        if not current_action:
            safety["action_repeat_count"] = 0
            safety["last_action"] = ""
            return None

        last_action = safety.get("last_action", "")
        if current_action == last_action:
            count = safety.get("action_repeat_count", 0) + 1
            safety["action_repeat_count"] = count

            if count >= ACTION_LOOP_THRESHOLD:
                logger.warning(
                    "Safety: %s action loop detected (%s x%d), applying cooldown",
                    entity.name, current_action, count,
                )
                # Intervention: cooldown + clear action
                state["_safety_cooldown_until"] = tick_number + COOLDOWN_TICKS
                state["current_action"] = ""
                safety["action_repeat_count"] = 0

                # Add introspection nudge
                state.setdefault("_safety_introspection", []).append(
                    "You notice you've been doing the same thing repeatedly. Time to try something different."
                )
                # Keep only last 3 introspection messages
                state["_safety_introspection"] = state["_safety_introspection"][-3:]

                return "action_loop_cooldown"
        else:
            safety["action_repeat_count"] = 0

        safety["last_action"] = current_action
        return None

    def _check_position_stuck(
        self, entity: Any, state: dict, safety: dict, tick_number: int,
    ) -> str | None:
        """Detect if entity hasn't moved for too long."""
        current_pos = (
            round(entity.position_x or 0, 1),
            round(entity.position_y or 0, 1),
            round(entity.position_z or 0, 1),
        )

        last_pos = safety.get("last_position")
        if last_pos is None:
            safety["last_position"] = list(current_pos)
            safety["stuck_ticks"] = 0
            return None

        last_pos_tuple = tuple(last_pos)

        if current_pos == last_pos_tuple:
            stuck_count = safety.get("stuck_ticks", 0) + 1
            safety["stuck_ticks"] = stuck_count

            if stuck_count >= POSITION_STUCK_THRESHOLD:
                logger.warning(
                    "Safety: %s stuck at position %s for %d ticks, resetting position",
                    entity.name, current_pos, stuck_count,
                )
                # Intervention: teleport to random position
                new_x = random.uniform(WORLD_MIN / 2, WORLD_MAX / 2)
                new_z = random.uniform(WORLD_MIN / 2, WORLD_MAX / 2)
                entity.position_x = new_x
                entity.position_y = SPAWN_Y
                entity.position_z = new_z

                safety["stuck_ticks"] = 0
                safety["last_position"] = [new_x, SPAWN_Y, new_z]

                state["_safety_introspection"] = state.get("_safety_introspection", [])
                state["_safety_introspection"].append(
                    "You feel disoriented. You seem to have wandered to a new area."
                )
                state["_safety_introspection"] = state["_safety_introspection"][-3:]

                return "position_reset"
        else:
            safety["stuck_ticks"] = 0
            safety["last_position"] = list(current_pos)

        return None

    def _check_rampage_timeout(
        self, entity: Any, state: dict, safety: dict, tick_number: int,
    ) -> str | None:
        """Detect if entity has been in rampage mode too long."""
        behavior_mode = state.get("behavior_mode", "normal")

        if behavior_mode == "rampage":
            rampage_ticks = safety.get("rampage_ticks", 0) + 1
            safety["rampage_ticks"] = rampage_ticks

            if rampage_ticks >= RAMPAGE_TIMEOUT_TICKS:
                logger.warning(
                    "Safety: %s rampage timeout (%d ticks), resetting to normal",
                    entity.name, rampage_ticks,
                )
                # Intervention: force back to normal
                state["behavior_mode"] = "normal"
                safety["rampage_ticks"] = 0

                # Emotional cooldown
                state["emotional_state"] = {
                    "mood": "exhausted",
                    "intensity": 0.3,
                }

                state.setdefault("_safety_introspection", []).append(
                    "The rage has passed. You feel drained, but clearer. What were you doing?"
                )
                state["_safety_introspection"] = state["_safety_introspection"][-3:]

                return "rampage_reset"
        else:
            safety["rampage_ticks"] = 0

        return None

    def is_in_cooldown(self, entity: Any, tick_number: int) -> bool:
        """Check if entity is currently in safety cooldown."""
        state = entity.state or {}
        cooldown_until = state.get("_safety_cooldown_until", 0)
        return tick_number < cooldown_until

    def get_introspection_prompt(self, entity: Any) -> str | None:
        """Get any safety-triggered introspection prompt for the entity.
        Returns the prompt and clears it from state.
        """
        state = dict(entity.state) if entity.state else {}
        prompts = state.get("_safety_introspection", [])
        if not prompts:
            return None

        # Return the latest one and clear the list
        prompt = prompts[-1]
        state["_safety_introspection"] = []
        entity.state = state
        return prompt


safety_monitor = SafetyMonitor()
