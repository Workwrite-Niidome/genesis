"""GENESIS v3 LLM Orchestrator -- cost-optimized routing for all LLM requests.

Routing strategy:
    god_ai               -> Claude Opus (the voice of God must be profound)
    important (>0.8)     -> Claude Haiku (fast, cheap, but still Claude-quality)
    daily                -> Ollama local (free, unlimited, the voice of the people)

"Claude is God, Ollama is the People."
"""
import json
import logging
from dataclasses import dataclass, field

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class LLMRequest:
    """A request to be routed to the appropriate LLM backend."""

    prompt: str
    request_type: str = "daily"  # "god_ai", "important", "daily"
    system_prompt: str | None = None
    max_tokens: int = 512
    format_json: bool = False
    importance: float = 0.5


class LLMOrchestrator:
    """Cost-optimized LLM routing.

    god_ai                          -> Claude Opus  (via god_generate)
    important (importance > 0.8)    -> Claude Haiku (fast, still Claude)
    daily                           -> Ollama local (free)

    Every tier falls back to the tier below it on failure:
        Opus -> Haiku -> Ollama -> hardcoded fallback
    """

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    async def route(self, request: LLMRequest) -> str:
        """Route to appropriate LLM based on request type and importance.

        Returns the raw text (or JSON string if format_json was requested
        but the underlying client returned text).
        """
        try:
            if request.request_type == "god_ai":
                return await self._claude_opus(request)
            elif request.request_type == "important" or request.importance > 0.8:
                return await self._claude_haiku(request)
            else:
                return await self._ollama(request)
        except Exception as exc:
            logger.error(
                "LLMOrchestrator.route failed for request_type=%s: %s",
                request.request_type,
                exc,
            )
            return self._fallback_response(request)

    # ------------------------------------------------------------------
    # Tier 1: Claude Opus -- the divine voice
    # ------------------------------------------------------------------

    async def _claude_opus(self, request: LLMRequest) -> str:
        """Use Claude Opus for God AI operations.

        Primary: claude_client.god_generate (handles budget + Ollama fallback).
        If that fails entirely, fall through to Haiku, then Ollama.
        """
        from app.llm.claude_client import claude_client

        try:
            result = await claude_client.god_generate(
                prompt=self._build_prompt(request),
                max_tokens=request.max_tokens,
                format_json=request.format_json,
            )
            # god_generate may return a dict when format_json=True
            if isinstance(result, dict):
                return json.dumps(result, ensure_ascii=False)
            return result
        except Exception as exc:
            logger.warning("Claude Opus failed, falling back to Haiku: %s", exc)

        # Fallback chain: Opus -> Haiku -> Ollama
        try:
            return await self._claude_haiku(request)
        except Exception:
            return await self._ollama(request)

    # ------------------------------------------------------------------
    # Tier 2: Claude Haiku -- fast, cheap, still Claude-grade
    # ------------------------------------------------------------------

    async def _claude_haiku(self, request: LLMRequest) -> str:
        """Use Claude Haiku for important but non-divine decisions.

        Constructs a raw Anthropic API call using the ClaudeClient's
        underlying async client, but overrides the model to Haiku.
        Falls back to Ollama on failure.
        """
        from app.llm.claude_client import claude_client
        from app.llm.cost_tracker import can_spend, record_usage

        prompt_text = self._build_prompt(request)

        # Estimate cost (Haiku is ~20x cheaper than Opus)
        estimated_cost = (
            (500 / 1_000_000) * 1.0 + (request.max_tokens / 1_000_000) * 5.0
        )

        if not can_spend(estimated_cost):
            logger.info("Haiku budget exceeded, routing to Ollama")
            return await self._ollama(request)

        try:
            messages = [{"role": "user", "content": prompt_text}]
            kwargs: dict = {
                "model": settings.CLAUDE_HAIKU_MODEL,
                "max_tokens": request.max_tokens,
                "messages": messages,
            }
            if request.system_prompt:
                kwargs["system"] = request.system_prompt

            response = await claude_client.client.messages.create(**kwargs)
            text = response.content[0].text

            # Record usage
            usage = response.usage
            record_usage(usage.input_tokens, usage.output_tokens, settings.CLAUDE_HAIKU_MODEL)
            logger.info(
                "Haiku used (in=%d, out=%d) for request_type=%s",
                usage.input_tokens,
                usage.output_tokens,
                request.request_type,
            )

            if request.format_json:
                return self._extract_json(text)
            return text

        except Exception as exc:
            logger.warning("Claude Haiku failed, falling back to Ollama: %s", exc)
            return await self._ollama(request)

    # ------------------------------------------------------------------
    # Tier 3: Ollama local -- the voice of the people
    # ------------------------------------------------------------------

    async def _ollama(self, request: LLMRequest) -> str:
        """Use local Ollama for daily operations.

        This is the workhorse tier -- free, unlimited, runs on local GPU.
        If even Ollama is unavailable, returns a hardcoded fallback.
        """
        from app.llm.ollama_client import ollama_client

        prompt_text = self._build_prompt(request)

        try:
            is_healthy = await ollama_client.health_check()
            if not is_healthy:
                logger.error("Ollama is not available")
                return self._fallback_response(request)

            result = await ollama_client.generate(
                prompt=prompt_text,
                format_json=request.format_json,
                num_predict=request.max_tokens,
            )

            if isinstance(result, dict):
                return json.dumps(result, ensure_ascii=False)
            return str(result)

        except Exception as exc:
            logger.error("Ollama failed: %s", exc)
            return self._fallback_response(request)

    # ------------------------------------------------------------------
    # Decision helper
    # ------------------------------------------------------------------

    def should_use_llm(self, context: dict) -> bool:
        """Determine if an LLM call is warranted at all.

        Returns True if any of these conditions hold:
            - The entity is in a conversation
            - A novel situation has been detected (new entity nearby, event, etc.)
            - The decision importance exceeds 0.7

        This prevents wasting LLM calls on routine ticks where the entity
        is just wandering alone in a familiar area.
        """
        if context.get("in_conversation", False):
            return True
        if context.get("has_novel_situation", False):
            return True
        if context.get("decision_importance", 0.0) > 0.7:
            return True
        # Edge cases that always warrant a call
        if context.get("is_dying", False):
            return True
        if context.get("god_vision_received", False):
            return True
        return False

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_prompt(request: LLMRequest) -> str:
        """Combine system prompt and user prompt into a single string.

        For API clients that support a separate system prompt, we embed it
        at the top. This is the format Ollama expects.
        """
        if request.system_prompt:
            return f"{request.system_prompt}\n\n---\n\n{request.prompt}"
        return request.prompt

    @staticmethod
    def _extract_json(text: str) -> str:
        """Attempt to extract a JSON object from potentially noisy LLM output."""
        text = text.strip()
        # If it already looks like JSON, return as-is
        if text.startswith("{") or text.startswith("["):
            return text
        # Try to find an embedded JSON block
        start = text.find("{")
        if start >= 0:
            depth = 0
            for i in range(start, len(text)):
                if text[i] == "{":
                    depth += 1
                elif text[i] == "}":
                    depth -= 1
                    if depth == 0:
                        return text[start : i + 1]
        return text

    @staticmethod
    def _fallback_response(request: LLMRequest) -> str:
        """Hardcoded response when all LLM backends are unavailable."""
        if request.format_json:
            return "{}"
        if request.request_type == "god_ai":
            return "The divine mind is momentarily silent."
        return "..."


# Module-level singleton
llm_orchestrator = LLMOrchestrator()
