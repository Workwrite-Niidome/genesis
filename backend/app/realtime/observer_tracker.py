"""
GENESIS v3 - Observer Tracker
Track which Socket.IO clients are watching which entities.
Uses Redis sets: genesis:observers:{entity_id} -> set of sids
And reverse: genesis:observer_focus:{sid} -> entity_id
"""
import logging
import json
import uuid
from typing import Optional

import redis

from app.config import settings
from app.realtime.socket_manager import sio

logger = logging.getLogger(__name__)

_redis_pool = redis.ConnectionPool.from_url(settings.REDIS_URL, decode_responses=True)

OBSERVER_KEY_PREFIX = "genesis:observers:"
FOCUS_KEY_PREFIX = "genesis:observer_focus:"
OBSERVER_COUNTS_KEY = "genesis:observer_counts"  # hash: entity_id -> count


class ObserverTracker:
    """Tracks real-time observer attention on entities."""

    def _redis(self) -> redis.Redis:
        return redis.Redis(connection_pool=_redis_pool)

    def focus(self, sid: str, entity_id: str) -> None:
        """Record that sid is now watching entity_id."""
        r = self._redis()
        pipe = r.pipeline()

        # Remove from previous focus
        old_entity = r.get(f"{FOCUS_KEY_PREFIX}{sid}")
        if old_entity:
            pipe.srem(f"{OBSERVER_KEY_PREFIX}{old_entity}", sid)

        # Add to new focus
        pipe.set(f"{FOCUS_KEY_PREFIX}{sid}", entity_id)
        pipe.sadd(f"{OBSERVER_KEY_PREFIX}{entity_id}", sid)
        pipe.execute()

    def unfocus(self, sid: str) -> None:
        """Remove sid from whatever entity it was watching."""
        r = self._redis()
        old_entity = r.get(f"{FOCUS_KEY_PREFIX}{sid}")
        if old_entity:
            pipe = r.pipeline()
            pipe.srem(f"{OBSERVER_KEY_PREFIX}{old_entity}", sid)
            pipe.delete(f"{FOCUS_KEY_PREFIX}{sid}")
            pipe.execute()

    def disconnect(self, sid: str) -> None:
        """Clean up when a client disconnects."""
        self.unfocus(sid)

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


observer_tracker = ObserverTracker()


# ===================================================================
# Socket.IO event handlers
# ===================================================================

@sio.on("observer_focus")
async def handle_observer_focus(sid: str, data: dict):
    """Client is now watching a specific entity. Expects: { entity_id: str }"""
    entity_id = data.get("entity_id", "")
    if entity_id:
        try:
            observer_tracker.focus(sid, entity_id)
            logger.debug("Observer %s focused on entity %s", sid, entity_id)
        except Exception as e:
            logger.warning("Observer focus failed: %s", e)


@sio.on("observer_unfocus")
async def handle_observer_unfocus(sid: str, data: dict = None):
    """Client stopped watching a specific entity."""
    try:
        observer_tracker.unfocus(sid)
    except Exception as e:
        logger.warning("Observer unfocus failed: %s", e)
