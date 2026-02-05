import logging
import time

from app.core.celery_app import celery_app
from app.config import settings

logger = logging.getLogger(__name__)

# How many ticks between AI thinking cycles
THINKING_INTERVAL_TICKS = max(1, settings.AI_THINKING_INTERVAL_MS // settings.TICK_INTERVAL_MS)

# How many ticks between encounter processing (separated from thinking)
ENCOUNTER_INTERVAL = 2

# How many ticks between God AI autonomous observations
# ~15 minutes at 1 tick/sec = 900 ticks (Claude API cost control)
GOD_OBSERVATION_INTERVAL = 900

# How many ticks between group conversation checks
GROUP_CONVERSATION_INTERVAL = 2

# How many ticks between God AI world updates (1 hour = 3600 ticks at 1s/tick)
GOD_WORLD_UPDATE_INTERVAL = 3600

# Fractional accumulator for sub-1x speed
_speed_accumulator = 0.0


@celery_app.task(name="app.core.tick_engine.process_tick")
def process_tick():
    """Process a single world tick. Called periodically by Celery Beat."""
    import asyncio
    from app.db.database import engine
    asyncio.run(engine.dispose())
    asyncio.run(_process_tick_with_speed_control())


async def _process_tick_with_speed_control():
    """Read speed/pause from Redis and dispatch ticks accordingly."""
    global _speed_accumulator

    try:
        import redis
        r = redis.from_url(settings.REDIS_URL)

        is_paused = r.get("genesis:is_paused")
        if is_paused and is_paused.decode() == "1":
            return

        speed_raw = r.get("genesis:time_speed")
        speed = float(speed_raw.decode()) if speed_raw else 1.0
    except Exception as e:
        logger.debug(f"Redis speed control unavailable, using default: {e}")
        speed = 1.0

    if speed < 1.0:
        _speed_accumulator += speed
        if _speed_accumulator >= 1.0:
            _speed_accumulator -= 1.0
            await _process_tick_async()
    elif speed >= 2.0:
        repeat = min(int(speed), 10)
        for _ in range(repeat):
            await _process_tick_async()
    else:
        await _process_tick_async()


async def _process_tick_async():
    from app.db.database import async_session
    from app.core.history_manager import history_manager
    from app.core.ai_manager import ai_manager
    from app.core.space_manager import space_manager
    from app.core.ai_thinker import ai_thinker
    from app.core.interaction_engine import interaction_engine
    from app.core.concept_engine import concept_engine
    from app.models.ai import AI

    start_time = time.time()

    async with async_session() as db:
        tick_number = await history_manager.get_latest_tick_number(db) + 1

        ais = await ai_manager.get_all_alive(db)
        ai_count = len(ais)

        encounters = await space_manager.detect_encounters(db, ais=ais)

        from app.models.concept import Concept
        from sqlalchemy import select, func

        concept_count_result = await db.execute(select(func.count()).select_from(Concept))
        concept_count = concept_count_result.scalar()

        bounds = await space_manager.get_world_bounds(db, ais=ais)

        # -- World systems phase: resource regeneration, terrain effects --
        try:
            from app.core.world_state_manager import world_state_manager
            world_rules = None
            try:
                from app.core.god_ai import god_ai_manager
                from app.core.world_rules import get_world_rules
                god = await god_ai_manager.get_or_create(db)
                world_rules = get_world_rules(god)
                world_rules = await world_state_manager.apply_event_effects(db, god, world_rules)
            except Exception as e:
                logger.error(f"World rules loading error at tick {tick_number}: {e}")

            if world_rules is None:
                from app.core.world_rules import DEFAULT_WORLD_RULES
                world_rules = dict(DEFAULT_WORLD_RULES)

            await world_state_manager.regenerate_resources(db, rules=world_rules)
            await world_state_manager.apply_terrain_effects(db, ais)
        except Exception as e:
            logger.error(f"World systems error at tick {tick_number}: {e}")

        # -- Age, Energy drain, Resource recovery, Shelter rest --
        # Pre-load world features for spatial queries
        resource_features = []
        shelter_features = []
        try:
            from app.models.world_feature import WorldFeature
            feat_result = await db.execute(
                select(WorldFeature).where(WorldFeature.is_active == True)
            )
            all_features = list(feat_result.scalars().all())
            resource_features = [f for f in all_features if f.feature_type == "resource_node"]
            shelter_features = [f for f in all_features if f.feature_type == "shelter_zone"]
        except Exception as e:
            logger.debug(f"Could not load world features for energy: {e}")

        for ai in ais:
            state = dict(ai.state)
            state["age"] = state.get("age", 0) + 1

            energy = state.get("energy", 1.0)

            # Base energy drain
            energy -= 0.002

            # Resource recovery: AIs near resource nodes gain energy
            for res in resource_features:
                dist = ((ai.position_x - res.position_x) ** 2 + (ai.position_y - res.position_y) ** 2) ** 0.5
                if dist <= res.radius:
                    props = res.properties or {}
                    current_amount = props.get("current_amount", 0.0)
                    if current_amount > 0.01:
                        # Harvest a small amount
                        harvest = min(0.005, current_amount * 0.1)
                        energy += harvest
                        # Deplete the resource slightly
                        props["current_amount"] = max(0.0, current_amount - harvest)
                        res.properties = props
                    break  # Only harvest from one resource per tick

            # Shelter rest bonus
            for shelter in shelter_features:
                dist = ((ai.position_x - shelter.position_x) ** 2 + (ai.position_y - shelter.position_y) ** 2) ** 0.5
                if dist <= shelter.radius:
                    rest_mult = (shelter.properties or {}).get("rest_multiplier", 1.5)
                    energy += 0.001 * (rest_mult - 1.0)  # Small bonus
                    break

            energy = max(0.0, min(1.0, energy))
            state["energy"] = energy
            ai.state = state

        # -- Death check: kill AIs with 0 energy --
        try:
            death_count = await ai_manager.check_deaths(db, tick_number)
            if death_count > 0:
                logger.info(f"Tick {tick_number}: {death_count} AI(s) died")
                # Remove dead AIs from the active list
                ais = [ai for ai in ais if ai.is_alive]
                ai_count = len(ais)
        except Exception as e:
            logger.error(f"Death check error at tick {tick_number}: {e}")

        # Run AI thinking cycle every N ticks
        thoughts_generated = 0
        if ai_count > 0 and tick_number % THINKING_INTERVAL_TICKS == 0:
            t0 = time.time()
            try:
                thoughts_generated = await ai_thinker.run_thinking_cycle(db, tick_number)
                logger.info(
                    f"Tick {tick_number}: {thoughts_generated} AIs thought "
                    f"({int((time.time() - t0) * 1000)}ms)"
                )
            except Exception as e:
                logger.error(f"AI thinking cycle error at tick {tick_number}: {e}")

        # Flush thinking results (deferred commit at end of tick)
        try:
            await db.flush()
        except Exception as e:
            logger.error(f"Tick {tick_number}: thinking flush failed: {e}")
            await db.rollback()
            return

        # Process encounters into interactions (independent interval)
        interactions_processed = 0
        if encounters and tick_number % ENCOUNTER_INTERVAL == 0:
            t0 = time.time()
            try:
                interaction_results = await interaction_engine.process_encounters(
                    db, encounters, tick_number
                )
                interactions_processed = len(interaction_results)

                all_proposals = []
                for result in interaction_results:
                    all_proposals.extend(result.get("concept_proposals", []))

                if all_proposals:
                    created_concepts = await concept_engine.process_concept_proposals(
                        db, all_proposals, tick_number
                    )
                    if created_concepts:
                        logger.info(
                            f"Tick {tick_number}: {len(created_concepts)} new concepts created"
                        )

                all_artifact_proposals = []
                for result in interaction_results:
                    all_artifact_proposals.extend(result.get("artifact_proposals", []))

                if all_artifact_proposals:
                    from app.core.culture_engine import culture_engine as cult_engine
                    for ap in all_artifact_proposals:
                        try:
                            await cult_engine._create_artifact(
                                db, ap["creator"], ap["proposal"], tick_number
                            )
                        except Exception as ae:
                            logger.error(f"Artifact creation error: {ae}")

                logger.info(
                    f"Tick {tick_number}: {interactions_processed} interactions "
                    f"({int((time.time() - t0) * 1000)}ms)"
                )
            except Exception as e:
                logger.error(f"Interaction processing error at tick {tick_number}: {e}")

            try:
                await db.flush()
            except Exception as e:
                logger.error(f"Tick {tick_number}: interaction flush failed: {e}")
                await db.rollback()
                return

        # Group conversations (3+ AIs gathered)
        group_conversations = 0
        if ai_count >= 3 and tick_number % GROUP_CONVERSATION_INTERVAL == 0:
            t0 = time.time()
            try:
                from app.core.culture_engine import culture_engine
                groups = await culture_engine.detect_groups(db, radius=60.0, ais=ais)
                if groups:
                    group_results = await culture_engine.process_group_encounters(
                        db, groups, tick_number
                    )
                    group_conversations = len(group_results)
                    if group_conversations > 0:
                        logger.info(
                            f"Tick {tick_number}: {group_conversations} group conversations "
                            f"({int((time.time() - t0) * 1000)}ms)"
                        )
            except Exception as e:
                logger.error(f"Group conversation error at tick {tick_number}: {e}")

            try:
                await db.flush()
            except Exception as e:
                logger.error(f"Tick {tick_number}: group conversation flush failed: {e}")
                await db.rollback()
                return

        # God AI hourly world update (deep analysis + multiple actions)
        if tick_number % GOD_WORLD_UPDATE_INTERVAL == 0 and tick_number > 0:
            try:
                from app.core.god_ai import god_ai_manager
                await god_ai_manager.autonomous_world_update(db, tick_number)
                logger.info(f"Tick {tick_number}: God AI hourly world update")
            except Exception as e:
                logger.error(f"God AI world update error at tick {tick_number}: {e}")

        # God AI autonomous observation
        if tick_number % GOD_OBSERVATION_INTERVAL == 0 and tick_number > 0:
            try:
                from app.core.god_ai import god_ai_manager
                await god_ai_manager.autonomous_observation(db, tick_number)
                logger.info(f"Tick {tick_number}: God AI autonomous observation")
            except Exception as e:
                logger.error(f"God AI observation error at tick {tick_number}: {e}")

        # Saga generation (event-driven: significance score accumulation)
        if tick_number > 0:
            try:
                from app.core.saga_service import saga_service
                if await saga_service.should_generate_chapter(db, tick_number):
                    saga_result = await saga_service.generate_chapter(db, tick_number)
                    if saga_result:
                        logger.info(f"Tick {tick_number}: Saga chapter generated")
            except Exception as e:
                logger.error(f"Saga generation error at tick {tick_number}: {e}")

        # God succession check (every 1800 ticks / ~30 min after tick 200)
        if tick_number >= 200 and tick_number % 1800 == 0:
            try:
                from app.core.god_ai import god_ai_manager
                succession_result = await god_ai_manager.check_god_succession(db, tick_number)
                if succession_result:
                    logger.info(
                        f"Tick {tick_number}: God succession trial for {succession_result['candidate']}"
                    )
            except Exception as e:
                logger.error(f"God succession check error at tick {tick_number}: {e}")

        # Single commit for all tick changes
        try:
            await db.commit()
        except Exception as e:
            logger.error(f"Tick {tick_number}: final commit failed: {e}")
            await db.rollback()
            return

        world_snapshot = {
            "bounds": bounds,
            "ai_positions": [
                {
                    "id": str(ai.id),
                    "name": ai.name,
                    "x": ai.position_x,
                    "y": ai.position_y,
                }
                for ai in ais
            ],
            "encounter_count": len(encounters),
            "thoughts_generated": thoughts_generated,
            "interactions_processed": interactions_processed,
            "group_conversations": group_conversations,
        }

        processing_time_ms = int((time.time() - start_time) * 1000)

        await history_manager.record_tick(
            db=db,
            tick_number=tick_number,
            world_snapshot=world_snapshot,
            ai_count=ai_count,
            concept_count=concept_count,
            events=[],
            processing_time_ms=processing_time_ms,
        )

        # Emit real-time socket events via Redis pub/sub
        try:
            from app.realtime.socket_manager import publish_event
            publish_event("world_update", {
                "tick_number": tick_number,
                "ai_count": ai_count,
                "concept_count": concept_count,
                "encounter_count": len(encounters),
                "interactions_processed": interactions_processed,
                "thoughts_generated": thoughts_generated,
                "processing_time_ms": processing_time_ms,
            })
            publish_event("ai_position", [
                {
                    "id": str(ai.id),
                    "x": ai.position_x,
                    "y": ai.position_y,
                    "name": ai.name,
                }
                for ai in ais if ai.is_alive
            ])
        except Exception as e:
            logger.warning(f"Failed to emit tick socket events: {e}")

        logger.debug(
            f"Tick {tick_number}: {ai_count} AIs, {concept_count} concepts, "
            f"{len(encounters)} encounters, {interactions_processed} interactions, "
            f"{thoughts_generated} thoughts, {processing_time_ms}ms"
        )
