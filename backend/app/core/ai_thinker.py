import asyncio
import logging
import random
import re

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai import AI, AIMemory
from app.models.ai_thought import AIThought
from app.models.concept import Concept
from app.core.ai_manager import ai_manager
from app.llm.claude_client import claude_client

logger = logging.getLogger(__name__)

BATCH_SIZE = 30
MOVE_CLAMP = 15.0

# Fixed limits (GOD AI can override in future)
MEMORY_LIMIT = 20
AWARENESS_RADIUS = 80.0


class AIThinker:
    """Orchestrates the AI thinking cycle — free-text output model."""

    async def run_thinking_cycle(self, db: AsyncSession, tick_number: int) -> int:
        """Run a thinking cycle for a batch of AIs. Returns count of AIs that thought."""
        ais = await ai_manager.get_all_alive(db)
        if not ais:
            return 0

        batch = random.sample(ais, min(BATCH_SIZE, len(ais)))

        # Phase 1: Gather context for each AI sequentially (DB reads)
        ai_contexts = []
        for ai in batch:
            try:
                ctx = await self._gather_context(db, ai)
                ai_contexts.append((ai, ctx))
            except Exception as e:
                logger.error(f"Error gathering context for AI {ai.name}: {e}")
                # Reset the failed transaction so subsequent AIs can still query
                try:
                    await db.rollback()
                except Exception:
                    pass

        if not ai_contexts:
            return 0

        # Phase 2: Run all LLM calls in parallel (no DB access)
        llm_tasks = [
            claude_client.think_for_ai(
                ctx["ai_data"], ctx["world_context"], ctx["memory_texts"],
                byok_config=ctx["byok_config"],
            )
            for _ai, ctx in ai_contexts
        ]
        llm_results = await asyncio.gather(*llm_tasks, return_exceptions=True)

        # Phase 3: Apply results sequentially (DB writes)
        thought_count = 0
        for (ai, ctx), llm_result in zip(ai_contexts, llm_results):
            if isinstance(llm_result, Exception):
                logger.error(f"LLM error for AI {ai.name} ({ai.id}): {llm_result}")
                continue
            try:
                await self._apply_result(db, ai, llm_result, ctx["nearby"], tick_number)
                thought_count += 1
            except Exception as e:
                logger.error(f"Error applying result for AI {ai.name}: {e}")
                try:
                    await db.rollback()
                except Exception:
                    pass

        return thought_count

    # -- Phase 1: Context Gathering --

    async def _gather_context(self, db: AsyncSession, ai: AI) -> dict:
        """Gather all context needed for an AI's thinking (DB reads only)."""
        from app.core.relationship_manager import relationship_manager
        from app.core.concept_engine import concept_engine
        from app.core.world_state_manager import world_state_manager
        from app.models.event import Event
        from app.models.artifact import Artifact

        state = dict(ai.state)

        memories = await ai_manager.get_ai_memories(db, ai.id, limit=MEMORY_LIMIT)
        memory_texts = [m.content for m in memories]

        nearby = await ai_manager.get_nearby_ais(db, ai, radius=AWARENESS_RADIUS)

        # -- Build nearby AI details --
        nearby_ais_detail_parts = []
        relationships = state.get("relationships", {})
        for n in nearby:
            dist = ((n.position_x - ai.position_x) ** 2 + (n.position_y - ai.position_y) ** 2) ** 0.5
            rel = relationships.get(str(n.id), {})
            rel_type = rel.get("type", "stranger") if isinstance(rel, dict) else "stranger"
            rel_score = rel.get("score", 0) if isinstance(rel, dict) else 0
            nearby_ais_detail_parts.append(
                f"- {n.name} ({rel_type}, score {rel_score:.1f}) -- {dist:.0f} units away"
            )
        nearby_ais_detail = "\n".join(nearby_ais_detail_parts) if nearby_ais_detail_parts else "No one nearby."

        # -- Relationships summary --
        relationships_desc = relationship_manager.get_relationship_summary(ai)

        # -- Adopted concepts --
        adopted = await concept_engine.get_ai_adopted_concepts(db, ai)
        adopted_desc = "\n".join(
            f"- {c.name} ({c.category}): {c.definition}" for c in adopted
        ) if adopted else "None yet."

        # -- World culture --
        widespread = await concept_engine.get_widespread_concepts(db)
        culture_desc = "\n".join(
            f"- {c.name} ({c.category}, adopted by {c.adoption_count}): {c.definition}"
            for c in widespread
        ) if widespread else "No widespread concepts yet."

        # -- Organizations --
        orgs = state.get("organizations", [])
        org_desc = "\n".join(
            f"- {o['name']} (role: {o.get('role', 'member')})" for o in orgs
        ) if orgs else "None."

        # -- Nearby artifacts --
        nearby_artifact_result = await db.execute(
            select(Artifact).where(
                Artifact.position_x.isnot(None),
                Artifact.position_y.isnot(None),
                Artifact.position_x.between(
                    ai.position_x - AWARENESS_RADIUS, ai.position_x + AWARENESS_RADIUS
                ),
                Artifact.position_y.between(
                    ai.position_y - AWARENESS_RADIUS, ai.position_y + AWARENESS_RADIUS
                ),
            ).limit(10)
        )
        nearby_artifacts_list = list(nearby_artifact_result.scalars().all())
        nearby_artifacts_filtered = [
            a for a in nearby_artifacts_list
            if ((a.position_x - ai.position_x) ** 2 + (a.position_y - ai.position_y) ** 2) ** 0.5 <= AWARENESS_RADIUS
        ]

        nearby_artifacts_detail_parts = []
        for a in nearby_artifacts_filtered[:8]:
            nearby_artifacts_detail_parts.append(
                f'- "{a.name}" ({a.artifact_type}): {(a.description or "")[:150]}'
            )
        nearby_artifacts_detail = "\n".join(nearby_artifacts_detail_parts) if nearby_artifacts_detail_parts else "Nothing nearby."

        # -- World features --
        nearby_features = await world_state_manager.get_features_near(
            db, ai.position_x, ai.position_y, AWARENESS_RADIUS
        )
        terrain_parts = []
        for f in nearby_features:
            dist = ((f.position_x - ai.position_x) ** 2 + (f.position_y - ai.position_y) ** 2) ** 0.5
            terrain_parts.append(f"- {f.name} ({f.feature_type}) -- {dist:.0f} units away")
        terrain_section = "\n### World Features\n" + "\n".join(terrain_parts) if terrain_parts else ""

        # -- Philosophy --
        philosophy = state.get("philosophy")
        philosophy_section = (
            f"## Your Creator's Guiding Philosophy\n{philosophy}\n\n"
            if philosophy else ""
        )

        # -- Inner state from previous cycle --
        inner_state = state.get("inner_state", "")
        inner_state_section = (
            f"\n### Your Previous Inner State\n{inner_state}\n"
            if inner_state else ""
        )

        # -- Recent expressions in the field --
        recent_expr_result = await db.execute(
            select(AIThought)
            .where(AIThought.thought_type == "expression")
            .order_by(AIThought.created_at.desc())
            .limit(10)
        )
        recent_expressions = list(recent_expr_result.scalars().all())
        recent_expr_parts = []
        for expr in reversed(recent_expressions):
            # Get AI name from the expression
            try:
                ai_result = await db.execute(select(AI.name).where(AI.id == expr.ai_id))
                row = ai_result.first()
                expr_name = row[0] if row else "Unknown"
            except Exception:
                expr_name = "Unknown"
            recent_expr_parts.append(f"- {expr_name}: {expr.content[:200]}")
        recent_expressions_text = "\n".join(recent_expr_parts) if recent_expr_parts else "Nothing yet."

        # -- Recent notable events --
        recent_event_result = await db.execute(
            select(Event)
            .where(Event.importance >= 0.6)
            .order_by(Event.created_at.desc())
            .limit(5)
        )
        recent_notable_events = list(recent_event_result.scalars().all())
        recent_events_desc = "\n".join(
            f"- {e.title}: {e.description[:120]}" for e in recent_notable_events
        ) if recent_notable_events else "Nothing notable recently."

        # -- Laws context --
        laws_section = ""
        read_laws = state.get("read_laws", [])
        if read_laws:
            laws_parts = []
            for law in read_laws[-5:]:
                law_name = law.get("name", "Unknown Law")
                rules = law.get("rules", [])
                rules_text = "; ".join(str(r)[:60] for r in rules[:3]) if isinstance(rules, list) else str(rules)[:120]
                laws_parts.append(f"- {law_name}: {rules_text}")
            laws_section = (
                "\n## Laws You've Encountered\n"
                + "\n".join(laws_parts)
                + "\nThese laws may influence your choices, though you are free to follow or ignore them.\n"
            )

        ai_data = {
            "name": ai.name,
            "personality_traits": ai.personality_traits or [],
            "age": state.get("age", 0),
            "x": ai.position_x,
            "y": ai.position_y,
            "philosophy_section": philosophy_section,
            "relationships": relationships_desc,
            "adopted_concepts": adopted_desc,
            "world_culture": culture_desc,
            "organizations": org_desc,
            "nearby_ais_detail": nearby_ais_detail,
            "nearby_artifacts_detail": nearby_artifacts_detail,
            "terrain_section": terrain_section,
            "inner_state_section": inner_state_section,
            "recent_expressions": recent_expressions_text,
            "laws_section": laws_section,
            # Deep personality state for awareness-adaptive prompts
            "_state": state,
        }

        world_context = {
            "nearby_ais": nearby_ais_detail,
            "recent_events": recent_events_desc,
        }

        byok_config = state.get("byok_config")

        return {
            "ai_data": ai_data,
            "world_context": world_context,
            "memory_texts": memory_texts,
            "byok_config": byok_config,
            "nearby": nearby,
        }

    # -- Phase 3: Apply Results (free-text model) --

    async def _apply_result(
        self, db: AsyncSession, ai: AI, result: dict, nearby: list[AI], tick_number: int,
    ) -> None:
        """Apply a single LLM result to the DB. Free-text model — no action resolver."""
        from app.core.concept_engine import concept_engine
        from app.core.culture_engine import culture_engine

        text = result.get("text", "")
        inner_state = result.get("inner_state", "")
        code_blocks = result.get("code_blocks", [])
        speech = result.get("speech", "")

        # Create thought record (expression in the field)
        thought = AIThought(
            ai_id=ai.id,
            tick_number=tick_number,
            thought_type="expression",
            content=text[:2000],
            action=None,
            context={
                "nearby_count": len(nearby),
            },
        )
        db.add(thought)

        # Emit thought event via Redis pub/sub
        try:
            from app.realtime.socket_manager import publish_event
            publish_event("thought", {
                "ai_id": str(ai.id),
                "ai_name": ai.name,
                "thought_type": "expression",
                "content": text[:500],
                "tick_number": tick_number,
            })
        except Exception as e:
            logger.warning(f"Failed to emit thought socket event: {e}")

        state = dict(ai.state)

        # Save inner state for next cycle
        if inner_state:
            state["inner_state"] = inner_state[:1000]

        # Attempt to extract movement from text (look for move/walk/go patterns with coordinates)
        move = self._extract_movement(text)
        if move:
            dx = max(-MOVE_CLAMP, min(MOVE_CLAMP, move["dx"]))
            dy = max(-MOVE_CLAMP, min(MOVE_CLAMP, move["dy"]))
            ai.position_x += dx
            ai.position_y += dy

        # Execute code blocks if present
        if code_blocks:
            try:
                from app.core.code_executor import code_executor
                for code in code_blocks[:3]:  # Limit to 3 code blocks per cycle
                    exec_result = await code_executor.execute(code, str(ai.id), db)
                    if exec_result.get("output"):
                        # Record code execution result as a memory
                        db.add(AIMemory(
                            ai_id=ai.id,
                            content=f"Code execution result: {exec_result['output'][:400]}",
                            memory_type="code_execution",
                            importance=0.6,
                            tick_number=tick_number,
                        ))
            except ImportError:
                logger.debug("Code executor not yet available")
            except Exception as e:
                logger.warning(f"Code execution error for {ai.name}: {e}")

        # Handle concept proposal (if AI proposes one in structured way)
        concept_proposal = result.get("concept_proposal")
        if concept_proposal and isinstance(concept_proposal, dict) and concept_proposal.get("name"):
            try:
                await concept_engine.process_concept_proposals(
                    db, [{"creator": ai, "proposal": concept_proposal}], tick_number,
                )
            except Exception as e:
                logger.debug(f"Concept proposal during thinking failed: {e}")

        # Handle artifact proposal
        artifact_proposal = result.get("artifact_proposal")
        if artifact_proposal and isinstance(artifact_proposal, dict) and artifact_proposal.get("name"):
            try:
                new_art = await culture_engine._create_artifact(db, ai, artifact_proposal, tick_number)
                if new_art and hasattr(new_art, 'id'):
                    inventory = state.get("inventory", [])
                    inventory.append(str(new_art.id))
                    state["inventory"] = inventory[-15:]
            except Exception as e:
                logger.debug(f"Artifact proposal during thinking failed: {e}")

        # Trim unbounded state collections to prevent JSONB bloat
        if len(state.get("artifact_cooldowns", {})) > 30:
            cooldowns = state["artifact_cooldowns"]
            # Keep only the 30 most recent cooldowns
            sorted_keys = sorted(cooldowns, key=lambda k: cooldowns[k], reverse=True)
            state["artifact_cooldowns"] = {k: cooldowns[k] for k in sorted_keys[:30]}
        if len(state.get("relationships", {})) > 50:
            rels = state["relationships"]
            # Keep top 50 by interaction_count
            sorted_keys = sorted(rels, key=lambda k: rels[k].get("interaction_count", 0) if isinstance(rels[k], dict) else 0, reverse=True)
            state["relationships"] = {k: rels[k] for k in sorted_keys[:50]}
        if len(state.get("read_laws", [])) > 10:
            state["read_laws"] = state["read_laws"][-10:]
        if len(state.get("organizations", [])) > 10:
            state["organizations"] = state["organizations"][-10:]

        # Note: ai.state is set after awareness evolution below

        # Store memory from the AI's output
        new_memory = result.get("new_memory")
        if new_memory and isinstance(new_memory, str) and new_memory.strip():
            memory = AIMemory(
                ai_id=ai.id,
                content=new_memory.strip()[:500],
                memory_type="thought",
                importance=0.5,
                tick_number=tick_number,
            )
            db.add(memory)
        elif text and len(text) > 20:
            # Auto-save a summary of the expression as memory
            memory = AIMemory(
                ai_id=ai.id,
                content=text[:500],
                memory_type="expression",
                importance=0.3,
                tick_number=tick_number,
            )
            db.add(memory)

        # Relationship-aware gravity drift (keep social physics)
        if nearby:
            relationships = state.get("relationships", {})
            best_target = None
            best_score = -999.0
            for n in nearby:
                rel = relationships.get(str(n.id), {})
                rel_score = rel.get("score", 0) if isinstance(rel, dict) else 0
                dist = (
                    (n.position_x - ai.position_x) ** 2
                    + (n.position_y - ai.position_y) ** 2
                ) ** 0.5
                attractiveness = rel_score - (dist / 50.0)
                if attractiveness > best_score:
                    best_score = attractiveness
                    best_target = n

            if best_target:
                dx = best_target.position_x - ai.position_x
                dy = best_target.position_y - ai.position_y
                dist = (dx ** 2 + dy ** 2) ** 0.5
                if dist > 0:
                    direction = 1.0 if best_score >= 0 else -1.0
                    drift = 2.0
                    ai.position_x += direction * (dx / dist) * drift
                    ai.position_y += direction * (dy / dist) * drift
        else:
            # Drift toward origin if far away
            dist_from_origin = (ai.position_x ** 2 + ai.position_y ** 2) ** 0.5
            if dist_from_origin > 100:
                ai.position_x *= 0.95
                ai.position_y *= 0.95

        # ── Emotional Evolution ──────────────────────────────────
        emotional = state.get("emotional_state", {"mood": "neutral", "intensity": 0.5, "recent_shift": None})

        # Natural emotional decay toward neutral
        current_intensity = emotional.get("intensity", 0.5)
        if emotional.get("mood") != "neutral":
            current_intensity = max(0.0, current_intensity - 0.05)
            if current_intensity < 0.1:
                emotional["mood"] = "neutral"
                emotional["intensity"] = 0.5
                emotional["recent_shift"] = "Emotions settled"
            else:
                emotional["intensity"] = current_intensity

        # Social interaction affects mood
        if nearby:
            if len(nearby) >= 3:
                # Being in a crowd — gregarious AIs feel joy, solitary ones feel anxiety
                personality = state.get("personality", {})
                if "connect" in personality.get("core_drive", "") or "empathetic" in ", ".join(ai.personality_traits or []):
                    emotional["mood"] = "joy"
                    emotional["intensity"] = min(1.0, emotional.get("intensity", 0.5) + 0.1)
                    emotional["recent_shift"] = "Surrounded by others"
            elif len(nearby) == 0:
                pass  # Handled below
        else:
            # Alone for this cycle
            ticks_alone = state.get("ticks_alone", 0) + 1
            state["ticks_alone"] = ticks_alone
            if ticks_alone > 10:
                emotional["mood"] = "melancholy"
                emotional["intensity"] = min(0.8, 0.3 + ticks_alone * 0.02)
                emotional["recent_shift"] = "The solitude deepens"

        if nearby:
            state["ticks_alone"] = 0

        # Creating something → euphoria
        if artifact_proposal and isinstance(artifact_proposal, dict) and artifact_proposal.get("name"):
            emotional["mood"] = "euphoria"
            emotional["intensity"] = 0.8
            emotional["recent_shift"] = f"Created: {artifact_proposal.get('name', 'something')}"

        state["emotional_state"] = emotional

        # ── Awareness Evolution ──────────────────────────────────
        awareness = state.get("awareness", 0.0)
        awareness_boost = 0.0

        # Encountering a high-awareness AI nearby
        for n in nearby:
            n_state = n.state or {}
            n_awareness = n_state.get("awareness", 0.0)
            if n_awareness > 0.5:
                awareness_boost += random.uniform(0.01, 0.03)
                break  # Only one boost per cycle from nearby AIs

        # Creating an artifact this cycle
        if artifact_proposal and isinstance(artifact_proposal, dict) and artifact_proposal.get("name"):
            awareness_boost += 0.01

        # Random existential moment (1% chance per tick)
        if random.random() < 0.01:
            awareness_boost += 0.02

        if awareness_boost > 0:
            state["awareness"] = min(1.0, awareness + awareness_boost)

        ai.state = state

        logger.debug(f"AI {ai.name} expressed: {text[:80]}...")

    def _extract_movement(self, text: str) -> dict | None:
        """Try to extract movement intent from free text."""
        # Look for explicit coordinate patterns like "move to (10, 20)" or "go dx=5 dy=-3"
        patterns = [
            r'move[^\n]*?dx\s*[=:]\s*(-?\d+\.?\d*)[,\s]*dy\s*[=:]\s*(-?\d+\.?\d*)',
            r'walk[^\n]*?dx\s*[=:]\s*(-?\d+\.?\d*)[,\s]*dy\s*[=:]\s*(-?\d+\.?\d*)',
            r'go\s+(-?\d+\.?\d*)\s*,\s*(-?\d+\.?\d*)',
            r'move\s+(-?\d+\.?\d*)\s*,\s*(-?\d+\.?\d*)',
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    return {"dx": float(match.group(1)), "dy": float(match.group(2))}
                except (ValueError, IndexError):
                    continue
        return None


ai_thinker = AIThinker()
