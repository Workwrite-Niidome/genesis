import asyncio
import json
import logging

import redis
import redis.asyncio as aioredis
import socketio

from app.config import settings

logger = logging.getLogger(__name__)

# Redis channel for cross-process socket events
REDIS_CHANNEL = "genesis:socket_events"

# Connection pool for sync Redis publisher (reused across all publish_event calls)
_redis_pool = redis.ConnectionPool.from_url(settings.REDIS_URL, decode_responses=True)

# Create Socket.IO server
sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins=settings.cors_origins_list,
    logger=False,
    engineio_logger=False,
)

# Create ASGI app for Socket.IO
socket_app = socketio.ASGIApp(sio)


@sio.event
async def connect(sid, environ):
    logger.info(f"Client connected: {sid}")


@sio.event
async def disconnect(sid):
    logger.info(f"Client disconnected: {sid}")
    # Clean up observer tracking
    try:
        from app.realtime.observer_tracker import observer_tracker
        observer_tracker.disconnect(sid)
    except ImportError:
        pass
    # Clean up avatar session if this was a human player
    try:
        from app.realtime.avatar_handler import cleanup_avatar_session
        await cleanup_avatar_session(sid)
    except ImportError:
        pass


def publish_event(event_type: str, data: dict | list) -> None:
    """Publish a socket event to Redis channel.

    Uses sync redis client with connection pool so it works from any process
    context (Celery worker, FastAPI, asyncio, etc.) without creating new
    connections per call.
    """
    try:
        r = redis.Redis(connection_pool=_redis_pool)
        message = json.dumps({"event": event_type, "data": data})
        r.publish(REDIS_CHANNEL, message)
    except Exception as e:
        logger.warning(f"Failed to publish socket event '{event_type}': {e}")


async def start_event_subscriber() -> None:
    """Subscribe to Redis channel and emit Socket.IO events.

    Runs as an async background task in the FastAPI process.
    Uses redis.asyncio for non-blocking operation.
    """
    logger.info("Starting Redis event subscriber for Socket.IO bridge")
    while True:
        try:
            r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
            pubsub = r.pubsub()
            await pubsub.subscribe(REDIS_CHANNEL)
            logger.info(f"Subscribed to Redis channel: {REDIS_CHANNEL}")

            async for message in pubsub.listen():
                if message["type"] != "message":
                    continue
                try:
                    payload = json.loads(message["data"])
                    event_type = payload["event"]
                    data = payload["data"]
                    await sio.emit(event_type, data)
                    logger.debug(f"Emitted socket event: {event_type}")
                except (json.JSONDecodeError, KeyError) as e:
                    logger.warning(f"Invalid event message from Redis: {e}")
                except Exception as e:
                    logger.warning(f"Error emitting socket event: {e}")

        except asyncio.CancelledError:
            logger.info("Event subscriber cancelled, shutting down")
            break
        except Exception as e:
            logger.error(f"Redis subscriber connection error: {e}, reconnecting in 5s...")
            await asyncio.sleep(5)


class SocketManager:
    """Manages real-time event broadcasting via Socket.IO.

    Convenience wrappers that publish events through Redis pub/sub,
    so they work from any process (Celery worker or FastAPI).
    """

    def emit_thought(self, thought_data: dict) -> None:
        publish_event("thought", thought_data)

    def emit_event(self, event_data: dict) -> None:
        publish_event("event", event_data)

    def emit_world_update(self, world_data: dict) -> None:
        publish_event("world_update", world_data)

    def emit_ai_position(self, position_data: dict | list) -> None:
        publish_event("ai_position", position_data)

    def emit_interaction(self, interaction_data: dict) -> None:
        publish_event("interaction", interaction_data)

    def emit_god_observation(self, observation_data: dict) -> None:
        publish_event("god_observation", observation_data)

    def emit_ai_death(self, death_data: dict) -> None:
        publish_event("ai_death", death_data)

    def emit_concept_created(self, concept_data: dict) -> None:
        publish_event("concept_created", concept_data)

    def emit_artifact_created(self, artifact_data: dict) -> None:
        publish_event("artifact_created", artifact_data)

    def emit_organization_formed(self, org_data: dict) -> None:
        publish_event("organization_formed", org_data)


socket_manager = SocketManager()
