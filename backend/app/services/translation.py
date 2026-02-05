"""
GENESIS v3 - Translation Service
==================================
DeepL-based real-time translation with Redis caching.

Provides cross-language communication between entities and observers
in the GENESIS world.  When DEEPL_API_KEY is not configured the service
degrades gracefully by returning the original text.

Caching strategy:
  - Translations are cached in Redis for 1 hour.
  - Cache key: ``genesis:translation:{sha256(text)}:{target_lang}``

Rate limiting:
  - Max 50 DeepL API calls per minute (sliding window in Redis).
"""

from __future__ import annotations

import hashlib
import logging
import time
from typing import Optional

import httpx
import redis.asyncio as aioredis

from app.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEEPL_API_URL = "https://api-free.deepl.com/v2/translate"
DEEPL_DETECT_URL = "https://api-free.deepl.com/v2/translate"  # detection via translate with short text

SUPPORTED_LANGUAGES = {"EN", "JA", "ZH", "KO", "ES", "FR", "DE"}

# Map i18next/frontend language codes to DeepL target codes.
# DeepL uses "EN-US" / "EN-GB" for English target; we default to EN.
LANG_CODE_MAP: dict[str, str] = {
    "en": "EN",
    "ja": "JA",
    "zh": "ZH",
    "ko": "KO",
    "es": "ES",
    "fr": "FR",
    "de": "DE",
}

CACHE_TTL_SECONDS = 3600  # 1 hour
RATE_LIMIT_MAX = 50       # calls per window
RATE_LIMIT_WINDOW = 60    # seconds

RATE_LIMIT_KEY = "genesis:translation:rate_limit"


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class TranslationService:
    """DeepL-based translation with Redis caching and rate limiting."""

    def __init__(self) -> None:
        self._api_key: Optional[str] = settings.DEEPL_API_KEY
        self._redis: Optional[aioredis.Redis] = None
        self._client: Optional[httpx.AsyncClient] = None

    # -- Lazy init helpers ---------------------------------------------------

    async def _get_redis(self) -> aioredis.Redis:
        if self._redis is None:
            self._redis = aioredis.from_url(
                settings.REDIS_URL, decode_responses=True
            )
        return self._redis

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=10.0)
        return self._client

    # -- Public API ----------------------------------------------------------

    async def translate(
        self,
        text: str,
        target_lang: str,
        source_lang: Optional[str] = None,
    ) -> str:
        """Translate *text* into *target_lang*.

        Parameters
        ----------
        text : str
            The text to translate.
        target_lang : str
            ISO-style language code (e.g. ``"en"``, ``"JA"``).
        source_lang : str, optional
            Source language code.  If ``None`` DeepL auto-detects.

        Returns
        -------
        str
            Translated text, or the original if the API key is missing,
            the target language equals the source, or an error occurs.
        """
        if not self._api_key:
            return text

        target_upper = self._normalize_lang(target_lang)
        if target_upper not in SUPPORTED_LANGUAGES:
            return text

        source_upper = self._normalize_lang(source_lang) if source_lang else None
        if source_upper and source_upper == target_upper:
            return text

        # Check cache first
        cache_key = self._cache_key(text, target_upper)
        try:
            r = await self._get_redis()
            cached = await r.get(cache_key)
            if cached is not None:
                return cached
        except Exception as exc:
            logger.warning("Redis cache read failed: %s", exc)

        # Rate limit check
        if not await self._check_rate_limit():
            logger.warning("Translation rate limit exceeded, returning original")
            return text

        # Call DeepL
        try:
            translated = await self._call_deepl(text, target_upper, source_upper)
        except Exception as exc:
            logger.error("DeepL API call failed: %s", exc)
            return text

        # Write cache
        try:
            r = await self._get_redis()
            await r.set(cache_key, translated, ex=CACHE_TTL_SECONDS)
        except Exception as exc:
            logger.warning("Redis cache write failed: %s", exc)

        return translated

    async def detect_language(self, text: str) -> str:
        """Detect the language of *text* via DeepL.

        Returns a normalised uppercase code (e.g. ``"EN"``).
        Falls back to ``"EN"`` on error.
        """
        if not self._api_key:
            return "EN"

        try:
            client = await self._get_client()
            response = await client.post(
                DEEPL_API_URL,
                data={
                    "auth_key": self._api_key,
                    "text": text[:200],  # short sample is enough for detection
                    "target_lang": "EN",  # required by API; we just want detected_source_language
                },
            )
            response.raise_for_status()
            data = response.json()
            detected = data["translations"][0].get("detected_source_language", "EN")
            return detected.upper()
        except Exception as exc:
            logger.warning("Language detection failed: %s", exc)
            return "EN"

    # -- Internal helpers ----------------------------------------------------

    def _cache_key(self, text: str, target_lang: str) -> str:
        """Build a Redis cache key for a translation pair."""
        text_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
        return f"genesis:translation:{text_hash}:{target_lang}"

    @staticmethod
    def _normalize_lang(code: Optional[str]) -> str:
        """Normalise a language code to the DeepL uppercase variant."""
        if not code:
            return ""
        code_lower = code.lower().split("-")[0]
        return LANG_CODE_MAP.get(code_lower, code.upper())

    async def _check_rate_limit(self) -> bool:
        """Sliding-window rate limit using a Redis sorted set.

        Returns ``True`` if the request is allowed.
        """
        try:
            r = await self._get_redis()
            now = time.time()
            window_start = now - RATE_LIMIT_WINDOW

            pipe = r.pipeline()
            # Remove entries outside the window
            pipe.zremrangebyscore(RATE_LIMIT_KEY, 0, window_start)
            # Count entries in current window
            pipe.zcard(RATE_LIMIT_KEY)
            # Add current request
            pipe.zadd(RATE_LIMIT_KEY, {str(now): now})
            # Set expiry on the key so it doesn't persist forever
            pipe.expire(RATE_LIMIT_KEY, RATE_LIMIT_WINDOW * 2)
            results = await pipe.execute()

            current_count = results[1]
            return current_count < RATE_LIMIT_MAX
        except Exception as exc:
            logger.warning("Rate limit check failed (allowing): %s", exc)
            return True  # fail open

    async def _call_deepl(
        self,
        text: str,
        target_lang: str,
        source_lang: Optional[str] = None,
    ) -> str:
        """Make the actual HTTP request to the DeepL API."""
        client = await self._get_client()

        payload: dict[str, str] = {
            "auth_key": self._api_key,
            "text": text,
            "target_lang": target_lang,
        }
        if source_lang:
            payload["source_lang"] = source_lang

        response = await client.post(DEEPL_API_URL, data=payload)
        response.raise_for_status()

        data = response.json()
        translations = data.get("translations", [])
        if not translations:
            return text
        return translations[0].get("text", text)

    async def close(self) -> None:
        """Shut down HTTP client and Redis connection."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
        if self._redis:
            await self._redis.close()


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

translation_service = TranslationService()
