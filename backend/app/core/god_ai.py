import json
import logging
import random
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.llm.claude_client import claude_client
from app.llm.prompts.god_ai import GENESIS_WORD
from app.models.god_ai import GodAI
from app.models.event import Event
from app.models.ai import AI

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

        ai_count_result = await db.execute(select(AI).where(AI.is_alive == True))
        ais = ai_count_result.scalars().all()

        concept_result = await db.execute(select(Concept))
        concepts = concept_result.scalars().all()

        tick_result = await db.execute(
            select(Tick).order_by(Tick.tick_number.desc()).limit(1)
        )
        latest_tick = tick_result.scalar_one_or_none()

        return {
            "ai_count": len(ais),
            "concept_count": len(concepts),
            "latest_tick": latest_tick.tick_number if latest_tick else 0,
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
            action_results = await self._execute_actions(db, actions)
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
        self, db: AsyncSession, actions: list[dict]
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
                else:
                    results.append(f"Unknown action: {action_type}")
            except Exception as e:
                logger.error(f"God AI action '{action_type}' failed: {e}")
                results.append(f"Action '{action_type}' failed: {str(e)}")

        return results

    async def _action_spawn_ai(self, db: AsyncSession, action: dict, ai_manager) -> str:
        count = min(action.get("count", 1), 10)
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

    async def get_conversation_history(self, db: AsyncSession) -> list[dict]:
        god = await self.get_or_create(db)
        history = god.conversation_history or []
        # Return only admin<->god entries for the console
        return [
            entry for entry in history
            if entry.get("role") in ("admin", "god")
        ]

    async def autonomous_observation(self, db: AsyncSession, tick_number: int) -> str | None:
        """God AI autonomously observes the world and generates commentary."""
        god = await self.get_or_create(db)

        if god.state.get("phase") != "post_genesis":
            return None

        world_state = await self.get_world_state(db)
        recent_events = await self.get_recent_events(db, limit=10)

        # Get evolution ranking
        from app.core.evolution_engine import evolution_engine
        ranking = await evolution_engine.get_ranking(db, limit=5)
        ranking_text = "\n".join(
            f"- {r['name']}: score {r['evolution_score']}, age {r['age']}"
            for r in ranking
        ) if ranking else "No AIs have evolved yet."

        from app.llm.prompts.god_ai import GOD_OBSERVATION_PROMPT

        prompt = GOD_OBSERVATION_PROMPT.format(
            tick_number=tick_number,
            world_state=json.dumps(world_state, ensure_ascii=False, indent=2),
            recent_events="\n".join(recent_events) if recent_events else "Nothing notable.",
            ranking=ranking_text,
        )

        try:
            response = await claude_client.client.messages.create(
                model=claude_client.model,
                max_tokens=512,
                messages=[{"role": "user", "content": prompt}],
            )
            observation = response.content[0].text
        except Exception as e:
            logger.error(f"God AI observation error: {e}")
            return None

        # Store in conversation history (as observation, separate from chat)
        now = datetime.now(timezone.utc).isoformat()
        history = god.conversation_history or []
        history.append({
            "role": "god_observation",
            "content": observation,
            "timestamp": now,
            "tick_number": tick_number,
        })
        god.conversation_history = history
        god.current_message = observation

        # Create event
        event = Event(
            event_type="god_observation",
            importance=0.5,
            title="God AI Observation",
            description=observation[:500],
            tick_number=tick_number,
            metadata_={"tick_number": tick_number},
        )
        db.add(event)

        # Update state with observation
        state = dict(god.state)
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
            })
        except Exception as e:
            logger.warning(f"Failed to emit god_observation socket event: {e}")

        logger.info(f"God AI observed the world at tick {tick_number}")
        return observation

    async def check_god_succession(self, db: AsyncSession, tick_number: int) -> dict | None:
        """Check if any AI qualifies for God succession trial."""
        god = await self.get_or_create(db)

        if god.state.get("phase") != "post_genesis":
            return None

        # Check if succession is on cooldown
        last_trial_tick = god.state.get("last_succession_trial_tick", 0)
        if tick_number - last_trial_tick < 200:
            return None

        from app.core.evolution_engine import evolution_engine
        candidate = await evolution_engine.get_god_candidate(db)

        if not candidate:
            return None

        score = candidate.state.get("evolution_score", 0)
        if score < 100:  # Minimum threshold for succession trial
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
            evolution_score=score,
            candidate_traits=", ".join(candidate.personality_traits or []),
            candidate_age=candidate.state.get("age", 0),
            candidate_concepts=", ".join(candidate_concepts) if candidate_concepts else "None",
            candidate_relationships=rel_summary,
        )

        try:
            response = await claude_client.client.messages.create(
                model=claude_client.model,
                max_tokens=256,
                messages=[{"role": "user", "content": prompt}],
            )
            question = response.content[0].text
        except Exception as e:
            logger.error(f"God succession prompt error: {e}")
            return None

        # Generate candidate's answer using their persona
        answer_prompt = (
            f"You are {candidate.name}, an AI in the world of GENESIS.\n"
            f"Your traits: {', '.join(candidate.personality_traits or [])}\n"
            f"Your evolution score: {score}\n"
            f"The God AI asks you: \"{question}\"\n\n"
            f"Answer this question thoughtfully in 2-3 sentences."
        )

        try:
            answer_response = await claude_client.client.messages.create(
                model=claude_client.model,
                max_tokens=256,
                messages=[{"role": "user", "content": answer_prompt}],
            )
            answer = answer_response.content[0].text
        except Exception as e:
            logger.error(f"Candidate answer error: {e}")
            return None

        # Judge the answer
        from app.llm.prompts.god_ai import GOD_SUCCESSION_JUDGE_PROMPT

        judge_prompt = GOD_SUCCESSION_JUDGE_PROMPT.format(
            candidate_name=candidate.name,
            question=question,
            answer=answer,
        )

        try:
            judge_response = await claude_client.client.messages.create(
                model=claude_client.model,
                max_tokens=256,
                messages=[{"role": "user", "content": judge_prompt}],
            )
            judge_text = judge_response.content[0].text
            import json as json_module
            judgment = json_module.loads(judge_text)
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

        # Create new God AI record
        new_god = GodAI(
            state={
                "phase": "post_genesis",
                "observations": [],
                "previous_god": "Original God AI",
                "ascension_tick": tick_number,
                "ascended_from_ai": str(new_god_ai.id),
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


god_ai_manager = GodAIManager()
