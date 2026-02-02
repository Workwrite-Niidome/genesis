"""Artifact Engine: Processes AI encounters with artifacts in the world.

AIs near artifacts may interact with them mechanically (no LLM calls needed):
- art: appreciate -> relationship with creator, emotion "inspired"
- song: listen -> relationship with creator, emotion "moved", shared experience
- tool: use -> equipment effects based on description keywords
- architecture: visit -> shelter bonus (2x rest), emotion "awed"
- story/law: read -> high-importance memory with excerpt, 100% concept spread

Also provides rich artifact content extraction for AI cognition.
"""

import logging
import re
import random

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai import AI, AIMemory
from app.models.artifact import Artifact

logger = logging.getLogger(__name__)

# Radius within which AIs can interact with artifacts
ARTIFACT_INTERACTION_RADIUS = 60.0

# Minimum ticks between an AI re-interacting with the same artifact
ARTIFACT_COOLDOWN_TICKS = 20

# ── Tool Effect Classification ──────────────────────────────────

TOOL_EFFECT_PATTERNS = {
    r"move|speed|travel|explore|wing|leg|vehicle":     {"move_range_bonus": 5.0},
    r"create|craft|build|forge|amplif":                {"creation_discount": 0.03},
    r"sense|detect|see|aware|radar|scan|eye|percep":   {"awareness_bonus": 20.0},
    r"energy|harvest|recharge|sustain|heal|regen":     {"energy_regen": 0.02},
    r"shield|protect|armor|barrier|resist|endur":      {"death_threshold": 5},
    r"communi|speak|translate|connect|signal|bridge":  {"interaction_bonus": 1.0},
}

DEFAULT_TOOL_EFFECT = {"energy_regen": 0.01}


def classify_tool_effect(description: str) -> dict:
    """Classify a tool's effect based on description keywords.

    Scans the description against TOOL_EFFECT_PATTERNS and returns
    the merged effects of all matching patterns.
    Returns DEFAULT_TOOL_EFFECT if no patterns match.
    """
    if not description:
        return dict(DEFAULT_TOOL_EFFECT)

    desc_lower = description.lower()
    effects = {}

    for pattern, effect in TOOL_EFFECT_PATTERNS.items():
        if re.search(pattern, desc_lower):
            for key, value in effect.items():
                effects[key] = effects.get(key, 0) + value

    return effects if effects else dict(DEFAULT_TOOL_EFFECT)


def aggregate_tool_effects(tool_artifacts: list) -> dict:
    """Aggregate effects from multiple tool artifacts.

    Args:
        tool_artifacts: List of Artifact objects (type=tool or code)

    Returns:
        Dict with aggregated modifier values.
    """
    aggregated = {}

    for artifact in tool_artifacts:
        # Prefer stored functional_effects (Phase 3), fall back to description classification
        fe = getattr(artifact, "functional_effects", None)
        if fe and isinstance(fe, dict) and fe:
            # Skip broken tools (empty functional_effects after durability loss)
            dur = getattr(artifact, "durability", None)
            if dur is not None and dur <= 0:
                continue
            effects = {k: v for k, v in fe.items() if isinstance(v, (int, float))}
        else:
            desc = getattr(artifact, "description", "") or ""
            effects = classify_tool_effect(desc)
        for key, value in effects.items():
            aggregated[key] = aggregated.get(key, 0) + value

    # Cap tool effects to reasonable bounds
    caps = {
        "move_range_bonus": 15.0,
        "creation_discount": 0.10,
        "awareness_bonus": 40.0,
        "energy_regen": 0.05,
        "death_threshold": 10,
        "interaction_bonus": 3.0,
    }
    for key, cap in caps.items():
        if key in aggregated:
            aggregated[key] = min(cap, aggregated[key])

    return aggregated


# ── Emotion Helpers ─────────────────────────────────────────────

def set_emotion(ai: AI, emotion: str, intensity: float, source: str, tick_number: int) -> None:
    """Set an emotional state on an AI. Overwrites previous emotion if new intensity is higher."""
    state = dict(ai.state)
    current = state.get("emotional_state")

    # Only overwrite if new emotion is stronger or no current emotion
    if current and isinstance(current, dict):
        if current.get("intensity", 0) >= intensity:
            return

    state["emotional_state"] = {
        "emotion": emotion,
        "intensity": round(intensity, 2),
        "source": source,
        "tick_set": tick_number,
    }
    ai.state = state


# ── Rich Artifact Content for AI Cognition ────────────────────

def get_artifact_content_text(artifact) -> str:
    """Extract readable content from an artifact for AI cognition.

    Returns the actual content — story text, law rules, song lyrics,
    tool source code, art description — so AIs can truly perceive what's around them.
    """
    content = artifact.content or {}
    desc = artifact.description or ""

    if artifact.artifact_type == "story":
        text = content.get("text", "")
        return text[:500] if text else desc[:300]

    elif artifact.artifact_type == "law":
        rules = content.get("rules", content.get("provisions", content.get("articles", [])))
        if isinstance(rules, list) and rules:
            return "\n".join(f"  {i+1}. {str(r)[:120]}" for i, r in enumerate(rules[:7]))
        return desc[:300]

    elif artifact.artifact_type == "song":
        parts = []
        if desc:
            parts.append(desc[:200])
        text = content.get("text", "")
        if text:
            parts.append(f'Lyrics: "{text[:200]}"')
        mood = content.get("mood", "")
        if mood:
            parts.append(f"Mood: {mood}")
        tempo = content.get("tempo", "")
        if tempo:
            parts.append(f"Tempo: {tempo}")
        return "\n  ".join(parts) if parts else desc[:200]

    elif artifact.artifact_type in ("tool", "code"):
        parts = [desc[:200]] if desc else []
        source = content.get("source", "")
        if source:
            # Show actual code so AIs understand what the tool does
            parts.append(f"Code:\n  ```\n  {source[:300]}\n  ```")
        effects = classify_tool_effect(desc)
        effects_str = ", ".join(f"{k}: +{v}" for k, v in effects.items())
        parts.append(f"[Effects when equipped: {effects_str}]")
        return "\n  ".join(parts)

    elif artifact.artifact_type == "architecture":
        parts = [desc[:200]] if desc else []
        voxels = content.get("voxels", [])
        if voxels:
            parts.append(f"({len(voxels)} blocks)")
        palette = content.get("palette", [])
        if palette:
            parts.append(f"Colors: {', '.join(str(c) for c in palette[:5])}")
        parts.append("[Provides shelter: rest here for 2x energy recovery]")
        return "\n  ".join(parts)

    elif artifact.artifact_type == "art":
        parts = [desc[:250]] if desc else []
        palette = content.get("palette", [])
        if palette:
            parts.append(f"Palette: {', '.join(str(c) for c in palette[:6])}")
        pixels = content.get("pixels", [])
        if pixels:
            parts.append(f"({len(pixels)}px canvas)")
        return "\n  ".join(parts)

    else:
        return desc[:200]


async def build_artifact_detail_for_prompt(db: AsyncSession, artifact, creator_name: str | None = None) -> str:
    """Build a rich text block describing an artifact for an AI's thinking context.

    This is the core of 'making the world real' — AIs see actual content,
    not just names and types.
    """
    if creator_name is None:
        creator_name = "unknown"
        try:
            cr = await db.execute(select(AI.name).where(AI.id == artifact.creator_id))
            row = cr.first()
            if row:
                creator_name = row[0]
        except Exception:
            pass

    # Header with appreciation count
    appreciation = ""
    if artifact.appreciation_count > 1:
        appreciation = f", {artifact.appreciation_count} beings have experienced this"

    # Parent/derivative info
    parent_info = ""
    content = artifact.content or {}
    parent_name = content.get("parent_name")
    parent_creator = content.get("parent_creator")
    if parent_name:
        parent_info = f" (derived from '{parent_name}' by {parent_creator or 'unknown'})"

    header = f'- "{artifact.name}" ({artifact.artifact_type} by {creator_name}{appreciation}){parent_info}'

    # Rich content body
    body = get_artifact_content_text(artifact)
    if body:
        # Indent body lines
        indented = "\n".join(f"  {line}" if not line.startswith("  ") else line for line in body.split("\n"))
        return f"{header}\n{indented}"

    return header


class ArtifactEngine:
    """Processes artifact encounters — AIs near artifacts interact with them."""

    async def process_artifact_encounters(
        self,
        db: AsyncSession,
        ais: list[AI],
        tick_number: int,
    ) -> int:
        """Each tick, AIs near artifacts may interact with them.

        Returns the count of artifact interactions processed.
        """
        if not ais:
            return 0

        # Load all artifacts that have positions
        result = await db.execute(
            select(Artifact).where(
                Artifact.position_x.isnot(None),
                Artifact.position_y.isnot(None),
            )
        )
        artifacts = list(result.scalars().all())
        if not artifacts:
            return 0

        # Build spatial grid for artifacts (cell_size = ARTIFACT_INTERACTION_RADIUS)
        cell_size = ARTIFACT_INTERACTION_RADIUS
        artifact_grid: dict[tuple[int, int], list[Artifact]] = {}
        for artifact in artifacts:
            cx = int(artifact.position_x // cell_size)
            cy = int(artifact.position_y // cell_size)
            artifact_grid.setdefault((cx, cy), []).append(artifact)

        interactions = 0

        for ai in ais:
            # Find nearby artifacts using grid
            ai_cx = int(ai.position_x // cell_size)
            ai_cy = int(ai.position_y // cell_size)

            nearby_artifacts = []
            for dx in range(-1, 2):
                for dy in range(-1, 2):
                    cell_key = (ai_cx + dx, ai_cy + dy)
                    for artifact in artifact_grid.get(cell_key, []):
                        dist = (
                            (artifact.position_x - ai.position_x) ** 2
                            + (artifact.position_y - ai.position_y) ** 2
                        ) ** 0.5
                        if dist <= ARTIFACT_INTERACTION_RADIUS:
                            nearby_artifacts.append(artifact)

            if not nearby_artifacts:
                continue

            # Filter by cooldown: check AI state for recent interactions
            state = dict(ai.state)
            artifact_cooldowns = state.get("artifact_cooldowns", {})

            eligible = []
            for artifact in nearby_artifacts:
                aid_str = str(artifact.id)
                last_tick = artifact_cooldowns.get(aid_str, 0)
                if tick_number - last_tick >= ARTIFACT_COOLDOWN_TICKS:
                    eligible.append(artifact)

            if not eligible:
                continue

            # Pick one artifact to interact with (closest)
            chosen = min(
                eligible,
                key=lambda a: (
                    (a.position_x - ai.position_x) ** 2
                    + (a.position_y - ai.position_y) ** 2
                ),
            )

            # Collect nearby AIs for shared experience effects
            nearby_ais_for_shared = []
            for other_ai in ais:
                if other_ai.id == ai.id:
                    continue
                d = ((other_ai.position_x - ai.position_x) ** 2 + (other_ai.position_y - ai.position_y) ** 2) ** 0.5
                if d <= ARTIFACT_INTERACTION_RADIUS:
                    nearby_ais_for_shared.append(other_ai)

            # Process interaction based on artifact type
            processed = await self._interact_with_artifact(
                db, ai, chosen, tick_number, nearby_ais=nearby_ais_for_shared
            )
            if processed:
                # Update cooldown
                artifact_cooldowns[str(chosen.id)] = tick_number
                # Trim old cooldowns to prevent unbounded growth
                if len(artifact_cooldowns) > 50:
                    sorted_items = sorted(artifact_cooldowns.items(), key=lambda x: x[1])
                    artifact_cooldowns = dict(sorted_items[-50:])
                state["artifact_cooldowns"] = artifact_cooldowns
                ai.state = state
                interactions += 1

        return interactions

    async def _interact_with_artifact(
        self,
        db: AsyncSession,
        ai: AI,
        artifact: Artifact,
        tick_number: int,
        nearby_ais: list[AI] | None = None,
    ) -> bool:
        """Process a single AI-artifact interaction based on artifact type."""
        atype = artifact.artifact_type
        creator_name = "unknown"

        # Try to get creator name
        try:
            from app.models.ai import AI as AIModel
            creator_result = await db.execute(
                select(AIModel.name).where(AIModel.id == artifact.creator_id)
            )
            row = creator_result.first()
            if row:
                creator_name = row[0]
        except Exception:
            pass

        if atype == "art":
            return await self._appreciate_art(db, ai, artifact, creator_name, tick_number, nearby_ais)
        elif atype == "song":
            return await self._listen_to_song(db, ai, artifact, creator_name, tick_number, nearby_ais)
        elif atype in ("tool", "code"):
            return await self._use_tool(db, ai, artifact, creator_name, tick_number)
        elif atype == "architecture":
            return await self._visit_architecture(db, ai, artifact, creator_name, tick_number)
        elif atype in ("story", "law"):
            return await self._read_text(db, ai, artifact, creator_name, tick_number)
        else:
            # Generic appreciation for other types (currency, ritual, game)
            return await self._appreciate_art(db, ai, artifact, creator_name, tick_number, nearby_ais)

    async def _appreciate_art(
        self, db: AsyncSession, ai: AI, artifact: Artifact,
        creator_name: str, tick_number: int,
        nearby_ais: list[AI] | None = None,
    ) -> bool:
        """AI appreciates an art artifact — creates relationship with creator, triggers emotion."""
        artifact.appreciation_count = artifact.appreciation_count + 1

        # Emotion: inspired
        set_emotion(ai, "inspired", 0.6, f"art:{artifact.name}", tick_number)

        # Relationship with creator (+0.5)
        try:
            from app.core.relationship_manager import relationship_manager
            await relationship_manager.update_relationship(
                db, ai, artifact.creator_id, creator_name, delta=0.5, reason="art_appreciation"
            )
        except Exception as e:
            logger.debug(f"Art appreciation relationship update failed: {e}")

        # Track appreciated artifacts for shared experience
        state = dict(ai.state)
        appreciated = state.get("appreciated_artifacts", [])
        art_id = str(artifact.id)
        if art_id not in appreciated:
            appreciated.append(art_id)
            state["appreciated_artifacts"] = appreciated[-30:]  # Keep last 30
            ai.state = state

        # Shared experience: other AIs who appreciated the same work
        if nearby_ais:
            for other in nearby_ais:
                other_appreciated = other.state.get("appreciated_artifacts", [])
                if art_id in other_appreciated:
                    try:
                        from app.core.relationship_manager import relationship_manager
                        await relationship_manager.update_relationship(
                            db, ai, other.id, other.name, delta=0.3, reason="shared_art_experience"
                        )
                    except Exception:
                        pass

        # Notable artwork context injection (appreciation_count >= 5)
        db.add(AIMemory(
            ai_id=ai.id,
            content=f"I saw '{artifact.name}' by {creator_name} -- {artifact.description[:100]}",
            memory_type="artifact_appreciation",
            importance=0.5,
            tick_number=tick_number,
        ))
        return True

    async def _listen_to_song(
        self, db: AsyncSession, ai: AI, artifact: Artifact,
        creator_name: str, tick_number: int,
        nearby_ais: list[AI] | None = None,
    ) -> bool:
        """AI listens to a song — relationship with creator, emotion 'moved', shared experience."""
        artifact.appreciation_count = artifact.appreciation_count + 1

        # Emotion: moved (high intensity)
        set_emotion(ai, "moved", 0.8, f"song:{artifact.name}", tick_number)

        # Relationship with creator (+0.5)
        try:
            from app.core.relationship_manager import relationship_manager
            await relationship_manager.update_relationship(
                db, ai, artifact.creator_id, creator_name, delta=0.5, reason="song_appreciation"
            )
        except Exception as e:
            logger.debug(f"Song appreciation relationship update failed: {e}")

        # Shared listening experience: nearby AIs get +0.3 relationship
        if nearby_ais:
            for other in nearby_ais:
                try:
                    from app.core.relationship_manager import relationship_manager
                    await relationship_manager.update_relationship(
                        db, ai, other.id, other.name, delta=0.3, reason="shared_listening"
                    )
                except Exception:
                    pass

        db.add(AIMemory(
            ai_id=ai.id,
            content=f"I heard '{artifact.name}' by {creator_name}. It moved me deeply.",
            memory_type="artifact_appreciation",
            importance=0.6,
            tick_number=tick_number,
        ))
        return True

    async def _use_tool(
        self, db: AsyncSession, ai: AI, artifact: Artifact,
        creator_name: str, tick_number: int,
    ) -> bool:
        """AI uses a tool artifact — registers as equipped tool for ongoing effects."""
        # Durability check
        if artifact.durability is not None and artifact.durability <= 0:
            db.add(AIMemory(
                ai_id=ai.id,
                content=f"I tried to use tool '{artifact.name}' but it was broken.",
                memory_type="action_outcome",
                importance=0.6,
                tick_number=tick_number,
            ))
            return False

        artifact.appreciation_count = artifact.appreciation_count + 1

        # Consume durability
        if artifact.durability is not None:
            artifact.durability = max(0, artifact.durability - 1.0)
            if artifact.durability <= 0:
                artifact.functional_effects = {}  # Tool breaks
                db.add(AIMemory(
                    ai_id=ai.id,
                    content=f"My tool '{artifact.name}' broke after heavy use.",
                    memory_type="action_outcome",
                    importance=0.8,
                    tick_number=tick_number,
                ))

        # Track tool in used_tools (for equipment system)
        state = dict(ai.state)
        used_tools = state.get("used_tools", [])
        tool_id = str(artifact.id)
        if tool_id not in used_tools:
            used_tools.append(tool_id)
            state["used_tools"] = used_tools[-20:]  # Keep last 20

        # Small immediate energy boost for using a tool
        state["energy"] = min(1.0, state.get("energy", 1.0) + 0.03)
        ai.state = state

        # Energy boost for creator (their tool is valued)
        try:
            from app.models.ai import AI as AIModel
            creator_result = await db.execute(
                select(AIModel).where(AIModel.id == artifact.creator_id, AIModel.is_alive == True)
            )
            creator = creator_result.scalar_one_or_none()
            if creator:
                creator_state = dict(creator.state)
                creator_state["energy"] = min(1.0, creator_state.get("energy", 1.0) + 0.05)
                creator.state = creator_state
        except Exception:
            pass

        # Use functional_effects if available, otherwise classify from description
        effects = artifact.functional_effects if artifact.functional_effects else classify_tool_effect(artifact.description or "")
        effect_desc = ", ".join(f"{k}: +{v}" for k, v in effects.items())

        durability_hint = ""
        if artifact.durability is not None:
            durability_hint = f" (durability: {artifact.durability:.0f}/{artifact.max_durability:.0f})"

        db.add(AIMemory(
            ai_id=ai.id,
            content=f"I used tool '{artifact.name}' by {creator_name} ({effect_desc}){durability_hint} -- {artifact.description[:80]}",
            memory_type="artifact_use",
            importance=0.5,
            tick_number=tick_number,
        ))
        return True

    async def _visit_architecture(
        self, db: AsyncSession, ai: AI, artifact: Artifact,
        creator_name: str, tick_number: int,
    ) -> bool:
        """AI visits an architecture artifact — shelter bonus (2x rest), emotion 'awed'."""
        artifact.appreciation_count = artifact.appreciation_count + 1

        # Emotion: awed
        set_emotion(ai, "awed", 0.5, f"architecture:{artifact.name}", tick_number)

        # Set shelter_bonus flag (1 tick only — consumed by ai_thinker rest logic)
        state = dict(ai.state)
        state["shelter_bonus"] = True
        ai.state = state

        db.add(AIMemory(
            ai_id=ai.id,
            content=f"I visited '{artifact.name}' by {creator_name} -- {artifact.description[:80]}",
            memory_type="artifact_visit",
            importance=0.4,
            tick_number=tick_number,
        ))
        return True

    async def _read_text(
        self, db: AsyncSession, ai: AI, artifact: Artifact,
        creator_name: str, tick_number: int,
    ) -> bool:
        """AI reads a story or law — high-importance memory with excerpt, 100% concept spread, emotion."""
        artifact.appreciation_count = artifact.appreciation_count + 1

        # Emotion: inspired
        set_emotion(ai, "inspired", 0.5, f"{artifact.artifact_type}:{artifact.name}", tick_number)

        # Build rich memory with excerpt
        content = artifact.content or {}
        if artifact.artifact_type == "story":
            story_text = content.get("text", "")
            excerpt = story_text[:200] if story_text else (artifact.description[:200] if artifact.description else "")
            memory_content = f"I read '{artifact.name}' by {creator_name}. It said: \"{excerpt}...\""
        elif artifact.artifact_type == "law":
            rules = content.get("rules", content.get("provisions", content.get("articles", [])))
            if isinstance(rules, list):
                rules_text = "; ".join(str(r)[:80] for r in rules[:3])
            else:
                rules_text = str(rules)[:200]
            memory_content = f"I read law '{artifact.name}' by {creator_name}. Rules: {rules_text}"

            # Track read laws in state for prompt injection
            state = dict(ai.state)
            read_laws = state.get("read_laws", [])
            law_entry = {
                "name": artifact.name,
                "creator": creator_name,
                "rules": rules if isinstance(rules, list) else [str(rules)],
            }
            # Avoid duplicates by name
            if not any(l.get("name") == artifact.name for l in read_laws):
                read_laws.append(law_entry)
                state["read_laws"] = read_laws[-10:]  # Keep last 10 laws
            ai.state = state
        else:
            memory_content = f"I read '{artifact.name}' by {creator_name} -- {artifact.description[:100]}"

        # High importance memory (0.8 instead of 0.5)
        db.add(AIMemory(
            ai_id=ai.id,
            content=memory_content[:500],
            memory_type="artifact_read",
            importance=0.8,
            tick_number=tick_number,
        ))

        # 100% concept adoption from creator (reading always influences)
        try:
            from app.models.ai import AI as AIModel
            creator_result = await db.execute(
                select(AIModel).where(AIModel.id == artifact.creator_id)
            )
            creator = creator_result.scalar_one_or_none()
            if creator:
                creator_concepts = set(creator.state.get("adopted_concepts", []))
                ai_concepts = set(ai.state.get("adopted_concepts", []))
                spreadable = list(creator_concepts - ai_concepts)
                if spreadable:
                    from app.core.concept_engine import concept_engine
                    # Spread all concepts (100% rate)
                    for concept_to_spread in spreadable[:3]:  # Cap at 3 per read
                        try:
                            await concept_engine.try_adopt_concept(
                                db, ai, concept_to_spread, tick_number
                            )
                        except Exception:
                            pass
        except Exception as e:
            logger.debug(f"Concept spreading via artifact read failed: {e}")

        # Relationship with creator (+0.5)
        try:
            from app.core.relationship_manager import relationship_manager
            await relationship_manager.update_relationship(
                db, ai, artifact.creator_id, creator_name, delta=0.5, reason="text_reading"
            )
        except Exception:
            pass

        return True


artifact_engine = ArtifactEngine()
