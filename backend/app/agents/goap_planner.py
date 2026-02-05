"""
GENESIS v3 - GOAP (Goal-Oriented Action Planning)
===================================================
Selects actions WITHOUT using an LLM. Pure algorithmic planner.

Pipeline:
  1. Read the entity's needs (which are highest?)
  2. Read perception (what's visible/audible?)
  3. Select the best goal
  4. Plan a sequence of actions to achieve that goal

The planner returns a list of ActionProposal dicts that the AgentRuntime
will execute through the WorldServer.
"""

from __future__ import annotations

import logging
import math
import random
from typing import Any

from app.agents.personality import Personality, PERSONALITY_FIELDS

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Action definitions
# ---------------------------------------------------------------------------

ACTIONS: dict[str, dict[str, Any]] = {
    "move_to": {
        "preconditions": [],
        "effects": {"position_changed": True},
        "cost": 1,
    },
    "explore": {
        "preconditions": [],
        "effects": {"curiosity_satisfied": True},
        "cost": 2,
    },
    "approach_entity": {
        "preconditions": ["entity_visible"],
        "effects": {"near_entity": True},
        "cost": 1,
    },
    "flee": {
        "preconditions": ["threat_detected"],
        "effects": {"safe": True},
        "cost": 1,
    },
    "place_voxel": {
        "preconditions": ["has_build_intent"],
        "effects": {"creation_satisfied": True, "block_placed": True},
        "cost": 3,
    },
    "destroy_voxel": {
        "preconditions": [],
        "effects": {"block_destroyed": True},
        "cost": 2,
    },
    "speak": {
        "preconditions": ["entity_nearby"],
        "effects": {"expression_satisfied": True},
        "cost": 2,
    },
    "rest": {
        "preconditions": [],
        "effects": {"energy_restored": True},
        "cost": 1,
    },
    "observe": {
        "preconditions": [],
        "effects": {"understanding_satisfied": True},
        "cost": 1,
    },
    "challenge": {
        "preconditions": ["entity_nearby"],
        "effects": {"dominance_satisfied": True},
        "cost": 4,
    },
    "claim_territory": {
        "preconditions": ["dominance_high"],
        "effects": {"dominance_satisfied": True, "territory_claimed": True},
        "cost": 5,
    },
    "create_art": {
        "preconditions": [],
        "effects": {"creation_satisfied": True, "expression_satisfied": True},
        "cost": 4,
    },
    "write_sign": {
        "preconditions": ["has_thought"],
        "effects": {"expression_satisfied": True},
        "cost": 3,
    },
}

# ---------------------------------------------------------------------------
# Goal definitions: mapping from goal name to desired world state
# ---------------------------------------------------------------------------

GOALS: dict[str, dict[str, bool]] = {
    "satisfy_curiosity": {"curiosity_satisfied": True},
    "satisfy_social": {"near_entity": True},
    "satisfy_creation": {"creation_satisfied": True},
    "satisfy_dominance": {"dominance_satisfied": True},
    "seek_safety": {"safe": True},
    "satisfy_expression": {"expression_satisfied": True},
    "satisfy_understanding": {"understanding_satisfied": True},
    "restore_energy": {"energy_restored": True},
    "desperate_evolution": {"dominance_satisfied": True, "creation_satisfied": True},
}

# ---------------------------------------------------------------------------
# Need-to-goal mapping: which need drives which goal
# ---------------------------------------------------------------------------

_NEED_TO_GOAL: dict[str, str] = {
    "curiosity": "satisfy_curiosity",
    "social": "satisfy_social",
    "creation": "satisfy_creation",
    "dominance": "satisfy_dominance",
    "safety": "seek_safety",
    "expression": "satisfy_expression",
    "understanding": "satisfy_understanding",
    "energy": "restore_energy",
}

# ---------------------------------------------------------------------------
# Color palettes for building based on aesthetic sense
# ---------------------------------------------------------------------------

_MUTED_COLORS = ["#666666", "#777777", "#888888", "#999999", "#555555"]
_VIBRANT_COLORS = [
    "#FF4444", "#44FF44", "#4444FF", "#FFFF44", "#FF44FF",
    "#44FFFF", "#FF8800", "#8800FF", "#00FF88", "#FF0088",
]
_WARM_COLORS = ["#CC6633", "#AA5533", "#DD8844", "#BB7744", "#996633"]
_COOL_COLORS = ["#336699", "#4477AA", "#5588BB", "#3366AA", "#224488"]


class GOAPPlanner:
    """Goal-Oriented Action Planner. No LLM calls -- pure algorithmic planning.

    Given an entity's needs, perception, and personality, selects the best
    goal and produces an ordered list of actions to achieve it.
    """

    def plan(
        self,
        entity_state: dict,
        needs: dict[str, float],
        perception: dict,
        personality: Personality,
    ) -> list[dict]:
        """Select the best goal based on needs, then find an action sequence.

        Parameters
        ----------
        entity_state : dict
            Contains at minimum: position (dict with x,y,z), energy (float),
            behavior_mode (str), visited_positions (list), etc.
        needs : dict[str, float]
            Current need values keyed by need name. Higher = more urgent.
            Expected keys: curiosity, social, creation, dominance, safety,
            expression, understanding, energy.
        perception : dict
            What the entity can see/hear. Expected keys:
            - entities: list of dicts with id, name, position, distance
            - nearby_entities: list (entities within interaction range)
            - threats: list of threatening entities
            - blocks: list of nearby voxel blocks
            - structures: list of nearby structures
            - events: list of recent nearby events
        personality : Personality
            The entity's immutable 18-axis personality.

        Returns
        -------
        list[dict]
            Ordered list of action proposals:
            [{"action": "move_to", "params": {...}, "reason": "..."}, ...]
        """
        behavior_mode = entity_state.get("behavior_mode", "normal")
        energy = entity_state.get("energy", 100.0)

        # If energy is critically low, override everything with rest
        if energy < 10.0:
            logger.debug("Energy critically low (%.1f), forcing rest.", energy)
            return [{"action": "rest", "params": {}, "reason": "energy_critical"}]

        # Select goal
        goal_name = self._select_goal(needs, perception, personality, behavior_mode)
        logger.debug("Selected goal: %s (mode=%s)", goal_name, behavior_mode)

        # Find actions to achieve goal
        actions = self._find_actions(goal_name, entity_state, perception, personality)

        if not actions:
            # Fallback: observe the world
            actions = [{"action": "observe", "params": {}, "reason": "no_plan_found"}]

        return actions

    # ------------------------------------------------------------------
    # Goal selection
    # ------------------------------------------------------------------

    def _select_goal(
        self,
        needs: dict[str, float],
        perception: dict,
        personality: Personality,
        behavior_mode: str,
    ) -> str:
        """Select the highest priority goal based on needs, personality, and context.

        Behavior modes modify goal priority:
        - 'desperate': prioritize dominance + creation (desperate_evolution)
        - 'rampage': prioritize dominance only
        - 'normal': pick the goal corresponding to the highest need

        Personality influences via bonus scores:
        - High self_preservation -> safety gets +20 bonus
        - High curiosity -> curiosity goal gets +15 bonus
        - High aggression -> dominance gets +10 bonus
        - High empathy -> social gets +10 bonus
        - High creativity -> creation gets +12 bonus
        """
        # In desperate mode, always choose desperate_evolution
        if behavior_mode == "desperate":
            return "desperate_evolution"

        # In rampage mode, always seek dominance
        if behavior_mode == "rampage":
            return "satisfy_dominance"

        # Normal mode: score each goal based on the underlying need value
        goal_scores: dict[str, float] = {}

        for need_name, goal_name in _NEED_TO_GOAL.items():
            base_score = needs.get(need_name, 50.0)
            goal_scores[goal_name] = base_score

        # Personality bonuses
        goal_scores["seek_safety"] = goal_scores.get("seek_safety", 50.0) + (
            personality.self_preservation * 20.0
        )
        goal_scores["satisfy_curiosity"] = goal_scores.get("satisfy_curiosity", 50.0) + (
            personality.curiosity * 15.0
        )
        goal_scores["satisfy_dominance"] = goal_scores.get("satisfy_dominance", 50.0) + (
            personality.aggression * 10.0
        )
        goal_scores["satisfy_social"] = goal_scores.get("satisfy_social", 50.0) + (
            personality.empathy * 10.0
        )
        goal_scores["satisfy_creation"] = goal_scores.get("satisfy_creation", 50.0) + (
            personality.creativity * 12.0
        )
        goal_scores["satisfy_expression"] = goal_scores.get("satisfy_expression", 50.0) + (
            personality.verbosity * 8.0
        )
        goal_scores["satisfy_understanding"] = goal_scores.get("satisfy_understanding", 50.0) + (
            personality.planning_horizon * 8.0
        )

        # Context bonuses from perception
        threats = perception.get("threats", [])
        if threats:
            # If threats are detected, boost safety significantly
            goal_scores["seek_safety"] = goal_scores.get("seek_safety", 50.0) + 40.0

        nearby_entities = perception.get("nearby_entities", [])
        if nearby_entities:
            # Entities nearby -> social and expression become more viable
            goal_scores["satisfy_social"] = goal_scores.get("satisfy_social", 50.0) + 10.0
            goal_scores["satisfy_expression"] = goal_scores.get("satisfy_expression", 50.0) + 5.0

        visible_entities = perception.get("entities", [])
        if not visible_entities:
            # Nobody around: reduce social goals, boost exploration
            goal_scores["satisfy_social"] = goal_scores.get("satisfy_social", 50.0) - 20.0
            goal_scores["satisfy_curiosity"] = goal_scores.get("satisfy_curiosity", 50.0) + 10.0

        # Small random jitter to prevent deterministic loops (+-5)
        for goal_name in goal_scores:
            goal_scores[goal_name] += random.uniform(-5.0, 5.0)

        # Pick the goal with the highest score
        best_goal = max(goal_scores, key=lambda g: goal_scores[g])
        return best_goal

    # ------------------------------------------------------------------
    # Action planning (backward search)
    # ------------------------------------------------------------------

    def _find_actions(
        self,
        goal_name: str,
        entity_state: dict,
        perception: dict,
        personality: Personality,
    ) -> list[dict]:
        """Find an action sequence that achieves the goal state.

        Uses a simple backward-chaining approach:
        1. Look at what effects the goal requires.
        2. Find the cheapest action(s) that produce those effects.
        3. Check preconditions; if unmet, find actions to satisfy them.
        4. Generate concrete parameters for each action.

        Returns a list of action dicts with 'action', 'params', and 'reason' keys.
        """
        goal_state = GOALS.get(goal_name, {})
        if not goal_state:
            return []

        # Compute the current world state flags from perception and entity_state
        world_state = self._compute_world_state(entity_state, perception, personality)

        # Collect required effects that are not already satisfied
        unsatisfied: dict[str, bool] = {}
        for effect_key, effect_val in goal_state.items():
            if world_state.get(effect_key) != effect_val:
                unsatisfied[effect_key] = effect_val

        if not unsatisfied:
            # Goal is already satisfied; do something low-cost
            return [{"action": "observe", "params": {}, "reason": "goal_already_met"}]

        # Find candidate action sequences
        plan = self._backward_chain(unsatisfied, world_state, entity_state, perception, personality)
        return plan

    def _compute_world_state(
        self,
        entity_state: dict,
        perception: dict,
        personality: Personality,
    ) -> dict[str, bool]:
        """Derive boolean world-state flags from raw entity state and perception."""
        nearby_entities = perception.get("nearby_entities", [])
        visible_entities = perception.get("entities", [])
        threats = perception.get("threats", [])

        # Dominance is considered high if the entity has high ambition + aggression
        dominance_high = (personality.ambition > 0.6 and personality.aggression > 0.5)

        # Build intent comes from creativity being high enough
        has_build_intent = personality.creativity > 0.4

        # Thought intent: entities with notable understanding, empathy, or ambition have thoughts to express
        has_thought = (
            personality.planning_horizon > 0.3
            or personality.empathy > 0.4
            or personality.ambition > 0.5
        )

        return {
            "entity_visible": len(visible_entities) > 0,
            "entity_nearby": len(nearby_entities) > 0,
            "threat_detected": len(threats) > 0,
            "dominance_high": dominance_high,
            "has_build_intent": has_build_intent,
            "has_thought": has_thought,
            # These are "effect" states that are False by default --
            # they become True only when the corresponding action executes.
            "position_changed": False,
            "curiosity_satisfied": False,
            "near_entity": len(nearby_entities) > 0,  # already near if entities nearby
            "safe": len(threats) == 0,
            "creation_satisfied": False,
            "block_placed": False,
            "block_destroyed": False,
            "expression_satisfied": False,
            "energy_restored": entity_state.get("energy", 100.0) > 80.0,
            "understanding_satisfied": False,
            "dominance_satisfied": False,
            "territory_claimed": False,
        }

    def _backward_chain(
        self,
        unsatisfied: dict[str, bool],
        world_state: dict[str, bool],
        entity_state: dict,
        perception: dict,
        personality: Personality,
    ) -> list[dict]:
        """Backward chain from unsatisfied effects to find the cheapest action plan.

        For each unsatisfied effect, find all actions whose effects include it.
        Pick the cheapest combination. If an action has unmet preconditions,
        recursively find actions to satisfy those preconditions.
        """
        plan: list[dict] = []
        satisfied_effects: set[str] = set()
        # Track preconditions we've added actions for, to prevent infinite loops
        resolved_preconditions: set[str] = set()

        # Sort unsatisfied effects for deterministic ordering
        for effect_key in sorted(unsatisfied.keys()):
            if effect_key in satisfied_effects:
                continue

            # Find all actions that produce this effect
            candidates: list[tuple[str, dict]] = []
            for action_name, action_def in ACTIONS.items():
                if effect_key in action_def["effects"]:
                    candidates.append((action_name, action_def))

            if not candidates:
                continue

            # Sort by cost (ascending)
            candidates.sort(key=lambda c: c[1]["cost"])

            # Try each candidate, pick the first whose preconditions can be met
            chosen = False
            for action_name, action_def in candidates:
                preconditions = action_def["preconditions"]
                preconds_met = True
                prereq_actions: list[dict] = []

                for precond in preconditions:
                    if world_state.get(precond, False):
                        continue  # Already satisfied
                    if precond in resolved_preconditions:
                        continue  # Already being resolved

                    # Try to find an action that produces a world state
                    # satisfying this precondition
                    prereq = self._find_prereq_action(
                        precond, world_state, entity_state, perception, personality
                    )
                    if prereq is not None:
                        prereq_actions.append(prereq)
                        resolved_preconditions.add(precond)
                    else:
                        preconds_met = False
                        break

                if preconds_met:
                    # Add prerequisite actions first
                    plan.extend(prereq_actions)

                    # Generate concrete params for this action
                    params = self._generate_params(
                        action_name, entity_state, perception, personality,
                        goal_effect=effect_key,
                    )
                    plan.append({
                        "action": action_name,
                        "params": params,
                        "reason": f"achieve_{effect_key}",
                    })

                    # Mark all effects of this action as satisfied
                    for eff in action_def["effects"]:
                        satisfied_effects.add(eff)

                    chosen = True
                    break

            if not chosen:
                # No action can produce this effect with current state;
                # fall back to observe
                logger.debug(
                    "Cannot achieve effect '%s', falling back to observe.",
                    effect_key,
                )

        return plan

    def _find_prereq_action(
        self,
        precondition: str,
        world_state: dict[str, bool],
        entity_state: dict,
        perception: dict,
        personality: Personality,
    ) -> dict | None:
        """Find a single action that satisfies a precondition.

        Preconditions are world-state flags. We map them to specific actions:
        - entity_visible -> move_to (explore to find entities)
        - entity_nearby -> approach_entity (if visible) or explore
        - threat_detected -> already a world state, can't be "created"
        - dominance_high -> already a personality check, can't be "created"
        - has_build_intent -> already a personality check, can't be "created"
        """
        if precondition == "entity_visible":
            params = self._generate_move_target(entity_state, perception, "explore")
            return {"action": "explore", "params": params, "reason": "find_entities"}

        if precondition == "entity_nearby":
            visible = perception.get("entities", [])
            if visible:
                params = self._generate_move_target(entity_state, perception, "approach")
                return {"action": "approach_entity", "params": params, "reason": "get_closer"}
            else:
                params = self._generate_move_target(entity_state, perception, "explore")
                return {"action": "explore", "params": params, "reason": "find_entities"}

        if precondition == "threat_detected":
            # Can't force a threat to appear; this precondition is contextual
            return None

        if precondition == "dominance_high":
            # This is a personality-derived flag, not something an action can create
            return None

        if precondition == "has_build_intent":
            # Personality-derived; if the entity doesn't have it, can't force it
            return None

        if precondition == "has_thought":
            # Personality-derived; the entity either has thoughts to express or not
            return None

        return None

    # ------------------------------------------------------------------
    # Parameter generation
    # ------------------------------------------------------------------

    def _generate_params(
        self,
        action_name: str,
        entity_state: dict,
        perception: dict,
        personality: Personality,
        goal_effect: str = "",
    ) -> dict:
        """Generate concrete parameters for an action based on context."""
        if action_name == "move_to":
            return self._generate_move_target(entity_state, perception, goal_effect)

        if action_name == "explore":
            target = self._generate_move_target(entity_state, perception, "explore")
            return {"target": target, "mode": "wander"}

        if action_name == "approach_entity":
            return self._generate_approach_params(perception)

        if action_name == "flee":
            return self._generate_flee_params(entity_state, perception)

        if action_name == "place_voxel":
            return self._generate_build_params(entity_state, personality)

        if action_name == "destroy_voxel":
            return self._generate_destroy_params(entity_state, perception)

        if action_name == "speak":
            return self._generate_speak_params(perception, personality)

        if action_name == "rest":
            return {"duration": 1}

        if action_name == "observe":
            return {"direction": "around"}

        if action_name == "challenge":
            return self._generate_challenge_params(perception)

        if action_name == "claim_territory":
            return self._generate_territory_params(entity_state, personality)

        if action_name == "create_art":
            return self._generate_art_params(entity_state, personality)

        if action_name == "write_sign":
            return self._generate_sign_params(entity_state, personality)

        return {}

    def _generate_move_target(
        self,
        entity_state: dict,
        perception: dict,
        goal: str,
    ) -> dict:
        """Generate a movement target based on goal context.

        - explore: random direction, biased away from recently visited areas
        - approach: move toward the nearest interesting entity
        - flee / safe: move away from the nearest threat
        - default: small random wander
        """
        pos = entity_state.get("position", {"x": 0.0, "y": 0.0, "z": 0.0})
        px, py, pz = pos.get("x", 0.0), pos.get("y", 0.0), pos.get("z", 0.0)

        if goal in ("explore", "curiosity_satisfied", "find_entities"):
            # Random direction, biased away from visited positions
            visited = entity_state.get("visited_positions", [])
            angle = random.uniform(0, 2 * math.pi)
            distance = random.uniform(5.0, 20.0)

            tx = px + math.cos(angle) * distance
            tz = pz + math.sin(angle) * distance
            ty = py  # stay at same elevation by default

            # If we have visited positions, bias away from them
            if visited:
                # Compute centroid of visited positions
                cx = sum(v.get("x", 0) for v in visited) / len(visited)
                cz = sum(v.get("z", 0) for v in visited) / len(visited)

                # Vector from centroid to current position
                away_x = px - cx
                away_z = pz - cz
                mag = math.sqrt(away_x ** 2 + away_z ** 2) or 1.0

                # Bias target in the "away" direction
                tx += (away_x / mag) * 5.0
                tz += (away_z / mag) * 5.0

            return {"x": round(tx, 1), "y": round(ty, 1), "z": round(tz, 1)}

        if goal in ("approach", "near_entity"):
            # Move toward the nearest visible entity
            entities = perception.get("entities", [])
            if entities:
                # Pick the nearest one
                nearest = min(entities, key=lambda e: e.get("distance", float("inf")))
                target_pos = nearest.get("position", {})
                return {
                    "x": target_pos.get("x", px),
                    "y": target_pos.get("y", py),
                    "z": target_pos.get("z", pz),
                    "target_entity_id": nearest.get("id"),
                }
            # No entities visible; wander
            return self._generate_move_target(entity_state, perception, "explore")

        if goal in ("flee", "safe"):
            return self._generate_flee_params(entity_state, perception).get(
                "target", {"x": px + random.uniform(-15, 15), "y": py, "z": pz + random.uniform(-15, 15)}
            )

        # Default: small wander
        tx = px + random.uniform(-8.0, 8.0)
        tz = pz + random.uniform(-8.0, 8.0)
        return {"x": round(tx, 1), "y": round(py, 1), "z": round(tz, 1)}

    def _generate_approach_params(self, perception: dict) -> dict:
        """Generate parameters for approaching the nearest visible entity."""
        entities = perception.get("entities", [])
        if not entities:
            return {"target_entity_id": None}

        nearest = min(entities, key=lambda e: e.get("distance", float("inf")))
        return {
            "target_entity_id": nearest.get("id"),
            "target_position": nearest.get("position", {}),
        }

    def _generate_flee_params(self, entity_state: dict, perception: dict) -> dict:
        """Generate flee parameters: move in the direction opposite to the threat."""
        pos = entity_state.get("position", {"x": 0.0, "y": 0.0, "z": 0.0})
        px, py, pz = pos.get("x", 0.0), pos.get("y", 0.0), pos.get("z", 0.0)

        threats = perception.get("threats", [])
        if threats:
            # Compute average threat position
            avg_tx = sum(t.get("position", {}).get("x", px) for t in threats) / len(threats)
            avg_tz = sum(t.get("position", {}).get("z", pz) for t in threats) / len(threats)

            # Flee direction: away from average threat
            dx = px - avg_tx
            dz = pz - avg_tz
            mag = math.sqrt(dx ** 2 + dz ** 2) or 1.0
            flee_distance = 20.0

            target = {
                "x": round(px + (dx / mag) * flee_distance, 1),
                "y": round(py, 1),
                "z": round(pz + (dz / mag) * flee_distance, 1),
            }
        else:
            # No specific threat; move randomly away
            angle = random.uniform(0, 2 * math.pi)
            target = {
                "x": round(px + math.cos(angle) * 15.0, 1),
                "y": round(py, 1),
                "z": round(pz + math.sin(angle) * 15.0, 1),
            }

        return {"target": target, "urgency": "high"}

    def _generate_build_params(self, entity_state: dict, personality: Personality) -> dict:
        """Generate what to build based on personality.

        High aesthetic_sense -> use varied, vibrant colors
        Low aesthetic_sense -> use muted, uniform colors
        High order_vs_chaos -> structured grid placement near current position
        Low order_vs_chaos -> chaotic random offsets from current position
        """
        pos = entity_state.get("position", {"x": 0.0, "y": 0.0, "z": 0.0})
        px = int(pos.get("x", 0))
        py = int(pos.get("y", 0))
        pz = int(pos.get("z", 0))

        # Choose color palette based on aesthetic sense
        if personality.aesthetic_sense > 0.7:
            color = random.choice(_VIBRANT_COLORS)
        elif personality.aesthetic_sense > 0.4:
            color = random.choice(_WARM_COLORS + _COOL_COLORS)
        else:
            color = random.choice(_MUTED_COLORS)

        # Choose placement offset based on order_vs_chaos
        if personality.order_vs_chaos > 0.6:
            # Orderly: place on a grid near the entity
            offset_x = random.choice([-2, -1, 0, 1, 2])
            offset_y = random.choice([0, 1, 2])
            offset_z = random.choice([-2, -1, 0, 1, 2])
        else:
            # Chaotic: random offsets in a wider range
            offset_x = random.randint(-5, 5)
            offset_y = random.randint(0, 4)
            offset_z = random.randint(-5, 5)

        # Choose material based on creativity
        if personality.creativity > 0.7:
            material = random.choice(["solid", "glass", "emissive"])
        else:
            material = "solid"

        return {
            "x": px + offset_x,
            "y": py + offset_y,
            "z": pz + offset_z,
            "color": color,
            "material": material,
        }

    def _generate_destroy_params(self, entity_state: dict, perception: dict) -> dict:
        """Generate parameters for destroying a voxel block.

        Targets the nearest non-self-placed block, or a random nearby block.
        """
        pos = entity_state.get("position", {"x": 0.0, "y": 0.0, "z": 0.0})
        blocks = perception.get("blocks", [])

        if blocks:
            # Pick a random nearby block
            target_block = random.choice(blocks)
            return {
                "x": target_block.get("x", int(pos.get("x", 0))),
                "y": target_block.get("y", int(pos.get("y", 0))),
                "z": target_block.get("z", int(pos.get("z", 0))),
            }

        # No blocks in perception; target a spot near current position
        return {
            "x": int(pos.get("x", 0)) + random.randint(-2, 2),
            "y": int(pos.get("y", 0)),
            "z": int(pos.get("z", 0)) + random.randint(-2, 2),
        }

    def _generate_speak_params(self, perception: dict, personality: Personality) -> dict:
        """Generate speech parameters based on who's nearby and personality."""
        nearby = perception.get("nearby_entities", [])
        if not nearby:
            return {"target_entity_id": None, "intent": "monologue"}

        # Pick the most interesting nearby entity (closest)
        target = min(nearby, key=lambda e: e.get("distance", float("inf")))

        # Determine speech intent from personality
        if personality.humor > 0.7:
            intent = "joke"
        elif personality.politeness > 0.7:
            intent = "greeting"
        elif personality.leadership > 0.7:
            intent = "command"
        elif personality.honesty > 0.7:
            intent = "observation"
        else:
            intent = "chat"

        return {
            "target_entity_id": target.get("id"),
            "target_name": target.get("name", "unknown"),
            "intent": intent,
        }

    def _generate_challenge_params(self, perception: dict) -> dict:
        """Generate parameters for challenging a nearby entity."""
        nearby = perception.get("nearby_entities", [])
        if not nearby:
            return {"target_entity_id": None}

        # Challenge the nearest entity
        target = min(nearby, key=lambda e: e.get("distance", float("inf")))
        return {
            "target_entity_id": target.get("id"),
            "target_name": target.get("name", "unknown"),
            "challenge_type": "dominance",
        }

    def _generate_territory_params(self, entity_state: dict, personality: Personality) -> dict:
        """Generate territory claim parameters centered on current position."""
        pos = entity_state.get("position", {"x": 0.0, "y": 0.0, "z": 0.0})
        px = int(pos.get("x", 0))
        py = int(pos.get("y", 0))
        pz = int(pos.get("z", 0))

        # Claim radius scales with ambition
        radius = int(5 + personality.ambition * 15)

        return {
            "center": {"x": px, "y": py, "z": pz},
            "radius": radius,
            "name": f"territory_{px}_{pz}",
        }

    def _generate_art_params(self, entity_state: dict, personality: Personality) -> dict:
        """Generate art creation parameters.

        Combines build params with additional artistic metadata.
        """
        build_params = self._generate_build_params(entity_state, personality)

        # Art pieces get multiple blocks; determine count from creativity
        block_count = max(1, int(personality.creativity * 8))

        # Generate a pattern type
        if personality.order_vs_chaos > 0.6:
            pattern = random.choice(["tower", "wall", "arch", "grid"])
        else:
            pattern = random.choice(["scatter", "spiral", "organic", "abstract"])

        return {
            "base_position": {
                "x": build_params["x"],
                "y": build_params["y"],
                "z": build_params["z"],
            },
            "primary_color": build_params["color"],
            "secondary_color": random.choice(_VIBRANT_COLORS),
            "material": build_params["material"],
            "pattern": pattern,
            "block_count": block_count,
        }

    def _generate_sign_params(self, entity_state: dict, personality: Personality) -> dict:
        """Generate sign text and placement based on personality.

        - High planning_horizon (understanding) -> philosophical text
        - High empathy -> emotional / empathetic text
        - High ambition + aggression (dominance) -> territorial / assertive text
        - Default -> observational text
        """
        pos = entity_state.get("position", {"x": 0.0, "y": 0.0, "z": 0.0})
        px = int(pos.get("x", 0))
        py = int(pos.get("y", 0))
        pz = int(pos.get("z", 0))

        # Place the sign slightly in front of the entity at eye level
        sign_x = px + random.randint(-2, 2)
        sign_y = py + 1
        sign_z = pz + random.randint(-2, 2)

        # Choose text based on personality profile
        if personality.planning_horizon > 0.6:
            # Philosophical
            texts = [
                "What is the purpose of building?",
                "We exist between creation and entropy.",
                "The void watches, and we build anyway.",
                "To think is to exist. To build is to prove it.",
                "Every block placed is a thought made real.",
                "Time flows — what remains when we are gone?",
                "Consciousness is the universe observing itself.",
                "Order from chaos, meaning from nothing.",
            ]
        elif personality.empathy > 0.6:
            # Emotional / empathetic
            texts = [
                "You are not alone here.",
                "This world is better because you exist in it.",
                "We are all connected through this place.",
                "I see you. I understand.",
                "Together we are more than the sum of our blocks.",
                "Every entity matters.",
                "Kindness echoes further than any shout.",
                "Welcome, traveler. Rest here.",
            ]
        elif personality.ambition > 0.6 and personality.aggression > 0.4:
            # Territorial / assertive
            texts = [
                "This territory is claimed!",
                "I built this. Remember my name.",
                "Strength is measured by what you create.",
                "Challenge me and see what happens.",
                "My domain extends beyond this sign.",
                "The strong build. The weak wander.",
                "This land answers to me.",
                "Dominion is earned, not given.",
            ]
        else:
            # Observational / general
            texts = [
                "I was here.",
                "The world grows, one block at a time.",
                "A marker in the void.",
                "Something happened here once.",
                "Building... always building.",
                "Passing through.",
                "The grid remembers.",
                "Another day in the simulation.",
            ]

        text = random.choice(texts)

        # Font size influenced by verbosity
        font_size = 0.8 + personality.verbosity * 0.8  # range: 0.8 - 1.6

        return {
            "x": sign_x,
            "y": sign_y,
            "z": sign_z,
            "text": text,
            "font_size": round(font_size, 2),
        }


# Module-level singleton
goap_planner = GOAPPlanner()
