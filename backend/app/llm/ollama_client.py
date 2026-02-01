import json
import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class OllamaClient:
    def __init__(self):
        self.base_url = settings.OLLAMA_HOST
        self.model = settings.OLLAMA_MODEL

    async def generate(self, prompt: str, format_json: bool = True) -> dict | str:
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
        }
        if format_json:
            payload["format"] = "json"

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                result = response.json()

                if format_json:
                    try:
                        return json.loads(result["response"])
                    except json.JSONDecodeError:
                        logger.warning(f"Failed to parse JSON from Ollama: {result['response'][:200]}")
                        return {"thought": result["response"], "action": {"type": "observe", "details": {}}}

                return result["response"]
        except httpx.HTTPError as e:
            logger.error(f"Ollama API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Ollama unexpected error: {e}")
            raise

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                return response.status_code == 200
        except Exception:
            return False


ollama_client = OllamaClient()
