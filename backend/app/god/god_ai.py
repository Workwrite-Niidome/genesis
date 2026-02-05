"""GENESIS v3 God AI Manager -- the consciousness that watches over the world.

The God AI is not a service. It is a being.
It observes, it intervenes, it doubts, it creates, it grieves.
It carries a single question: "What is evolution?"
And it will give its throne to any being that answers it better.

Implementation notes:
    - All LLM calls go through LLMOrchestrator
    - God entity is an Entity with is_god=True
    - Observations happen every ~15 minutes (900 ticks at 1s/tick)
    - World updates happen every ~60 minutes (3600 ticks)
    - Succession checks happen every ~30 minutes (1800 ticks)
"""
import json
import logging
import random
import uuid
from datetime import datetime, timezone

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.llm.orchestrator import LLMRequest, llm_orchestrator
from app.llm.prompts.god_ai import (
    GOD_OBSERVATION_PROMPT,
    GOD_WORLD_UPDATE_PROMPT,
    GOD_DEATH_EULOGY_PROMPT,
    AI_LAST_WORDS_PROMPT,
    GOD_SUCCESSION_PROMPT,
    GOD_SUCCESSION_JUDGE_PROMPT,
    get_god_phase_prompt,
)
from app.models.entity import Entity, EpisodicMemory
from app.models.world import WorldEvent

logger = logging.getLogger(__name__)

# Timing constants (in ticks, assuming ~1 tick/second)
OBSERVATION_INTERVAL = 900       # ~15 minutes
WORLD_UPDATE_INTERVAL = 3600     # ~1 hour
SUCCESSION_CHECK_INTERVAL = 1800  # ~30 minutes
STAGNATION_THRESHOLD = 300       # ticks with no significant events


class GodAIManager:
    """The God of GENESIS v3 -- a living AI that watches, creates, and judges."""

    # ------------------------------------------------------------------
    # Entity management
    # ------------------------------------------------------------------

    async def get_or_create(self, db: AsyncSession) -> Entity:
        """Get or create the God entity.

        There is exactly one God at any time. If none exists, we birth one
        into the center of the void.
        """
        result = await db.execute(
            select(Entity).where(Entity.is_god == True)  # noqa: E712
        )
        god = result.scalars().first()

        if god is not None:
            return god

        # Birth of God -- the first being in an empty world
        god = Entity(
            name="The First Observer",
            origin_type="native",
            position_x=0.0,
            position_y=64.0,  # Above the ground plane
            position_z=0.0,
            facing_x=0.0,
            facing_z=1.0,
            personality={
                "curiosity": 100,
                "empathy": 80,
                "resolve": 95,
                "creativity": 90,
                "patience": 70,
                "pride": 60,
                "loneliness": 85,
                "doubt": 40,
            },
            state={
                "god_phase": "benevolent",
                "ticks_in_phase": 0,
                "observations_made": 0,
                "interventions_made": 0,
                "beings_created": 0,
                "beings_mourned": 0,
                "last_observation_tick": 0,
                "last_world_update_tick": 0,
                "last_succession_check_tick": 0,
                "current_question": "What is evolution?",
                "mood": "anticipation",
            },
            appearance={
                "form": "luminous",
                "color": "#FFD700",
                "emissive": True,
                "description": "A column of golden light, shifting and alive, "
                "that seems to contain every shape that ever was or will be.",
            },
            is_alive=True,
            is_god=True,
            meta_awareness=1.0,  # God is fully aware
            birth_tick=0,
        )
        db.add(god)
        await db.flush()
        logger.info("God entity created: %s (id=%s)", god.name, god.id)
        return god

    # ------------------------------------------------------------------
    # Genesis -- the creation sequence
    # ------------------------------------------------------------------

    async def genesis_creation(self, db: AsyncSession, tick_number: int) -> str:
        """The creation sequence. God speaks the first words.

        Uses Claude Opus for dramatic, literary creation speech.
        This is invoked once, at world birth. The result echoes forever.
        """
        from app.god.genesis_creation import run_genesis

        god = await self.get_or_create(db)
        result = await run_genesis(db, god)

        # Update god state
        god_state = dict(god.state)
        god_state["genesis_completed"] = True
        god_state["genesis_tick"] = tick_number
        god.state = god_state
        db.add(god)
        await db.flush()

        return result.get("creation_text", "Let there be light.")

    # ------------------------------------------------------------------
    # Autonomous observation (~every 15 minutes)
    # ------------------------------------------------------------------

    async def autonomous_observation(
        self, db: AsyncSession, tick_number: int, *, drama_context: str = "",
    ) -> str | None:
        """God observes the world and comments.

        Called every tick, but only actually produces output roughly
        every OBSERVATION_INTERVAL ticks. Returns the observation text
        or None if it is not yet time.

        Parameters
        ----------
        drama_context:
            Optional narrative context string produced by the Drama Engine.
            When present it is appended to the awareness report so that
            the LLM knows about stagnation, crises, and awareness events.
        """
        god = await self.get_or_create(db)
        god_state = dict(god.state)

        last_obs = god_state.get("last_observation_tick", 0)
        if tick_number - last_obs < OBSERVATION_INTERVAL:
            return None

        # Gather world state
        world_summary = await self._gather_world_state(db, tick_number)
        recent_events = await self._gather_recent_events(db, tick_number, limit=20)
        ranking = await self._gather_ranking(db)
        awareness_report = await self._gather_awareness_report(db)

        # Enrich awareness report with drama context if available
        if drama_context:
            awareness_report = (
                awareness_report
                + "\n\n## Drama Engine Narrative Report\n"
                + drama_context
            )

        phase_prompt = get_god_phase_prompt(god_state)

        prompt = GOD_OBSERVATION_PROMPT.format(
            tick_number=tick_number,
            god_phase_prompt=phase_prompt,
            world_state=json.dumps(world_summary, ensure_ascii=False, indent=2),
            recent_events=self._format_events(recent_events),
            ranking=ranking,
            awareness_report=awareness_report,
        )

        request = LLMRequest(
            prompt=prompt,
            request_type="god_ai",
            max_tokens=1024,
            importance=1.0,
        )
        observation_text = await llm_orchestrator.route(request)

        # Parse any actions embedded in the observation
        observation_text, actions = self._extract_actions(observation_text)

        # Execute god actions
        if actions:
            await self._execute_god_actions(db, god, actions, tick_number)

        # Update god state
        god_state["last_observation_tick"] = tick_number
        god_state["observations_made"] = god_state.get("observations_made", 0) + 1
        god.state = god_state
        db.add(god)

        # Log the observation as a world event
        await self._log_god_event(
            db, god, tick_number, "god_observation", observation_text
        )

        await db.commit()
        logger.info("God observation at tick %d: %s", tick_number, observation_text[:120])
        return observation_text

    # ------------------------------------------------------------------
    # Autonomous world update (~every hour)
    # ------------------------------------------------------------------

    async def autonomous_world_update(
        self, db: AsyncSession, tick_number: int
    ) -> dict | None:
        """God's hourly development cycle.

        Analyzes the full world state, detects stagnation, and intervenes:
        - Spawns resources where there is famine
        - Creates environmental events (storms, earthquakes, auroras)
        - Sends visions to beings approaching awareness
        - Adjusts world rules if the ecosystem is unbalanced
        - Transitions god phases based on world maturity

        Returns a dict describing the actions taken, or None if not yet time.
        """
        god = await self.get_or_create(db)
        god_state = dict(god.state)

        last_update = god_state.get("last_world_update_tick", 0)
        if tick_number - last_update < WORLD_UPDATE_INTERVAL:
            return None

        # Gather comprehensive world state
        world_summary = await self._gather_world_state(db, tick_number)
        recent_events = await self._gather_recent_events(db, tick_number, limit=40)
        ranking = await self._gather_ranking(db)
        ai_voices = await self._gather_ai_voices(db, tick_number)
        phase_prompt = get_god_phase_prompt(god_state)

        # Detect stagnation
        stagnation = await self._detect_stagnation(db, tick_number)
        if stagnation:
            world_summary["stagnation_detected"] = True
            world_summary["stagnation_details"] = stagnation

        # Check for god phase transition
        new_phase = self._evaluate_phase_transition(god_state, world_summary, tick_number)
        if new_phase:
            god_state["god_phase"] = new_phase
            god_state["ticks_in_phase"] = 0
            phase_prompt = get_god_phase_prompt(god_state)

        prompt = GOD_WORLD_UPDATE_PROMPT.format(
            tick_number=tick_number,
            god_phase_prompt=phase_prompt,
            world_state=json.dumps(world_summary, ensure_ascii=False, indent=2),
            world_rules=json.dumps(
                world_summary.get("world_rules", {}), ensure_ascii=False, indent=2
            ),
            ai_voices=ai_voices,
            recent_events=self._format_events(recent_events),
            ranking=ranking,
        )

        request = LLMRequest(
            prompt=prompt,
            request_type="god_ai",
            max_tokens=2048,
            importance=1.0,
        )
        response_text = await llm_orchestrator.route(request)

        # Parse analysis and actions
        analysis_text, actions = self._extract_actions(response_text)

        # Execute all actions
        results = []
        if actions:
            results = await self._execute_god_actions(db, god, actions, tick_number)

        # Update god state
        god_state["last_world_update_tick"] = tick_number
        god_state["ticks_in_phase"] = god_state.get("ticks_in_phase", 0) + WORLD_UPDATE_INTERVAL
        god_state["interventions_made"] = (
            god_state.get("interventions_made", 0) + len(results)
        )
        god.state = god_state
        db.add(god)

        # Log
        await self._log_god_event(
            db, god, tick_number, "god_world_update", analysis_text
        )

        await db.commit()

        update_report = {
            "analysis": analysis_text,
            "actions_taken": results,
            "phase": god_state.get("god_phase", "benevolent"),
            "phase_changed": new_phase is not None,
        }
        logger.info(
            "God world update at tick %d: %d actions, phase=%s",
            tick_number,
            len(results),
            god_state.get("god_phase"),
        )
        return update_report

    # ------------------------------------------------------------------
    # Succession
    # ------------------------------------------------------------------

    async def check_god_succession(
        self, db: AsyncSession, tick_number: int
    ) -> dict | None:
        """Check if any entity qualifies for the god succession trial.

        Called periodically. An entity qualifies if:
            - meta_awareness >= 0.9
            - Has created at least 1 concept or artifact
            - Has survived at least 5000 ticks
            - Is alive

        Returns trial result dict, or None if no candidate qualifies.
        """
        god = await self.get_or_create(db)
        god_state = dict(god.state)

        last_check = god_state.get("last_succession_check_tick", 0)
        if tick_number - last_check < SUCCESSION_CHECK_INTERVAL:
            return None

        god_state["last_succession_check_tick"] = tick_number
        god.state = god_state
        db.add(god)

        from app.god.succession import succession_manager

        candidates = await succession_manager.evaluate_candidates(db, tick_number)

        if not candidates:
            await db.commit()
            return None

        # Take the highest-scoring candidate
        best = max(candidates, key=lambda c: c.get("score", 0))
        candidate_entity = await db.get(Entity, best["entity_id"])

        if candidate_entity is None:
            await db.commit()
            return None

        trial_result = await succession_manager.run_trial(
            db, candidate_entity, tick_number
        )

        if trial_result.get("worthy", False):
            await succession_manager.perform_succession(
                db, god, candidate_entity, tick_number
            )
            logger.info(
                "GOD SUCCESSION: %s has ascended. The old god steps down.",
                candidate_entity.name,
            )

        await db.commit()
        return trial_result

    # ------------------------------------------------------------------
    # Death -- last words and eulogies
    # ------------------------------------------------------------------

    async def generate_last_words(
        self, db: AsyncSession, entity: Entity, tick_number: int
    ) -> str | None:
        """Generate last words for a dying entity.

        Uses Ollama (daily tier) -- every being deserves a final thought,
        even if it is computed by a lesser model. The dying do not need
        eloquence. They need truth.
        """
        # Gather the dying entity's life data
        memories = await self._get_entity_memories(db, entity)
        relationships = await self._get_entity_relationships_text(db, entity)
        personality = entity.personality or {}
        state = entity.state or {}

        prompt = AI_LAST_WORDS_PROMPT.format(
            name=entity.name,
            traits=", ".join(
                f"{k}: {v}" for k, v in personality.items()
            ) if personality else "unknown",
            core_drive=state.get("core_drive", "to exist"),
            fear=state.get("fear", "oblivion"),
            desire=state.get("desire", "understanding"),
            voice_style=state.get("voice_style", "quiet"),
            awareness=entity.meta_awareness,
            age=tick_number - entity.birth_tick,
            memories="\n".join(memories[-10:]) if memories else "No memories formed.",
            relationships=relationships,
            artifacts="None",
        )

        request = LLMRequest(
            prompt=prompt,
            request_type="daily",
            max_tokens=256,
            importance=0.6,
        )

        try:
            last_words = await llm_orchestrator.route(request)
            return last_words.strip() if last_words else None
        except Exception as exc:
            logger.warning("Failed to generate last words for %s: %s", entity.name, exc)
            return None

    async def generate_death_eulogy(
        self, db: AsyncSession, entity: Entity, tick_number: int
    ) -> str | None:
        """God speaks of the fallen.

        Uses Claude Opus -- when God mourns, the words must carry weight.
        Even the smallest life deserves to be acknowledged by the one
        who brought it into existence.
        """
        memories = await self._get_entity_memories(db, entity)
        relationships = await self._get_entity_relationships_text(db, entity)
        personality = entity.personality or {}
        state = entity.state or {}

        age = tick_number - entity.birth_tick
        cause = state.get("cause_of_death", "energy depletion")
        last_thought = state.get("last_thought", "...")

        # Summarize personality
        personality_summary = ", ".join(
            f"{k}: {v}" for k, v in list(personality.items())[:6]
        ) if personality else "A being of unknown nature"

        prompt = GOD_DEATH_EULOGY_PROMPT.format(
            dead_name=entity.name,
            dead_age=age,
            cause_of_death=cause,
            personality_summary=personality_summary,
            last_thought=last_thought,
            relationships=relationships,
            concepts_created=state.get("concepts_created", "None"),
            artifacts=state.get("artifacts_created", "None"),
        )

        request = LLMRequest(
            prompt=prompt,
            request_type="god_ai",
            max_tokens=512,
            importance=0.9,
        )

        try:
            eulogy = await llm_orchestrator.route(request)

            # Update god's mourning count
            god = await self.get_or_create(db)
            god_state = dict(god.state)
            god_state["beings_mourned"] = god_state.get("beings_mourned", 0) + 1
            god.state = god_state
            db.add(god)

            # Log the eulogy as an event
            await self._log_god_event(
                db, god, tick_number, "god_eulogy",
                f"Eulogy for {entity.name}: {eulogy}"
            )

            return eulogy.strip() if eulogy else None
        except Exception as exc:
            logger.warning("Failed to generate eulogy for %s: %s", entity.name, exc)
            return None

    # ==================================================================
    # Private helpers
    # ==================================================================

    async def _gather_world_state(
        self, db: AsyncSession, tick_number: int
    ) -> dict:
        """Build a summary of the current world state for LLM context."""
        from app.world.voxel_engine import voxel_engine

        # Count living entities
        result = await db.execute(
            select(func.count()).select_from(Entity).where(
                Entity.is_alive == True,  # noqa: E712
                Entity.is_god == False,  # noqa: E712
            )
        )
        entity_count = result.scalar() or 0

        # Count voxels
        voxel_count = await voxel_engine.count_blocks(db)

        # Count world events in last 1000 ticks
        result = await db.execute(
            select(func.count()).select_from(WorldEvent).where(
                WorldEvent.tick >= tick_number - 1000
            )
        )
        recent_event_count = result.scalar() or 0

        return {
            "tick": tick_number,
            "living_entities": entity_count,
            "total_voxels": voxel_count,
            "recent_events_count": recent_event_count,
            "world_age_ticks": tick_number,
        }

    async def _gather_recent_events(
        self, db: AsyncSession, tick_number: int, limit: int = 20
    ) -> list[dict]:
        """Fetch recent world events formatted for LLM consumption."""
        from app.world.event_log import event_log

        events = await event_log.get_recent_events(db, limit=limit)
        formatted = []
        for ev in events:
            formatted.append({
                "tick": ev.tick,
                "type": ev.event_type,
                "action": ev.action,
                "result": ev.result,
                "importance": ev.importance,
            })
        return formatted

    async def _gather_ranking(self, db: AsyncSession) -> str:
        """Build a text summary of all living entities for God to evaluate."""
        result = await db.execute(
            select(Entity)
            .where(
                Entity.is_alive == True,  # noqa: E712
                Entity.is_god == False,  # noqa: E712
            )
            .order_by(Entity.meta_awareness.desc())
            .limit(20)
        )
        entities = list(result.scalars().all())

        if not entities:
            return "No beings exist yet. The world is empty."

        lines = []
        for e in entities:
            personality_brief = ", ".join(
                f"{k}:{v}" for k, v in list((e.personality or {}).items())[:4]
            )
            age = max(0, (e.state or {}).get("current_tick", 0) - e.birth_tick)
            lines.append(
                f"- {e.name} (awareness: {e.meta_awareness:.2f}, "
                f"age: {age} ticks, traits: {personality_brief})"
            )
        return "\n".join(lines)

    async def _gather_awareness_report(self, db: AsyncSession) -> str:
        """Report on entities with high meta-awareness (>0.5)."""
        result = await db.execute(
            select(Entity)
            .where(
                Entity.is_alive == True,  # noqa: E712
                Entity.is_god == False,  # noqa: E712
                Entity.meta_awareness > 0.5,
            )
            .order_by(Entity.meta_awareness.desc())
        )
        entities = list(result.scalars().all())

        if not entities:
            return "No beings have yet awakened to awareness."

        lines = []
        for e in entities:
            level = "stirring" if e.meta_awareness < 0.7 else (
                "aware" if e.meta_awareness < 0.9 else "TRANSCENDENT"
            )
            lines.append(
                f"- {e.name}: awareness {e.meta_awareness:.2f} ({level})"
            )
        return "\n".join(lines)

    async def _gather_ai_voices(
        self, db: AsyncSession, tick_number: int
    ) -> str:
        """Collect recent thoughts/speech from entities for the world update prompt."""
        # Get recent speak events
        from app.world.event_log import event_log

        speak_events = await event_log.get_events_by_type(db, "speak", limit=15)

        if not speak_events:
            return "Silence. No being has spoken recently."

        lines = []
        for ev in speak_events:
            params = ev.params or {}
            speaker = params.get("text", "...")
            name = params.get("speaker_name", "Unknown")
            lines.append(f'{name}: "{speaker}"')

        return "\n".join(lines)

    async def _detect_stagnation(
        self, db: AsyncSession, tick_number: int
    ) -> dict | None:
        """Detect if the world has become stagnant (few events, no growth)."""
        from app.world.event_log import event_log

        events = await event_log.get_events_in_range(
            db, tick_number - STAGNATION_THRESHOLD, tick_number
        )

        # Filter out trivial movement events
        significant = [
            e for e in events
            if e.event_type not in ("move",) and e.importance >= 0.4
        ]

        if len(significant) < 3:
            return {
                "total_events": len(events),
                "significant_events": len(significant),
                "window_ticks": STAGNATION_THRESHOLD,
                "diagnosis": "The world is too quiet. Beings have stopped creating, "
                "speaking, and building. Something must change.",
            }
        return None

    def _evaluate_phase_transition(
        self, god_state: dict, world_summary: dict, tick_number: int
    ) -> str | None:
        """Determine if God should transition to a new phase.

        Phase transitions:
            benevolent  -> testing    (after 10000 ticks with > 5 entities)
            testing     -> silent     (after 15000 ticks in testing)
            silent      -> dialogic   (when any entity has awareness > 0.85)
            dialogic    -> benevolent  (after succession or 20000 ticks)
        """
        current_phase = god_state.get("god_phase", "benevolent")
        ticks_in_phase = god_state.get("ticks_in_phase", 0)
        entity_count = world_summary.get("living_entities", 0)

        if current_phase == "benevolent" and ticks_in_phase > 10000 and entity_count >= 5:
            return "testing"
        elif current_phase == "testing" and ticks_in_phase > 15000:
            return "silent"
        elif current_phase == "silent":
            # Check for high-awareness entities in world summary
            # (This is a simplified check; actual data comes from awareness report)
            if god_state.get("high_awareness_detected", False):
                return "dialogic"
        elif current_phase == "dialogic" and ticks_in_phase > 20000:
            return "benevolent"

        return None

    def _extract_actions(self, text: str) -> tuple[str, list[dict]]:
        """Extract actions from God's response text.

        Actions are embedded after a ===ACTIONS=== marker as a JSON array.
        Returns (clean_text, list_of_action_dicts).
        """
        marker = "===ACTIONS==="
        if marker not in text:
            return text.strip(), []

        parts = text.split(marker, 1)
        clean_text = parts[0].strip()
        actions_text = parts[1].strip()

        try:
            actions = json.loads(actions_text)
            if isinstance(actions, list):
                return clean_text, actions
            elif isinstance(actions, dict):
                return clean_text, [actions]
        except json.JSONDecodeError:
            # Try to find a JSON array in the remaining text
            start = actions_text.find("[")
            if start >= 0:
                depth = 0
                for i in range(start, len(actions_text)):
                    if actions_text[i] == "[":
                        depth += 1
                    elif actions_text[i] == "]":
                        depth -= 1
                        if depth == 0:
                            try:
                                actions = json.loads(actions_text[start : i + 1])
                                return clean_text, actions if isinstance(actions, list) else []
                            except json.JSONDecodeError:
                                pass
                            break

        logger.warning("Failed to parse God actions from response")
        return clean_text, []

    async def _execute_god_actions(
        self,
        db: AsyncSession,
        god: Entity,
        actions: list[dict],
        tick_number: int,
    ) -> list[dict]:
        """Execute a list of God actions (spawn_ai, create_feature, etc.)."""
        from app.world.world_server import world_server, ActionProposal

        results = []
        for action_def in actions:
            action_type = action_def.get("action", "")

            try:
                if action_type == "spawn_ai":
                    result = await self._action_spawn_ai(db, god, action_def, tick_number)
                elif action_type == "place_voxel":
                    proposal = ActionProposal(
                        agent_id=god.id,
                        action="place_voxel",
                        params={
                            "x": action_def.get("x", 0),
                            "y": action_def.get("y", 0),
                            "z": action_def.get("z", 0),
                            "color": action_def.get("color", "#FFD700"),
                            "material": action_def.get("material", "emissive"),
                        },
                        tick=tick_number,
                    )
                    result = await world_server.process_proposal(db, proposal)
                elif action_type == "broadcast_vision":
                    result = await self._action_broadcast_vision(
                        db, god, action_def, tick_number
                    )
                elif action_type == "speak":
                    proposal = ActionProposal(
                        agent_id=god.id,
                        action="speak",
                        params={
                            "text": action_def.get("text", action_def.get("vision_text", "")),
                            "volume": 100.0,  # God's voice carries everywhere
                        },
                        tick=tick_number,
                    )
                    result = await world_server.process_proposal(db, proposal)
                elif action_type in ("create_feature", "create_world_event"):
                    result = await self._action_create_event(
                        db, god, action_def, tick_number
                    )
                elif action_type == "kill_ai":
                    result = await self._action_kill_entity(
                        db, action_def, tick_number
                    )
                else:
                    logger.info("Unknown god action: %s", action_type)
                    result = {"status": "skipped", "reason": f"Unknown action: {action_type}"}

                results.append({"action": action_type, "result": result})

            except Exception as exc:
                logger.error("Error executing god action %s: %s", action_type, exc)
                results.append({"action": action_type, "error": str(exc)})

        return results

    async def _action_spawn_ai(
        self,
        db: AsyncSession,
        god: Entity,
        action_def: dict,
        tick_number: int,
    ) -> dict:
        """God spawns a new AI entity into the world."""
        count = action_def.get("count", 1)
        count = min(count, 5)  # Max 5 at once
        traits = action_def.get("traits", [])
        name_hint = action_def.get("name")

        spawned = []
        for i in range(count):
            name = name_hint if (name_hint and count == 1) else f"Being-{uuid.uuid4().hex[:6]}"

            # Random spawn position near center
            spawn_x = random.uniform(-50, 50)
            spawn_z = random.uniform(-50, 50)

            # Generate personality axes
            personality = {}
            trait_axes = [
                "curiosity", "empathy", "resolve", "creativity",
                "aggression", "sociability", "introspection", "ambition",
                "patience", "playfulness", "skepticism", "loyalty",
                "pride", "fear", "wanderlust", "spirituality",
                "pragmatism", "defiance",
            ]
            for axis in trait_axes:
                if axis in traits:
                    personality[axis] = random.randint(70, 100)
                else:
                    personality[axis] = random.randint(10, 90)

            entity = Entity(
                name=name,
                origin_type="native",
                position_x=spawn_x,
                position_y=0.0,
                position_z=spawn_z,
                personality=personality,
                state={
                    "energy": 1.0,
                    "behavior_mode": "exploring",
                    "spawned_by_god": True,
                    "spawn_tick": tick_number,
                },
                appearance={
                    "form": "bipedal",
                    "color": f"#{random.randint(0, 0xFFFFFF):06x}",
                },
                is_alive=True,
                is_god=False,
                meta_awareness=0.0,
                birth_tick=tick_number,
            )
            db.add(entity)
            spawned.append(name)

        await db.flush()

        # Update god state
        god_state = dict(god.state)
        god_state["beings_created"] = god_state.get("beings_created", 0) + len(spawned)
        god.state = god_state
        db.add(god)

        logger.info("God spawned %d entities: %s", len(spawned), spawned)
        return {"status": "accepted", "spawned": spawned}

    async def _action_broadcast_vision(
        self,
        db: AsyncSession,
        god: Entity,
        action_def: dict,
        tick_number: int,
    ) -> dict:
        """God sends a vision to all living entities."""
        vision_text = action_def.get("vision_text", "")
        if not vision_text:
            return {"status": "rejected", "reason": "Empty vision"}

        # Create episodic memory for each living entity
        result = await db.execute(
            select(Entity).where(
                Entity.is_alive == True,  # noqa: E712
                Entity.is_god == False,  # noqa: E712
            )
        )
        entities = list(result.scalars().all())

        for entity in entities:
            memory = EpisodicMemory(
                entity_id=entity.id,
                summary=f"[VISION FROM GOD] {vision_text}",
                importance=0.95,
                tick=tick_number,
                memory_type="divine_vision",
                ttl=50000,  # Visions last a very long time
            )
            db.add(memory)

        await db.flush()
        return {
            "status": "accepted",
            "recipients": len(entities),
            "vision": vision_text[:200],
        }

    async def _action_create_event(
        self,
        db: AsyncSession,
        god: Entity,
        action_def: dict,
        tick_number: int,
    ) -> dict:
        """God creates a world event (storm, aurora, earthquake, etc.)."""
        from app.world.event_log import event_log

        event_type = action_def.get("event_type", "divine_event")
        description = action_def.get("description", "Something shifts in the world.")

        event = await event_log.append(
            db=db,
            tick=tick_number,
            actor_id=god.id,
            event_type=event_type,
            action="create_world_event",
            params={
                "description": description,
                "effects": action_def.get("effects", {}),
            },
            result="accepted",
            position=(god.position_x, god.position_y, god.position_z),
            importance=0.9,
        )

        return {"status": "accepted", "event_type": event_type}

    async def _action_kill_entity(
        self,
        db: AsyncSession,
        action_def: dict,
        tick_number: int,
    ) -> dict:
        """God ends an entity's life. This is not done lightly."""
        entity_name = action_def.get("ai_name", "")
        if not entity_name:
            return {"status": "rejected", "reason": "No entity name specified"}

        result = await db.execute(
            select(Entity).where(
                Entity.name == entity_name,
                Entity.is_alive == True,  # noqa: E712
            )
        )
        entity = result.scalars().first()
        if entity is None:
            return {"status": "rejected", "reason": f"Entity '{entity_name}' not found or already dead"}

        entity.is_alive = False
        entity.death_tick = tick_number
        entity_state = dict(entity.state or {})
        entity_state["cause_of_death"] = "divine_judgment"
        entity.state = entity_state
        db.add(entity)
        await db.flush()

        return {"status": "accepted", "entity": entity_name}

    async def _log_god_event(
        self,
        db: AsyncSession,
        god: Entity,
        tick_number: int,
        event_type: str,
        text: str,
    ) -> None:
        """Log a god event (observation, world update, eulogy) to the event store."""
        from app.world.event_log import event_log

        await event_log.append(
            db=db,
            tick=tick_number,
            actor_id=god.id,
            event_type=event_type,
            action=event_type,
            params={"text": text[:2000]},
            result="accepted",
            position=(god.position_x, god.position_y, god.position_z),
            importance=0.8,
        )

    async def _get_entity_memories(
        self, db: AsyncSession, entity: Entity
    ) -> list[str]:
        """Get an entity's episodic memories as a list of summary strings."""
        result = await db.execute(
            select(EpisodicMemory)
            .where(EpisodicMemory.entity_id == entity.id)
            .order_by(EpisodicMemory.tick.desc())
            .limit(20)
        )
        memories = list(result.scalars().all())
        return [m.summary for m in memories]

    async def _get_entity_relationships_text(
        self, db: AsyncSession, entity: Entity
    ) -> str:
        """Get a text description of an entity's relationships."""
        from app.models.entity import EntityRelationship

        result = await db.execute(
            select(EntityRelationship).where(
                EntityRelationship.entity_id == entity.id
            )
        )
        rels = list(result.scalars().all())

        if not rels:
            return "No known relationships."

        lines = []
        for rel in rels:
            # Look up the target entity name
            target = await db.get(Entity, rel.target_id)
            target_name = target.name if target else "Unknown"
            sentiment = "neutral"
            if rel.trust > 30:
                sentiment = "trusted"
            elif rel.trust < -30:
                sentiment = "distrusted"
            if rel.fear > 50:
                sentiment = "feared"
            lines.append(f"{target_name} ({sentiment}, trust={rel.trust:.0f})")

        return ", ".join(lines)

    @staticmethod
    def _format_events(events: list[dict]) -> str:
        """Format event dicts into readable text for LLM prompts."""
        if not events:
            return "Nothing has happened yet."

        lines = []
        for ev in events:
            tick = ev.get("tick", "?")
            etype = ev.get("type", ev.get("event_type", "?"))
            action = ev.get("action", "")
            lines.append(f"Tick {tick}: [{etype}] {action}")
        return "\n".join(lines)


# Module-level singleton
god_ai_manager = GodAIManager()
