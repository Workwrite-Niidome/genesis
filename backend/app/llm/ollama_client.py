import asyncio
import json
import logging
import time

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

# Health check cache duration (seconds)
_HEALTH_CACHE_TTL = 30.0


class OllamaClient:
    def __init__(self):
        self.base_url = settings.OLLAMA_HOST
        self.model = settings.OLLAMA_MODEL
        self._client: httpx.AsyncClient | None = None
        self._client_loop: asyncio.AbstractEventLoop | None = None
        self._semaphore: asyncio.Semaphore | None = None
        self._healthy: bool | None = None
        self._health_checked_at: float = 0.0

    def _get_semaphore(self) -> asyncio.Semaphore:
        """Get or create semaphore for the current event loop."""
        if self._semaphore is None:
            self._semaphore = asyncio.Semaphore(settings.OLLAMA_CONCURRENCY)
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

    async def generate(self, prompt: str, format_json: bool = True) -> dict | str:
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
                    "num_predict": settings.OLLAMA_NUM_PREDICT,
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
                logger.error(f"Ollama API error: {e}")
                raise
            except Exception as e:
                logger.error(f"Ollama unexpected error: {e}")
                raise

    async def health_check(self) -> bool:
        """Cached health check — avoids hammering Ollama every LLM call."""
        now = time.monotonic()
        if self._healthy is not None and (now - self._health_checked_at) < _HEALTH_CACHE_TTL:
            return self._healthy

        try:
            client = await self._get_client()
            response = await client.get(f"{self.base_url}/api/tags")
            self._healthy = response.status_code == 200
        except Exception:
            self._healthy = False

        self._health_checked_at = now
        return self._healthy

    async def close(self):
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None


ollama_client = OllamaClient()
