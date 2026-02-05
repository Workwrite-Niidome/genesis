"""
GENESIS v3 - Observer Tracker
Track which Socket.IO clients are watching which entities.
Uses Redis sets: genesis:observers:{entity_id} -> set of sids
And reverse: genesis:observer_focus:{sid} -> entity_id

Also maintains:
  genesis:online_observers  (hash: observer_id -> JSON)
  genesis:observer_focus_map (hash: observer_id -> entity_id)
  genesis:sid_observer_map  (hash: sid -> observer_id)

Socket.IO event handlers:
  connect     - register observer session
  disconnect  - remove observer session
  focus_entity - track which entity observer is watching
  observer_chat - broadcast chat messages in real time
"""

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

import redis

from app.config import settings
from app.realtime.socket_manager import sio, publish_event

logger = logging.getLogger(__name__)

_redis_pool = redis.ConnectionPool.from_url(settings.REDIS_URL, decode_responses=True)

OBSERVER_KEY_PREFIX = "genesis:observers:"
FOCUS_KEY_PREFIX = "genesis:observer_focus:"
OBSERVER_COUNTS_KEY = "genesis:observer_counts"  # hash: entity_id -> count

# Keys shared with the REST API
ONLINE_OBSERVERS_KEY = "genesis:online_observers"        # hash: observer_id -> JSON
OBSERVER_FOCUS_MAP_KEY = "genesis:observer_focus_map"    # hash: observer_id -> entity_id
SID_OBSERVER_MAP_KEY = "genesis:sid_observer_map"        # hash: sid -> observer_id


class ObserverTracker:
    """Tracks real-time observer attention on entities."""

    def _redis(self) -> redis.Redis:
        return redis.Redis(connection_pool=_redis_pool)

    # ----- Session management (sid <-> observer_id) -----

    def register_session(self, sid: str, observer_id: str, display_name: str) -> None:
        """Register a Socket.IO session and mark observer online."""
        r = self._redis()
        pipe = r.pipeline()
        pipe.hset(SID_OBSERVER_MAP_KEY, sid, observer_id)
        pipe.hset(
            ONLINE_OBSERVERS_KEY,
            observer_id,
            json.dumps({"id": observer_id, "display_name": display_name}),
        )
        pipe.execute()

    def unregister_session(self, sid: str) -> Optional[str]:
        """Unregister a Socket.IO session and clean up.

        Returns the observer_id that was associated with this sid, or None.
        """
        r = self._redis()
        observer_id = r.hget(SID_OBSERVER_MAP_KEY, sid)

        pipe = r.pipeline()
        pipe.hdel(SID_OBSERVER_MAP_KEY, sid)

        if observer_id:
            pipe.hdel(ONLINE_OBSERVERS_KEY, observer_id)
            pipe.hdel(OBSERVER_FOCUS_MAP_KEY, observer_id)

        pipe.execute()
        return observer_id

    def get_observer_id_for_sid(self, sid: str) -> Optional[str]:
        """Look up observer_id by Socket.IO session id."""
        r = self._redis()
        return r.hget(SID_OBSERVER_MAP_KEY, sid)

    # ----- Focus tracking -----

    def focus(self, sid_or_id: str, entity_id: str) -> None:
        """Record that sid_or_id is now watching entity_id.

        Works with either a Socket.IO sid or an observer_id.
        """
        r = self._redis()
        pipe = r.pipeline()

        # Remove from previous focus
        old_entity = r.get(f"{FOCUS_KEY_PREFIX}{sid_or_id}")
        if old_entity:
            pipe.srem(f"{OBSERVER_KEY_PREFIX}{old_entity}", sid_or_id)

        # Add to new focus
        pipe.set(f"{FOCUS_KEY_PREFIX}{sid_or_id}", entity_id)
        pipe.sadd(f"{OBSERVER_KEY_PREFIX}{entity_id}", sid_or_id)

        # Also update the observer_focus_map if we can resolve observer_id
        observer_id = r.hget(SID_OBSERVER_MAP_KEY, sid_or_id)
        if observer_id:
            pipe.hset(OBSERVER_FOCUS_MAP_KEY, observer_id, entity_id)
        else:
            # sid_or_id might already be an observer_id
            pipe.hset(OBSERVER_FOCUS_MAP_KEY, sid_or_id, entity_id)

        pipe.execute()

    def unfocus(self, sid_or_id: str) -> None:
        """Remove sid_or_id from whatever entity it was watching."""
        r = self._redis()
        old_entity = r.get(f"{FOCUS_KEY_PREFIX}{sid_or_id}")
        if old_entity:
            pipe = r.pipeline()
            pipe.srem(f"{OBSERVER_KEY_PREFIX}{old_entity}", sid_or_id)
            pipe.delete(f"{FOCUS_KEY_PREFIX}{sid_or_id}")

            observer_id = r.hget(SID_OBSERVER_MAP_KEY, sid_or_id)
            if observer_id:
                pipe.hdel(OBSERVER_FOCUS_MAP_KEY, observer_id)
            else:
                pipe.hdel(OBSERVER_FOCUS_MAP_KEY, sid_or_id)

            pipe.execute()

    def disconnect(self, sid: str) -> None:
        """Clean up when a client disconnects."""
        self.unfocus(sid)
        self.unregister_session(sid)

    def get_observer_count(self, entity_id: str) -> int:
        """Get the number of observers watching a specific entity."""
        r = self._redis()
        return r.scard(f"{OBSERVER_KEY_PREFIX}{entity_id}")

    def get_all_observer_counts(self) -> dict[str, int]:
        """Get observer counts for all entities that have any observers.
        Scans for OBSERVER_KEY_PREFIX keys and returns counts.
        Used once per tick to bulk-update entity states.
        """
        r = self._redis()
        counts: dict[str, int] = {}
        cursor = 0
        while True:
            cursor, keys = r.scan(cursor, match=f"{OBSERVER_KEY_PREFIX}*", count=100)
            for key in keys:
                entity_id = key.replace(OBSERVER_KEY_PREFIX, "")
                count = r.scard(key)
                if count > 0:
                    counts[entity_id] = count
            if cursor == 0:
                break
        return counts

    def get_total_online(self) -> int:
        """Get total number of online observers."""
        r = self._redis()
        return r.hlen(ONLINE_OBSERVERS_KEY)


observer_tracker = ObserverTracker()


# ===================================================================
# Socket.IO event handlers
# ===================================================================

@sio.on("register_observer")
async def handle_register_observer(sid: str, data: dict):
    """Client identifies itself after connection.

    Expects: { observer_id: str, display_name: str, token: str (optional) }
    This allows a client to upgrade from a temporary session to an
    authenticated observer.
    """
    observer_id = data.get("observer_id", "")
    display_name = data.get("display_name", "Anonymous")

    if observer_id:
        # Re-register with proper identity (replaces temp session)
        observer_tracker.register_session(sid, observer_id, display_name)
        logger.info(
            "Observer %s registered as %s (%s)", sid, observer_id, display_name
        )
        await sio.emit("registered", {"observer_id": observer_id}, to=sid)


@sio.on("focus_entity")
async def handle_focus_entity(sid: str, data: dict):
    """Client is now watching a specific entity.

    Expects: { entity_id: str }
    """
    entity_id = data.get("entity_id", "")
    if entity_id:
        try:
            observer_tracker.focus(sid, entity_id)
            logger.debug("Observer %s focused on entity %s", sid, entity_id)

            # Notify other clients of updated observer count for this entity
            count = observer_tracker.get_observer_count(entity_id)
            publish_event("entity_observer_count", {
                "entity_id": entity_id,
                "observer_count": count,
            })
        except Exception as e:
            logger.warning("Observer focus failed: %s", e)


@sio.on("observer_focus")
async def handle_observer_focus(sid: str, data: dict):
    """Alias for focus_entity (backward compatibility).

    Expects: { entity_id: str }
    """
    entity_id = data.get("entity_id", "")
    if entity_id:
        try:
            observer_tracker.focus(sid, entity_id)
            logger.debug("Observer %s focused on entity %s", sid, entity_id)

            count = observer_tracker.get_observer_count(entity_id)
            publish_event("entity_observer_count", {
                "entity_id": entity_id,
                "observer_count": count,
            })
        except Exception as e:
            logger.warning("Observer focus failed: %s", e)


@sio.on("observer_unfocus")
async def handle_observer_unfocus(sid: str, data: dict = None):
    """Client stopped watching a specific entity."""
    try:
        observer_tracker.unfocus(sid)
    except Exception as e:
        logger.warning("Observer unfocus failed: %s", e)


@sio.on("observer_chat")
async def handle_observer_chat(sid: str, data: dict):
    """Observer sends a chat message via Socket.IO.

    Expects: { message: str, channel: str (optional, default "global") }

    The message is broadcast to all connected clients in real time.
    It is also persisted to the database asynchronously if a DB session
    is available.
    """
    message = data.get("message", "").strip()
    channel = data.get("channel", "global")

    if not message:
        return

    if len(message) > 500:
        message = message[:500]

    # Resolve observer identity from sid
    observer_id = observer_tracker.get_observer_id_for_sid(sid)
    display_name = "Anonymous"

    if observer_id:
        r = observer_tracker._redis()
        raw = r.hget(ONLINE_OBSERVERS_KEY, observer_id)
        if raw:
            try:
                info = json.loads(raw)
                display_name = info.get("display_name", "Anonymous")
            except (json.JSONDecodeError, TypeError):
                pass

    # Build chat payload
    chat_payload = {
        "id": str(uuid.uuid4()),
        "username": display_name,
        "observer_id": observer_id or f"tmp_{sid}",
        "channel": channel,
        "content": message,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    # Broadcast to all connected clients
    publish_event("chat_message", chat_payload)

    logger.debug("Chat from %s (%s): %s", display_name, sid, message[:50])
