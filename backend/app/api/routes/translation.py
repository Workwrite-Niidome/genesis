"""
GENESIS v3 - Translation API
================================
Provides a REST endpoint for on-demand text translation via DeepL.

Endpoints
---------
POST /api/v3/translate
    Translate text to a target language.

The endpoint is rate-limited per client IP to prevent abuse.
"""

from __future__ import annotations

import hashlib
import logging
import time
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.services.translation import translation_service, SUPPORTED_LANGUAGES

logger = logging.getLogger(__name__)

router = APIRouter()

# ---------------------------------------------------------------------------
# Per-IP rate limiting (in-memory, lightweight)
# ---------------------------------------------------------------------------

_IP_RATE_LIMIT: dict[str, list[float]] = {}
IP_RATE_MAX = 60        # requests per window per IP
IP_RATE_WINDOW = 60.0   # seconds


def _check_ip_rate(ip: str) -> bool:
    """Return True if the IP is within its rate limit."""
    now = time.monotonic()
    window_start = now - IP_RATE_WINDOW

    if ip not in _IP_RATE_LIMIT:
        _IP_RATE_LIMIT[ip] = []

    # Prune old entries
    _IP_RATE_LIMIT[ip] = [t for t in _IP_RATE_LIMIT[ip] if t > window_start]

    if len(_IP_RATE_LIMIT[ip]) >= IP_RATE_MAX:
        return False

    _IP_RATE_LIMIT[ip].append(now)
    return True


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class TranslateRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000, description="Text to translate")
    target_lang: str = Field(..., min_length=2, max_length=5, description="Target language code (e.g. 'ja', 'EN')")
    source_lang: Optional[str] = Field(None, min_length=2, max_length=5, description="Source language code (optional, auto-detected)")


class TranslateResponse(BaseModel):
    translated_text: str
    source_lang: str
    target_lang: str


class DetectRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000)


class DetectResponse(BaseModel):
    detected_lang: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/translate", response_model=TranslateResponse)
async def translate_text(body: TranslateRequest, request: Request):
    """Translate text to the specified target language.

    - Uses DeepL API under the hood with Redis caching.
    - If no API key is configured, returns the original text unchanged.
    - Rate-limited per client IP.
    """
    client_ip = request.client.host if request.client else "unknown"

    if not _check_ip_rate(client_ip):
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Please try again later.",
        )

    # Detect source language if not provided
    source_lang = body.source_lang
    if not source_lang:
        source_lang = await translation_service.detect_language(body.text)

    # Normalise target
    target_upper = translation_service._normalize_lang(body.target_lang)
    source_upper = translation_service._normalize_lang(source_lang)

    # Same language? Return original.
    if source_upper == target_upper:
        return TranslateResponse(
            translated_text=body.text,
            source_lang=source_upper,
            target_lang=target_upper,
        )

    translated = await translation_service.translate(
        text=body.text,
        target_lang=body.target_lang,
        source_lang=body.source_lang,
    )

    return TranslateResponse(
        translated_text=translated,
        source_lang=source_upper,
        target_lang=target_upper,
    )


@router.post("/detect", response_model=DetectResponse)
async def detect_language(body: DetectRequest, request: Request):
    """Detect the language of the given text."""
    client_ip = request.client.host if request.client else "unknown"

    if not _check_ip_rate(client_ip):
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Please try again later.",
        )

    detected = await translation_service.detect_language(body.text)
    return DetectResponse(detected_lang=detected)
