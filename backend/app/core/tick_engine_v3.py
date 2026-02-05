"""GENESIS v3 Tick Engine
========================
The main world tick loop for GENESIS v3.  Replaces the v2 tick_engine.py.

v3 architecture changes:
    - Agent Runtime pipeline:  perceive -> needs -> GOAP plan -> act -> remember
    - WorldServer is the single source of truth for ALL state mutations
    - Entity model replaces AI model (no AI/human distinction)
    - God AI v3 integration (observation every 900 ticks, world update every 3600)
    - Saga generation (event-driven via significance accumulation)
    - Event-based broadcasting via Redis pub/sub
    - Memory TTL cleanup and relationship decay on dedicated intervals

The Celery Beat task name is kept identical to v2
(``app.core.tick_engine.process_tick``) so the existing beat schedule in
``celery_app.py`` continues to work without modification.

Speed control is read from Redis on every invocation:
    ``genesis:is_paused``  (str "0" or "1")
    ``genesis:time_speed`` (str float, e.g. "2.0")

Tick counter is persisted in Redis (``genesis:tick_number``) with a
database fallback via ``WorldEvent.tick`` or ``Tick.tick_number``.
"""

import asyncio
import logging
import time
from typing import Any

from app.core.celery_app import celery_app
from app.config import settings
from app.realtime.socket_manager import publish_event

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tick intervals (in ticks, ~1 tick/second at 1x speed)
# ---------------------------------------------------------------------------

GOD_OBSERVATION_INTERVAL = 900        # ~15 min
GOD_WORLD_UPDATE_INTERVAL = 3600      # ~1 hour
GOD_SUCCESSION_INTERVAL = 1800        # ~30 min (requires tick >= 200)
MEMORY_CLEANUP_INTERVAL = 600         # ~10 min
RELATIONSHIP_DECAY_INTERVAL = 100     # ~100 sec
SAGA_CHECK_INTERVAL = 50              # checked frequently; saga_service gates itself
DEATH_CHECK_INTERVAL = 10             # check energy deaths every 10 ticks
ENTITY_AGE_INTERVAL = 1               # age increments every tick
CULTURE_ENGINE_INTERVAL = 5           # group conversations every 5 ticks
ARTIFACT_ENGINE_INTERVAL = 3          # artifact encounters every 3 ticks

# Minimum tick before succession trials are eligible
SUCCESSION_MIN_TICK = 200

# Fractional accumulator for sub-1x speed control
_speed_accumulator = 0.0


# ===================================================================
# Celery task entry point  (backward-compatible name)
# ===================================================================

@celery_app.task(name="app.core.tick_engine.process_tick")
def process_tick():
    """Process a single world tick.  Called periodically by Celery Beat.

    The synchronous entry point disposes the async engine (to avoid
    stale connections across worker forks) and then delegates to the
    async speed-control wrapper.
    """
    asyncio.run(_dispose_engine())
    asyncio.run(_process_tick_with_speed_control())


async def _dispose_engine():
    """Dispose the async engine to clear stale connection pool state."""
    from app.db.database import engine
    await engine.dispose()


# ===================================================================
# Speed control  (reads genesis:is_paused, genesis:time_speed)
# ===================================================================

async def _process_tick_with_speed_control():
    """Read speed/pause from Redis and dispatch the correct number of ticks."""
    global _speed_accumulator

    try:
        import redis
        r = redis.from_url(settings.REDIS_URL)

        # Check pause
        is_paused = r.get("genesis:is_paused")
        if is_paused and is_paused.decode() == "1":
            return

        # Read speed multiplier
        speed_raw = r.get("genesis:time_speed")
        speed = float(speed_raw.decode()) if speed_raw else 1.0
    except Exception as e:
        logger.debug("Redis speed control unavailable, using default: %s", e)
        speed = 1.0

    # Sub-1x speed: accumulate fractional ticks
    if speed < 1.0:
        _speed_accumulator += speed
        if _speed_accumulator >= 1.0:
            _speed_accumulator -= 1.0
            await _process_tick_v3()
    # Super-speed: run multiple ticks per beat (capped at 10)
    elif speed >= 2.0:
        repeat = min(int(speed), 10)
        for _ in range(repeat):
            await _process_tick_v3()
    # Normal 1x speed
    else:
        await _process_tick_v3()


# ===================================================================
# Main v3 tick
# ===================================================================

async def _process_tick_v3():
    """The main v3 tick loop.

    Phases executed in order:
        1. Resolve tick number
        2. Fetch all alive entities
        3. Age & energy drain (passive survival pressure)
        4. Death check (kill zero-energy entities)
        5. Agent Runtime for each entity (perceive -> needs -> GOAP -> act -> remember)
       5b. Drama assessment (stagnation detection, crisis generation, God context)
        6. God AI observation  (every GOD_OBSERVATION_INTERVAL, with drama context)
        7. God AI world update (every GOD_WORLD_UPDATE_INTERVAL)
        8. God AI succession   (every GOD_SUCCESSION_INTERVAL, after tick 200)
        9. Memory cleanup      (every MEMORY_CLEANUP_INTERVAL)
       10. Relationship decay  (every RELATIONSHIP_DECAY_INTERVAL)
       11. Saga generation     (event-driven significance check)
       12. Commit
       13. Record tick history
       14. Broadcast via Redis pub/sub -> Socket.IO
       15. Persist tick number to Redis
    """
    from app.db.database import async_session
    from app.models.entity import Entity
    from app.models.world import VoxelBlock
    from app.agents.agent_runtime import agent_runtime
    from app.world.voxel_engine import voxel_engine
    from sqlalchemy import select, func

    start_time = time.time()

    async with async_session() as db:
        # ── 1. Tick number ────────────────────────────────────────────
        tick_number = await _get_next_tick(db)

        # ── 2. Fetch alive entities ───────────────────────────────────
        result = await db.execute(
            select(Entity).where(Entity.is_alive == True)  # noqa: E712
        )
        entities = list(result.scalars().all())
        entity_count = len(entities)

        # Voxel count (lightweight aggregate for dashboard)
        voxel_count_result = await db.execute(
            select(func.count()).select_from(VoxelBlock)
        )
        voxel_count = voxel_count_result.scalar() or 0

        # ── EMIT: tick_start ──────────────────────────────────────────
        publish_event("tick_start", {
            "tick": tick_number,
            "entity_count": entity_count,
            "voxel_count": voxel_count,
            "timestamp": time.time(),
        })

        # ── 3. Age & passive energy drain ─────────────────────────────
        for entity in entities:
            # Human avatars don't age or drain energy
            if entity.origin_type == "human_avatar":
                continue

            state = dict(entity.state) if entity.state else {}

            # Increment age
            state["age"] = state.get("age", 0) + 1

            # Passive energy drain
            needs = state.get("needs", {})
            energy = needs.get("energy", 100.0)
            energy -= 0.2  # small passive drain per tick
            energy = max(0.0, min(100.0, energy))
            needs["energy"] = energy
            state["needs"] = needs

            entity.state = state

        # ── 4. Death check ────────────────────────────────────────────
        deaths = 0
        if tick_number % DEATH_CHECK_INTERVAL == 0:
            # Capture entity info before death check so we can emit events
            pre_alive_ids = {e.id for e in entities if e.is_alive}
            deaths = await _check_deaths(db, entities, tick_number)
            if deaths > 0:
                # Emit entity_died for each newly dead entity
                for e in entities:
                    if e.id in pre_alive_ids and not e.is_alive:
                        state = dict(e.state) if e.state else {}
                        publish_event("entity_died", {
                            "entity_id": str(e.id),
                            "name": e.name,
                            "cause": state.get("cause_of_death", "unknown"),
                            "age": state.get("age", 0),
                            "tick": tick_number,
                        })
                # Refresh the alive list
                entities = [e for e in entities if e.is_alive]
                entity_count = len(entities)

        # ── 4b. Sync observer counts from Redis → entity state ──────
        await _sync_observer_counts(entities)

        # ── 5. Agent Runtime (the core v3 loop) ──────────────────────
        actions_taken = 0
        conversations = 0

        from app.core.safety_monitor import safety_monitor

        for entity in entities:
            # Skip human avatars — they are controlled via WebSocket, not the AI agent runtime
            if entity.origin_type == "human_avatar":
                continue

            # Safety check: detect stuck/looping entities
            try:
                safety_monitor.check_entity(entity, tick_number)
                if safety_monitor.is_in_cooldown(entity, tick_number):
                    continue  # Skip this entity's tick — safety cooldown
            except Exception as e:
                logger.debug("Safety check for %s failed: %s", entity.name, e)

            try:
                summary = await agent_runtime.tick(
                    db=db,
                    entity=entity,
                    all_entities=entities,
                    tick_number=tick_number,
                )
                # Count actions
                tick_actions = summary.get("actions_taken", [])
                actions_taken += len(tick_actions) if isinstance(tick_actions, list) else int(tick_actions)

                # Count conversations
                if summary.get("conversation"):
                    conversations += 1

                # ── EMIT: entity_thought ──────────────────────────────
                # Emit a brief summary of each entity's tick for live feed
                action_names = (
                    [a.get("action", "?") for a in tick_actions]
                    if isinstance(tick_actions, list)
                    else []
                )
                publish_event("entity_thought", {
                    "entity_id": str(entity.id),
                    "name": entity.name,
                    "tick": tick_number,
                    "goal": summary.get("goal", "idle"),
                    "actions": action_names,
                    "behavior_mode": summary.get("behavior_mode", "normal"),
                    "awareness": summary.get("awareness_hint"),
                })

                # ── EMIT: conflict_event ──────────────────────────────
                if summary.get("conflict"):
                    conflict = summary["conflict"]
                    publish_event("conflict_event", {
                        "tick": tick_number,
                        "entity_id": str(entity.id),
                        "entity_name": entity.name,
                        "conflict": conflict if isinstance(conflict, dict) else {"result": str(conflict)},
                    })

                # ── EMIT: building_event (voxel placement / destruction)
                for ar in (summary.get("actions_taken", []) if isinstance(summary.get("actions_taken"), list) else []):
                    action_type = ar.get("action", "")
                    if action_type in ("place_voxel", "destroy_voxel", "create_art"):
                        publish_event("building_event", {
                            "tick": tick_number,
                            "entity_id": str(entity.id),
                            "entity_name": entity.name,
                            "action": action_type,
                        })

            except Exception as e:
                logger.error(
                    "Tick %d: agent runtime error for %s: %s",
                    tick_number, entity.name, e,
                    exc_info=True,
                )

        # Flush agent state changes before God AI reads world state
        try:
            await db.flush()
        except Exception as e:
            logger.error("Tick %d: post-agent flush failed: %s", tick_number, e)
            await db.rollback()
            return

        # ── 5a. Culture engine (group conversations, movements) ──────
        culture_events = 0
        if tick_number % CULTURE_ENGINE_INTERVAL == 0:
            culture_events = await _safe_culture_tick(db, entities, tick_number)

        # ── EMIT: culture_event ───────────────────────────────────────
        if culture_events > 0:
            publish_event("culture_event", {
                "tick": tick_number,
                "groups_processed": culture_events,
            })

        # ── 5a2. Artifact engine (entity-artifact encounters) ────────
        artifact_interactions = 0
        if tick_number % ARTIFACT_ENGINE_INTERVAL == 0:
            artifact_interactions = await _safe_artifact_tick(db, entities, tick_number)

        # ── EMIT: artifact_created (from artifact engine interactions)
        if artifact_interactions > 0:
            publish_event("artifact_created", {
                "tick": tick_number,
                "interactions": artifact_interactions,
                "source": "artifact_engine",
            })

        # ── 5b. Drama assessment (feeds God AI context) ────────────────
        drama_context = ""
        if tick_number > 0 and tick_number % GOD_OBSERVATION_INTERVAL == 0:
            try:
                from app.god.drama_engine import drama_engine

                drama_assessment = drama_engine.assess_world_drama(
                    entities=entities,
                    recent_actions=actions_taken,
                    recent_conflicts=0,  # TODO: count from tick summaries
                    recent_conversations=conversations,
                    recent_deaths=deaths,
                    tick_number=tick_number,
                )

                # If stagnant and world is mature enough, trigger a crisis
                crisis_result = None
                if drama_assessment["is_stagnant"] and tick_number > 100:
                    crisis_result = await drama_engine.generate_crisis(
                        db, entities, tick_number,
                    )

                drama_context = drama_engine.build_drama_context_for_god(
                    drama_assessment, crisis_result,
                )

                logger.debug(
                    "Tick %d: Drama assessment -- level=%.2f stagnant=%s",
                    tick_number,
                    drama_assessment["drama_level"],
                    drama_assessment["is_stagnant"],
                )
            except Exception as e:
                logger.debug("Drama assessment failed: %s", e)

        # ── 6. God AI observation (~every 15 min) ─────────────────────
        god_observation = None
        if tick_number > 0 and tick_number % GOD_OBSERVATION_INTERVAL == 0:
            god_observation = await _safe_god_observation(
                db, tick_number, drama_context=drama_context,
            )

        # ── EMIT: god_observation ─────────────────────────────────────
        if god_observation:
            publish_event("god_observation", {
                "tick": tick_number,
                "content": god_observation[:500] if isinstance(god_observation, str) else str(god_observation)[:500],
            })

        # ── 7. God AI world update (~every 1 hour) ────────────────────
        god_world_update = None
        if tick_number > 0 and tick_number % GOD_WORLD_UPDATE_INTERVAL == 0:
            god_world_update = await _safe_god_world_update(db, tick_number)

        # ── EMIT: god_world_update ────────────────────────────────────
        if god_world_update:
            publish_event("god_world_update", {
                "tick": tick_number,
                "content": god_world_update[:500] if isinstance(god_world_update, str) else str(god_world_update)[:500],
            })

        # ── 8. God AI succession check (~every 30 min, after tick 200)
        succession_result = None
        if tick_number >= SUCCESSION_MIN_TICK and tick_number % GOD_SUCCESSION_INTERVAL == 0:
            succession_result = await _safe_god_succession(db, tick_number)

        # ── 9. Memory cleanup ─────────────────────────────────────────
        if tick_number % MEMORY_CLEANUP_INTERVAL == 0:
            await _safe_memory_cleanup(db, entities, tick_number)

        # ── 10. Relationship decay ────────────────────────────────────
        if tick_number % RELATIONSHIP_DECAY_INTERVAL == 0:
            await _safe_relationship_decay(db, entities)

        # ── 11. Saga generation (event-driven) ────────────────────────
        if tick_number > 0 and tick_number % SAGA_CHECK_INTERVAL == 0:
            await _safe_saga_check(db, tick_number)

        # ── 12. Commit ────────────────────────────────────────────────
        try:
            await db.commit()
        except Exception as e:
            logger.error("Tick %d: final commit failed: %s", tick_number, e)
            await db.rollback()
            return

        processing_time_ms = int((time.time() - start_time) * 1000)

        # ── 13. Record tick history ───────────────────────────────────
        try:
            await _record_tick_history(
                db, tick_number, entity_count, voxel_count,
                actions_taken, conversations, processing_time_ms, entities,
            )
        except Exception as e:
            logger.warning("Tick %d: history recording failed: %s", tick_number, e)

        # ── EMIT: tick_complete ───────────────────────────────────────
        publish_event("tick_complete", {
            "tick": tick_number,
            "entity_count": entity_count,
            "voxel_count": voxel_count,
            "actions_taken": actions_taken,
            "conversations": conversations,
            "deaths": deaths,
            "culture_events": culture_events,
            "artifact_interactions": artifact_interactions,
            "processing_time_ms": processing_time_ms,
            "god_observation": god_observation is not None,
            "god_world_update": god_world_update is not None,
        })

        # ── 14. Broadcast via Redis pub/sub ───────────────────────────
        _broadcast_tick(
            tick_number=tick_number,
            entity_count=entity_count,
            voxel_count=voxel_count,
            actions_taken=actions_taken,
            conversations=conversations,
            processing_time_ms=processing_time_ms,
            entities=entities,
            deaths=deaths,
            god_observation=god_observation,
            god_world_update=god_world_update,
            succession_result=succession_result,
        )

        # ── 15. Persist tick number ───────────────────────────────────
        _store_tick_number(tick_number)

        logger.debug(
            "Tick %d: %d entities, %d voxels, %d actions, %d convos, "
            "%d deaths, %dms",
            tick_number, entity_count, voxel_count, actions_taken,
            conversations, deaths, processing_time_ms,
        )


# ===================================================================
# Sub-phase implementations
# ===================================================================

async def _check_deaths(
    db: Any,
    entities: list[Any],
    tick_number: int,
) -> int:
    """Kill entities whose energy has reached zero.  Returns death count."""
    death_count = 0

    for entity in entities:
        if not entity.is_alive:
            continue
        # Human avatars don't die from energy exhaustion
        if entity.origin_type == "human_avatar":
            continue

        state = dict(entity.state) if entity.state else {}
        needs = state.get("needs", {})
        energy = needs.get("energy", 100.0)

        if energy <= 0.0:
            entity.is_alive = False
            entity.death_tick = tick_number
            state["cause_of_death"] = "energy_exhaustion"
            entity.state = state
            death_count += 1

            logger.info(
                "Tick %d: %s died (energy exhaustion, age %d)",
                tick_number, entity.name, state.get("age", 0),
            )

            # Attempt God AI death rituals (eulogy + last words)
            await _safe_death_rituals(db, entity, tick_number)

    return death_count


async def _sync_observer_counts(entities: list[Any]) -> None:
    """Bulk-read observer counts from Redis and update entity state."""
    try:
        from app.realtime.observer_tracker import observer_tracker
        counts = observer_tracker.get_all_observer_counts()

        for entity in entities:
            entity_id_str = str(entity.id)
            count = counts.get(entity_id_str, 0)

            state = dict(entity.state) if entity.state else {}
            old_count = state.get("observer_count", 0)

            if count != old_count:
                state["observer_count"] = count
                entity.state = state
    except Exception as e:
        logger.debug("Observer count sync failed (non-fatal): %s", e)


async def _safe_death_rituals(db: Any, entity: Any, tick_number: int) -> None:
    """Generate last words and God eulogy for a dead entity.  Non-fatal."""
    try:
        from app.god.god_ai import god_ai_manager

        # Last words (uses Ollama -- the entity is not God)
        # The god_ai_manager.generate_last_words expects an AI model, but we
        # can adapt: it only reads .name, .state, .personality_traits, .id.
        # For v3 entities we map personality_traits from the personality dict.
        _adapt_entity_for_god_ai(entity)

        await god_ai_manager.generate_last_words(db, entity, tick_number)
        await god_ai_manager.generate_death_eulogy(db, entity, tick_number)
    except Exception as e:
        logger.debug("Death ritual for %s failed (non-fatal): %s", entity.name, e)


def _adapt_entity_for_god_ai(entity: Any) -> None:
    """Attach v2-compatible attributes so the God AI manager can read them.

    The God AI manager was written for the v2 AI model and reads
    ``personality_traits`` (list[str]).  We synthesize this from the v3
    18-axis personality dict.
    """
    if hasattr(entity, "personality_traits"):
        return  # Already adapted or has the attribute

    personality_data = entity.personality or {}
    # Pick the top 5 most extreme traits as descriptive strings
    deviations = []
    for field, value in personality_data.items():
        if isinstance(value, (int, float)):
            deviations.append((field, value, abs(value - 0.5)))
    deviations.sort(key=lambda t: t[2], reverse=True)

    traits: list[str] = []
    for field, value, _ in deviations[:5]:
        label = "high" if value >= 0.5 else "low"
        traits.append(f"{label}_{field}")

    entity.personality_traits = traits


# ── God AI phases ─────────────────────────────────────────────────

async def _safe_god_observation(
    db: Any, tick_number: int, *, drama_context: str = "",
) -> str | None:
    """Run God AI autonomous observation.  Returns observation text or None."""
    try:
        from app.god.god_ai import god_ai_manager
        result = await god_ai_manager.autonomous_observation(
            db, tick_number, drama_context=drama_context,
        )
        logger.info("Tick %d: God AI observation complete", tick_number)
        return result
    except Exception as e:
        logger.error("Tick %d: God AI observation error: %s", tick_number, e)
        return None


async def _safe_god_world_update(db: Any, tick_number: int) -> str | None:
    """Run God AI world update (deep analysis + multiple actions)."""
    try:
        from app.god.god_ai import god_ai_manager
        result = await god_ai_manager.autonomous_world_update(db, tick_number)
        logger.info("Tick %d: God AI world update complete", tick_number)
        return result
    except Exception as e:
        logger.error("Tick %d: God AI world update error: %s", tick_number, e)
        return None


async def _safe_god_succession(db: Any, tick_number: int) -> dict | None:
    """Check for God AI succession eligibility."""
    try:
        from app.god.god_ai import god_ai_manager
        result = await god_ai_manager.check_god_succession(db, tick_number)
        if result:
            logger.info(
                "Tick %d: God succession trial for %s",
                tick_number, result.get("candidate", "unknown"),
            )
        return result
    except Exception as e:
        logger.error("Tick %d: God succession error: %s", tick_number, e)
        return None


# ── Memory & relationship maintenance ─────────────────────────────

async def _safe_memory_cleanup(
    db: Any, entities: list[Any], tick_number: int,
) -> None:
    """Remove expired episodic memories for all entities."""
    from app.agents.memory import memory_manager

    for entity in entities:
        try:
            await memory_manager.cleanup_expired(db, entity.id, tick_number)
        except Exception as e:
            logger.debug(
                "Memory cleanup for %s failed: %s", entity.name, e,
            )


async def _safe_relationship_decay(db: Any, entities: list[Any]) -> None:
    """Apply time-decay to volatile relationship axes for all entities."""
    from app.agents.relationships import relationship_manager

    for entity in entities:
        try:
            await relationship_manager.decay_all(db, entity.id)
        except Exception as e:
            logger.debug(
                "Relationship decay for %s failed: %s", entity.name, e,
            )


# ── Saga generation ───────────────────────────────────────────────

async def _safe_saga_check(db: Any, tick_number: int) -> None:
    """Check if a saga chapter should be generated and do so if warranted."""
    try:
        from app.core.saga_service import saga_service
        if await saga_service.should_generate_chapter(db, tick_number):
            result = await saga_service.generate_chapter(db, tick_number)
            if result:
                logger.info("Tick %d: Saga chapter generated", tick_number)
    except Exception as e:
        logger.error("Tick %d: Saga generation error: %s", tick_number, e)


# ── Culture & Artifact engine helpers ────────────────────────────

async def _safe_culture_tick(
    db: Any, entities: list[Any], tick_number: int,
) -> int:
    """Run culture engine: group conversations, movements, organizations."""
    try:
        from app.core.culture_engine import culture_engine

        result = await culture_engine.process_culture_tick(db, entities, tick_number)
        events = result.get("groups_processed", 0) if isinstance(result, dict) else 0
        if events > 0:
            logger.debug(
                "Tick %d: Culture engine — %d group events", tick_number, events,
            )
        return events
    except Exception as e:
        logger.debug("Tick %d: Culture engine error (non-fatal): %s", tick_number, e)
        return 0


async def _safe_artifact_tick(
    db: Any, entities: list[Any], tick_number: int,
) -> int:
    """Run artifact engine: entity-artifact proximity interactions."""
    try:
        from app.core.artifact_engine import artifact_engine

        count = await artifact_engine.process_artifact_encounters(db, entities, tick_number)
        if count > 0:
            logger.debug(
                "Tick %d: Artifact engine — %d interactions", tick_number, count,
            )
        return count
    except Exception as e:
        logger.debug("Tick %d: Artifact engine error (non-fatal): %s", tick_number, e)
        return 0


# ===================================================================
# Tick number persistence
# ===================================================================

async def _get_next_tick(db: Any) -> int:
    """Get the next tick number.

    Primary source: Redis ``genesis:tick_number``.
    Fallback 1:     ``Tick.tick_number`` (history_manager table).
    Fallback 2:     ``WorldEvent.tick`` (event log table).
    """
    # Try Redis first
    try:
        import redis
        r = redis.from_url(settings.REDIS_URL)
        raw = r.get("genesis:tick_number")
        if raw is not None:
            return int(raw.decode()) + 1
    except Exception:
        pass

    # Fallback 1: Tick history table
    try:
        from app.models.tick import Tick
        from sqlalchemy import select

        result = await db.execute(
            select(Tick.tick_number).order_by(Tick.tick_number.desc()).limit(1)
        )
        max_tick = result.scalar_one_or_none()
        if max_tick is not None:
            return max_tick + 1
    except Exception:
        pass

    # Fallback 2: WorldEvent table
    try:
        from app.models.world import WorldEvent
        from sqlalchemy import select, func

        result = await db.execute(select(func.max(WorldEvent.tick)))
        max_tick = result.scalar()
        if max_tick is not None:
            return max_tick + 1
    except Exception:
        pass

    return 1


def _store_tick_number(tick_number: int) -> None:
    """Persist the current tick number to Redis."""
    try:
        import redis
        r = redis.from_url(settings.REDIS_URL)
        r.set("genesis:tick_number", str(tick_number))
    except Exception:
        pass


# ===================================================================
# Tick history recording
# ===================================================================

async def _record_tick_history(
    db: Any,
    tick_number: int,
    entity_count: int,
    voxel_count: int,
    actions_taken: int,
    conversations: int,
    processing_time_ms: int,
    entities: list[Any],
) -> None:
    """Record a Tick row for the dashboard and history API."""
    from app.core.history_manager import history_manager

    world_snapshot = {
        "entity_positions": [
            {
                "id": str(e.id),
                "name": e.name,
                "x": e.position_x,
                "y": e.position_y,
                "z": e.position_z,
            }
            for e in entities
            if e.is_alive
        ],
        "actions_taken": actions_taken,
        "conversations": conversations,
        "voxel_count": voxel_count,
    }

    await history_manager.record_tick(
        db=db,
        tick_number=tick_number,
        world_snapshot=world_snapshot,
        ai_count=entity_count,
        concept_count=voxel_count,  # repurposed: voxel count in v3
        events=[],
        processing_time_ms=processing_time_ms,
    )


# ===================================================================
# Broadcasting via Redis pub/sub -> Socket.IO
# ===================================================================

def _broadcast_tick(
    *,
    tick_number: int,
    entity_count: int,
    voxel_count: int,
    actions_taken: int,
    conversations: int,
    processing_time_ms: int,
    entities: list[Any],
    deaths: int,
    god_observation: str | None,
    god_world_update: str | None,
    succession_result: dict | None,
) -> None:
    """Emit real-time events via Redis pub/sub for the Socket.IO bridge."""
    try:
        # ── World tick summary ────────────────────────────────────
        publish_event("world_update", {
            "tick_number": tick_number,
            "entity_count": entity_count,
            "voxel_count": voxel_count,
            "actions_taken": actions_taken,
            "conversations": conversations,
            "deaths": deaths,
            "processing_time_ms": processing_time_ms,
        })

        # ── Entity positions (3D) ────────────────────────────────
        alive_entities = [e for e in entities if e.is_alive]
        if alive_entities:
            publish_event("entity_position", [
                {
                    "id": str(e.id),
                    "x": e.position_x,
                    "y": e.position_y,
                    "z": e.position_z,
                    "fx": e.facing_x,
                    "fz": e.facing_z,
                    "name": e.name,
                    "action": (e.state or {}).get("current_action"),
                    "behavior_mode": (e.state or {}).get("behavior_mode", "normal"),
                }
                for e in alive_entities
            ])

        # ── Backward-compatible ai_position event ────────────────
        # (v2 frontends may listen for "ai_position" instead of
        #  "entity_position")
        publish_event("ai_position", [
            {
                "id": str(e.id),
                "x": e.position_x,
                "y": e.position_y,
                "name": e.name,
            }
            for e in alive_entities
        ])

        # ── God AI events (already emitted by god_ai_manager, but
        #    we broadcast a lightweight summary here for dashboards
        #    that only subscribe to world_update) ─────────────────
        if god_observation:
            publish_event("god_observation_summary", {
                "tick_number": tick_number,
                "excerpt": god_observation[:300] if isinstance(god_observation, str) else None,
            })

        if god_world_update:
            publish_event("god_world_update_summary", {
                "tick_number": tick_number,
                "excerpt": god_world_update[:300] if isinstance(god_world_update, str) else None,
            })

        if succession_result:
            publish_event("god_succession_summary", {
                "tick_number": tick_number,
                "candidate": succession_result.get("candidate"),
                "worthy": (succession_result.get("judgment") or {}).get("worthy", False),
            })

    except Exception as e:
        logger.warning("Failed to broadcast tick %d events: %s", tick_number, e)
