import json
import logging
from datetime import datetime, timezone

import anthropic

from app.config import settings
from app.llm.prompts.god_ai import GOD_AI_SYSTEM_PROMPT, GOD_AI_GENESIS_PROMPT, GENESIS_WORD

logger = logging.getLogger(__name__)


class ClaudeClient:
    def __init__(self):
        self.client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.model = settings.CLAUDE_MODEL

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


claude_client = ClaudeClient()
