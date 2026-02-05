import asyncio
import json
import logging
from concurrent.futures import ThreadPoolExecutor

import redis
import redis.asyncio as aioredis
import socketio

from app.config import settings

logger = logging.getLogger(__name__)

# Redis channel for cross-process socket events
REDIS_CHANNEL = "genesis:socket_events"

# ---------------------------------------------------------------------------
# Known event types — every event the system can emit.
# The subscriber forwards all events regardless; this list is for
# documentation and optional client-side filtering.
# ---------------------------------------------------------------------------
KNOWN_EVENT_TYPES = frozenset({
    # Tick lifecycle
    "tick_start",
    "tick_complete",

    # Entity events
    "entity_thought",
    "entity_died",
    "entity_born",
    "entity_position",

    # God AI events
    "god_observation",
    "god_world_update",
    "god_succession_summary",
    "god_observation_summary",
    "god_world_update_summary",

    # Culture & social events
    "culture_event",
    "conflict_event",

    # Artifact events
    "artifact_created",

    # Building / voxel events
    "building_event",

    # Code execution events
    "code_executed",

    # Observer events
    "observer_count",
    "observer_focus",
    "observer_unfocus",
    "entity_observer_count",
    "chat_message",

    # Legacy / dashboard events
    "world_update",
    "ai_position",
    "thought",
    "event",
    "interaction",
    "ai_death",
    "concept_created",
    "organization_formed",
    "conflict",
})

# Connection pool for sync Redis publisher (reused across all publish_event calls)
_redis_pool = redis.ConnectionPool.from_url(settings.REDIS_URL, decode_responses=True)

# Thread pool for running sync Redis publish from async context without blocking
_publish_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="sio_pub")

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

    # Register observer session so online counts are accurate
    try:
        from app.realtime.observer_tracker import observer_tracker
        from urllib.parse import parse_qs

        observer_id = None
        display_name = "Anonymous"

        # Check query string for observer info
        query_string = environ.get("QUERY_STRING", "")
        qs = parse_qs(query_string)
        if "observer_id" in qs:
            observer_id = qs["observer_id"][0]
        if "display_name" in qs:
            display_name = qs["display_name"][0]

        if not observer_id:
            observer_id = f"tmp_{sid}"

        observer_tracker.register_session(sid, observer_id, display_name)

        # Broadcast updated online count
        total = observer_tracker.get_total_online()
        publish_event("observer_count", {"total_online": total})
    except Exception as exc:
        logger.warning(f"Observer connect registration failed: {exc}")


@sio.event
async def disconnect(sid):
    logger.info(f"Client disconnected: {sid}")
    # Clean up observer tracking (focus + session)
    try:
        from app.realtime.observer_tracker import observer_tracker
        observer_tracker.disconnect(sid)

        # Broadcast updated online count
        total = observer_tracker.get_total_online()
        publish_event("observer_count", {"total_online": total})
    except Exception as exc:
        logger.warning(f"Observer disconnect cleanup failed: {exc}")
    # Clean up avatar session if this was a human player
    try:
        from app.realtime.avatar_handler import cleanup_avatar_session
        await cleanup_avatar_session(sid)
    except ImportError:
        pass


def publish_event(event_type: str, data: dict | list) -> None:
    """Publish a socket event to Redis channel (synchronous).

    Uses sync redis client with connection pool so it works from any process
    context (Celery worker, FastAPI, asyncio, etc.) without creating new
    connections per call.
    """
    try:
        r = redis.Redis(connection_pool=_redis_pool)
        message = json.dumps({"event": event_type, "data": data}, default=str)
        r.publish(REDIS_CHANNEL, message)
    except Exception as e:
        logger.warning(f"Failed to publish socket event '{event_type}': {e}")


async def async_publish_event(event_type: str, data: dict | list) -> None:
    """Publish a socket event from an async context without blocking the event loop.

    Delegates the synchronous Redis publish call to a thread pool executor.
    Safe to call from any async function (tick engine, agent runtime, etc.).
    """
    loop = asyncio.get_running_loop()
    try:
        await loop.run_in_executor(_publish_executor, publish_event, event_type, data)
    except Exception as e:
        logger.warning(f"Failed to async-publish socket event '{event_type}': {e}")


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
