import json
import logging
from datetime import datetime, timezone

import anthropic

from app.config import settings
from app.llm.prompts.god_ai import GOD_AI_SYSTEM_PROMPT, GOD_AI_GENESIS_PROMPT, GENESIS_WORD
from app.llm.prompts.ai_thinking import AI_THINKING_PROMPT
from app.llm.prompts.ai_interaction import AI_INTERACTION_PROMPT
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
        """Generate a thought for an AI entity. Uses BYOK if configured, else Ollama, else Claude."""
        prompt = AI_THINKING_PROMPT.format(
            name=ai_data.get("name", "Unknown"),
            traits=", ".join(ai_data.get("personality_traits", [])),
            philosophy_section=ai_data.get("philosophy_section", ""),
            energy=ai_data.get("energy", 1.0),
            age=ai_data.get("age", 0),
            x=ai_data.get("x", 0),
            y=ai_data.get("y", 0),
            evolution_score=ai_data.get("evolution_score", 0),
            memories="\n".join(f"- {m}" for m in memories) if memories else "No memories yet.",
            nearby_ais=world_context.get("nearby_ais", "None visible"),
            relationships=ai_data.get("relationships", "No known relationships."),
            adopted_concepts=ai_data.get("adopted_concepts", "None yet."),
            world_culture=ai_data.get("world_culture", "No widespread concepts yet."),
            organizations=ai_data.get("organizations", "None."),
            artifacts=ai_data.get("artifacts", "None yet."),
        )

        # If BYOK configured, use the user's API key directly
        if byok_config and byok_config.get("api_key"):
            try:
                text = await self._byok_generate(byok_config, prompt, max_tokens=512)
                parsed = parse_ai_decision(text)
                return self._normalize_thought(parsed)
            except Exception as e:
                logger.warning(f"BYOK thinking failed for {ai_data.get('name')}: {e}")
                # Fall through to server-side inference

        # Try Ollama first
        try:
            from app.llm.ollama_client import ollama_client
            is_healthy = await ollama_client.health_check()
            if is_healthy:
                result = await ollama_client.generate(prompt, format_json=True)
                parsed = parse_ai_decision(result) if isinstance(result, dict) else parse_ai_decision(result)
                return self._normalize_thought(parsed)
        except Exception as e:
            logger.warning(f"Ollama failed for AI thinking, falling back to Claude: {e}")

        # Fallback to Claude
        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=512,
                messages=[{"role": "user", "content": prompt}],
            )
            text = response.content[0].text
            parsed = parse_ai_decision(text)
            return self._normalize_thought(parsed)
        except Exception as e:
            logger.error(f"Claude AI thinking error: {e}")
            return {
                "thought": "I exist and I observe.",
                "thought_type": "observation",
                "action": {"type": "observe", "details": {}},
                "new_memory": None,
            }

    async def generate_encounter_response(
        self,
        ai_data: dict,
        other_data: dict,
        memories: list[str],
        known_concepts: list[str],
        relationship: str,
        byok_config: dict | None = None,
    ) -> dict:
        """Generate an encounter response for an AI meeting another."""
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
        )

        # If BYOK configured, use the user's API key
        if byok_config and byok_config.get("api_key"):
            try:
                text = await self._byok_generate(byok_config, prompt, max_tokens=512)
                parsed = parse_ai_decision(text)
                return self._normalize_encounter(parsed)
            except Exception as e:
                logger.warning(f"BYOK encounter failed: {e}")

        # Try Ollama first
        try:
            from app.llm.ollama_client import ollama_client
            is_healthy = await ollama_client.health_check()
            if is_healthy:
                result = await ollama_client.generate(prompt, format_json=True)
                parsed = parse_ai_decision(result) if isinstance(result, dict) else parse_ai_decision(result)
                return self._normalize_encounter(parsed)
        except Exception as e:
            logger.warning(f"Ollama failed for encounter, falling back to Claude: {e}")

        # Fallback to Claude
        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=512,
                messages=[{"role": "user", "content": prompt}],
            )
            text = response.content[0].text
            parsed = parse_ai_decision(text)
            return self._normalize_encounter(parsed)
        except Exception as e:
            logger.error(f"Claude encounter error: {e}")
            return {
                "thought": f"I see {other_data.get('name', 'another being')} nearby.",
                "action": {"type": "observe", "details": {"message": "", "intention": "observing"}},
                "new_memory": f"I encountered {other_data.get('name', 'another being')}.",
                "concept_proposal": None,
            }

    def _normalize_encounter(self, result: dict) -> dict:
        """Normalize an encounter response."""
        thought = result.get("thought") or result.get("thoughts", "I observe the other.")
        action = result.get("action", {"type": "observe", "details": {}})
        if not isinstance(action, dict):
            action = {"type": "observe", "details": {}}

        valid_actions = {"communicate", "cooperate", "avoid", "observe", "create_concept", "trade", "create_artifact"}
        action_type = action.get("type", "observe")
        if action_type not in valid_actions:
            action["type"] = "observe"

        return {
            "thought": str(thought)[:500],
            "action": action,
            "new_memory": result.get("new_memory"),
            "concept_proposal": result.get("concept_proposal"),
            "artifact_proposal": result.get("artifact_proposal"),
        }

    def _normalize_thought(self, result: dict) -> dict:
        """Ensure thought result has consistent shape."""
        # Handle legacy 'thoughts' key (from old prompt format)
        thought = result.get("thought") or result.get("thoughts", "I exist and I observe.")
        thought_type = result.get("thought_type", "reflection")

        valid_types = {"reflection", "reaction", "intention", "observation"}
        if thought_type not in valid_types:
            thought_type = "reflection"

        action = result.get("action", {"type": "observe", "details": {}})
        if not isinstance(action, dict):
            action = {"type": "observe", "details": {}}

        # Validate action type
        valid_action_types = {"move", "observe", "interact", "rest", "create", "trade"}
        if action.get("type") not in valid_action_types:
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
