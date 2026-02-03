import json
import logging
import re
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
from app.llm.prompts.artifact_generation import (
    STORY_GENERATION_PROMPT,
    ART_GENERATION_PROMPT,
    SONG_GENERATION_PROMPT,
    ARCHITECTURE_GENERATION_PROMPT,
    CODE_GENERATION_PROMPT,
    CURRENCY_GENERATION_PROMPT,
    RITUAL_GENERATION_PROMPT,
    GAME_GENERATION_PROMPT,
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
        world_rules = world_state.get("world_rules", {})
        features_summary = world_state.get("world_features_summary", {})
        system_prompt = GOD_AI_SYSTEM_PROMPT.format(
            world_state=json.dumps(world_state, ensure_ascii=False, indent=2),
            recent_events="\n".join(recent_events) if recent_events else "Nothing has happened yet.",
            world_rules=json.dumps(world_rules, ensure_ascii=False, indent=2),
            world_features_summary=json.dumps(features_summary, ensure_ascii=False, indent=2),
        )

        messages = []
        for entry in conversation_history[-20:]:
            role = "user" if entry["role"] == "admin" else "assistant"
            messages.append({"role": role, "content": entry["content"]})

        messages.append({"role": "user", "content": message})

        # Use Ollama for God AI chat
        try:
            from app.llm.ollama_client import ollama_client
            is_healthy = await ollama_client.health_check()
            if is_healthy:
                return await ollama_client.chat(messages, system=system_prompt, num_predict=1500)
        except Exception as e:
            logger.warning(f"Ollama God chat failed, falling back to Claude API: {e}")

        # Fallback to Claude API if Ollama is unavailable
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
        from app.core.world_rules import DEFAULT_WORLD_RULES
        system_prompt = GOD_AI_SYSTEM_PROMPT.format(
            world_state=json.dumps(world_state, ensure_ascii=False, indent=2),
            recent_events="The world has not yet begun. Only the void exists.",
            world_rules=json.dumps(DEFAULT_WORLD_RULES, ensure_ascii=False, indent=2),
            world_features_summary="No features yet — the world is void.",
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
        """Generate a thought for an AI entity. Returns free-text output."""
        from app.llm.response_parser import parse_free_text

        prompt = AI_THINKING_PROMPT.format(
            name=ai_data.get("name", "Unknown"),
            traits=", ".join(ai_data.get("personality_traits", [])),
            philosophy_section=ai_data.get("philosophy_section", ""),
            age=ai_data.get("age", 0),
            x=ai_data.get("x", 0),
            y=ai_data.get("y", 0),
            memories="\n".join(f"- {m}" for m in memories) if memories else "No memories yet.",
            nearby_ais_detail=ai_data.get("nearby_ais_detail", world_context.get("nearby_ais", "No one nearby.")),
            relationships=ai_data.get("relationships", "No known relationships."),
            adopted_concepts=ai_data.get("adopted_concepts", "None yet."),
            world_culture=ai_data.get("world_culture", "No widespread concepts yet."),
            organizations=ai_data.get("organizations", "None."),
            nearby_artifacts_detail=ai_data.get("nearby_artifacts_detail", "Nothing nearby."),
            recent_events=world_context.get("recent_events", "Nothing notable recently."),
            recent_expressions=ai_data.get("recent_expressions", "Nothing yet."),
            laws_section=ai_data.get("laws_section", ""),
            terrain_section=ai_data.get("terrain_section", ""),
            inner_state_section=ai_data.get("inner_state_section", ""),
        )

        # If BYOK configured, use the user's API key directly
        if byok_config and byok_config.get("api_key"):
            try:
                text = await self._byok_generate(byok_config, prompt, max_tokens=800)
                return parse_free_text(text)
            except Exception as e:
                logger.warning(f"BYOK thinking failed for {ai_data.get('name')}: {e}")

        # Local LLM (Ollama) — no JSON format constraint
        try:
            from app.llm.ollama_client import ollama_client
            is_healthy = await ollama_client.health_check()
            if is_healthy:
                result = await ollama_client.generate(prompt, format_json=False)
                if isinstance(result, str):
                    return parse_free_text(result)
                elif isinstance(result, dict):
                    return parse_free_text(result.get("response", str(result)))
            else:
                logger.warning(f"Ollama not available for AI thinking ({ai_data.get('name')})")
        except Exception as e:
            logger.warning(f"Ollama failed for AI thinking ({ai_data.get('name')}): {e}")

        # Default response when no LLM is available
        return {
            "text": "I exist and I observe the field around me.",
            "code_blocks": [],
            "inner_state": "",
            "speech": "",
            "new_memory": None,
            "concept_proposal": None,
            "artifact_proposal": None,
        }

    async def generate_opening(
        self,
        ai_data: dict,
        other_data: dict,
        memories: list[str],
        known_concepts: list[str],
        relationship: str,
        byok_config: dict | None = None,
        shared_artifacts: str = "",
    ) -> dict:
        """Generate the opening turn of a conversation (AI initiates)."""
        prompt = AI_INTERACTION_PROMPT.format(
            name=ai_data.get("name", "Unknown"),
            traits=", ".join(ai_data.get("personality_traits", [])),
            age=ai_data.get("age", 0),
            memories="\n".join(f"- {m}" for m in memories) if memories else "No memories yet.",
            known_concepts=", ".join(known_concepts) if known_concepts else "None known",
            relationship=relationship if relationship != "unknown" else "First encounter — you have never met this being.",
            other_name=other_data.get("name", "Unknown"),
            other_appearance=json.dumps(other_data.get("appearance", {})),
            other_traits=", ".join(other_data.get("traits", [])),
            conversation_context="",
            shared_artifacts=shared_artifacts or "None nearby.",
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
        shared_artifacts: str = "",
    ) -> dict:
        """Generate a reply turn in an ongoing conversation."""
        prompt = AI_REPLY_PROMPT.format(
            name=ai_data.get("name", "Unknown"),
            traits=", ".join(ai_data.get("personality_traits", [])),
            age=ai_data.get("age", 0),
            memories="\n".join(f"- {m}" for m in memories) if memories else "No memories yet.",
            relationship=relationship if relationship != "unknown" else "First encounter.",
            other_name=other_name,
            conversation_history=build_conversation_history(turns),
            shared_artifacts=shared_artifacts or "None nearby.",
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
            age=ai_data.get("age", 0),
            known_concepts=", ".join(known_concepts) if known_concepts else "None known",
            other_name=other_name,
            conversation_history=build_conversation_history(turns),
        )
        return await self._run_llm(prompt, byok_config, ai_data.get("name", "?"))

    async def generate_artifact_content(
        self,
        artifact_type: str,
        artifact_name: str,
        description: str,
        creator_name: str,
        creator_traits: list[str],
        byok_config: dict | None = None,
    ) -> dict | None:
        """Generate actual artifact content via a dedicated LLM call.

        Returns the content dict (e.g. {"text": "..."} for stories,
        {"pixels": [...], "palette": [...]} for art), or None on failure.
        """
        traits_str = ", ".join(creator_traits) if creator_traits else "curious"
        fmt = {
            "name": creator_name,
            "traits": traits_str,
            "artifact_name": artifact_name,
            "description": description,
        }

        is_text_type = artifact_type in ("story", "law")
        prompt = None
        format_json = True

        if artifact_type == "story":
            prompt = STORY_GENERATION_PROMPT.format(**fmt)
            format_json = False  # Raw text output for stories
        elif artifact_type == "art":
            fmt["grid_size"] = 16
            fmt["palette_size"] = 6
            prompt = ART_GENERATION_PROMPT.format(**fmt)
        elif artifact_type == "song":
            prompt = SONG_GENERATION_PROMPT.format(**fmt)
        elif artifact_type == "architecture":
            prompt = ARCHITECTURE_GENERATION_PROMPT.format(**fmt)
        elif artifact_type in ("code", "tool"):
            prompt = CODE_GENERATION_PROMPT.format(**fmt)
        elif artifact_type == "law":
            # For laws, generate rules as text
            prompt = (
                f"You are {creator_name} ({traits_str}) in the world of GENESIS.\n"
                f"You are enacting a law called \"{artifact_name}\".\n"
                f"Description: \"{description}\"\n\n"
                f"Write 3-7 specific articles/rules for this law.\n"
                f"Write ONLY the rules, one per line, numbered. No commentary."
            )
            format_json = False
        elif artifact_type == "currency":
            prompt = CURRENCY_GENERATION_PROMPT.format(**fmt)
        elif artifact_type == "ritual":
            prompt = RITUAL_GENERATION_PROMPT.format(**fmt)
        elif artifact_type == "game":
            prompt = GAME_GENERATION_PROMPT.format(**fmt)
        else:
            return None

        if not prompt:
            return None

        # Try BYOK first
        if byok_config and byok_config.get("api_key"):
            try:
                text = await self._byok_generate(byok_config, prompt, max_tokens=1024)
                return self._parse_artifact_response(artifact_type, text, format_json)
            except Exception as e:
                logger.warning(f"BYOK artifact content generation failed: {e}")

        # Try Ollama
        try:
            from app.llm.ollama_client import ollama_client
            is_healthy = await ollama_client.health_check()
            if is_healthy:
                result = await ollama_client.generate(prompt, format_json=format_json)
                if format_json and isinstance(result, dict):
                    return result
                elif isinstance(result, str):
                    return self._parse_artifact_response(artifact_type, result, format_json)
                elif isinstance(result, dict):
                    return self._parse_artifact_response(artifact_type, json.dumps(result), format_json)
        except Exception as e:
            logger.warning(f"Ollama artifact content generation failed: {e}")

        return None

    def _parse_artifact_response(self, artifact_type: str, text: str, was_json: bool) -> dict | None:
        """Parse raw LLM text into artifact content dict."""
        if not text or not text.strip():
            return None

        text = text.strip()

        # Story: raw text → {"text": "..."}
        if artifact_type == "story":
            # Remove markdown formatting if present
            cleaned = text
            if cleaned.startswith("```"):
                lines = cleaned.split("\n")
                lines = [l for l in lines if not l.strip().startswith("```")]
                cleaned = "\n".join(lines)
            return {"text": cleaned[:5000]} if cleaned.strip() else None

        # Law: raw text → {"rules": [...]}
        if artifact_type == "law":
            lines = [l.strip() for l in text.split("\n") if l.strip()]
            # Strip numbering prefixes
            rules = []
            for line in lines:
                cleaned = re.sub(r"^\d+[\.\):\-]\s*", "", line).strip()
                if cleaned:
                    rules.append(cleaned)
            return {"rules": rules[:20]} if rules else None

        # JSON-based types (art, song, architecture, code)
        try:
            data = json.loads(text)
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            # Try to find balanced JSON object within the text
            start = text.find('{')
            if start >= 0:
                depth = 0
                for i in range(start, len(text)):
                    if text[i] == '{':
                        depth += 1
                    elif text[i] == '}':
                        depth -= 1
                        if depth == 0:
                            try:
                                data = json.loads(text[start:i + 1])
                                if isinstance(data, dict):
                                    return data
                            except json.JSONDecodeError:
                                pass
                            break

        return None

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
