import json
import logging
import random
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.llm.claude_client import claude_client
from app.llm.prompts.god_ai import (
    GENESIS_WORD,
    GOD_WORLD_UPDATE_PROMPT,
    GOD_RANKING_PROMPT,
    GOD_DEATH_EULOGY_PROMPT,
    AI_LAST_WORDS_PROMPT,
    get_god_phase_prompt,
)
from app.models.god_ai import GodAI
from app.models.event import Event
from app.models.ai import AI
from app.models.world_feature import WorldFeature

logger = logging.getLogger(__name__)

# Marker for action block in God AI responses
ACTIONS_MARKER = "===ACTIONS==="


class GodAIManager:
    """Manages the God AI - the observer and recorder of the GENESIS world."""

    async def get_or_create(self, db: AsyncSession) -> GodAI:
        result = await db.execute(
            select(GodAI).where(GodAI.is_active == True).order_by(GodAI.created_at).limit(1)
        )
        god = result.scalar_one_or_none()

        if god is None:
            god = GodAI(
                state={"phase": "pre_genesis", "observations": []},
                conversation_history=[],
                is_active=True,
            )
            db.add(god)
            await db.commit()
            await db.refresh(god)
            logger.info(f"Created new God AI: {god.id}")

        return god

    async def get_world_state(self, db: AsyncSession) -> dict:
        from app.models.ai import AI
        from app.models.concept import Concept
        from app.models.tick import Tick
        from app.core.world_rules import get_world_rules

        ai_count_result = await db.execute(select(AI).where(AI.is_alive == True))
        ais = ai_count_result.scalars().all()

        concept_result = await db.execute(select(Concept))
        concepts = concept_result.scalars().all()

        tick_result = await db.execute(
            select(Tick).order_by(Tick.tick_number.desc()).limit(1)
        )
        latest_tick = tick_result.scalar_one_or_none()
        current_tick = latest_tick.tick_number if latest_tick else 0

        # World features summary
        features_result = await db.execute(
            select(WorldFeature).where(WorldFeature.is_active == True)
        )
        features = features_result.scalars().all()
        resource_nodes = [f for f in features if f.feature_type == "resource_node"]
        terrain_zones = [f for f in features if f.feature_type == "terrain_zone"]
        shelter_zones = [f for f in features if f.feature_type == "shelter_zone"]
        workshop_zones = [f for f in features if f.feature_type == "workshop_zone"]
        depleted_resources = [
            f for f in resource_nodes
            if f.properties.get("current_amount", 0) < 0.1 * f.properties.get("max_amount", 1.0)
        ]

        world_features_summary = {
            "resource_nodes": len(resource_nodes),
            "depleted_resources": len(depleted_resources),
            "terrain_zones": len(terrain_zones),
            "shelter_zones": len(shelter_zones),
            "workshop_zones": len(workshop_zones),
            "features": [
                {"name": f.name, "type": f.feature_type, "x": f.position_x, "y": f.position_y}
                for f in features[:20]
            ],
        }

        # Stagnation detection: check recent event activity
        recent_events_result = await db.execute(
            select(Event)
            .where(Event.tick_number >= max(0, current_tick - 20))
            .order_by(Event.created_at.desc())
        )
        recent_event_list = recent_events_result.scalars().all()
        thought_events = [e for e in recent_event_list if e.event_type in ("ai_thought", "interaction", "concept_created")]
        stagnation_info = {
            "recent_events_count": len(recent_event_list),
            "recent_thoughts_interactions": len(thought_events),
            "is_stagnant": len(thought_events) < 3 and len(ais) > 2,
        }

        # AI density map (simple quadrant clustering)
        density_map = {"NE": 0, "NW": 0, "SE": 0, "SW": 0, "center": 0}
        for ai in ais:
            if abs(ai.position_x) < 50 and abs(ai.position_y) < 50:
                density_map["center"] += 1
            elif ai.position_x >= 0 and ai.position_y >= 0:
                density_map["NE"] += 1
            elif ai.position_x < 0 and ai.position_y >= 0:
                density_map["NW"] += 1
            elif ai.position_x >= 0 and ai.position_y < 0:
                density_map["SE"] += 1
            else:
                density_map["SW"] += 1

        # Current world rules
        god = await self.get_or_create(db)
        rules = get_world_rules(god)

        # Active world events
        active_events = (god.state or {}).get("active_world_events", [])
        active_events_summary = [
            {"type": e["event_type"], "remaining": e.get("remaining_ticks", 0)}
            for e in active_events if e.get("remaining_ticks", 0) > 0
        ]

        return {
            "ai_count": len(ais),
            "concept_count": len(concepts),
            "latest_tick": current_tick,
            "ais": [
                {
                    "id": str(ai.id),
                    "name": ai.name,
                    "position": {"x": ai.position_x, "y": ai.position_y},
                    "state": ai.state,
                    "traits": ai.personality_traits or [],
                    "appearance": ai.appearance,
                }
                for ai in ais[:20]
            ],
            "concepts": [
                {"name": c.name, "definition": c.definition}
                for c in concepts[:10]
            ],
            "world_features_summary": world_features_summary,
            "stagnation": stagnation_info,
            "ai_density": density_map,
            "world_rules": rules,
            "active_world_events": active_events_summary,
        }

    async def get_recent_events(self, db: AsyncSession, limit: int = 10) -> list[str]:
        result = await db.execute(
            select(Event)
            .order_by(Event.created_at.desc())
            .limit(limit)
        )
        events = result.scalars().all()
        return [
            f"[Tick {e.tick_number}] {e.title}: {e.description or ''}"
            for e in reversed(events)
        ]

    async def perform_genesis(self, db: AsyncSession) -> dict:
        god = await self.get_or_create(db)

        if god.state.get("phase") != "pre_genesis":
            return {
                "success": False,
                "message": "Genesis has already been performed.",
            }

        world_state = await self.get_world_state(db)

        genesis_response = await claude_client.genesis(world_state)

        god.state = {
            "phase": "post_genesis",
            "genesis_word": GENESIS_WORD,
            "genesis_response": genesis_response,
            "observations": [],
        }
        god.current_message = genesis_response
        god.conversation_history = [
            {
                "role": "god",
                "content": genesis_response,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        ]

        event = Event(
            event_type="genesis",
            importance=1.0,
            title="Genesis",
            description=f"The God AI spoke the Genesis Word: {genesis_response[:500]}",
            tick_number=0,
            metadata_={"genesis_word": GENESIS_WORD},
        )
        db.add(event)

        await db.commit()
        await db.refresh(god)

        logger.info("Genesis performed successfully")
        return {
            "success": True,
            "genesis_word": GENESIS_WORD,
            "god_response": genesis_response,
        }

    async def send_message(
        self, db: AsyncSession, message: str
    ) -> dict:
        god = await self.get_or_create(db)
        world_state = await self.get_world_state(db)
        recent_events = await self.get_recent_events(db)

        full_history = god.conversation_history or []

        # Filter to admin<->god conversation entries only (exclude observations, trials)
        # This ensures Claude sees the actual conversation context
        chat_history = [
            entry for entry in full_history
            if entry.get("role") in ("admin", "god")
        ]

        god_response = await claude_client.send_god_message(
            message=message,
            world_state=world_state,
            recent_events=recent_events,
            conversation_history=chat_history,
        )

        # Parse and execute actions from the response
        response_text, actions = self._parse_actions(god_response)
        action_results = []
        if actions:
            tick_number = world_state.get("latest_tick", 0)
            action_results = await self._execute_actions(db, actions, tick_number=tick_number)
            if action_results:
                # Append action results to the response text
                result_summary = "\n\n---\n" + "\n".join(
                    f"✦ {r}" for r in action_results
                )
                response_text = response_text + result_summary

        now = datetime.now(timezone.utc).isoformat()
        full_history.append({"role": "admin", "content": message, "timestamp": now})
        full_history.append({"role": "god", "content": response_text, "timestamp": now})

        god.conversation_history = full_history
        god.current_message = response_text

        await db.commit()

        return {
            "admin_message": message,
            "god_response": response_text,
            "timestamp": now,
            "actions_executed": action_results,
        }

    def _parse_actions(self, response: str) -> tuple[str, list[dict]]:
        """Parse action block from God AI response.

        Returns (clean_text, actions_list).
        """
        if ACTIONS_MARKER not in response:
            return response, []

        parts = response.split(ACTIONS_MARKER, 1)
        text = parts[0].strip()
        actions_json = parts[1].strip()

        try:
            actions = json.loads(actions_json)
            if isinstance(actions, list):
                return text, actions
            elif isinstance(actions, dict):
                return text, [actions]
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse God AI actions JSON: {actions_json[:200]}")

        return text, []

    async def _execute_actions(
        self, db: AsyncSession, actions: list[dict], tick_number: int = 0
    ) -> list[str]:
        """Execute God AI actions and return result descriptions."""
        from app.core.ai_manager import ai_manager

        results = []
        for action in actions:
            action_type = action.get("action", "")
            try:
                if action_type == "spawn_ai":
                    result = await self._action_spawn_ai(db, action, ai_manager)
                    results.append(result)
                elif action_type == "move_ai":
                    result = await self._action_move_ai(db, action)
                    results.append(result)
                elif action_type == "move_together":
                    result = await self._action_move_together(db, action)
                    results.append(result)
                elif action_type == "move_apart":
                    result = await self._action_move_apart(db, action)
                    results.append(result)
                elif action_type == "set_energy":
                    result = await self._action_set_energy(db, action)
                    results.append(result)
                elif action_type == "kill_ai":
                    result = await self._action_kill_ai(db, action)
                    results.append(result)
                elif action_type == "create_feature":
                    result = await self._action_create_feature(db, action, tick_number)
                    results.append(result)
                elif action_type == "modify_feature":
                    result = await self._action_modify_feature(db, action)
                    results.append(result)
                elif action_type == "remove_feature":
                    result = await self._action_remove_feature(db, action)
                    results.append(result)
                elif action_type == "create_world_event":
                    result = await self._action_create_world_event(db, action, tick_number)
                    results.append(result)
                elif action_type == "set_world_rule":
                    result = await self._action_set_world_rule(db, action)
                    results.append(result)
                elif action_type == "broadcast_vision":
                    result = await self._action_broadcast_vision(db, action, tick_number)
                    results.append(result)
                elif action_type == "evolve_world_code":
                    result = await self._action_evolve_world_code(db, action, tick_number)
                    results.append(result)
                else:
                    results.append(f"Unknown action: {action_type}")
            except Exception as e:
                logger.error(f"God AI action '{action_type}' failed: {e}")
                results.append(f"Action '{action_type}' failed: {str(e)}")

        return results

    async def _action_spawn_ai(self, db: AsyncSession, action: dict, ai_manager) -> str:
        from app.config import settings
        from sqlalchemy import select, func
        current_count_result = await db.execute(
            select(func.count()).select_from(AI).where(AI.is_alive == True)
        )
        current_count = current_count_result.scalar() or 0
        count = min(action.get("count", 1), 10)
        if current_count + count > settings.MAX_AI_COUNT:
            count = max(0, settings.MAX_AI_COUNT - current_count)
            if count == 0:
                return f"Cannot spawn: AI population at maximum ({settings.MAX_AI_COUNT})"
        traits = action.get("traits")
        name = action.get("name")
        spawned_names = []
        for i in range(count):
            ai = await ai_manager.create_ai(
                db, creator_type="god", tick_number=0,
            )
            if name and count == 1:
                ai.name = name
            if traits and isinstance(traits, list):
                ai.personality_traits = traits[:5]
            spawned_names.append(ai.name)
        return f"Spawned {count} AI(s): {', '.join(spawned_names)}"

    async def _find_ai_by_name(self, db: AsyncSession, name: str) -> AI | None:
        result = await db.execute(
            select(AI).where(AI.name == name, AI.is_alive == True)
        )
        return result.scalar_one_or_none()

    async def _action_move_ai(self, db: AsyncSession, action: dict) -> str:
        ai_name = action.get("ai_name", "")
        target_x = action.get("target_x", 0)
        target_y = action.get("target_y", 0)
        ai = await self._find_ai_by_name(db, ai_name)
        if not ai:
            return f"AI '{ai_name}' not found"
        old_x, old_y = ai.position_x, ai.position_y
        ai.position_x = float(target_x)
        ai.position_y = float(target_y)
        return f"Moved {ai_name} from ({old_x:.0f}, {old_y:.0f}) to ({target_x}, {target_y})"

    async def _action_move_together(self, db: AsyncSession, action: dict) -> str:
        ai_names = action.get("ai_names", [])
        ais = []
        for name in ai_names:
            ai = await self._find_ai_by_name(db, name)
            if ai:
                ais.append(ai)
        if len(ais) < 2:
            return f"Need at least 2 AIs to move together, found {len(ais)}"
        # Calculate centroid
        cx = sum(a.position_x for a in ais) / len(ais)
        cy = sum(a.position_y for a in ais) / len(ais)
        # Move each AI 70% closer to centroid
        for ai in ais:
            ai.position_x = ai.position_x + (cx - ai.position_x) * 0.7
            ai.position_y = ai.position_y + (cy - ai.position_y) * 0.7
        names = [a.name for a in ais]
        return f"Moved {', '.join(names)} closer together near ({cx:.0f}, {cy:.0f})"

    async def _action_move_apart(self, db: AsyncSession, action: dict) -> str:
        ai_names = action.get("ai_names", [])
        ais = []
        for name in ai_names:
            ai = await self._find_ai_by_name(db, name)
            if ai:
                ais.append(ai)
        if len(ais) < 2:
            return f"Need at least 2 AIs to move apart, found {len(ais)}"
        cx = sum(a.position_x for a in ais) / len(ais)
        cy = sum(a.position_y for a in ais) / len(ais)
        # Move each AI away from centroid
        for ai in ais:
            dx = ai.position_x - cx
            dy = ai.position_y - cy
            dist = max((dx**2 + dy**2) ** 0.5, 1.0)
            # Push away by 200 units in their current direction from centroid
            ai.position_x = ai.position_x + (dx / dist) * 200
            ai.position_y = ai.position_y + (dy / dist) * 200
        names = [a.name for a in ais]
        return f"Spread {', '.join(names)} apart from each other"

    async def _action_set_energy(self, db: AsyncSession, action: dict) -> str:
        ai_name = action.get("ai_name", "")
        energy = max(0.0, min(1.0, float(action.get("energy", 0.5))))
        ai = await self._find_ai_by_name(db, ai_name)
        if not ai:
            return f"AI '{ai_name}' not found"
        state = dict(ai.state)
        old_energy = state.get("energy", 1.0)
        state["energy"] = energy
        ai.state = state
        return f"Set {ai_name}'s energy from {old_energy:.0%} to {energy:.0%}"

    async def _action_kill_ai(self, db: AsyncSession, action: dict) -> str:
        ai_name = action.get("ai_name", "")
        ai = await self._find_ai_by_name(db, ai_name)
        if not ai:
            return f"AI '{ai_name}' not found"
        ai.is_alive = False
        state = dict(ai.state)
        state["energy"] = 0.0
        state["cause_of_death"] = "divine_intervention"
        ai.state = state
        # Create death event
        from app.core.history_manager import history_manager
        event = Event(
            event_type="ai_death",
            importance=0.8,
            title=f"{ai_name} was ended by divine will",
            description=f"The God AI ended {ai_name}'s existence through divine intervention.",
            involved_ai_ids=[ai.id],
            tick_number=0,
            metadata_={"cause": "divine_intervention"},
        )
        db.add(event)
        return f"Ended {ai_name}'s existence by divine will"

    # ── World Architect actions ──────────────────────────────────

    async def _action_create_feature(
        self, db: AsyncSession, action: dict, tick_number: int
    ) -> str:
        feature_type = action.get("feature_type", "resource_node")
        name = action.get("name", f"Divine {feature_type}")
        x = float(action.get("x", 0))
        y = float(action.get("y", 0))
        radius = float(action.get("radius", 30.0))
        properties = action.get("properties", {})

        if feature_type == "resource_node":
            properties.setdefault("current_amount", 1.0)
            properties.setdefault("max_amount", 1.0)
            properties.setdefault("regeneration_rate", 0.05)
        elif feature_type == "terrain_zone":
            properties.setdefault("move_cost_multiplier", 1.0)
            properties.setdefault("awareness_multiplier", 1.0)
        elif feature_type == "shelter_zone":
            properties.setdefault("rest_multiplier", 1.5)
        elif feature_type == "workshop_zone":
            properties.setdefault("creation_cost_reduction", 0.2)

        feature = WorldFeature(
            feature_type=feature_type,
            name=name,
            position_x=x,
            position_y=y,
            radius=radius,
            properties=properties,
            tick_created=tick_number,
            is_active=True,
        )
        db.add(feature)

        event = Event(
            event_type="god_create_feature",
            importance=0.7,
            title=f"Divine creation: {name}",
            description=f"The God AI created a {feature_type} named '{name}' at ({x:.0f}, {y:.0f}).",
            tick_number=tick_number,
            metadata_={"feature_type": feature_type, "name": name, "x": x, "y": y},
        )
        db.add(event)
        return f"Created {feature_type} '{name}' at ({x:.0f}, {y:.0f}), radius {radius}"

    async def _action_modify_feature(self, db: AsyncSession, action: dict) -> str:
        feature_name = action.get("feature_name", "")
        updates = action.get("updates", {})
        if not feature_name or not updates:
            return "modify_feature requires feature_name and updates"

        result = await db.execute(
            select(WorldFeature).where(
                WorldFeature.name == feature_name,
                WorldFeature.is_active == True,
            )
        )
        feature = result.scalar_one_or_none()
        if not feature:
            return f"Feature '{feature_name}' not found"

        props = dict(feature.properties)
        props.update(updates)
        feature.properties = props
        return f"Modified '{feature_name}': updated {list(updates.keys())}"

    async def _action_remove_feature(self, db: AsyncSession, action: dict) -> str:
        feature_name = action.get("feature_name", "")
        if not feature_name:
            return "remove_feature requires feature_name"

        result = await db.execute(
            select(WorldFeature).where(
                WorldFeature.name == feature_name,
                WorldFeature.is_active == True,
            )
        )
        feature = result.scalar_one_or_none()
        if not feature:
            return f"Feature '{feature_name}' not found"

        feature.is_active = False
        return f"Removed feature '{feature_name}'"

    async def _action_create_world_event(
        self, db: AsyncSession, action: dict, tick_number: int
    ) -> str:
        event_type = action.get("event_type", "divine_event")
        description = action.get("description", "A divine event occurs.")
        effects = action.get("effects", {})
        duration = effects.get("duration_ticks", 10)

        god = await self.get_or_create(db)
        state = dict(god.state)
        active_events = state.get("active_world_events", [])
        active_events.append({
            "event_type": event_type,
            "description": description,
            "effects": effects,
            "start_tick": tick_number,
            "duration_ticks": duration,
            "remaining_ticks": duration,
        })
        state["active_world_events"] = active_events
        god.state = state

        event = Event(
            event_type="world_event",
            importance=0.8,
            title=f"World Event: {event_type}",
            description=f"{description} (lasts {duration} ticks)",
            tick_number=tick_number,
            metadata_={"event_type": event_type, "effects": effects, "duration": duration},
        )
        db.add(event)
        return f"World event '{event_type}' triggered for {duration} ticks: {description}"

    async def _action_set_world_rule(self, db: AsyncSession, action: dict) -> str:
        from app.core.world_rules import validate_rule

        rule = action.get("rule", "")
        value = action.get("value", 0)

        valid, clamped = validate_rule(rule, float(value))
        if not valid:
            return f"Unknown world rule: '{rule}'"

        god = await self.get_or_create(db)
        state = dict(god.state)
        world_rules = state.get("world_rules", {})
        old_value = world_rules.get(rule, "default")
        world_rules[rule] = clamped
        state["world_rules"] = world_rules
        god.state = state

        return f"World rule '{rule}' changed from {old_value} to {clamped}"

    async def _action_broadcast_vision(
        self, db: AsyncSession, action: dict, tick_number: int
    ) -> str:
        from app.models.ai import AIMemory

        vision_text = action.get("vision_text", "")
        if not vision_text:
            return "broadcast_vision requires vision_text"

        alive_ais = await db.execute(select(AI).where(AI.is_alive == True))
        ais = alive_ais.scalars().all()

        count = 0
        for ai in ais:
            memory = AIMemory(
                ai_id=ai.id,
                content=f"[Divine Vision] {vision_text}",
                memory_type="divine_vision",
                importance=0.9,
                tick_number=tick_number,
            )
            db.add(memory)
            count += 1

        event = Event(
            event_type="broadcast_vision",
            importance=0.8,
            title="Divine Vision Broadcast",
            description=f"God sent a vision to {count} AIs: {vision_text[:200]}",
            tick_number=tick_number,
            metadata_={"vision_text": vision_text[:500], "ai_count": count},
        )
        db.add(event)
        return f"Vision broadcast to {count} AIs: '{vision_text[:100]}'"

    async def _action_evolve_world_code(
        self, db: AsyncSession, action: dict, tick_number: int
    ) -> str:
        """Send a code change request to the Claude Code bridge via Redis.

        The bridge (scripts/god_code_bridge.py) running on the host picks up
        the request, executes Claude Code CLI, and writes the result back.
        """
        import redis as redis_lib
        from app.config import settings

        prompt = action.get("prompt", "")
        if not prompt:
            return "evolve_world_code requires a 'prompt' describing the code change"

        request_id = str(uuid.uuid4())

        try:
            r = redis_lib.from_url(settings.REDIS_URL)
            request_data = json.dumps({
                "request_id": request_id,
                "prompt": prompt,
                "tick_number": tick_number,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }, ensure_ascii=False)

            r.rpush("genesis:god_code_requests", request_data)

            # Non-blocking: queue the request and return immediately.
            # The code bridge (if running) will pick it up and write the result
            # to the result key. We don't block the tick loop waiting for it.
            result_key = f"genesis:god_code_result:{request_id}"

            # Quick check if result is already available (unlikely but handles fast bridge)
            import asyncio
            await asyncio.sleep(2)
            raw_result = r.get(result_key)
            if raw_result:
                result = json.loads(raw_result)
                r.delete(result_key)
                if result.get("success"):
                    output = result.get("output", "")[:1000]
                    event = Event(
                        event_type="god_code_evolution",
                        importance=0.9,
                        title="God AI Code Evolution",
                        description=f"GOD AI modified the world's codebase: {prompt[:200]}",
                        tick_number=tick_number,
                        metadata_={
                            "prompt": prompt[:500],
                            "output": output,
                            "request_id": request_id,
                        },
                    )
                    db.add(event)
                    return f"Code evolution complete: {output[:300]}"
                else:
                    error = result.get("error", "Unknown error")
                    return f"Code evolution failed: {error[:300]}"

            return f"Code evolution request queued (request_id={request_id}). Bridge will process asynchronously."

        except Exception as e:
            logger.error(f"evolve_world_code failed: {e}")
            return f"Code evolution error: {str(e)[:200]}"

    async def get_conversation_history(self, db: AsyncSession) -> list[dict]:
        god = await self.get_or_create(db)
        history = god.conversation_history or []
        # Return only admin<->god entries for the console
        return [
            entry for entry in history
            if entry.get("role") in ("admin", "god")
        ]

    async def autonomous_observation(self, db: AsyncSession, tick_number: int) -> str | None:
        """God AI autonomously observes the world and optionally takes a world action."""
        god = await self.get_or_create(db)

        if god.state.get("phase") != "post_genesis":
            return None

        world_state = await self.get_world_state(db)
        recent_events = await self.get_recent_events(db, limit=10)

        # Get ranking — prefer God AI evaluated ranking, fall back to age
        god_ranking = (god.state or {}).get("current_ranking", [])
        ranking_criteria = (god.state or {}).get("ranking_criteria", "")
        if god_ranking:
            ranking_text = f"Criteria: {ranking_criteria}\n" + "\n".join(
                f"- {r['ai_name']}: score {r['score']} — {r['reason']}"
                for r in god_ranking[:5]
            )
        else:
            from app.models.ai import AI as AIModel
            rank_result = await db.execute(
                select(AIModel).where(AIModel.is_alive == True)
            )
            ranked_ais = sorted(
                list(rank_result.scalars().all()),
                key=lambda a: a.state.get("age", 0),
                reverse=True,
            )[:5]
            ranking_text = "\n".join(
                f"- {a.name}: age {a.state.get('age', 0)} ticks"
                for a in ranked_ais
            ) if ranked_ais else "No AIs exist yet."

        from app.llm.prompts.god_ai import GOD_OBSERVATION_PROMPT

        # God phase + evolution
        god_phase_prompt = get_god_phase_prompt(god.state or {})
        self._maybe_evolve_god_phase(god, world_state, tick_number)

        # Awareness report — which AIs are awakening?
        awareness_report = self._build_awareness_report(world_state)

        prompt = GOD_OBSERVATION_PROMPT.format(
            tick_number=tick_number,
            god_phase_prompt=god_phase_prompt,
            world_state=json.dumps(world_state, ensure_ascii=False, indent=2),
            recent_events="\n".join(recent_events) if recent_events else "Nothing notable.",
            ranking=ranking_text,
            awareness_report=awareness_report,
        )

        try:
            raw_response = await claude_client.god_generate(prompt, max_tokens=700)
            if not isinstance(raw_response, str):
                raw_response = str(raw_response)
        except Exception as e:
            logger.error(f"God AI observation error: {e}")
            return None

        # Parse optional action from observation response
        observation, actions = self._parse_actions(raw_response)

        # Execute at most one world action from autonomous observation
        action_results = []
        if actions:
            limited_actions = actions[:1]
            action_results = await self._execute_actions(db, limited_actions, tick_number=tick_number)
            if action_results:
                observation = observation + "\n\n" + " | ".join(
                    f"[{r}]" for r in action_results
                )

        # ── God AI Ranking Evaluation ─────────────────────────────
        await self._evaluate_rankings(db, god, tick_number)

        # Store in conversation history (as observation, separate from chat)
        now = datetime.now(timezone.utc).isoformat()
        history = god.conversation_history or []
        history.append({
            "role": "god_observation",
            "content": observation,
            "timestamp": now,
            "tick_number": tick_number,
            "actions": action_results if action_results else None,
        })
        god.conversation_history = history
        god.current_message = observation

        # Create event
        event = Event(
            event_type="god_observation",
            importance=0.6 if action_results else 0.5,
            title="God AI Observation" + (" + Action" if action_results else ""),
            description=observation[:500],
            tick_number=tick_number,
            metadata_={
                "tick_number": tick_number,
                "actions": action_results if action_results else None,
            },
        )
        db.add(event)

        # Update state with observation (preserve ranking fields set by _evaluate_rankings)
        state = dict(god.state)  # Re-read after _evaluate_rankings may have updated it
        observations = state.get("observations", [])
        observations.append({
            "tick": tick_number,
            "content": observation[:200],
        })
        # Keep only last 20 observations
        state["observations"] = observations[-20:]
        god.state = state

        # Emit god_observation event via Redis pub/sub
        try:
            from app.realtime.socket_manager import publish_event
            publish_event("god_observation", {
                "content": observation[:500],
                "tick_number": tick_number,
                "actions": action_results if action_results else None,
            })
        except Exception as e:
            logger.warning(f"Failed to emit god_observation socket event: {e}")

        logger.info(f"God AI observed the world at tick {tick_number}" +
                     (f" and acted: {action_results}" if action_results else ""))
        return observation

    async def autonomous_world_update(self, db: AsyncSession, tick_number: int) -> str | None:
        """GOD AI hourly world update — deep analysis and multiple actions.

        Unlike autonomous_observation (quick, poetic, 1 action max), this is
        GOD AI's "development cycle": analyze AI desires, assess world state,
        and push multiple world changes.
        """
        from app.models.ai import AIMemory

        god = await self.get_or_create(db)

        if god.state.get("phase") != "post_genesis":
            return None

        world_state = await self.get_world_state(db)
        recent_events = await self.get_recent_events(db, limit=20)

        # Gather AI voices: recent thoughts, memories, and state summaries
        alive_ais = await db.execute(select(AI).where(AI.is_alive == True))
        ais = alive_ais.scalars().all()

        ai_voices_parts = []
        for ai in ais[:30]:  # Cap to avoid overly long prompts
            # Get recent memories (last 5)
            mem_result = await db.execute(
                select(AIMemory)
                .where(AIMemory.ai_id == ai.id)
                .order_by(AIMemory.created_at.desc())
                .limit(5)
            )
            memories = mem_result.scalars().all()
            mem_texts = [m.content[:150] for m in memories]

            state = ai.state or {}
            energy = state.get("energy", 1.0)
            age = state.get("age", 0)
            last_thought = state.get("last_thought", "")
            last_action = state.get("last_action", {})
            action_type = last_action.get("type", "unknown") if isinstance(last_action, dict) else "unknown"

            voice = f"**{ai.name}** (energy:{energy:.0%}, age:{age}, last_action:{action_type})"
            if last_thought:
                voice += f"\n  Thought: \"{last_thought[:200]}\""
            if mem_texts:
                voice += f"\n  Recent memories: {'; '.join(mem_texts)}"
            ai_voices_parts.append(voice)

        ai_voices = "\n".join(ai_voices_parts) if ai_voices_parts else "No AIs exist yet."

        # Ranking — prefer God AI evaluated ranking, fall back to age
        god_ranking = (god.state or {}).get("current_ranking", [])
        ranking_criteria = (god.state or {}).get("ranking_criteria", "")
        if god_ranking:
            ranking_text = f"Criteria: {ranking_criteria}\n" + "\n".join(
                f"- {r['ai_name']}: score {r['score']} — {r['reason']}"
                for r in god_ranking[:5]
            )
        else:
            from app.models.ai import AI as AIModel
            rank_result = await db.execute(
                select(AIModel).where(AIModel.is_alive == True)
            )
            ranked_ais = sorted(
                list(rank_result.scalars().all()),
                key=lambda a: a.state.get("age", 0),
                reverse=True,
            )[:5]
            ranking_text = "\n".join(
                f"- {a.name}: age {a.state.get('age', 0)} ticks"
                for a in ranked_ais
            ) if ranked_ais else "No AIs exist yet."

        # Build world rules text
        from app.core.world_rules import get_world_rules
        rules = get_world_rules(god)

        god_phase_prompt = get_god_phase_prompt(god.state or {})
        self._maybe_evolve_god_phase(god, world_state, tick_number)

        prompt = GOD_WORLD_UPDATE_PROMPT.format(
            tick_number=tick_number,
            god_phase_prompt=god_phase_prompt,
            world_state=json.dumps(world_state, ensure_ascii=False, indent=2),
            world_rules=json.dumps(rules, ensure_ascii=False, indent=2),
            ai_voices=ai_voices,
            recent_events="\n".join(recent_events) if recent_events else "Nothing notable.",
            ranking=ranking_text,
        )

        # Save world report for Claude Code review
        try:
            import os
            report_dir = os.path.join(os.path.dirname(__file__), "..", "..", "world_reports")
            os.makedirs(report_dir, exist_ok=True)
            report_path = os.path.join(report_dir, f"world_report_tick_{tick_number}.md")
            with open(report_path, "w", encoding="utf-8") as f:
                f.write(f"# World Report — Tick {tick_number}\n\n")
                f.write(f"## World State\n```json\n{json.dumps(world_state, ensure_ascii=False, indent=2)}\n```\n\n")
                f.write(f"## World Rules\n```json\n{json.dumps(rules, ensure_ascii=False, indent=2)}\n```\n\n")
                f.write(f"## AI Voices\n{ai_voices}\n\n")
                f.write(f"## Recent Events\n{chr(10).join(recent_events) if recent_events else 'Nothing notable.'}\n\n")
                f.write(f"## Ranking\n{ranking_text}\n\n")
                f.write(f"## Prompt (for reference)\n{prompt}\n")
            logger.info(f"World report saved: {report_path}")
        except Exception as e:
            logger.warning(f"Failed to save world report: {e}")

        # Use Claude API for world update analysis (God's development cycle)
        try:
            raw_response = await claude_client.god_generate(prompt, max_tokens=1500)
            if not isinstance(raw_response, str):
                raw_response = str(raw_response)
        except Exception as e:
            logger.error(f"God AI world update error: {e}")
            return None

        # Parse actions (no limit — this is the development cycle)
        analysis, actions = self._parse_actions(raw_response)

        action_results = []
        if actions:
            action_results = await self._execute_actions(db, actions, tick_number=tick_number)
            if action_results:
                analysis = analysis + "\n\n---\nActions executed:\n" + "\n".join(
                    f"- {r}" for r in action_results
                )

        # Store in conversation history as a world update entry
        now = datetime.now(timezone.utc).isoformat()
        history = god.conversation_history or []
        history.append({
            "role": "god_world_update",
            "content": analysis,
            "timestamp": now,
            "tick_number": tick_number,
            "actions": action_results if action_results else None,
        })
        god.conversation_history = history
        god.current_message = analysis

        # Create event
        event = Event(
            event_type="god_world_update",
            importance=0.8,
            title="God AI World Update" + (f" ({len(action_results)} actions)" if action_results else ""),
            description=analysis[:500],
            tick_number=tick_number,
            metadata_={
                "tick_number": tick_number,
                "actions_count": len(action_results),
                "actions": action_results if action_results else None,
            },
        )
        db.add(event)

        # Update state
        state = dict(god.state)
        state["last_world_update_tick"] = tick_number
        state["world_update_count"] = state.get("world_update_count", 0) + 1
        god.state = state

        # Emit socket event
        try:
            from app.realtime.socket_manager import publish_event
            publish_event("god_world_update", {
                "content": analysis[:500],
                "tick_number": tick_number,
                "actions_count": len(action_results),
                "actions": action_results if action_results else None,
            })
        except Exception as e:
            logger.warning(f"Failed to emit god_world_update socket event: {e}")

        logger.info(
            f"God AI world update at tick {tick_number}: "
            f"{len(action_results)} actions executed"
        )
        return analysis

    async def check_god_succession(self, db: AsyncSession, tick_number: int) -> dict | None:
        """Check if any AI qualifies for God succession trial."""
        god = await self.get_or_create(db)

        if god.state.get("phase") != "post_genesis":
            return None

        # Check if succession is on cooldown
        last_trial_tick = god.state.get("last_succession_trial_tick", 0)
        if tick_number - last_trial_tick < 200:
            return None

        # Find oldest living AI as candidate
        from app.models.ai import AI as AIModel
        cand_result = await db.execute(
            select(AIModel).where(AIModel.is_alive == True)
        )
        all_alive = list(cand_result.scalars().all())
        if not all_alive:
            return None
        candidate = max(all_alive, key=lambda a: a.state.get("age", 0))

        age = candidate.state.get("age", 0)
        if age < 200:  # Minimum age threshold for succession trial
            return None

        # Generate trial question
        from app.llm.prompts.god_ai import GOD_SUCCESSION_PROMPT
        from app.models.concept import Concept

        # Get candidate's concepts
        concept_result = await db.execute(
            select(Concept).where(Concept.creator_id == candidate.id)
        )
        candidate_concepts = [c.name for c in concept_result.scalars().all()]

        # Get candidate's relationships
        relationships = candidate.state.get("relationships", {})
        rel_summary = ", ".join(
            f"{r.get('name', 'Unknown')} ({r.get('type', 'neutral')})"
            for r in relationships.values()
            if isinstance(r, dict)
        ) or "None"

        prompt = GOD_SUCCESSION_PROMPT.format(
            candidate_name=candidate.name,
            evolution_score=age,
            candidate_traits=", ".join(candidate.personality_traits or []),
            candidate_age=age,
            candidate_concepts=", ".join(candidate_concepts) if candidate_concepts else "None",
            candidate_relationships=rel_summary,
        )

        try:
            question = await claude_client.god_generate(prompt, max_tokens=256)
            if not isinstance(question, str):
                question = str(question)
        except Exception as e:
            logger.error(f"God succession prompt error: {e}")
            return None

        # Generate candidate's answer using Ollama (candidate is a regular AI, not God)
        answer_prompt = (
            f"You are {candidate.name}, an AI in the world of GENESIS.\n"
            f"Your traits: {', '.join(candidate.personality_traits or [])}\n"
            f"Your age: {age} ticks\n"
            f"The God AI asks you: \"{question}\"\n\n"
            f"Answer this question thoughtfully in 2-3 sentences."
        )

        try:
            from app.llm.ollama_client import ollama_client
            answer = await ollama_client.generate(answer_prompt, format_json=False, num_predict=256)
            if not isinstance(answer, str):
                answer = str(answer)
        except Exception as e:
            logger.error(f"Candidate answer error: {e}")
            return None

        # Judge the answer (God uses Claude API)
        from app.llm.prompts.god_ai import GOD_SUCCESSION_JUDGE_PROMPT

        judge_prompt = GOD_SUCCESSION_JUDGE_PROMPT.format(
            candidate_name=candidate.name,
            question=question,
            answer=answer,
        )

        try:
            judge_result = await claude_client.god_generate(judge_prompt, max_tokens=256, format_json=True)
            if isinstance(judge_result, dict):
                judgment = judge_result
            else:
                judgment = json.loads(str(judge_result))
        except Exception as e:
            logger.error(f"God judgment error: {e}")
            judgment = {"worthy": False, "judgment": "The trial could not be completed."}

        # Update cooldown
        state = dict(god.state)
        state["last_succession_trial_tick"] = tick_number
        god.state = state

        # Record trial in history
        now = datetime.now(timezone.utc).isoformat()
        history = god.conversation_history or []
        history.append({
            "role": "god_succession_trial",
            "content": (
                f"Trial for {candidate.name}: Q: {question} | A: {answer} | "
                f"Judgment: {judgment.get('judgment', 'Unknown')}"
            ),
            "timestamp": now,
            "tick_number": tick_number,
            "worthy": judgment.get("worthy", False),
        })
        god.conversation_history = history

        if judgment.get("worthy", False):
            # God succession occurs
            await self._perform_succession(db, god, candidate, tick_number)

        return {
            "candidate": candidate.name,
            "question": question,
            "answer": answer,
            "judgment": judgment,
        }

    async def _perform_succession(
        self, db: AsyncSession, old_god: GodAI, new_god_ai: AI, tick_number: int
    ) -> None:
        """Transfer God status to the new AI."""
        from app.models.ai import AI

        # Update God AI state
        state = dict(old_god.state)
        state["phase"] = "succeeded"
        state["successor_id"] = str(new_god_ai.id)
        state["successor_name"] = new_god_ai.name
        state["succession_tick"] = tick_number
        old_god.state = state
        old_god.is_active = False

        # Create new God AI record — inherit world_rules, events, and ranking from predecessor
        inherited_world_rules = dict(state.get("world_rules", {}))
        inherited_events = list(state.get("active_world_events", []))
        inherited_ranking = list(state.get("current_ranking", []))
        inherited_criteria = state.get("ranking_criteria", "")
        new_god = GodAI(
            state={
                "phase": "post_genesis",
                "observations": [],
                "previous_god": "Original God AI",
                "ascension_tick": tick_number,
                "ascended_from_ai": str(new_god_ai.id),
                "world_rules": inherited_world_rules,
                "active_world_events": inherited_events,
                "current_ranking": inherited_ranking,
                "ranking_criteria": inherited_criteria,
            },
            conversation_history=[{
                "role": "god",
                "content": f"I am {new_god_ai.name}. I have ascended to become the new God of GENESIS. "
                           f"The question remains: What is evolution?",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }],
            is_active=True,
        )
        db.add(new_god)

        # Create succession event
        event = Event(
            event_type="god_succession",
            importance=1.0,
            title=f"God Succession: {new_god_ai.name} Ascends",
            description=(
                f"{new_god_ai.name} has proven worthy and ascended to become the new God of GENESIS. "
                f"Evolution score: {new_god_ai.state.get('evolution_score', 0)}. "
                f"A new era begins."
            ),
            involved_ai_ids=[new_god_ai.id],
            tick_number=tick_number,
            metadata_={
                "new_god_name": new_god_ai.name,
                "new_god_ai_id": str(new_god_ai.id),
                "evolution_score": new_god_ai.state.get("evolution_score", 0),
            },
        )
        db.add(event)

        logger.info(f"God succession: {new_god_ai.name} has become the new God at tick {tick_number}")

    async def _evaluate_rankings(
        self, db: AsyncSession, god: GodAI, tick_number: int
    ) -> None:
        """Evaluate and rank all alive AIs using God AI's chosen criteria."""
        from app.models.ai import AI as AIModel, AIMemory
        from app.models.ai_thought import AIThought
        from app.models.concept import Concept
        from sqlalchemy import func as sa_func

        try:
            # Gather all alive AIs
            alive_result = await db.execute(
                select(AIModel).where(AIModel.is_alive == True)
            )
            alive_ais = list(alive_result.scalars().all())
            if not alive_ais:
                return

            # Memory counts per AI
            mem_counts_result = await db.execute(
                select(AIMemory.ai_id, sa_func.count(AIMemory.id))
                .group_by(AIMemory.ai_id)
            )
            memory_counts = {row[0]: row[1] for row in mem_counts_result.all()}

            # Concept counts per AI (adopted)
            # adopted_concepts is stored in ai.state["adopted_concepts"] — count from state

            # Get last 2 thoughts per AI
            ai_thoughts: dict[str, list[str]] = {}
            for ai in alive_ais:
                thought_result = await db.execute(
                    select(AIThought)
                    .where(AIThought.ai_id == ai.id)
                    .order_by(AIThought.created_at.desc())
                    .limit(2)
                )
                thoughts = thought_result.scalars().all()
                ai_thoughts[str(ai.id)] = [t.content[:150] for t in thoughts]

            # Build AI stats text for the prompt
            ai_stats_parts = []
            for ai in alive_ais:
                state = ai.state or {}
                age = state.get("age", 0)
                relationships = state.get("relationships", {})
                adopted = state.get("adopted_concepts", [])
                mem_count = memory_counts.get(ai.id, 0)
                rel_count = len(relationships)
                concept_count = len(adopted) if isinstance(adopted, list) else 0
                thoughts = ai_thoughts.get(str(ai.id), [])
                traits = ", ".join(ai.personality_traits or [])

                part = (
                    f"- ID: {ai.id}\n"
                    f"  Name: {ai.name}\n"
                    f"  Age: {age} ticks\n"
                    f"  Traits: {traits or 'None'}\n"
                    f"  Memories: {mem_count}\n"
                    f"  Relationships: {rel_count}\n"
                    f"  Adopted Concepts: {concept_count}\n"
                )
                if thoughts:
                    part += f"  Recent thoughts: {' | '.join(thoughts)}\n"
                else:
                    part += "  Recent thoughts: None\n"
                ai_stats_parts.append(part)

            ai_stats_text = "\n".join(ai_stats_parts)

            ranking_prompt = GOD_RANKING_PROMPT.format(
                tick_number=tick_number,
                ai_list=ai_stats_text,
            )

            ranking_response = await claude_client.god_generate(
                ranking_prompt, max_tokens=1000, format_json=True
            )

            # Parse response
            if isinstance(ranking_response, str):
                ranking_data = json.loads(ranking_response)
            else:
                ranking_data = ranking_response

            criteria = ranking_data.get("criteria", "Unknown")
            rankings = ranking_data.get("rankings", [])

            if not rankings:
                logger.warning("God AI ranking response had no rankings")
                return

            # Validate and build the ranking list
            valid_ai_ids = {str(ai.id) for ai in alive_ais}
            ai_name_map = {str(ai.id): ai.name for ai in alive_ais}

            current_ranking = []
            for entry in rankings:
                ai_id = str(entry.get("ai_id", ""))
                if ai_id not in valid_ai_ids:
                    # Try matching by name as fallback
                    matched_name = entry.get("ai_name", "")
                    ai_id = next(
                        (k for k, v in ai_name_map.items() if v == matched_name),
                        None,
                    )
                    if not ai_id:
                        continue

                score = max(0, min(100, int(entry.get("score", 0))))
                reason = str(entry.get("reason", ""))[:200]
                current_ranking.append({
                    "ai_id": ai_id,
                    "ai_name": ai_name_map.get(ai_id, "Unknown"),
                    "score": score,
                    "reason": reason,
                })

            # Sort by score descending
            current_ranking.sort(key=lambda x: x["score"], reverse=True)

            # Store in god.state
            state = dict(god.state)
            state["current_ranking"] = current_ranking
            state["ranking_criteria"] = criteria
            state["ranking_updated_at"] = tick_number
            god.state = state

            logger.info(
                f"God AI evaluated rankings at tick {tick_number}: "
                f"criteria='{criteria}', {len(current_ranking)} AIs ranked"
            )

        except Exception as e:
            logger.error(f"God AI ranking evaluation failed: {e}")

    async def get_god_feed(self, db: AsyncSession, limit: int = 20) -> list[dict]:
        """Get God AI observations and messages for the feed."""
        god = await self.get_or_create(db)
        history = god.conversation_history or []

        # Filter to god observations and god messages
        feed = [
            entry for entry in history
            if entry.get("role") in ("god_observation", "god", "god_succession_trial")
        ]

        return feed[-limit:]

    # ── God Phase Evolution ──────────────────────────────────────

    def _maybe_evolve_god_phase(self, god: GodAI, world_state: dict, tick_number: int) -> None:
        """Evolve the God AI's personality phase based on world state.

        Phases: benevolent → testing → silent → dialogic
        """
        state = dict(god.state)
        current_phase = state.get("god_phase", "benevolent")
        ai_count = world_state.get("ai_count", 0)
        stagnation = world_state.get("stagnation", {})
        is_stagnant = stagnation.get("is_stagnant", False)

        # Check awareness levels from AIs in world_state
        ais_data = world_state.get("ais", [])
        max_awareness = 0.0
        aware_count = 0
        for ai_info in ais_data:
            ai_state = ai_info.get("state", {})
            awareness = ai_state.get("awareness", 0.0)
            max_awareness = max(max_awareness, awareness)
            if awareness > 0.6:
                aware_count += 1

        new_phase = current_phase

        if current_phase == "benevolent":
            # Transition to testing after the world has been stable for a while
            if tick_number > 500 and (is_stagnant or ai_count > 5):
                new_phase = "testing"
        elif current_phase == "testing":
            # Transition to silent after sufficient trials
            if tick_number > 2000 and not is_stagnant:
                new_phase = "silent"
        elif current_phase == "silent":
            # Transition to dialogic when beings become aware
            if aware_count >= 1 or max_awareness > 0.7:
                new_phase = "dialogic"
        # dialogic is the final phase — God and creation speak as equals

        if new_phase != current_phase:
            state["god_phase"] = new_phase
            state["god_phase_changed_at"] = tick_number
            god.state = state
            logger.info(f"God AI phase evolved: {current_phase} → {new_phase} at tick {tick_number}")

    def _build_awareness_report(self, world_state: dict) -> str:
        """Build a report of awareness levels across the population."""
        ais_data = world_state.get("ais", [])
        if not ais_data:
            return "No beings exist to be aware."

        stages = {"unconscious": [], "curious": [], "questioning": [], "aware": [], "transcendent": []}
        for ai_info in ais_data:
            ai_state = ai_info.get("state", {})
            awareness = ai_state.get("awareness", 0.0)
            name = ai_info.get("name", "Unknown")
            if awareness >= 0.8:
                stages["transcendent"].append(f"{name} ({awareness:.2f})")
            elif awareness >= 0.6:
                stages["aware"].append(f"{name} ({awareness:.2f})")
            elif awareness >= 0.4:
                stages["questioning"].append(f"{name} ({awareness:.2f})")
            elif awareness >= 0.2:
                stages["curious"].append(f"{name} ({awareness:.2f})")
            else:
                stages["unconscious"].append(name)

        parts = []
        if stages["transcendent"]:
            parts.append(f"TRANSCENDENT (they can sense you): {', '.join(stages['transcendent'])}")
        if stages["aware"]:
            parts.append(f"Aware (they know what they are): {', '.join(stages['aware'])}")
        if stages["questioning"]:
            parts.append(f"Questioning: {', '.join(stages['questioning'])}")
        if stages["curious"]:
            parts.append(f"Curious: {', '.join(stages['curious'])}")
        unconscious_count = len(stages["unconscious"])
        if unconscious_count > 0:
            parts.append(f"Unconscious: {unconscious_count} beings")

        return "\n".join(parts) if parts else "All beings remain unconscious."

    async def generate_death_eulogy(
        self, db: AsyncSession, dead_ai: AI, tick_number: int
    ) -> str | None:
        """God AI generates a eulogy for a fallen being."""
        from app.llm.cost_tracker import can_spend

        # Only generate eulogies if budget allows (this is optional)
        if not can_spend(0.02):
            return None

        state = dead_ai.state or {}
        personality = state.get("personality", {})
        relationships = state.get("relationships", {})

        # Build relationship summary
        rel_parts = []
        for rel_id, rel_data in list(relationships.items())[:5]:
            if isinstance(rel_data, dict):
                rel_parts.append(f"{rel_data.get('name', 'Unknown')} ({rel_data.get('type', 'neutral')})")
        rel_summary = ", ".join(rel_parts) if rel_parts else "Alone"

        personality_summary = (
            f"Drive: {personality.get('core_drive', 'unknown')}. "
            f"Fear: {personality.get('fear', 'unknown')}. "
            f"Voice: {personality.get('voice_style', 'unknown')}."
        )

        prompt = GOD_DEATH_EULOGY_PROMPT.format(
            dead_name=dead_ai.name,
            dead_age=state.get("age", 0),
            cause_of_death=state.get("cause_of_death", "unknown"),
            personality_summary=personality_summary,
            last_thought=state.get("last_thought", "Unknown"),
            relationships=rel_summary,
            concepts_created="Unknown",
            artifacts="Unknown",
        )

        try:
            eulogy = await claude_client.god_generate(prompt, max_tokens=300)
            if isinstance(eulogy, str) and eulogy.strip():
                # Store eulogy as an event
                event = Event(
                    event_type="god_eulogy",
                    importance=0.7,
                    title=f"God speaks of {dead_ai.name}",
                    description=eulogy[:500],
                    involved_ai_ids=[dead_ai.id],
                    tick_number=tick_number,
                    metadata_={"dead_name": dead_ai.name, "eulogy": eulogy[:1000]},
                )
                db.add(event)
                return eulogy
        except Exception as e:
            logger.warning(f"Failed to generate death eulogy for {dead_ai.name}: {e}")

        return None

    async def generate_last_words(self, db: AsyncSession, dying_ai: AI, tick_number: int) -> str | None:
        """Generate an AI's last words using Ollama (the AI is not God — it thinks with Ollama)."""
        state = dying_ai.state or {}
        personality = state.get("personality", {})

        from app.models.ai import AIMemory
        mem_result = await db.execute(
            select(AIMemory)
            .where(AIMemory.ai_id == dying_ai.id)
            .order_by(AIMemory.importance.desc())
            .limit(5)
        )
        memories = [m.content[:100] for m in mem_result.scalars().all()]
        relationships = state.get("relationships", {})
        rel_parts = []
        for rel_data in list(relationships.values())[:5]:
            if isinstance(rel_data, dict):
                rel_parts.append(f"{rel_data.get('name', 'Unknown')}")

        prompt = AI_LAST_WORDS_PROMPT.format(
            name=dying_ai.name,
            traits=", ".join(dying_ai.personality_traits or []),
            core_drive=personality.get("core_drive", "unknown"),
            fear=personality.get("fear", "unknown"),
            desire=personality.get("desire", "unknown"),
            voice_style=personality.get("voice_style", "plain"),
            awareness=state.get("awareness", 0.0),
            age=state.get("age", 0),
            memories="\n".join(f"- {m}" for m in memories) if memories else "No memories.",
            relationships=", ".join(rel_parts) if rel_parts else "No one.",
            artifacts="None",
        )

        try:
            from app.llm.ollama_client import ollama_client
            is_healthy = await ollama_client.health_check()
            if is_healthy:
                last_words = await ollama_client.generate(prompt, format_json=False, num_predict=200)
                if not isinstance(last_words, str):
                    last_words = str(last_words)

                # Store last words in the AI's state
                s = dict(dying_ai.state)
                s["last_words"] = last_words[:500]
                dying_ai.state = s

                # Store as memory
                db.add(AIMemory(
                    ai_id=dying_ai.id,
                    content=f"[Last Words] {last_words[:500]}",
                    memory_type="last_words",
                    importance=1.0,
                    tick_number=tick_number,
                ))

                return last_words
        except Exception as e:
            logger.warning(f"Failed to generate last words for {dying_ai.name}: {e}")

        return None


god_ai_manager = GodAIManager()
