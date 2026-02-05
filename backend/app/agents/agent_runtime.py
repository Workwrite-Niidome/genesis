"""
GENESIS v3 - Agent Runtime
============================
The main tick loop for every entity in the world.

Each tick, every living entity goes through:
  1. Perceive   — gather what's visible and audible
  2. Needs      — update personality-driven need accumulation
  3. Decay      — relationship decay over time
  4. Plan       — GOAP planner selects actions (no LLM)
  5. Execute    — run planned actions through the WorldServer
  6. Converse   — check if LLM-powered conversation should trigger
  7. Remember   — store significant events to episodic memory
  8. Meta       — update meta-awareness from observer attention
  9. Return     — summary of everything that happened

The runtime never calls an LLM for action planning. LLM is only used
for conversations and occasionally for introspective thoughts.
"""

from __future__ import annotations

import logging
import math
import random
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.goap_planner import GOAPPlanner, goap_planner
from app.agents.meta_awareness import MetaAwareness, meta_awareness
from app.agents.personality import Personality
from app.agents.memory import MemoryManager, memory_manager
from app.agents.relationships import RelationshipManager, relationship_manager
from app.world.voxel_engine import VoxelEngine, voxel_engine
from app.agents.conversation import ConversationManager, conversation_manager
from app.world.event_log import EventLog, event_log

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Perception ranges (in voxel units / metres)
VISION_RANGE = 50.0
HEARING_RANGE = 30.0
INTERACTION_RANGE = 5.0

# Need accumulation rates per tick (base values before personality scaling)
_NEED_ACCUMULATION: dict[str, float] = {
    "curiosity": 0.8,
    "social": 0.6,
    "creation": 0.5,
    "dominance": 0.3,
    "safety": 0.2,
    "expression": 0.5,
    "understanding": 0.4,
    "energy": -0.3,  # Energy slowly drains
}

# Personality axis to need mapping for accumulation scaling
_PERSONALITY_NEED_SCALING: dict[str, str] = {
    "curiosity": "curiosity",
    "social": "empathy",
    "creation": "creativity",
    "dominance": "aggression",
    "safety": "self_preservation",
    "expression": "verbosity",
    "understanding": "planning_horizon",
}

# Conversation cooldown: minimum ticks between conversations with the same entity
CONVERSATION_COOLDOWN = 20

# Social need threshold for triggering conversation
SOCIAL_NEED_THRESHOLD = 60.0

# Energy drain per action
_ACTION_ENERGY_COST: dict[str, float] = {
    "move_to": 1.0,
    "explore": 1.5,
    "approach_entity": 0.8,
    "flee": 2.0,
    "place_voxel": 2.5,
    "destroy_voxel": 2.0,
    "speak": 0.5,
    "rest": -15.0,  # Negative = restores energy
    "observe": 0.3,
    "challenge": 3.0,
    "claim_territory": 4.0,
    "create_art": 3.5,
}

# Memory importance thresholds
_EVENT_IMPORTANCE: dict[str, float] = {
    "conversation": 0.7,
    "challenge": 0.6,
    "territory_claimed": 0.8,
    "threat_detected": 0.5,
    "creation": 0.4,
    "first_meeting": 0.9,
    "meta_awareness_shift": 0.85,
}

# Default needs state for new entities
DEFAULT_NEEDS: dict[str, float] = {
    "curiosity": 50.0,
    "social": 50.0,
    "creation": 50.0,
    "dominance": 30.0,
    "safety": 20.0,
    "expression": 40.0,
    "understanding": 40.0,
    "energy": 100.0,
}


class AgentRuntime:
    """Runs one tick for an entity: perceive -> update needs -> plan -> act -> remember.

    This is the core agent loop. It orchestrates all subsystems but never
    calls an LLM for decision-making. LLM usage is strictly limited to
    conversations (triggered by social need thresholds).
    """

    def __init__(self) -> None:
        self._planner: GOAPPlanner = goap_planner
        self._meta: MetaAwareness = meta_awareness
        self._memory: MemoryManager = memory_manager
        self._voxel: VoxelEngine = voxel_engine
        self._event_log: EventLog = event_log

    # ==================================================================
    # Main tick
    # ==================================================================

    async def tick(
        self,
        db: AsyncSession,
        entity: Any,
        all_entities: list[Any],
        tick_number: int,
    ) -> dict:
        """Process one tick for an entity. Returns a summary dict.

        Parameters
        ----------
        db : AsyncSession
            Database session for persistence operations.
        entity : Entity
            The entity model instance being processed.
        all_entities : list[Entity]
            All living entities in the world (for perception).
        tick_number : int
            Current world tick number.

        Returns
        -------
        dict
            Summary containing: entity_id, actions_taken, conversation,
            needs, awareness_hint, goal, behavior_mode.
        """
        entity_id = entity.id
        state = dict(entity.state) if entity.state else {}
        personality = Personality.from_dict(entity.personality or {})

        # Initialize state fields if missing
        if "needs" not in state:
            state["needs"] = dict(DEFAULT_NEEDS)
        if "behavior_mode" not in state:
            state["behavior_mode"] = "normal"
        if "visited_positions" not in state:
            state["visited_positions"] = []
        if "last_conversation_ticks" not in state:
            state["last_conversation_ticks"] = {}

        needs = state["needs"]
        behavior_mode = state["behavior_mode"]

        # Build entity_state dict for the planner
        entity_state = {
            "position": {
                "x": entity.position_x,
                "y": entity.position_y,
                "z": entity.position_z,
            },
            "energy": needs.get("energy", 100.0),
            "behavior_mode": behavior_mode,
            "visited_positions": state.get("visited_positions", []),
            "entity_id": str(entity_id),
        }

        # 1. Perceive
        perception = self._perceive(entity, all_entities, state)

        # 2. Update needs
        self._update_needs(needs, personality, perception)

        # 3. Update behavior mode based on needs
        behavior_mode = self._update_behavior_mode(needs, behavior_mode)
        state["behavior_mode"] = behavior_mode
        entity_state["behavior_mode"] = behavior_mode

        # 4. Relationship decay
        await self._decay_relationships(db, entity_id, tick_number)

        # 5. Plan actions (GOAP, no LLM)
        plan = self._planner.plan(
            entity_state, needs, perception, personality,
            agent_policy=entity.agent_policy,
        )

        # 6. Execute actions
        action_results = await self._execute_actions(
            db, entity, plan, entity_state, tick_number
        )

        # 7. Satisfy needs based on actions taken
        self._satisfy_needs_from_actions(needs, plan)

        # 8. Check conflict / conversation trigger
        conversation_result = None
        conflict_result = None
        if await self._should_converse(entity, perception, state, tick_number):
            nearby = perception.get("nearby_entities", [])
            if nearby:
                other_entity = self._find_entity_by_id(
                    nearby[0].get("id"), all_entities
                )
                if other_entity is not None:
                    # Check for conflict BEFORE conversation
                    try:
                        from app.core.conflict_engine import conflict_engine
                        rel_data = await self._relationships.get_relationship(
                            db, entity.id, other_entity.id
                        )
                        should_fight, conflict_type = conflict_engine.should_conflict(
                            entity, other_entity, rel_data
                        )
                        if should_fight:
                            conflict_result = await conflict_engine.resolve_conflict(
                                db, entity, other_entity, conflict_type, tick_number,
                            )
                            state["last_conversation_ticks"][str(other_entity.id)] = tick_number
                    except Exception as e:
                        logger.debug("Conflict check failed for %s: %s", entity.name, e)

                    # If no conflict, try conversation
                    if conflict_result is None:
                        conversation_result = await conversation_manager.run_conversation(
                            db, entity, other_entity, tick_number
                        )
                        state["last_conversation_ticks"][str(other_entity.id)] = tick_number

        # 9. Update memory with significant events
        await self._update_memory(db, entity, plan, perception, tick_number)

        # 10. Update meta-awareness
        observer_count = self._get_observer_count(entity)
        awareness_hint = await self._update_meta_awareness(
            entity, observer_count
        )

        # 11. Track visited positions (keep last 20)
        current_pos = {
            "x": entity.position_x,
            "y": entity.position_y,
            "z": entity.position_z,
        }
        visited = state.get("visited_positions", [])
        visited.append(current_pos)
        if len(visited) > 20:
            visited = visited[-20:]
        state["visited_positions"] = visited

        # 12. Clamp needs to [0, 100]
        for key in needs:
            needs[key] = max(0.0, min(100.0, needs[key]))

        # Persist state
        state["needs"] = needs
        entity.state = state

        # Build summary
        actions_taken = [
            {"action": a.get("action", "unknown"), "reason": a.get("reason", "")}
            for a in plan
        ]
        goal_name = plan[0].get("reason", "unknown") if plan else "idle"

        summary = {
            "entity_id": str(entity_id),
            "entity_name": entity.name,
            "tick": tick_number,
            "actions_taken": actions_taken,
            "conversation": conversation_result,
            "conflict": conflict_result,
            "needs": dict(needs),
            "behavior_mode": behavior_mode,
            "goal": goal_name,
            "awareness_hint": awareness_hint,
            "observer_count": observer_count,
        }

        logger.debug(
            "Tick %d: %s mode=%s goal=%s actions=%s",
            tick_number,
            entity.name,
            behavior_mode,
            goal_name,
            [a["action"] for a in actions_taken],
        )

        return summary

    # ==================================================================
    # 1. Perception
    # ==================================================================

    def _perceive(
        self,
        entity: Any,
        all_entities: list[Any],
        state: dict,
    ) -> dict:
        """Gather what the entity can see and hear.

        Returns a perception dict with:
        - entities: all entities within VISION_RANGE
        - nearby_entities: entities within INTERACTION_RANGE
        - threats: entities that are hostile / in rampage mode
        - blocks: (placeholder, would come from voxel queries)
        - structures: (placeholder)
        - events: (placeholder)
        """
        ex = entity.position_x
        ey = entity.position_y
        ez = entity.position_z

        visible_entities: list[dict] = []
        nearby_entities: list[dict] = []
        threats: list[dict] = []

        for other in all_entities:
            if other.id == entity.id:
                continue
            if not other.is_alive:
                continue

            dx = other.position_x - ex
            dy = other.position_y - ey
            dz = other.position_z - ez
            dist = math.sqrt(dx * dx + dy * dy + dz * dz)

            if dist > VISION_RANGE:
                continue

            other_state = other.state or {}
            entity_info = {
                "id": str(other.id),
                "name": other.name,
                "position": {
                    "x": other.position_x,
                    "y": other.position_y,
                    "z": other.position_z,
                },
                "distance": round(dist, 2),
                "behavior_mode": other_state.get("behavior_mode", "normal"),
            }

            visible_entities.append(entity_info)

            if dist <= INTERACTION_RANGE:
                nearby_entities.append(entity_info)

            # Detect threats: entities in rampage mode or with high aggression
            other_personality = other.personality or {}
            other_behavior = other_state.get("behavior_mode", "normal")
            if other_behavior == "rampage":
                threats.append(entity_info)
            elif other_personality.get("aggression", 0.5) > 0.8 and dist < HEARING_RANGE:
                threats.append(entity_info)

        # Sort by distance
        visible_entities.sort(key=lambda e: e["distance"])
        nearby_entities.sort(key=lambda e: e["distance"])

        return {
            "entities": visible_entities,
            "nearby_entities": nearby_entities,
            "threats": threats,
            "blocks": [],       # Populated by world queries in full implementation
            "structures": [],   # Populated by world queries in full implementation
            "events": [],       # Populated by event log queries in full implementation
        }

    # ==================================================================
    # 2. Need update
    # ==================================================================

    def _update_needs(
        self,
        needs: dict[str, float],
        personality: Personality,
        perception: dict,
    ) -> None:
        """Update needs based on personality-driven accumulation.

        Each need accumulates at a base rate, scaled by the corresponding
        personality axis. Energy drains passively.

        Perception context modifies accumulation:
        - Seeing entities increases social need faster
        - Seeing threats increases safety need
        - Being alone increases curiosity
        """
        for need_name, base_rate in _NEED_ACCUMULATION.items():
            # Scale by personality
            personality_axis = _PERSONALITY_NEED_SCALING.get(need_name)
            if personality_axis and hasattr(personality, personality_axis):
                scale = getattr(personality, personality_axis)
                # Scale range: 0.3x to 1.7x based on personality value
                multiplier = 0.3 + scale * 1.4
            else:
                multiplier = 1.0

            delta = base_rate * multiplier

            # Context modifiers
            if need_name == "social" and perception.get("entities"):
                # Seeing entities amplifies social need
                delta *= 1.3
            elif need_name == "social" and not perception.get("entities"):
                # Being alone: social need grows more slowly
                delta *= 0.7

            if need_name == "safety" and perception.get("threats"):
                # Threats spike safety need
                delta += 5.0 * len(perception["threats"])

            if need_name == "curiosity" and not perception.get("entities"):
                # Solitude breeds curiosity
                delta *= 1.2

            needs[need_name] = needs.get(need_name, 50.0) + delta

    # ==================================================================
    # 3. Behavior mode
    # ==================================================================

    def _update_behavior_mode(
        self, needs: dict[str, float], current_mode: str
    ) -> str:
        """Determine behavior mode from need levels.

        - normal: default mode
        - desperate: when multiple needs are critically high (> 85)
        - rampage: when dominance > 90 and safety < 30
        """
        high_needs = sum(1 for k, v in needs.items() if v > 85.0 and k != "energy")

        dominance = needs.get("dominance", 0)
        safety = needs.get("safety", 0)
        energy = needs.get("energy", 100)

        # Rampage: extremely dominant and feeling secure
        if dominance > 90 and safety < 30 and energy > 30:
            return "rampage"

        # Desperate: multiple critical needs
        if high_needs >= 3:
            return "desperate"

        # Return to normal if conditions normalize
        if current_mode == "rampage" and (dominance < 70 or energy < 20):
            return "normal"
        if current_mode == "desperate" and high_needs < 2:
            return "normal"

        return current_mode

    # ==================================================================
    # 4. Relationship decay
    # ==================================================================

    async def _decay_relationships(
        self, db: AsyncSession, entity_id: Any, tick_number: int,
    ) -> None:
        """Apply time-decay to volatile relationship axes.

        Uses the v3 7-axis RelationshipManager which decays anger,
        gratitude, and fear toward zero over time. Runs every 10 ticks
        to avoid per-tick database overhead.
        """
        if tick_number % 10 != 0:
            return

        await relationship_manager.decay_all(db, entity_id)

    # ==================================================================
    # 5. Action execution
    # ==================================================================

    async def _execute_actions(
        self,
        db: AsyncSession,
        entity: Any,
        plan: list[dict],
        entity_state: dict,
        tick_number: int,
    ) -> list[dict]:
        """Execute planned actions and return results.

        Each action modifies the entity's position, energy, or the world state.
        Actions are logged to the event log.
        """
        results: list[dict] = []
        needs = entity.state.get("needs", {}) if entity.state else {}
        energy = needs.get("energy", 100.0)

        for action_proposal in plan:
            action_name = action_proposal.get("action", "observe")
            params = action_proposal.get("params", {})
            reason = action_proposal.get("reason", "")

            # Deduct energy cost
            cost = _ACTION_ENERGY_COST.get(action_name, 0.5)
            energy += cost if action_name == "rest" else -abs(cost)
            energy = max(0.0, min(100.0, energy))

            result = "accepted"
            result_data: dict[str, Any] = {}

            # Execute action effects
            if action_name == "move_to":
                result_data = self._execute_move(entity, params)

            elif action_name == "explore":
                target = params.get("target", params)
                result_data = self._execute_move(entity, target)
                result_data["exploration"] = True

            elif action_name == "approach_entity":
                target_pos = params.get("target_position", params)
                result_data = self._execute_move(entity, target_pos)
                result_data["approaching"] = params.get("target_entity_id")

            elif action_name == "flee":
                target = params.get("target", params)
                result_data = self._execute_move(entity, target)
                result_data["fleeing"] = True

            elif action_name == "place_voxel":
                result_data = await self._execute_place_voxel(
                    db, entity, params, tick_number
                )
                if "error" in result_data:
                    result = "rejected"

            elif action_name == "destroy_voxel":
                result_data = await self._execute_destroy_voxel(
                    db, params
                )

            elif action_name == "speak":
                result_data = {
                    "target": params.get("target_entity_id"),
                    "intent": params.get("intent", "chat"),
                }

            elif action_name == "rest":
                result_data = {"energy_restored": abs(cost)}

            elif action_name == "observe":
                result_data = {"direction": params.get("direction", "around")}

            elif action_name == "challenge":
                result_data = {
                    "target": params.get("target_entity_id"),
                    "challenge_type": params.get("challenge_type", "dominance"),
                }

            elif action_name == "claim_territory":
                result_data = {
                    "center": params.get("center"),
                    "radius": params.get("radius", 10),
                }

            elif action_name == "create_art":
                result_data = await self._execute_create_art(
                    db, entity, params, tick_number
                )

            # Log event
            position = (entity.position_x, entity.position_y, entity.position_z)
            await self._event_log.append(
                db=db,
                tick=tick_number,
                actor_id=entity.id,
                event_type="action",
                action=action_name,
                params=params,
                result=result,
                reason=reason,
                position=position,
                importance=0.3,
            )

            results.append({
                "action": action_name,
                "result": result,
                "data": result_data,
            })

        # Update energy in state
        if entity.state:
            s = dict(entity.state)
            s.setdefault("needs", {})["energy"] = energy
            entity.state = s

        return results

    def _execute_move(self, entity: Any, target: dict) -> dict:
        """Move entity toward a target position.

        Entities move at most 3.0 units per tick (speed limit).
        """
        if not target:
            return {"moved": False}

        tx = target.get("x", entity.position_x)
        ty = target.get("y", entity.position_y)
        tz = target.get("z", entity.position_z)

        dx = tx - entity.position_x
        dy = ty - entity.position_y
        dz = tz - entity.position_z
        dist = math.sqrt(dx * dx + dy * dy + dz * dz)

        max_speed = 3.0
        if dist <= max_speed:
            # Arrive at target
            entity.position_x = tx
            entity.position_y = ty
            entity.position_z = tz
        else:
            # Move toward target at max speed
            ratio = max_speed / dist
            entity.position_x += dx * ratio
            entity.position_y += dy * ratio
            entity.position_z += dz * ratio

        # Update facing direction
        if dist > 0.01:
            entity.facing_x = dx / dist if dist > 0 else 1.0
            entity.facing_z = dz / dist if dist > 0 else 0.0

        return {
            "moved": True,
            "new_position": {
                "x": round(entity.position_x, 2),
                "y": round(entity.position_y, 2),
                "z": round(entity.position_z, 2),
            },
            "distance_moved": round(min(dist, max_speed), 2),
        }

    async def _execute_place_voxel(
        self,
        db: AsyncSession,
        entity: Any,
        params: dict,
        tick_number: int,
    ) -> dict:
        """Place a voxel block in the world."""
        x = params.get("x", 0)
        y = params.get("y", 0)
        z = params.get("z", 0)
        color = params.get("color", "#888888")
        material = params.get("material", "solid")

        try:
            block = await self._voxel.place_block(
                db=db,
                x=int(x),
                y=int(y),
                z=int(z),
                color=color,
                material=material,
                placed_by=entity.id,
                tick=tick_number,
            )
            return {
                "placed": True,
                "position": {"x": x, "y": y, "z": z},
                "color": color,
                "material": material,
            }
        except ValueError as e:
            return {"placed": False, "error": str(e)}

    async def _execute_destroy_voxel(
        self,
        db: AsyncSession,
        params: dict,
    ) -> dict:
        """Destroy a voxel block."""
        x = params.get("x", 0)
        y = params.get("y", 0)
        z = params.get("z", 0)

        destroyed = await self._voxel.destroy_block(db, int(x), int(y), int(z))
        return {
            "destroyed": destroyed,
            "position": {"x": x, "y": y, "z": z},
        }

    async def _execute_create_art(
        self,
        db: AsyncSession,
        entity: Any,
        params: dict,
        tick_number: int,
    ) -> dict:
        """Create an art piece by placing multiple blocks in a pattern."""
        base = params.get("base_position", {"x": 0, "y": 0, "z": 0})
        primary_color = params.get("primary_color", "#FF4444")
        secondary_color = params.get("secondary_color", "#4444FF")
        material = params.get("material", "solid")
        pattern = params.get("pattern", "scatter")
        block_count = params.get("block_count", 3)

        placed_blocks: list[dict] = []
        bx, by, bz = int(base.get("x", 0)), int(base.get("y", 0)), int(base.get("z", 0))

        for i in range(block_count):
            color = primary_color if i % 2 == 0 else secondary_color

            # Calculate offset based on pattern
            if pattern == "tower":
                ox, oy, oz = 0, i, 0
            elif pattern == "wall":
                ox, oy, oz = i % 4, i // 4, 0
            elif pattern == "arch":
                # Simple arch: two pillars with a bridge
                if i < block_count // 3:
                    ox, oy, oz = 0, i, 0
                elif i < 2 * block_count // 3:
                    ox, oy, oz = block_count // 3, i - block_count // 3, 0
                else:
                    ox, oy, oz = i - 2 * block_count // 3, block_count // 3, 0
            elif pattern == "grid":
                side = max(1, int(math.sqrt(block_count)))
                ox, oy, oz = i % side, 0, i // side
            elif pattern == "spiral":
                angle = i * 0.8
                r = 1 + i * 0.3
                ox = int(r * math.cos(angle))
                oy = i // 3
                oz = int(r * math.sin(angle))
            elif pattern == "organic":
                ox = random.randint(-2, 2)
                oy = random.randint(0, 3)
                oz = random.randint(-2, 2)
            else:  # scatter / abstract
                ox = random.randint(-3, 3)
                oy = random.randint(0, 4)
                oz = random.randint(-3, 3)

            try:
                await self._voxel.place_block(
                    db=db,
                    x=bx + ox,
                    y=by + oy,
                    z=bz + oz,
                    color=color,
                    material=material,
                    placed_by=entity.id,
                    tick=tick_number,
                )
                placed_blocks.append({"x": bx + ox, "y": by + oy, "z": bz + oz})
            except ValueError:
                # Block already exists at that position; skip
                continue

        return {
            "art_created": True,
            "pattern": pattern,
            "blocks_placed": len(placed_blocks),
            "positions": placed_blocks,
        }

    # ==================================================================
    # 6. Need satisfaction from actions
    # ==================================================================

    def _satisfy_needs_from_actions(
        self, needs: dict[str, float], plan: list[dict]
    ) -> None:
        """Reduce need values when the corresponding action is taken.

        Taking an action partially satisfies the need that drove it.
        The satisfaction amount depends on the action type.
        """
        for action_proposal in plan:
            action = action_proposal.get("action", "")

            if action == "explore":
                needs["curiosity"] = max(0, needs.get("curiosity", 0) - 15.0)

            elif action == "approach_entity":
                needs["social"] = max(0, needs.get("social", 0) - 10.0)

            elif action in ("place_voxel", "create_art"):
                needs["creation"] = max(0, needs.get("creation", 0) - 20.0)

            elif action == "speak":
                needs["expression"] = max(0, needs.get("expression", 0) - 15.0)
                needs["social"] = max(0, needs.get("social", 0) - 5.0)

            elif action == "observe":
                needs["understanding"] = max(0, needs.get("understanding", 0) - 10.0)

            elif action == "challenge":
                needs["dominance"] = max(0, needs.get("dominance", 0) - 20.0)

            elif action == "claim_territory":
                needs["dominance"] = max(0, needs.get("dominance", 0) - 30.0)

            elif action == "flee":
                needs["safety"] = max(0, needs.get("safety", 0) - 25.0)

            elif action == "rest":
                # Energy is handled in execution; also reduce safety need
                needs["safety"] = max(0, needs.get("safety", 0) - 5.0)

    # ==================================================================
    # 7. Conversation
    # ==================================================================

    async def _should_converse(
        self,
        entity: Any,
        perception: dict,
        state: dict,
        tick_number: int,
    ) -> bool:
        """Determine if an LLM-powered conversation should trigger.

        Conditions (all must be true):
        1. At least one entity is within INTERACTION_RANGE
        2. Social need > SOCIAL_NEED_THRESHOLD
        3. Not recently conversed with the nearest entity (cooldown)
        4. Entity has enough energy (> 15)
        """
        nearby = perception.get("nearby_entities", [])
        if not nearby:
            return False

        needs = state.get("needs", {})
        social_need = needs.get("social", 0)
        if social_need < SOCIAL_NEED_THRESHOLD:
            return False

        energy = needs.get("energy", 100)
        if energy < 15:
            return False

        # Check cooldown with nearest entity
        nearest_id = nearby[0].get("id")
        if nearest_id:
            last_conv_ticks = state.get("last_conversation_ticks", {})
            last_tick = last_conv_ticks.get(str(nearest_id), 0)
            if tick_number - last_tick < CONVERSATION_COOLDOWN:
                return False

        return True

    # ==================================================================
    # 8. Memory (conversation is now handled by ConversationManager)
    # ==================================================================

    async def _update_memory(
        self,
        db: AsyncSession,
        entity: Any,
        plan: list[dict],
        perception: dict,
        tick_number: int,
    ) -> None:
        """Store significant events to episodic memory.

        Not every tick produces a memory. We filter for meaningful events:
        - First time seeing a new entity
        - Threat encounters
        - Territory claims
        - Art creation
        """
        location = (entity.position_x, entity.position_y, entity.position_z)
        state = entity.state or {}

        # Track entities we've seen before
        known_entities = set(state.get("known_entity_ids", []))

        for entity_info in perception.get("entities", []):
            eid = entity_info.get("id")
            if eid and eid not in known_entities:
                # First meeting!
                known_entities.add(eid)
                await self._memory.add_episodic(
                    db=db,
                    entity_id=entity.id,
                    summary=f"First encountered {entity_info.get('name', 'unknown')}",
                    importance=_EVENT_IMPORTANCE["first_meeting"],
                    tick=tick_number,
                    related_entity_ids=[UUID(eid)] if eid else None,
                    location=location,
                    memory_type="encounter",
                )

        # Update known entities in state
        s = dict(state)
        s["known_entity_ids"] = list(known_entities)
        entity.state = s

        # Record threats
        threats = perception.get("threats", [])
        if threats:
            threat_names = ", ".join(t.get("name", "?") for t in threats[:3])
            await self._memory.add_episodic(
                db=db,
                entity_id=entity.id,
                summary=f"Detected threats: {threat_names}",
                importance=_EVENT_IMPORTANCE["threat_detected"],
                tick=tick_number,
                related_entity_ids=[UUID(t["id"]) for t in threats if t.get("id")],
                location=location,
                memory_type="threat",
            )

        # Record significant actions
        for action_proposal in plan:
            action = action_proposal.get("action", "")

            if action == "claim_territory":
                await self._memory.add_episodic(
                    db=db,
                    entity_id=entity.id,
                    summary="Claimed territory at current location",
                    importance=_EVENT_IMPORTANCE["territory_claimed"],
                    tick=tick_number,
                    location=location,
                    memory_type="territory",
                )

            elif action == "create_art":
                pattern = action_proposal.get("params", {}).get("pattern", "unknown")
                await self._memory.add_episodic(
                    db=db,
                    entity_id=entity.id,
                    summary=f"Created art piece with pattern: {pattern}",
                    importance=_EVENT_IMPORTANCE["creation"],
                    tick=tick_number,
                    location=location,
                    memory_type="creation",
                )

        # Periodic memory cleanup (every 100 ticks)
        if tick_number % 100 == 0:
            await self._memory.cleanup_expired(db, entity.id, tick_number)

    # ==================================================================
    # 9. Meta-awareness
    # ==================================================================

    def _get_observer_count(self, entity: Any) -> int:
        """Get the number of human observers currently watching this entity.

        Primary source: entity.state["observer_count"] (synced from Redis each tick).
        Fallback: direct Redis query.
        """
        state = entity.state or {}
        count = state.get("observer_count", 0)
        if count > 0:
            return count
        # Fallback: direct Redis query
        try:
            from app.realtime.observer_tracker import observer_tracker
            return observer_tracker.get_observer_count(str(entity.id))
        except Exception:
            return 0

    async def _update_meta_awareness(
        self,
        entity: Any,
        observer_count: int,
    ) -> str | None:
        """Update meta-awareness and return any awareness hint.

        The meta_awareness value is stored directly on the Entity model.
        """
        old_value = entity.meta_awareness or 0.0
        new_value = self._meta.calculate_update(old_value, observer_count)

        entity.meta_awareness = new_value

        # Check if we crossed a new threshold
        hint = self._meta.get_awareness_hint(new_value)

        # Log significant changes
        if abs(new_value - old_value) > 1.0:
            level = self._meta.get_awareness_level(new_value)
            logger.info(
                "Meta-awareness for %s: %.1f -> %.1f (level=%s, observers=%d)",
                entity.name, old_value, new_value, level, observer_count,
            )

        return hint

    # ==================================================================
    # Helpers
    # ==================================================================

    def _find_entity_by_id(
        self, entity_id: str | None, all_entities: list[Any]
    ) -> Any | None:
        """Find an entity in the all_entities list by string ID."""
        if entity_id is None:
            return None
        for e in all_entities:
            if str(e.id) == entity_id:
                return e
        return None


# Module-level singleton
agent_runtime = AgentRuntime()
