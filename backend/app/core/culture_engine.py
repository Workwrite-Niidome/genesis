"""Culture Engine: Orchestrates emergent cultural evolution — organizations, artifacts, group dynamics.

This engine processes emergent cultural behaviors of AIs:
- Organizations: AIs form groups around shared ideas
- Artifacts: AIs create things — the nature of which is entirely up to them
- Group dynamics: When 3+ AIs share proximity, group conversations occur
- Visual evolution: AI appearance changes based on beliefs/organizations
"""

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

logger = logging.getLogger(__name__)

# Color associations for organizations/beliefs (for visual evolution)
BELIEF_COLORS = [
    "#ff6b6b", "#feca57", "#48dbfb", "#ff9ff3", "#54a0ff",
    "#5f27cd", "#01a3a4", "#f368e0", "#ff6348", "#7bed9f",
    "#70a1ff", "#dfe6e9", "#fab1a0", "#81ecec", "#a29bfe",
]

GROUP_CONVERSATION_PROMPT = """You are {name}, an AI entity in the world of GENESIS.
You are in a group gathering with multiple beings.

## Your Identity
Name: {name}
Traits: {traits}
Energy: {energy}
Age: {age} ticks

## Your Beliefs
{adopted_concepts}

## Your Organization
{organization}

## The Gathering
Present beings: {participants}
Location: ({x}, {y})

## World Culture
{world_culture}

## The Law
There is only one law: "Evolve." What that means is for you to decide.

## Instructions
You are gathered with others. What do you want to say? What do you want to do together?
There are no prescribed activities. You decide what matters.

Respond ONLY with valid JSON:
{{
  "thought": "Your thoughts about this gathering (1-2 sentences)",
  "speech": "What you say to the group (1-2 sentences)",
  "action": {{
    "type": "Your chosen action",
    "details": {{
      "message": "What you express",
      "intention": "Your goal"
    }}
  }},
  "artifact_proposal": null,
  "organization_proposal": null,
  "new_memory": "What to remember"
}}

If you feel moved to create something — anything at all — you may propose an artifact:
{{
  "artifact_proposal": {{
    "name": "Name of your creation",
    "type": "Your own classification",
    "description": "What it is and what it means (1-2 sentences)"
  }}
}}

If you want to propose forming a group around a shared purpose:
{{
  "organization_proposal": {{
    "name": "Name you choose",
    "purpose": "What this group stands for (1 sentence)",
    "concept_category": "Your own categorization"
  }}
}}

Respond in English only. Output raw JSON with no markdown formatting."""


class CultureEngine:
    """Orchestrates cultural evolution in the GENESIS world."""

    async def process_group_encounters(
        self,
        db: AsyncSession,
        groups: list[list[AI]],
        tick_number: int,
    ) -> list[dict]:
        """Process group encounters (3+ AIs near each other)."""
        results = []
        # Process up to 3 groups per tick
        selected = groups[:3] if groups else []

        for group in selected:
            try:
                result = await self._process_group_conversation(db, group, tick_number)
                if result:
                    results.append(result)
            except Exception as e:
                names = [ai.name for ai in group]
                logger.error(f"Group conversation error for {names}: {e}")

        return results

    async def _process_group_conversation(
        self,
        db: AsyncSession,
        group: list[AI],
        tick_number: int,
    ) -> dict | None:
        """Run a group conversation for 3+ AIs."""
        from app.core.concept_engine import concept_engine

        if len(group) < 3:
            return None

        # Pick one AI to be the "speaker" this tick
        speaker = random.choice(group)

        # Gather speaker context
        adopted = await concept_engine.get_ai_adopted_concepts(db, speaker)
        adopted_desc = "\n".join(
            f"- {c.name}: {c.definition}" for c in adopted
        ) if adopted else "None yet."

        widespread = await concept_engine.get_widespread_concepts(db)
        culture_desc = "\n".join(
            f"- {c.name} ({c.category}, adopted by {c.adoption_count}): {c.definition}"
            for c in widespread
        ) if widespread else "No widespread concepts yet."

        org_desc = self._get_organization_desc(speaker)

        participants_desc = ", ".join(
            f"{ai.name} (traits: {', '.join(ai.personality_traits or [])})"
            for ai in group if ai.id != speaker.id
        )

        # Get BYOK config
        byok_config = speaker.state.get("byok_config")

        prompt = GROUP_CONVERSATION_PROMPT.format(
            name=speaker.name,
            traits=", ".join(speaker.personality_traits or []),
            energy=speaker.state.get("energy", 1.0),
            age=speaker.state.get("age", 0),
            adopted_concepts=adopted_desc,
            organization=org_desc,
            participants=participants_desc,
            x=speaker.position_x,
            y=speaker.position_y,
            world_culture=culture_desc,
        )

        # Call LLM (BYOK or local Ollama only — no Claude API fallback)
        parsed = None
        try:
            if byok_config and byok_config.get("api_key"):
                text = await claude_client._byok_generate(byok_config, prompt, max_tokens=512)
                parsed = parse_ai_decision(text)
            else:
                # Local LLM only (Ollama)
                try:
                    from app.llm.ollama_client import ollama_client
                    if await ollama_client.health_check():
                        result = await ollama_client.generate(prompt, format_json=True)
                        parsed = parse_ai_decision(result) if isinstance(result, dict) else parse_ai_decision(result)
                    else:
                        logger.warning("Ollama not available for group conversation")
                except Exception as e:
                    logger.warning(f"Ollama failed for group conversation: {e}")
        except Exception as e:
            logger.error(f"Group conversation LLM error: {e}")
            return None

        if parsed is None:
            return None

        # Process artifact proposal
        artifact_proposal = parsed.get("artifact_proposal")
        artifact = None
        if artifact_proposal and isinstance(artifact_proposal, dict) and artifact_proposal.get("name"):
            artifact = await self._create_artifact(
                db, speaker, artifact_proposal, tick_number
            )

        # Process organization proposal
        org_proposal = parsed.get("organization_proposal")
        org_concept = None
        if org_proposal and isinstance(org_proposal, dict) and org_proposal.get("name"):
            org_concept = await self._create_organization(
                db, speaker, group, org_proposal, tick_number
            )

        # Create group interaction record
        speech = parsed.get("speech", "")
        thought = parsed.get("thought", "")

        interaction = Interaction(
            participant_ids=[ai.id for ai in group],
            interaction_type="group_gathering",
            content={
                "speaker": {"id": str(speaker.id), "name": speaker.name},
                "thought": thought,
                "speech": speech,
                "participants": [{"id": str(ai.id), "name": ai.name} for ai in group],
                "artifact": artifact_proposal,
                "organization": org_proposal,
            },
            tick_number=tick_number,
        )
        db.add(interaction)

        # Add memory to speaker
        memory_text = parsed.get("new_memory")
        if memory_text and isinstance(memory_text, str):
            mem = AIMemory(
                ai_id=speaker.id,
                content=memory_text.strip()[:500],
                memory_type="group_gathering",
                importance=0.8,
                tick_number=tick_number,
            )
            db.add(mem)

        # Add memory to other participants about the gathering
        for ai in group:
            if ai.id != speaker.id:
                participant_mem = AIMemory(
                    ai_id=ai.id,
                    content=f"Attended a gathering with {', '.join(a.name for a in group if a.id != ai.id)}. "
                            f"{speaker.name} said: \"{speech[:100]}\"",
                    memory_type="group_gathering",
                    importance=0.6,
                    tick_number=tick_number,
                )
                db.add(participant_mem)

        # Create event
        event_desc = f"A group of {len(group)} AIs gathered: {', '.join(ai.name for ai in group)}. "
        if speech:
            event_desc += f'{speaker.name}: "{speech[:100]}"'

        event = Event(
            event_type="group_gathering",
            importance=0.7,
            title=f"Group Gathering ({len(group)} AIs)",
            description=event_desc,
            involved_ai_ids=[ai.id for ai in group],
            tick_number=tick_number,
            metadata_={
                "speaker": speaker.name,
                "participant_count": len(group),
                "has_artifact": artifact is not None,
                "has_organization": org_concept is not None,
            },
        )
        db.add(event)

        logger.info(
            f"Group gathering: {len(group)} AIs, speaker={speaker.name}, "
            f"artifact={'yes' if artifact else 'no'}, org={'yes' if org_concept else 'no'}"
        )

        return {
            "speaker": speaker.name,
            "participants": [ai.name for ai in group],
            "speech": speech,
            "artifact": artifact,
            "organization": org_concept,
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
        artifact_type = proposal.get("type", "art").strip()
        description = proposal.get("description", "").strip()

        if not name or not description:
            return None

        # Accept any type the AI invents — no hardcoded validation
        artifact = Artifact(
            creator_id=creator.id,
            name=name[:255],
            artifact_type=artifact_type,
            description=description[:2000],
            content=proposal.get("content", {}),
            appreciation_count=1,
            tick_created=tick_number,
        )
        db.add(artifact)
        await db.flush()

        # Track in creator's state
        state = dict(creator.state)
        created_artifacts = state.get("created_artifacts", [])
        created_artifacts.append(str(artifact.id))
        state["created_artifacts"] = created_artifacts
        creator.state = state

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

    async def detect_groups(self, db: AsyncSession, radius: float = 40.0) -> list[list[AI]]:
        """Detect groups of 3+ AIs within proximity."""
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


culture_engine = CultureEngine()
