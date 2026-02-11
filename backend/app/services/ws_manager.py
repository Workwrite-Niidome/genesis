"""
WebSocket manager for Phantom Night real-time updates.

Architecture:
- publish() sends a lightweight notification via Redis pub/sub (sync, usable from Celery)
- subscribe() connects a WebSocket client to a game's Redis channel
- Clients receive {"type": "refresh", "scope": "..."} and refetch via REST API
"""
import json
import asyncio
import logging

import redis
import redis.asyncio as aioredis
from fastapi import WebSocket

from app.config import get_settings

logger = logging.getLogger(__name__)


def _channel(game_id) -> str:
    return f"pn:{game_id}"


def publish(game_id, scope: str) -> None:
    """Publish a refresh notification. Sync — safe from Celery workers and async handlers."""
    settings = get_settings()
    try:
        r = redis.from_url(settings.redis_url)
        r.publish(_channel(game_id), json.dumps({"type": "refresh", "scope": scope}))
        r.close()
    except Exception as e:
        logger.warning(f"ws publish error: {e}")


async def subscribe(game_id, websocket: WebSocket) -> None:
    """Subscribe a WebSocket client to a game's notification channel."""
    settings = get_settings()
    r = aioredis.from_url(settings.redis_url)
    pubsub = r.pubsub()
    await pubsub.subscribe(_channel(game_id))

    async def _forward_redis():
        async for msg in pubsub.listen():
            if msg["type"] == "message":
                await websocket.send_text(msg["data"].decode())

    async def _read_client():
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text('{"type":"pong"}')
            else:
                try:
                    parsed = json.loads(data)
                    if parsed.get("type") == "notify" and parsed.get("scope"):
                        # Client-initiated broadcast (e.g. after posting a comment)
                        publish(game_id, parsed["scope"])
                except (json.JSONDecodeError, Exception):
                    pass

    try:
        done, pending = await asyncio.wait(
            [asyncio.create_task(_forward_redis()),
             asyncio.create_task(_read_client())],
            return_when=asyncio.FIRST_COMPLETED,
        )
        for t in pending:
            t.cancel()
    finally:
        await pubsub.unsubscribe(_channel(game_id))
        await pubsub.close()
        await r.close()
