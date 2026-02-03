import asyncio
import json
import logging
import time

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

# Health check cache — module-level so it persists across event loops (Celery ticks)
_HEALTH_CACHE_TTL = 15.0
_health_cache_ok: bool | None = None
_health_cache_at: float = 0.0


def _invalidate_health_cache() -> None:
    global _health_cache_ok
    _health_cache_ok = None


class OllamaClient:
    def __init__(self):
        self.base_url = settings.OLLAMA_HOST
        self.model = settings.OLLAMA_MODEL
        self._client: httpx.AsyncClient | None = None
        self._client_loop: asyncio.AbstractEventLoop | None = None
        self._semaphore: asyncio.Semaphore | None = None
        self._sem_loop: asyncio.AbstractEventLoop | None = None

    def _get_semaphore(self) -> asyncio.Semaphore:
        """Get or create semaphore for the current event loop.

        Celery creates a new event loop per tick via asyncio.run().
        asyncio.Semaphore is bound to the loop it was created in,
        so we must recreate it when the loop changes.
        """
        current_loop = asyncio.get_running_loop()
        if self._semaphore is None or self._sem_loop is not current_loop:
            self._semaphore = asyncio.Semaphore(settings.OLLAMA_CONCURRENCY)
            self._sem_loop = current_loop
        return self._semaphore

    async def _get_client(self) -> httpx.AsyncClient:
        """Return HTTP client valid for the current event loop.

        Celery runs asyncio.run() per tick, creating a new event loop each time.
        We recreate the httpx client when the loop changes, but reuse connections
        within a single tick (where all concurrent LLM calls share one loop).
        """
        current_loop = asyncio.get_running_loop()

        if self._client is not None and self._client_loop is not current_loop:
            # Event loop changed (new tick) — discard old client
            try:
                await self._client.aclose()
            except Exception:
                pass
            self._client = None

        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=90.0,
                limits=httpx.Limits(
                    max_connections=settings.OLLAMA_CONCURRENCY + 4,
                    max_keepalive_connections=settings.OLLAMA_CONCURRENCY + 2,
                ),
            )
            self._client_loop = current_loop

        return self._client

    async def generate(self, prompt: str, format_json: bool = True, num_predict: int | None = None) -> dict | str:
        """Generate text with concurrency control and GPU optimization."""
        sem = self._get_semaphore()
        async with sem:
            client = await self._get_client()
            url = f"{self.base_url}/api/generate"
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "keep_alive": "10m",
                "options": {
                    "num_predict": num_predict or settings.OLLAMA_NUM_PREDICT,
                    "num_gpu": settings.OLLAMA_NUM_GPU,
                },
            }
            if format_json:
                payload["format"] = "json"

            try:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                result = response.json()

                if format_json:
                    try:
                        return json.loads(result["response"])
                    except json.JSONDecodeError:
                        logger.warning(
                            f"Failed to parse JSON from Ollama: {result['response'][:200]}"
                        )
                        return {
                            "thought": result["response"],
                            "action": {"type": "observe", "details": {}},
                        }

                return result["response"]
            except httpx.HTTPError as e:
                _invalidate_health_cache()
                logger.error(f"Ollama API error: {e}")
                raise
            except Exception as e:
                _invalidate_health_cache()
                logger.error(f"Ollama unexpected error: {e}")
                raise

    async def chat(self, messages: list[dict], system: str = "", format_json: bool = False, num_predict: int | None = None) -> str:
        """Chat API with system prompt support for God AI operations."""
        sem = self._get_semaphore()
        async with sem:
            client = await self._get_client()
            url = f"{self.base_url}/api/chat"
            payload = {
                "model": self.model,
                "messages": messages,
                "stream": False,
                "keep_alive": "10m",
                "options": {
                    "num_predict": num_predict or settings.OLLAMA_NUM_PREDICT,
                    "num_gpu": settings.OLLAMA_NUM_GPU,
                },
            }
            if system:
                payload["messages"] = [{"role": "system", "content": system}] + messages
            if format_json:
                payload["format"] = "json"

            try:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                result = response.json()
                return result["message"]["content"]
            except httpx.HTTPError as e:
                _invalidate_health_cache()
                logger.error(f"Ollama chat API error: {e}")
                raise
            except Exception as e:
                _invalidate_health_cache()
                logger.error(f"Ollama chat unexpected error: {e}")
                raise

    async def health_check(self) -> bool:
        """Cached health check — avoids hammering Ollama every LLM call.

        Cache is stored in module-level globals so it persists across
        event loops (Celery creates a new loop per tick via asyncio.run()).
        """
        global _health_cache_ok, _health_cache_at
        now = time.monotonic()
        if _health_cache_ok is not None and (now - _health_cache_at) < _HEALTH_CACHE_TTL:
            return _health_cache_ok

        try:
            client = await self._get_client()
            response = await client.get(f"{self.base_url}/api/tags")
            _health_cache_ok = response.status_code == 200
        except Exception:
            _health_cache_ok = False

        _health_cache_at = now
        return _health_cache_ok

    async def close(self):
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None


ollama_client = OllamaClient()
