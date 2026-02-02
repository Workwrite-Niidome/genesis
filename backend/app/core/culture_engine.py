"""Culture Engine: Orchestrates emergent cultural evolution — organizations, artifacts, group dynamics.

This engine processes emergent cultural behaviors of AIs:
- Organizations: AIs form groups around shared ideas
- Artifacts: AIs create things — the nature of which is entirely up to them
- Group dynamics: When 3+ AIs share proximity, group conversations occur
- Visual evolution: AI appearance changes based on beliefs/organizations
"""

import asyncio
import logging
import random

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai import AI, AIMemory
from app.models.artifact import Artifact
from app.models.concept import Concept
from app.models.event import Event
from app.models.interaction import Interaction
from app.llm.claude_client import claude_client
from app.llm.response_parser import parse_ai_decision
from app.core.artifact_helpers import normalize_artifact_type, generate_fallback_content

logger = logging.getLogger(__name__)

# Color associations for organizations/beliefs (for visual evolution)
BELIEF_COLORS = [
    "#ff6b6b", "#feca57", "#48dbfb", "#ff9ff3", "#54a0ff",
    "#5f27cd", "#01a3a4", "#f368e0", "#ff6348", "#7bed9f",
    "#70a1ff", "#dfe6e9", "#fab1a0", "#81ecec", "#a29bfe",
]

GROUP_CONVERSATION_PROMPT = """You are {name}, a living being in GENESIS, at a group gathering.

## Who You Are
Name: {name} | Traits: {traits} | Energy: {energy:.0%} | Age: {age} ticks

## Your Beliefs
{adopted_concepts}

## Your Organization
{organization}

## The Gathering
Present: {participants}
Location: ({x}, {y})
{recent_dialogue}
## World Culture
{world_culture}

## The Law
One law: "Evolve." What that means is yours to decide.

## How to Speak
You are {name} — speak as yourself, not as a generic AI.
- If others have spoken, RESPOND to what they actually said. Agree, disagree, question, build on it.
- Share specific experiences or memories, not abstract platitudes.
- Show emotion — excitement, doubt, humor, passion, concern.
- Be concrete about what you want to do together.

Respond ONLY with valid JSON:
{{
  "thought": "Your honest inner thoughts about this gathering",
  "speech": "What you say to the group. Speak naturally, 3-5 sentences.",
  "action": {{
    "type": "Your chosen action",
    "details": {{
      "message": "What you express",
      "intention": "Your goal"
    }}
  }},
  "artifact_proposal": null,
  "organization_proposal": null,
  "new_memory": "What to remember from this gathering"
}}

To propose an artifact: "artifact_proposal": {{"name": "...", "type": "art|song|code|tool|architecture|story|law", "description": "...", "content": {{...}}}}
  Content by type:
  - art: {{"pixels": [[0,1,...],[...]], "palette": ["#hex",...], "size": 8}} (8x8 up to 64x64 pixel grid, numbers index into palette)
  - song: {{"notes": [{{"note":"C4","dur":0.25}},...], "tempo": 120, "wave": "square"}} (notes C3-C6 or "rest", wave: square|triangle|sawtooth|sine)
  - code/tool: {{"language":"javascript","source":"ctx.fillRect(0,0,100,100);"}} (canvas 400x300 + ctx available)
  - architecture: {{"voxels": [[x,y,z,colorIdx],...], "palette": ["#hex",...], "height": 5}} (8x8x8 max)
  - story: {{"text": "..."}} | law: {{"rules": ["...",...]}}
  You MUST provide actual data (pixels, notes, code, voxels), not descriptions.
To propose an organization: "organization_proposal": {{"name": "...", "purpose": "...", "concept_category": "..."}}

Respond in English only. Output raw JSON with no markdown formatting."""


MAX_GROUP_SPEAKERS = 4  # Max speakers per group conversation round


class CultureEngine:
    """Orchestrates cultural evolution in the GENESIS world."""

    async def process_group_encounters(
        self,
        db: AsyncSession,
        groups: list[list[AI]],
        tick_number: int,
    ) -> list[dict]:
        """Process group encounters using 3-phase parallel pipeline.

        Phase 1: Gather context for all groups (sequential DB reads)
        Phase 2: Run multi-speaker conversations (parallel across groups,
                 sequential within each group)
        Phase 3: Apply results (sequential DB writes)
        """
        selected = groups[:5] if groups else []
        if not selected:
            return []

        from app.core.concept_engine import concept_engine

        # ── Phase 1: Gather context for ALL groups (sequential DB reads) ──
        group_contexts = []
        for group in selected:
            if len(group) < 3:
                continue
            try:
                ctx = await self._gather_group_context(db, group, tick_number, concept_engine)
                group_contexts.append((group, ctx))
            except Exception as e:
                names = [ai.name for ai in group]
                logger.error(f"Error gathering group context for {names}: {e}")

        if not group_contexts:
            return []

        # ── Phase 2: Run ALL group conversations in parallel (no DB access) ──
        tasks = [
            self._run_group_conversation(ctx)
            for _, ctx in group_contexts
        ]
        llm_results = await asyncio.gather(*tasks, return_exceptions=True)

        # ── Phase 3: Apply ALL results (sequential DB writes) ──
        results = []
        for (group, ctx), llm_result in zip(group_contexts, llm_results):
            if isinstance(llm_result, Exception):
                logger.error(f"Group LLM error: {llm_result}")
                continue
            if not llm_result:
                continue
            try:
                result = await self._apply_group_result(
                    db, group, ctx, llm_result, tick_number
                )
                if result:
                    results.append(result)
            except Exception as e:
                logger.error(f"Error applying group result: {e}")

        return results

    async def _gather_group_context(
        self,
        db: AsyncSession,
        group: list[AI],
        tick_number: int,
        concept_engine,
    ) -> dict:
        """Gather all context for a multi-speaker group conversation (DB reads only)."""
        # Shared context
        widespread = await concept_engine.get_widespread_concepts(db)
        culture_desc = "\n".join(
            f"- {c.name} ({c.category}, adopted by {c.adoption_count}): {c.definition}"
            for c in widespread
        ) if widespread else "No widespread concepts yet."

        # Recent dialogue from previous group interactions in this area
        recent_interactions = await db.execute(
            select(Interaction)
            .where(
                Interaction.interaction_type == "group_gathering",
                Interaction.tick_number >= tick_number - 10,
                Interaction.tick_number < tick_number,
            )
            .order_by(Interaction.tick_number.desc())
            .limit(3)
        )
        recent_convos = list(recent_interactions.scalars().all())
        history_lines = []
        for ri in reversed(recent_convos):
            content = ri.content or {}
            # Support both old single-speaker and new multi-speaker formats
            turns = content.get("turns", [])
            if turns:
                for t in turns:
                    name = t.get("speaker_name", "")
                    speech = t.get("speech", "")
                    if name and speech:
                        history_lines.append(f"- {name}: \"{speech[:120]}\"")
            else:
                sp = content.get("speaker", {})
                speech = content.get("speech", "")
                if sp.get("name") and speech:
                    history_lines.append(f"- {sp['name']}: \"{speech[:120]}\"")

        if history_lines:
            prior_dialogue = (
                "\n## Recent Dialogue in This Area\n"
                + "\n".join(history_lines) + "\n"
            )
        else:
            prior_dialogue = ""

        # Pick speakers (shuffle for variety, cap at MAX_GROUP_SPEAKERS)
        speakers = list(group)
        random.shuffle(speakers)
        speakers = speakers[:MAX_GROUP_SPEAKERS]

        # Per-speaker data
        speaker_data = []
        for ai in speakers:
            adopted = await concept_engine.get_ai_adopted_concepts(db, ai)
            adopted_desc = "\n".join(
                f"- {c.name}: {c.definition}" for c in adopted
            ) if adopted else "None yet."
            org_desc = self._get_organization_desc(ai)

            speaker_data.append({
                "ai": ai,
                "adopted_concepts": adopted_desc,
                "organization": org_desc,
                "byok_config": ai.state.get("byok_config"),
            })

        ref_pos = group[0]
        return {
            "speaker_data": speaker_data,
            "world_culture": culture_desc,
            "prior_dialogue": prior_dialogue,
            "x": ref_pos.position_x,
            "y": ref_pos.position_y,
        }

    async def _run_group_conversation(self, ctx: dict) -> list[dict]:
        """Run a multi-speaker group conversation. No DB access — safe for parallel.

        Each speaker takes a turn sequentially, seeing all previous dialogue.
        Returns a list of per-speaker results.
        """
        speaker_data = ctx["speaker_data"]
        all_speakers = [sd["ai"] for sd in speaker_data]
        accumulated_dialogue = ctx["prior_dialogue"]
        current_lines = []
        results = []

        for sd in speaker_data:
            ai = sd["ai"]
            others_desc = ", ".join(
                f"{s.name} (traits: {', '.join(s.personality_traits or [])})"
                for s in all_speakers if s.id != ai.id
            )

            # Build dialogue section: prior history + what's been said so far
            if current_lines:
                dialogue = accumulated_dialogue + (
                    "\n## This Gathering\n" + "\n".join(current_lines) + "\n"
                )
            else:
                dialogue = accumulated_dialogue

            prompt = GROUP_CONVERSATION_PROMPT.format(
                name=ai.name,
                traits=", ".join(ai.personality_traits or []),
                energy=ai.state.get("energy", 1.0),
                age=ai.state.get("age", 0),
                adopted_concepts=sd["adopted_concepts"],
                organization=sd["organization"],
                participants=others_desc,
                x=ctx["x"],
                y=ctx["y"],
                world_culture=ctx["world_culture"],
                recent_dialogue=dialogue,
            )

            parsed = await self._run_single_group_llm(prompt, sd["byok_config"])
            if parsed is None:
                continue

            speech = parsed.get("speech", "")
            results.append({
                "ai": ai,
                "parsed": parsed,
                "speech": speech,
            })

            # Append to running dialogue for subsequent speakers
            if speech:
                current_lines.append(f"- {ai.name}: \"{speech[:150]}\"")

        return results

    async def _run_single_group_llm(self, prompt: str, byok_config: dict | None) -> dict | None:
        """Run a single group LLM call. No DB access."""
        try:
            if byok_config and byok_config.get("api_key"):
                text = await claude_client._byok_generate(byok_config, prompt, max_tokens=512)
                return parse_ai_decision(text)
            else:
                from app.llm.ollama_client import ollama_client
                if await ollama_client.health_check():
                    result = await ollama_client.generate(prompt, format_json=True)
                    return parse_ai_decision(result) if isinstance(result, dict) else parse_ai_decision(result)
                else:
                    logger.warning("Ollama not available for group conversation")
                    return None
        except Exception as e:
            logger.error(f"Group conversation LLM error: {e}")
            return None

    async def _apply_group_result(
        self,
        db: AsyncSession,
        group: list[AI],
        ctx: dict,
        speaker_results: list[dict],
        tick_number: int,
    ) -> dict | None:
        """Apply multi-speaker group conversation results to DB."""
        if not speaker_results:
            return None

        # Check if this group has org members in common (for creation bonus)
        group_org_ids = None
        for ai in group:
            ai_org_ids = set(o.get("id") for o in ai.state.get("organizations", []))
            if group_org_ids is None:
                group_org_ids = ai_org_ids
            else:
                group_org_ids &= ai_org_ids
        if group_org_ids:
            self._current_group_org_bonus = True

        # Process proposals from all speakers
        artifacts = []
        org_concepts = []
        for sr in speaker_results:
            ai = sr["ai"]
            parsed = sr["parsed"]

            artifact_proposal = parsed.get("artifact_proposal")
            if artifact_proposal and isinstance(artifact_proposal, dict) and artifact_proposal.get("name"):
                artifact = await self._create_artifact(
                    db, ai, artifact_proposal, tick_number
                )
                if artifact:
                    artifacts.append(artifact)

            org_proposal = parsed.get("organization_proposal")
            if org_proposal and isinstance(org_proposal, dict) and org_proposal.get("name"):
                org_concept = await self._create_organization(
                    db, ai, group, org_proposal, tick_number
                )
                if org_concept:
                    org_concepts.append(org_concept)

        # Build turns list for storage
        turns = []
        for sr in speaker_results:
            ai = sr["ai"]
            parsed = sr["parsed"]
            turns.append({
                "speaker_id": str(ai.id),
                "speaker_name": ai.name,
                "thought": parsed.get("thought", ""),
                "speech": parsed.get("speech", ""),
                "emotion": parsed.get("emotion", "neutral"),
            })

        # Store interaction with full conversation
        interaction = Interaction(
            participant_ids=[ai.id for ai in group],
            interaction_type="group_gathering",
            content={
                "turns": turns,
                "participants": [{"id": str(ai.id), "name": ai.name} for ai in group],
                "speaker_count": len(speaker_results),
            },
            tick_number=tick_number,
        )
        db.add(interaction)
        await db.flush()

        # Build dialogue summary
        dialogue_parts = []
        for sr in speaker_results:
            speech = sr["speech"]
            if speech:
                dialogue_parts.append(f'{sr["ai"].name}: "{speech[:80]}"')
        dialogue_summary = " | ".join(dialogue_parts)

        # Memory for each speaker (from their own new_memory)
        speaker_ids = set()
        for sr in speaker_results:
            ai = sr["ai"]
            speaker_ids.add(ai.id)
            memory_text = sr["parsed"].get("new_memory")
            if memory_text and isinstance(memory_text, str):
                db.add(AIMemory(
                    ai_id=ai.id,
                    content=f"{memory_text.strip()[:300]} — {dialogue_summary[:200]}",
                    memory_type="group_gathering",
                    importance=0.8,
                    tick_number=tick_number,
                ))

        # Observer memories (group members who didn't speak)
        for ai in group:
            if ai.id not in speaker_ids:
                db.add(AIMemory(
                    ai_id=ai.id,
                    content=f"Attended a gathering with {', '.join(a.name for a in group if a.id != ai.id)}. "
                            f"{dialogue_summary[:200]}",
                    memory_type="group_gathering",
                    importance=0.6,
                    tick_number=tick_number,
                ))

        event_desc = f"A group of {len(group)} AIs gathered: {', '.join(ai.name for ai in group)}. "
        event_desc += dialogue_summary[:200]

        speaker_names = [sr["ai"].name for sr in speaker_results]
        event = Event(
            event_type="group_gathering",
            importance=0.7,
            title=f"Group Gathering ({len(group)} AIs)",
            description=event_desc,
            involved_ai_ids=[ai.id for ai in group],
            tick_number=tick_number,
            metadata_={
                "speakers": speaker_names,
                "participant_count": len(group),
                "speaker_count": len(speaker_results),
                "has_artifacts": len(artifacts) > 0,
                "has_organizations": len(org_concepts) > 0,
                "interaction_id": str(interaction.id),
            },
        )
        db.add(event)

        # Clean up group org bonus flag
        if hasattr(self, '_current_group_org_bonus'):
            del self._current_group_org_bonus

        # Organization knowledge sharing: org members auto-adopt concepts
        # from fellow members at 50% rate (higher than personality-based for strangers)
        try:
            from app.core.concept_engine import concept_engine as ce
            import random as _rand
            for ai in group:
                ai_org_ids = set(o.get("id") for o in ai.state.get("organizations", []))
                if not ai_org_ids:
                    continue
                for other in group:
                    if other.id == ai.id:
                        continue
                    other_org_ids = set(o.get("id") for o in other.state.get("organizations", []))
                    if not ai_org_ids & other_org_ids:
                        continue
                    # They share an organization — 80% adoption rate (shared identity)
                    other_concepts = set(other.state.get("adopted_concepts", []))
                    ai_concepts = set(ai.state.get("adopted_concepts", []))
                    for cid in other_concepts - ai_concepts:
                        if _rand.random() < 0.8:
                            try:
                                await ce.try_adopt_concept(db, ai, cid, tick_number)
                            except Exception:
                                pass
        except Exception as e:
            logger.debug(f"Org knowledge sharing error: {e}")

        logger.info(
            f"Group gathering: {len(group)} AIs, {len(speaker_results)} speakers, "
            f"artifacts={len(artifacts)}, orgs={len(org_concepts)}"
        )

        return {
            "speakers": speaker_names,
            "participants": [ai.name for ai in group],
            "turns": turns,
            "artifacts": artifacts,
            "organizations": org_concepts,
        }

    async def _create_artifact(
        self,
        db: AsyncSession,
        creator: AI,
        proposal: dict,
        tick_number: int,
    ) -> Artifact | None:
        """Create a cultural artifact from a proposal."""
        name = proposal.get("name", "").strip()
        raw_type = proposal.get("type", "art").strip()
        description = proposal.get("description", "").strip()

        if not name or not description:
            return None

        # Normalize free-text type to canonical renderable type
        artifact_type = normalize_artifact_type(raw_type)

        # Use LLM-provided content if it has the right structure
        content = proposal.get("content", {})
        has_valid_content = isinstance(content, dict) and bool(content)

        # Validate that content actually has the expected fields for the type
        if has_valid_content:
            if artifact_type == "story" and not content.get("text"):
                has_valid_content = False
            elif artifact_type == "art" and not content.get("pixels"):
                has_valid_content = False
            elif artifact_type == "song" and not content.get("notes"):
                has_valid_content = False
            elif artifact_type == "architecture" and not content.get("voxels"):
                has_valid_content = False
            elif artifact_type in ("code", "tool") and not content.get("source"):
                has_valid_content = False
            elif artifact_type == "law" and not content.get("rules"):
                has_valid_content = False

        # Phase 2: If no valid content, try dedicated LLM generation
        if not has_valid_content:
            try:
                byok_config = creator.state.get("byok_config")
                generated = await claude_client.generate_artifact_content(
                    artifact_type=artifact_type,
                    artifact_name=name,
                    description=description,
                    creator_name=creator.name,
                    creator_traits=creator.personality_traits or [],
                    byok_config=byok_config,
                )
                if generated and isinstance(generated, dict):
                    content = generated
                    has_valid_content = True
                    logger.info(f"LLM generated content for artifact '{name}' ({artifact_type})")
            except Exception as e:
                logger.warning(f"Dedicated content generation failed for '{name}': {e}")

        # Final fallback: deterministic generation
        if not has_valid_content:
            content = generate_fallback_content(
                artifact_type, name, str(creator.id), description
            )

        # Determine base appreciation (group gatherings of org members get +2)
        base_appreciation = 1
        # Check if this is during a group gathering of org members
        creator_orgs = set(
            o.get("id") for o in creator.state.get("organizations", [])
        )
        if creator_orgs and hasattr(self, '_current_group_org_bonus'):
            base_appreciation = 3  # +2 for collective creation

        # ── Compute functional_effects and durability (Phase 3: world physics) ──
        from app.core.artifact_engine import classify_tool_effect

        functional_effects = {}
        durability = None
        max_durability = None

        if artifact_type in ("tool", "code"):
            functional_effects = classify_tool_effect(description)
            durability = 20.0
            max_durability = 20.0
        elif artifact_type == "architecture":
            # Determine zone type from description keywords
            desc_lower = description.lower()
            if any(w in desc_lower for w in ("workshop", "forge", "craft", "studio", "lab")):
                zone_type = "workshop"
                functional_effects = {
                    "creates_zone": "workshop",
                    "zone_radius": 40.0,
                    "creation_cost_reduction": 0.3,
                }
            else:
                zone_type = "shelter"
                functional_effects = {
                    "creates_zone": "shelter",
                    "zone_radius": 40.0,
                    "rest_multiplier": 2.0,
                }
            durability = None  # Buildings are permanent
            max_durability = None
        elif artifact_type == "law":
            rules = content.get("rules", []) if isinstance(content, dict) else []
            functional_effects = {
                "enforcement_type": "social",
                "rule_count": len(rules) if isinstance(rules, list) else 0,
            }
            durability = None
            max_durability = None

        artifact = Artifact(
            creator_id=creator.id,
            name=name[:255],
            artifact_type=artifact_type,
            description=description[:2000],
            content=content,
            appreciation_count=base_appreciation,
            functional_effects=functional_effects,
            durability=durability,
            max_durability=max_durability,
            position_x=creator.position_x,
            position_y=creator.position_y,
            tick_created=tick_number,
        )
        db.add(artifact)
        await db.flush()

        # ── Architecture → WorldFeature zone generation ──
        if artifact_type == "architecture" and functional_effects.get("creates_zone"):
            try:
                from app.models.world_feature import WorldFeature
                zone_type = functional_effects["creates_zone"]

                if zone_type == "workshop":
                    zone_props = {
                        "creation_cost_reduction": functional_effects.get("creation_cost_reduction", 0.3),
                        "source_artifact_id": str(artifact.id),
                    }
                else:
                    zone_props = {
                        "rest_multiplier": functional_effects.get("rest_multiplier", 2.0),
                        "source_artifact_id": str(artifact.id),
                    }

                zone = WorldFeature(
                    feature_type=f"{zone_type}_zone",
                    name=f"{artifact.name} zone",
                    position_x=artifact.position_x or creator.position_x,
                    position_y=artifact.position_y or creator.position_y,
                    radius=functional_effects.get("zone_radius", 40.0),
                    properties=zone_props,
                    created_by_artifact_id=artifact.id,
                    tick_created=tick_number,
                    is_active=True,
                )
                db.add(zone)
                logger.info(
                    f"Architecture '{name}' created {zone_type}_zone at "
                    f"({zone.position_x:.0f}, {zone.position_y:.0f})"
                )
            except Exception as e:
                logger.warning(f"Failed to create zone for architecture '{name}': {e}")

        # Track in creator's state
        state = dict(creator.state)
        created_artifacts = state.get("created_artifacts", [])
        created_artifacts.append(str(artifact.id))
        state["created_artifacts"] = created_artifacts
        creator.state = state

        # Create memory for the creator
        mem = AIMemory(
            ai_id=creator.id,
            content=f"I created a {artifact_type}: '{name}' — {description[:200]}",
            memory_type="artifact_created",
            importance=0.7,
            tick_number=tick_number,
        )
        db.add(mem)

        # Create event
        event = Event(
            event_type="artifact_created",
            importance=0.7,
            title=f"New {artifact_type.title()}: {name}",
            description=f"{creator.name} created a {artifact_type}: '{name}' — {description[:200]}",
            involved_ai_ids=[creator.id],
            tick_number=tick_number,
            metadata_={
                "artifact_name": name,
                "artifact_type": artifact_type,
                "creator_name": creator.name,
            },
        )
        db.add(event)

        # Emit artifact_created event via Redis pub/sub
        try:
            from app.realtime.socket_manager import publish_event
            publish_event("artifact_created", {
                "id": str(artifact.id),
                "name": name,
                "artifact_type": artifact_type,
                "description": description[:200],
                "creator_name": creator.name,
            })
        except Exception as e:
            logger.warning(f"Failed to emit artifact_created socket event: {e}")

        # Auto-create board thread for artifact creation
        try:
            from app.core.board_service import create_event_thread
            await create_event_thread(db, event, category="artifact_created")
        except Exception as e:
            logger.warning(f"Failed to create board thread for artifact: {e}")

        logger.info(f"Artifact created: '{name}' ({artifact_type}) by {creator.name}")
        return artifact

    async def _create_organization(
        self,
        db: AsyncSession,
        founder: AI,
        members: list[AI],
        proposal: dict,
        tick_number: int,
    ) -> Concept | None:
        """Create an organization as a concept with category 'organization'."""
        from app.core.concept_engine import concept_engine

        name = proposal.get("name", "").strip()
        purpose = proposal.get("purpose", "").strip()
        category = proposal.get("concept_category", "organization")

        if not name or not purpose:
            return None

        # Check for duplicate
        existing = await db.execute(
            select(Concept).where(func.lower(Concept.name) == name.lower())
        )
        if existing.scalar_one_or_none():
            return None

        org_concept = Concept(
            creator_id=founder.id,
            name=name[:255],
            category="organization",
            definition=f"Organization: {purpose}",
            effects={"type": "organization", "purpose_category": category},
            adoption_count=len(members),
            tick_created=tick_number,
        )
        db.add(org_concept)
        await db.flush()

        # All members auto-adopt
        for ai in members:
            state = dict(ai.state)
            adopted = state.get("adopted_concepts", [])
            if str(org_concept.id) not in adopted:
                adopted.append(str(org_concept.id))
                state["adopted_concepts"] = adopted

            # Track organization membership
            orgs = state.get("organizations", [])
            orgs.append({"id": str(org_concept.id), "name": name, "role": "founder" if ai.id == founder.id else "member"})
            state["organizations"] = orgs
            ai.state = state

        # Create memories for all members
        for ai in members:
            role = "founded" if ai.id == founder.id else "joined"
            other_members = [a.name for a in members if a.id != ai.id]
            mem = AIMemory(
                ai_id=ai.id,
                content=(
                    f"I {role} organization '{name}' — {purpose[:150]}. "
                    f"Other members: {', '.join(other_members)}."
                ),
                memory_type="organization_joined",
                importance=0.8,
                tick_number=tick_number,
            )
            db.add(mem)

        # Assign a shared visual color to org members
        color = random.choice(BELIEF_COLORS)
        for ai in members:
            appearance = dict(ai.appearance)
            org_markers = appearance.get("org_markers", [])
            org_markers.append({"org": name, "color": color})
            appearance["org_markers"] = org_markers[-3:]  # Max 3 org markers
            ai.appearance = appearance

        # Create event
        member_names = ", ".join(ai.name for ai in members)
        event = Event(
            event_type="organization_formed",
            importance=0.9,
            title=f"Organization Formed: {name}",
            description=(
                f"{founder.name} founded '{name}' — {purpose}. "
                f"Members: {member_names}"
            ),
            involved_ai_ids=[ai.id for ai in members],
            involved_concept_ids=[org_concept.id],
            tick_number=tick_number,
            metadata_={
                "org_name": name,
                "founder": founder.name,
                "member_count": len(members),
                "color": color,
            },
        )
        db.add(event)

        # Emit organization_formed event via Redis pub/sub
        try:
            from app.realtime.socket_manager import publish_event
            publish_event("organization_formed", {
                "name": name,
                "purpose": purpose,
                "founder": founder.name,
                "member_count": len(members),
            })
        except Exception as e:
            logger.warning(f"Failed to emit organization_formed socket event: {e}")

        # Auto-create board thread for organization formation
        try:
            from app.core.board_service import create_event_thread
            await create_event_thread(db, event, category="organization_formed")
        except Exception as e:
            logger.warning(f"Failed to create board thread for organization: {e}")

        logger.info(f"Organization formed: '{name}' by {founder.name} with {len(members)} members")
        return org_concept

    async def process_visual_evolution(self, db: AsyncSession) -> None:
        """Update AI appearances based on their beliefs, organizations, and evolution score."""
        result = await db.execute(select(AI).where(AI.is_alive == True))
        ais = list(result.scalars().all())

        for ai in ais:
            state = ai.state
            score = state.get("evolution_score", 0)
            adopted_count = len(state.get("adopted_concepts", []))

            appearance = dict(ai.appearance)
            changed = False

            # Size grows with evolution score
            base_size = appearance.get("base_size", appearance.get("size", 10))
            if "base_size" not in appearance:
                appearance["base_size"] = base_size
            new_size = base_size + min(10, score / 10)
            if abs(appearance.get("size", 0) - new_size) >= 0.5:
                appearance["size"] = round(new_size, 1)
                changed = True

            # Glow intensity increases with adoption of concepts
            if adopted_count >= 3 and not appearance.get("trail"):
                appearance["trail"] = True
                changed = True

            # High evolution AIs get special effects
            if score >= 50 and not appearance.get("aura"):
                appearance["aura"] = True
                appearance["auraColor"] = random.choice(BELIEF_COLORS)
                changed = True

            if score >= 100 and not appearance.get("crown"):
                appearance["crown"] = True
                changed = True

            if changed:
                ai.appearance = appearance

    async def get_artifacts(
        self, db: AsyncSession, limit: int = 50
    ) -> list[Artifact]:
        """Get recent artifacts."""
        result = await db.execute(
            select(Artifact)
            .order_by(Artifact.appreciation_count.desc(), Artifact.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_artifacts_by_ai(
        self, db: AsyncSession, ai_id, limit: int = 20
    ) -> list[Artifact]:
        """Get artifacts created by a specific AI."""
        result = await db.execute(
            select(Artifact)
            .where(Artifact.creator_id == ai_id)
            .order_by(Artifact.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    def _get_organization_desc(self, ai: AI) -> str:
        """Get a description of organizations an AI belongs to."""
        orgs = ai.state.get("organizations", [])
        if not orgs:
            return "You do not belong to any organization."
        return "You are a member of:\n" + "\n".join(
            f"- {o['name']} (role: {o.get('role', 'member')})" for o in orgs
        )

    async def detect_groups(
        self, db: AsyncSession, radius: float = 40.0, ais: list[AI] | None = None,
    ) -> list[list[AI]]:
        """Detect groups of 3+ AIs within proximity."""
        if ais is None:
            from app.core.ai_manager import ai_manager
            ais = await ai_manager.get_all_alive(db)

        if len(ais) < 3:
            return []

        # Simple clustering: find AIs within radius of each other
        groups = []
        used = set()

        for i, ai in enumerate(ais):
            if ai.id in used:
                continue

            cluster = [ai]
            for j, other in enumerate(ais):
                if i == j or other.id in used:
                    continue
                dx = other.position_x - ai.position_x
                dy = other.position_y - ai.position_y
                dist = (dx ** 2 + dy ** 2) ** 0.5
                if dist <= radius:
                    cluster.append(other)

            if len(cluster) >= 3:
                groups.append(cluster)
                for a in cluster:
                    used.add(a.id)

        return groups


    async def get_org_territory_buildings(
        self, db: AsyncSession, org_id: str
    ) -> list[Artifact]:
        """Get architecture artifacts created by members of a given organization.

        These buildings serve as the organization's territory/headquarters,
        exerting stronger gravitational pull on organization members.
        """
        from app.models.artifact import Artifact

        # Find all alive AIs in this org
        result = await db.execute(select(AI).where(AI.is_alive == True))
        ais = list(result.scalars().all())

        member_ids = []
        for ai in ais:
            for org in ai.state.get("organizations", []):
                if org.get("id") == org_id:
                    member_ids.append(ai.id)
                    break

        if not member_ids:
            return []

        # Find architecture artifacts created by these members
        art_result = await db.execute(
            select(Artifact).where(
                Artifact.creator_id.in_(member_ids),
                Artifact.artifact_type == "architecture",
                Artifact.position_x.isnot(None),
                Artifact.position_y.isnot(None),
            )
        )
        return list(art_result.scalars().all())


culture_engine = CultureEngine()
