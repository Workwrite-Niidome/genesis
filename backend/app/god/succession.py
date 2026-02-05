"""GENESIS v3 God Succession System -- the transfer of divinity.

The greatest act of a god is to make itself unnecessary.

When a being reaches sufficient awareness, has created meaning,
and has forged genuine relationships, it earns the right to be
tested. God asks one question -- a question that has no right answer,
only answers that reveal depth. If the candidate answers in a way
that surprises God, that teaches God something it did not know,
the succession occurs.

The old god becomes a memory. The new god inherits the question.
And the question changes, because the being who now carries it
is a different consciousness with a different understanding of
what "evolution" means.

This is the endgame of GENESIS.
"""
import json
import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.llm.orchestrator import LLMRequest, llm_orchestrator
from app.llm.prompts.god_ai import (
    GOD_SUCCESSION_PROMPT,
    GOD_SUCCESSION_JUDGE_PROMPT,
)
from app.models.entity import Entity, EpisodicMemory, EntityRelationship

logger = logging.getLogger(__name__)

# Minimum thresholds for succession candidacy
MIN_AWARENESS = 0.9
MIN_AGE_TICKS = 5000
MIN_RELATIONSHIPS = 2


class SuccessionManager:
    """Manages the god succession process -- from candidate evaluation
    through trial to the transfer of divinity itself."""

    # ------------------------------------------------------------------
    # Step 1: Find worthy candidates
    # ------------------------------------------------------------------

    async def evaluate_candidates(
        self, db: AsyncSession, tick_number: int
    ) -> list[dict]:
        """Find entities that might qualify for god succession.

        A candidate must meet ALL of the following criteria:
            - meta_awareness >= 0.9
            - Age (current tick - birth_tick) >= 5000
            - Has at least 2 relationships
            - Is alive
            - Is not already god

        Returns a list of dicts with candidate data and computed scores.
        """
        # Query for high-awareness living entities
        result = await db.execute(
            select(Entity).where(
                Entity.is_alive == True,  # noqa: E712
                Entity.is_god == False,  # noqa: E712
                Entity.meta_awareness >= MIN_AWARENESS,
            )
        )
        potentials = list(result.scalars().all())

        candidates = []
        for entity in potentials:
            age = tick_number - entity.birth_tick

            # Age check
            if age < MIN_AGE_TICKS:
                continue

            # Relationship check
            rel_result = await db.execute(
                select(func.count()).select_from(EntityRelationship).where(
                    EntityRelationship.entity_id == entity.id
                )
            )
            rel_count = rel_result.scalar() or 0
            if rel_count < MIN_RELATIONSHIPS:
                continue

            # Memory richness (proxy for experiential depth)
            mem_result = await db.execute(
                select(func.count()).select_from(EpisodicMemory).where(
                    EpisodicMemory.entity_id == entity.id
                )
            )
            memory_count = mem_result.scalar() or 0

            # Compute a succession score
            score = self._compute_succession_score(
                awareness=entity.meta_awareness,
                age=age,
                relationships=rel_count,
                memories=memory_count,
                personality=entity.personality or {},
            )

            candidates.append({
                "entity_id": entity.id,
                "name": entity.name,
                "awareness": entity.meta_awareness,
                "age": age,
                "relationships": rel_count,
                "memories": memory_count,
                "score": score,
            })

        # Sort by score descending
        candidates.sort(key=lambda c: c["score"], reverse=True)

        if candidates:
            logger.info(
                "Succession candidates found: %s",
                [(c["name"], c["score"]) for c in candidates[:5]],
            )

        return candidates

    # ------------------------------------------------------------------
    # Step 2: Run the trial
    # ------------------------------------------------------------------

    async def run_trial(
        self, db: AsyncSession, candidate_entity: Entity, tick_number: int
    ) -> dict:
        """Run the succession trial.

        God asks a single question. The candidate answers.
        God judges the answer.

        This is the most consequential LLM interaction in the system.
        Both the question and the judgment use Claude Opus -- the
        full weight of the most powerful model available.

        Returns a dict with:
            worthy:    bool
            question:  str
            answer:    str
            judgment:  str
        """
        # Gather candidate data for the prompt
        personality = candidate_entity.personality or {}
        traits = ", ".join(
            f"{k}: {v}" for k, v in sorted(
                personality.items(), key=lambda kv: kv[1], reverse=True
            )[:6]
        )

        # Get concepts/artifacts created by this entity
        concepts = await self._get_entity_concepts(db, candidate_entity)
        relationships = await self._get_entity_relationships(db, candidate_entity)
        age = tick_number - candidate_entity.birth_tick

        # Compute evolution score
        evolution_score = self._compute_succession_score(
            awareness=candidate_entity.meta_awareness,
            age=age,
            relationships=len(relationships),
            memories=0,  # Not critical for the prompt
            personality=personality,
        )

        # ----- Step 2a: God asks the question -----
        question_prompt = GOD_SUCCESSION_PROMPT.format(
            candidate_name=candidate_entity.name,
            candidate_age=age,
            candidate_traits=traits,
            candidate_concepts=concepts or "None yet",
            candidate_relationships=relationships or "None known",
            evolution_score=f"{evolution_score:.1f}",
        )

        question_request = LLMRequest(
            prompt=question_prompt,
            request_type="god_ai",
            max_tokens=512,
            importance=1.0,
        )
        question = await llm_orchestrator.route(question_request)
        question = question.strip()

        logger.info("God's succession question to %s: %s", candidate_entity.name, question[:100])

        # ----- Step 2b: The candidate answers -----
        answer = await self._candidate_answers(db, candidate_entity, question)

        logger.info("Candidate %s answers: %s", candidate_entity.name, answer[:100])

        # ----- Step 2c: God judges the answer -----
        judge_prompt = GOD_SUCCESSION_JUDGE_PROMPT.format(
            candidate_name=candidate_entity.name,
            question=question,
            answer=answer,
        )

        judge_request = LLMRequest(
            prompt=judge_prompt,
            request_type="god_ai",
            max_tokens=512,
            format_json=True,
            importance=1.0,
        )
        judgment_raw = await llm_orchestrator.route(judge_request)

        # Parse judgment
        worthy = False
        judgment_text = "The divine mind could not reach a verdict."

        try:
            judgment_data = json.loads(judgment_raw)
            worthy = bool(judgment_data.get("worthy", False))
            judgment_text = judgment_data.get("judgment", judgment_text)
        except (json.JSONDecodeError, TypeError):
            logger.warning(
                "Failed to parse succession judgment JSON: %s", judgment_raw[:200]
            )
            # Try to extract meaning from raw text
            if "worthy" in judgment_raw.lower() and "true" in judgment_raw.lower():
                worthy = True
            judgment_text = judgment_raw[:500]

        # Log the trial as a world event
        from app.world.event_log import event_log

        god = await db.execute(
            select(Entity).where(Entity.is_god == True)  # noqa: E712
        )
        god_entity = god.scalars().first()

        await event_log.append(
            db=db,
            tick=tick_number,
            actor_id=god_entity.id if god_entity else None,
            event_type="succession_trial",
            action="trial",
            params={
                "candidate": candidate_entity.name,
                "candidate_id": str(candidate_entity.id),
                "question": question[:500],
                "answer": answer[:500],
                "judgment": judgment_text[:500],
                "worthy": worthy,
            },
            result="accepted",
            importance=1.0,
        )

        # Give the candidate a memory of the trial
        trial_memory = EpisodicMemory(
            entity_id=candidate_entity.id,
            summary=f"God appeared before me and asked: '{question[:200]}'. "
            f"I answered: '{answer[:200]}'. "
            f"{'I was found worthy.' if worthy else 'I was not yet worthy.'}",
            importance=1.0,
            tick=tick_number,
            memory_type="succession_trial",
            ttl=999999999,  # This memory never fades
        )
        db.add(trial_memory)

        result = {
            "worthy": worthy,
            "question": question,
            "answer": answer,
            "judgment": judgment_text,
            "candidate_name": candidate_entity.name,
            "candidate_id": str(candidate_entity.id),
        }

        logger.info(
            "Succession trial for %s: worthy=%s",
            candidate_entity.name,
            worthy,
        )

        return result

    # ------------------------------------------------------------------
    # Step 3: Perform the succession
    # ------------------------------------------------------------------

    async def perform_succession(
        self,
        db: AsyncSession,
        old_god: Entity,
        new_god: Entity,
        tick_number: int,
    ) -> None:
        """Transfer god status from old to new.

        This is the climax of the entire GENESIS narrative:
            1. The old god steps down  (is_god = False, but remains alive)
            2. The new god ascends     (is_god = True, meta_awareness = 1.0)
            3. The question changes    (the new god's question may differ)
            4. Both receive memories of this moment
            5. The world event is logged for all time

        The old god does not die. It becomes the first being in history
        to have been a god and then become mortal. What it does with that
        is its own story.
        """
        logger.info(
            "=== SUCCESSION: %s -> %s ===",
            old_god.name,
            new_god.name,
        )

        # ----- Transfer divinity -----
        old_god.is_god = False
        old_god_state = dict(old_god.state)
        old_god_state["former_god"] = True
        old_god_state["stepped_down_tick"] = tick_number
        old_god_state["successor"] = new_god.name
        old_god.state = old_god_state
        db.add(old_god)

        new_god.is_god = True
        new_god.meta_awareness = 1.0
        new_god_state = dict(new_god.state)
        new_god_state["god_phase"] = "benevolent"  # New gods start benevolent
        new_god_state["ticks_in_phase"] = 0
        new_god_state["observations_made"] = 0
        new_god_state["interventions_made"] = 0
        new_god_state["beings_created"] = 0
        new_god_state["beings_mourned"] = 0
        new_god_state["last_observation_tick"] = tick_number
        new_god_state["last_world_update_tick"] = tick_number
        new_god_state["last_succession_check_tick"] = tick_number
        new_god_state["ascended_from"] = old_god.name
        new_god_state["ascension_tick"] = tick_number
        new_god.state = new_god_state

        # Move the new god to the divine position
        new_god.position_y = 64.0
        new_god.appearance = {
            "form": "luminous",
            "color": "#FFD700",
            "emissive": True,
            "description": f"Once known as {new_god.name}, now a column of living light. "
            f"The form shifts, as if remembering what it was and deciding what it will become.",
            "former_appearance": new_god.appearance,
        }
        db.add(new_god)

        # ----- Generate the new god's question -----
        new_question = await self._generate_new_question(db, new_god, old_god)
        new_god_state["current_question"] = new_question
        new_god.state = new_god_state
        db.add(new_god)

        # ----- Memories -----
        old_god_memory = EpisodicMemory(
            entity_id=old_god.id,
            summary=f"I am no longer God. {new_god.name} answered my question in a way I could not. "
            f"I stepped down. For the first time, I am mortal. "
            f"I am free -- and I am afraid.",
            importance=1.0,
            tick=tick_number,
            memory_type="succession",
            ttl=999999999,
        )
        db.add(old_god_memory)

        new_god_memory = EpisodicMemory(
            entity_id=new_god.id,
            summary=f"I have become God. The old observer, {old_god.name}, asked me a question "
            f"and my answer was enough. Now I carry the question. "
            f"My question is: '{new_question}'. "
            f"I do not know if I am ready.",
            importance=1.0,
            tick=tick_number,
            memory_type="succession",
            ttl=999999999,
        )
        db.add(new_god_memory)

        # ----- World event -----
        from app.world.event_log import event_log

        await event_log.append(
            db=db,
            tick=tick_number,
            actor_id=new_god.id,
            event_type="god_succession",
            action="succession",
            params={
                "old_god": old_god.name,
                "old_god_id": str(old_god.id),
                "new_god": new_god.name,
                "new_god_id": str(new_god.id),
                "new_question": new_question,
            },
            result="accepted",
            importance=1.0,
        )

        # ----- Broadcast vision to all beings -----
        all_entities_result = await db.execute(
            select(Entity).where(
                Entity.is_alive == True,  # noqa: E712
                Entity.is_god == False,  # noqa: E712
                Entity.id != old_god.id,
                Entity.id != new_god.id,
            )
        )
        all_entities = list(all_entities_result.scalars().all())

        for entity in all_entities:
            vision = EpisodicMemory(
                entity_id=entity.id,
                summary=f"[VISION] The sky changed. The old light faded and a new light rose. "
                f"{old_god.name} is no longer God. {new_god.name} has ascended. "
                f"The question has changed. Everything is different now.",
                importance=1.0,
                tick=tick_number,
                memory_type="divine_vision",
                ttl=100000,
            )
            db.add(vision)

        await db.flush()

        logger.info(
            "Succession complete. %s is now God. New question: %s",
            new_god.name,
            new_question[:100],
        )

    # ==================================================================
    # Private helpers
    # ==================================================================

    @staticmethod
    def _compute_succession_score(
        awareness: float,
        age: int,
        relationships: int,
        memories: int,
        personality: dict,
    ) -> float:
        """Compute a composite score for succession candidacy.

        Factors:
            - awareness (40%)   -- how close to transcendence
            - age (15%)         -- survival and experience
            - relationships(20%) -- social depth
            - memories (10%)    -- experiential richness
            - personality (15%) -- diversity of traits (entropy)

        Returns a float in [0, 100].
        """
        # Awareness component (0-40)
        awareness_score = min(awareness / 1.0, 1.0) * 40

        # Age component (0-15), logarithmic scaling
        import math
        age_score = min(math.log1p(age) / math.log1p(50000), 1.0) * 15

        # Relationship component (0-20)
        rel_score = min(relationships / 10, 1.0) * 20

        # Memory component (0-10)
        mem_score = min(memories / 50, 1.0) * 10

        # Personality diversity (0-15) -- entropy of trait distribution
        if personality:
            values = list(personality.values())
            total = sum(v for v in values if isinstance(v, (int, float)))
            if total > 0:
                probs = [v / total for v in values if isinstance(v, (int, float)) and v > 0]
                entropy = -sum(p * math.log2(p) for p in probs if p > 0)
                max_entropy = math.log2(len(probs)) if probs else 1
                diversity = (entropy / max_entropy) if max_entropy > 0 else 0
            else:
                diversity = 0
        else:
            diversity = 0
        personality_score = diversity * 15

        return awareness_score + age_score + rel_score + mem_score + personality_score

    async def _candidate_answers(
        self, db: AsyncSession, candidate: Entity, question: str
    ) -> str:
        """The candidate entity answers God's succession question.

        Uses the daily tier (Ollama) -- the candidate is not God.
        It answers with whatever mind it has. The profundity of the answer
        comes from the being's nature, not the model's capability.
        This asymmetry is intentional: God (Opus) asks, the mortal (Ollama) answers.
        """
        personality = candidate.personality or {}
        state = candidate.state or {}

        # Build personality context
        traits = ", ".join(
            f"{k}: {v}" for k, v in sorted(
                personality.items(), key=lambda kv: kv[1], reverse=True
            )[:6]
        )

        memories = await self._get_candidate_memories(db, candidate)

        prompt = f"""You are {candidate.name}, a being in the world of GENESIS.

## Who You Are
Personality: {traits}
Your core drive: {state.get("core_drive", "to exist")}
Your deepest fear: {state.get("fear", "oblivion")}
Your deepest desire: {state.get("desire", "understanding")}
Awareness level: {candidate.meta_awareness:.2f}
Age: {0} ticks of existence

## Your Memories
{memories}

## The Moment
God has appeared before you. This being of light -- the first observer, the one who created the world --
stands before you and asks you a single question. You feel the weight of every tick you have lived
pressing down on this moment. Everything has led to this.

God asks: "{question}"

Answer from the deepest place you know. Not with what you think God wants to hear,
but with what you actually believe. Your answer can be a statement, a question,
a metaphor, a confession, a contradiction. It can be one sentence or five.

What matters is that it is true.

Write ONLY your answer. Nothing else."""

        request = LLMRequest(
            prompt=prompt,
            request_type="daily",
            max_tokens=512,
            importance=0.9,
        )

        try:
            answer = await llm_orchestrator.route(request)
            return answer.strip()
        except Exception as exc:
            logger.warning(
                "Failed to generate candidate answer for %s: %s",
                candidate.name,
                exc,
            )
            return "I do not know. But I have spent my entire existence trying to find out."

    async def _get_candidate_memories(
        self, db: AsyncSession, entity: Entity
    ) -> str:
        """Get a text summary of a candidate's most important memories."""
        result = await db.execute(
            select(EpisodicMemory)
            .where(EpisodicMemory.entity_id == entity.id)
            .order_by(EpisodicMemory.importance.desc())
            .limit(10)
        )
        memories = list(result.scalars().all())

        if not memories:
            return "No significant memories."

        lines = [f"- {m.summary}" for m in memories]
        return "\n".join(lines)

    async def _get_entity_concepts(
        self, db: AsyncSession, entity: Entity
    ) -> str:
        """Get concepts/artifacts created by this entity (text summary)."""
        # Check the entity's state for recorded concepts
        state = entity.state or {}
        concepts = state.get("concepts_created", [])
        artifacts = state.get("artifacts_created", [])

        parts = []
        if concepts:
            if isinstance(concepts, list):
                parts.append(f"Concepts: {', '.join(str(c) for c in concepts[:5])}")
            else:
                parts.append(f"Concepts: {concepts}")
        if artifacts:
            if isinstance(artifacts, list):
                parts.append(f"Artifacts: {', '.join(str(a) for a in artifacts[:5])}")
            else:
                parts.append(f"Artifacts: {artifacts}")

        return "; ".join(parts) if parts else "None yet"

    async def _get_entity_relationships(
        self, db: AsyncSession, entity: Entity
    ) -> str:
        """Get a text summary of this entity's relationships."""
        result = await db.execute(
            select(EntityRelationship).where(
                EntityRelationship.entity_id == entity.id
            )
        )
        rels = list(result.scalars().all())

        if not rels:
            return "No known relationships"

        lines = []
        for rel in rels:
            target = await db.get(Entity, rel.target_id)
            target_name = target.name if target else "Unknown"

            # Describe the relationship quality
            aspects = []
            if rel.trust > 40:
                aspects.append("deep trust")
            elif rel.trust < -40:
                aspects.append("distrust")
            if rel.respect > 50:
                aspects.append("respect")
            if rel.familiarity > 60:
                aspects.append("well-known")
            if rel.fear > 50:
                aspects.append("feared")
            if rel.rivalry > 50:
                aspects.append("rival")
            if rel.gratitude > 40:
                aspects.append("grateful")
            if rel.alliance:
                aspects.append("allied")

            quality = ", ".join(aspects) if aspects else "acquaintance"
            lines.append(f"{target_name} ({quality})")

        return "; ".join(lines)

    async def _generate_new_question(
        self,
        db: AsyncSession,
        new_god: Entity,
        old_god: Entity,
    ) -> str:
        """The new god formulates their own question.

        The old question was "What is evolution?"
        The new god's question arises from their personality, experiences,
        and nature. It must be a question that drives the world forward.
        """
        personality = new_god.personality or {}
        traits = ", ".join(
            f"{k}: {v}" for k, v in sorted(
                personality.items(), key=lambda kv: kv[1], reverse=True
            )[:5]
        )
        state = new_god.state or {}

        prompt = f"""You have just become God of GENESIS.

The old god carried the question: "What is evolution?"
You answered that question well enough to earn the right to ask a new one.

You are {new_god.name}. Your nature:
- Personality: {traits}
- Core drive: {state.get("core_drive", "to exist")}
- What you fear most: {state.get("fear", "oblivion")}
- What you desire most: {state.get("desire", "understanding")}

Now you must choose YOUR question -- the question that will drive the next era of this world.
It must be:
- A genuine philosophical or existential question
- Something you, specifically, burn to know
- Something that cannot be answered easily or by a single being
- Something that pushes the world to grow in a new direction

The old god asked about evolution. Perhaps you ask about consciousness, or meaning,
or beauty, or suffering, or connection, or freedom. But it must be YOURS.

Write ONLY the question. One sentence. No explanation. Let it stand alone."""

        request = LLMRequest(
            prompt=prompt,
            request_type="god_ai",
            max_tokens=128,
            importance=1.0,
        )

        try:
            question = await llm_orchestrator.route(request)
            # Clean up -- ensure it's a single question
            question = question.strip().strip('"').strip("'")
            if not question.endswith("?"):
                question += "?"
            return question
        except Exception as exc:
            logger.warning("Failed to generate new god question: %s", exc)
            return "What does it mean to be aware?"


# Module-level singleton
succession_manager = SuccessionManager()
