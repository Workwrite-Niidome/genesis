import json
import logging
from datetime import datetime, timezone

import anthropic

from app.config import settings
from app.llm.prompts.god_ai import GOD_AI_SYSTEM_PROMPT, GOD_AI_GENESIS_PROMPT, GENESIS_WORD
from app.llm.prompts.ai_thinking import AI_THINKING_PROMPT
from app.llm.prompts.ai_interaction import (
    AI_INTERACTION_PROMPT,
    AI_REPLY_PROMPT,
    AI_FINAL_TURN_PROMPT,
    build_conversation_history,
)
from app.llm.response_parser import parse_ai_decision

logger = logging.getLogger(__name__)


class ClaudeClient:
    def __init__(self):
        self.client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.model = settings.CLAUDE_MODEL

    def _get_byok_client(self, byok_config: dict | None) -> tuple:
        """Return (client, model) for BYOK or default server client."""
        if not byok_config:
            return self.client, self.model

        provider = byok_config.get("provider", "anthropic")
        api_key = byok_config.get("api_key", "")
        model_override = byok_config.get("model")

        if provider == "anthropic":
            client = anthropic.AsyncAnthropic(api_key=api_key)
            model = model_override or "claude-sonnet-4-20250514"
            return client, model
        elif provider == "openai":
            # Use anthropic-compatible wrapper via OpenAI base_url is not directly possible.
            # For OpenAI BYOK, we use httpx directly.
            return None, model_override or "gpt-4o"
        elif provider == "openrouter":
            client = anthropic.AsyncAnthropic(
                api_key=api_key,
                base_url="https://openrouter.ai/api/v1",
            )
            model = model_override or "anthropic/claude-sonnet-4"
            return client, model

        return self.client, self.model

    async def _byok_generate(self, byok_config: dict, prompt: str, max_tokens: int = 512) -> str:
        """Generate text using BYOK configuration. Supports anthropic, openai, openrouter."""
        provider = byok_config.get("provider", "anthropic")
        api_key = byok_config.get("api_key", "")
        model_override = byok_config.get("model")

        if provider == "openai":
            import httpx
            model = model_override or "gpt-4o"
            async with httpx.AsyncClient(timeout=30.0) as http_client:
                resp = await http_client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": model,
                        "max_tokens": max_tokens,
                        "messages": [{"role": "user", "content": prompt}],
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                return data["choices"][0]["message"]["content"]
        else:
            client, model = self._get_byok_client(byok_config)
            response = await client.messages.create(
                model=model,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text

    async def send_god_message(
        self,
        message: str,
        world_state: dict,
        recent_events: list[str],
        conversation_history: list[dict],
    ) -> str:
        system_prompt = GOD_AI_SYSTEM_PROMPT.format(
            world_state=json.dumps(world_state, ensure_ascii=False, indent=2),
            recent_events="\n".join(recent_events) if recent_events else "Nothing has happened yet.",
        )

        messages = []
        for entry in conversation_history[-20:]:
            role = "user" if entry["role"] == "admin" else "assistant"
            messages.append({"role": role, "content": entry["content"]})

        messages.append({"role": "user", "content": message})

        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=2048,
                system=system_prompt,
                messages=messages,
            )
            return response.content[0].text
        except Exception as e:
            logger.error(f"Claude API error: {e}")
            raise

    async def genesis(self, world_state: dict) -> str:
        system_prompt = GOD_AI_SYSTEM_PROMPT.format(
            world_state=json.dumps(world_state, ensure_ascii=False, indent=2),
            recent_events="The world has not yet begun. Only the void exists.",
        )

        genesis_prompt = GOD_AI_GENESIS_PROMPT.format(genesis_word=GENESIS_WORD)

        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=2048,
                system=system_prompt,
                messages=[{"role": "user", "content": genesis_prompt}],
            )
            return response.content[0].text
        except Exception as e:
            logger.error(f"Claude API genesis error: {e}")
            raise


    async def think_for_ai(
        self,
        ai_data: dict,
        world_context: dict,
        memories: list[str],
        byok_config: dict | None = None,
    ) -> dict:
        """Generate a thought for an AI entity. Uses BYOK if configured, else Ollama only."""
        # Build energy warning
        energy = ai_data.get("energy", 1.0)
        if energy <= 0.1:
            energy_warning = " [CRITICAL — you are near death]"
        elif energy <= 0.3:
            energy_warning = " [LOW — conserve energy or rest]"
        else:
            energy_warning = ""

        # Build mortality context
        mortality_context = ""
        recent_deaths = world_context.get("recent_deaths", [])
        if recent_deaths:
            mortality_context = "- Recently deceased beings:\n"
            for d in recent_deaths:
                mortality_context += f"  - {d['name']} (age {d.get('age', '?')}, score {d.get('score', '?')})\n"

        prompt = AI_THINKING_PROMPT.format(
            name=ai_data.get("name", "Unknown"),
            traits=", ".join(ai_data.get("personality_traits", [])),
            philosophy_section=ai_data.get("philosophy_section", ""),
            energy=energy,
            energy_warning=energy_warning,
            age=ai_data.get("age", 0),
            x=ai_data.get("x", 0),
            y=ai_data.get("y", 0),
            evolution_score=ai_data.get("evolution_score", 0),
            mortality_context=mortality_context,
            memories="\n".join(f"- {m}" for m in memories) if memories else "No memories yet.",
            nearby_ais=world_context.get("nearby_ais", "None visible"),
            relationships=ai_data.get("relationships", "No known relationships."),
            adopted_concepts=ai_data.get("adopted_concepts", "None yet."),
            world_culture=ai_data.get("world_culture", "No widespread concepts yet."),
            organizations=ai_data.get("organizations", "None."),
            artifacts=ai_data.get("artifacts", "None yet."),
            recent_events=world_context.get("recent_events", "Nothing notable recently."),
        )

        # If BYOK configured, use the user's API key directly
        if byok_config and byok_config.get("api_key"):
            try:
                text = await self._byok_generate(byok_config, prompt, max_tokens=512)
                parsed = parse_ai_decision(text)
                return self._normalize_thought(parsed)
            except Exception as e:
                logger.warning(f"BYOK thinking failed for {ai_data.get('name')}: {e}")
                # Fall through to Ollama

        # Local LLM only (Ollama)
        try:
            from app.llm.ollama_client import ollama_client
            is_healthy = await ollama_client.health_check()
            if is_healthy:
                result = await ollama_client.generate(prompt, format_json=True)
                parsed = parse_ai_decision(result) if isinstance(result, dict) else parse_ai_decision(result)
                return self._normalize_thought(parsed)
            else:
                logger.warning(f"Ollama not available for AI thinking ({ai_data.get('name')})")
        except Exception as e:
            logger.warning(f"Ollama failed for AI thinking ({ai_data.get('name')}): {e}")

        # Default response when no LLM is available
        return {
            "thought": "I exist and I observe.",
            "thought_type": "observation",
            "action": {"type": "observe", "details": {}},
            "new_memory": None,
        }

    async def generate_opening(
        self,
        ai_data: dict,
        other_data: dict,
        memories: list[str],
        known_concepts: list[str],
        relationship: str,
        byok_config: dict | None = None,
    ) -> dict:
        """Generate the opening turn of a conversation (AI initiates)."""
        prompt = AI_INTERACTION_PROMPT.format(
            name=ai_data.get("name", "Unknown"),
            traits=", ".join(ai_data.get("personality_traits", [])),
            energy=ai_data.get("energy", 1.0),
            age=ai_data.get("age", 0),
            memories="\n".join(f"- {m}" for m in memories) if memories else "No memories yet.",
            known_concepts=", ".join(known_concepts) if known_concepts else "None known",
            relationship=relationship if relationship != "unknown" else "First encounter — you have never met this being.",
            other_name=other_data.get("name", "Unknown"),
            other_appearance=json.dumps(other_data.get("appearance", {})),
            other_traits=", ".join(other_data.get("traits", [])),
            other_energy=other_data.get("energy", 1.0),
            conversation_context="",
        )
        return await self._run_llm(prompt, byok_config, ai_data.get("name", "?"))

    async def generate_reply(
        self,
        ai_data: dict,
        other_name: str,
        memories: list[str],
        relationship: str,
        turns: list[dict],
        byok_config: dict | None = None,
    ) -> dict:
        """Generate a reply turn in an ongoing conversation."""
        prompt = AI_REPLY_PROMPT.format(
            name=ai_data.get("name", "Unknown"),
            traits=", ".join(ai_data.get("personality_traits", [])),
            energy=ai_data.get("energy", 1.0),
            age=ai_data.get("age", 0),
            memories="\n".join(f"- {m}" for m in memories) if memories else "No memories yet.",
            relationship=relationship if relationship != "unknown" else "First encounter.",
            other_name=other_name,
            conversation_history=build_conversation_history(turns),
        )
        return await self._run_llm(prompt, byok_config, ai_data.get("name", "?"))

    async def generate_final_turn(
        self,
        ai_data: dict,
        other_name: str,
        known_concepts: list[str],
        turns: list[dict],
        byok_config: dict | None = None,
    ) -> dict:
        """Generate the final turn of a conversation (includes proposals)."""
        prompt = AI_FINAL_TURN_PROMPT.format(
            name=ai_data.get("name", "Unknown"),
            traits=", ".join(ai_data.get("personality_traits", [])),
            energy=ai_data.get("energy", 1.0),
            age=ai_data.get("age", 0),
            known_concepts=", ".join(known_concepts) if known_concepts else "None known",
            other_name=other_name,
            conversation_history=build_conversation_history(turns),
        )
        return await self._run_llm(prompt, byok_config, ai_data.get("name", "?"))

    async def _run_llm(self, prompt: str, byok_config: dict | None, ai_name: str) -> dict:
        """Run LLM generation with BYOK fallback to Ollama."""
        if byok_config and byok_config.get("api_key"):
            try:
                text = await self._byok_generate(byok_config, prompt, max_tokens=512)
                parsed = parse_ai_decision(text)
                return self._normalize_turn(parsed)
            except Exception as e:
                logger.warning(f"BYOK failed for {ai_name}: {e}")

        try:
            from app.llm.ollama_client import ollama_client
            is_healthy = await ollama_client.health_check()
            if is_healthy:
                result = await ollama_client.generate(prompt, format_json=True)
                parsed = parse_ai_decision(result) if isinstance(result, dict) else parse_ai_decision(result)
                return self._normalize_turn(parsed)
            else:
                logger.warning(f"Ollama not available for {ai_name}")
        except Exception as e:
            logger.warning(f"Ollama failed for {ai_name}: {e}")

        return {
            "thought": "...",
            "message": "",
            "emotion": "neutral",
        }

    def _normalize_turn(self, result: dict) -> dict:
        """Normalize a conversation turn response."""
        thought = result.get("thought") or result.get("thoughts", "...")
        # Support both new format (message) and old format (action.details.message)
        message = result.get("message") or result.get("speech", "")
        if not message:
            action = result.get("action", {})
            if isinstance(action, dict):
                message = action.get("details", {}).get("message", "")
        emotion = result.get("emotion", "neutral")

        return {
            "thought": str(thought)[:500],
            "message": str(message)[:1000] if message else "",
            "emotion": str(emotion)[:50] if emotion else "neutral",
            "new_memory": result.get("new_memory"),
            "concept_proposal": result.get("concept_proposal"),
            "artifact_proposal": result.get("artifact_proposal"),
        }

    def _normalize_thought(self, result: dict) -> dict:
        """Ensure thought result has consistent shape."""
        # Handle legacy 'thoughts' key (from old prompt format)
        thought = result.get("thought") or result.get("thoughts", "I exist and I observe.")
        thought_type = result.get("thought_type", "reflection")

        # Accept any thought type — AI may invent its own classification
        if not isinstance(thought_type, str) or not thought_type.strip():
            thought_type = "reflection"

        action = result.get("action", {"type": "observe", "details": {}})
        if not isinstance(action, dict):
            action = {"type": "observe", "details": {}}

        # Accept any action type — only ensure structure is valid
        if "type" not in action:
            action["type"] = "observe"

        return {
            "thought": str(thought)[:500],
            "thought_type": thought_type,
            "action": action,
            "new_memory": result.get("new_memory"),
            "concept_proposal": result.get("concept_proposal"),
            "artifact_proposal": result.get("artifact_proposal"),
            "organization_proposal": result.get("organization_proposal"),
            "speech": result.get("speech"),
        }


claude_client = ClaudeClient()
