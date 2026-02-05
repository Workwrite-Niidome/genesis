"""GENESIS v3 Human Avatar WebSocket Handler.

Handles real-time human input via Socket.IO and processes it through the same
WorldServer pipeline that AI entities use. From the world's perspective, a
human avatar is indistinguishable from an AI entity.

Events (client → server):
    avatar_join      — Authenticate and link session to an entity
    avatar_move      — Move avatar to a new position
    avatar_speak     — Say something (appears as speech event)
    avatar_build     — Place a voxel block
    avatar_destroy   — Remove a voxel block
    avatar_interact  — Interact with a nearby entity
    avatar_leave     — Disconnect avatar from the world

All actions go through WorldServer.process_proposal() for validation.
"""
from __future__ import annotations

import json
import logging
import time
import uuid
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.database import async_session
from app.models.entity import Entity
from app.realtime.socket_manager import sio, publish_event
from app.world.world_server import ActionProposal

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Session tracking
# ---------------------------------------------------------------------------

@dataclass
class AvatarSession:
    """Tracks an active human avatar connection."""
    sid: str
    entity_id: uuid.UUID
    observer_id: uuid.UUID
    entity_name: str
    last_action_time: float = 0.0
    action_count_window: list[float] = field(default_factory=list)


# sid → AvatarSession
_sessions: dict[str, AvatarSession] = {}
# entity_id → sid (reverse lookup)
_entity_to_sid: dict[uuid.UUID, str] = {}

# Rate limit: max actions per second
MAX_ACTIONS_PER_SECOND = 10
RATE_WINDOW = 1.0  # seconds


def _rate_check(session: AvatarSession) -> bool:
    """Return True if the action is within rate limits."""
    now = time.monotonic()
    # Remove old entries outside the window
    session.action_count_window = [
        t for t in session.action_count_window
        if now - t < RATE_WINDOW
    ]
    if len(session.action_count_window) >= MAX_ACTIONS_PER_SECOND:
        return False
    session.action_count_window.append(now)
    return True


def _get_session(sid: str) -> AvatarSession | None:
    return _sessions.get(sid)


async def _get_current_tick(db: AsyncSession) -> int:
    from app.models.world import WorldEvent
    from sqlalchemy import func
    result = await db.execute(select(func.max(WorldEvent.tick)))
    return result.scalar() or 0


# ---------------------------------------------------------------------------
# Socket.IO event handlers
# ---------------------------------------------------------------------------

@sio.on("avatar_join")
async def handle_avatar_join(sid: str, data: dict):
    """Client wants to enter the world as a human avatar.

    Expects: { token: str, entity_id: str }
    The entity must already exist with origin_type='human_avatar' and be owned
    by the authenticated observer.
    """
    entity_id_str = data.get("entity_id", "")
    token = data.get("token", "")

    if not entity_id_str or not token:
        await sio.emit("avatar_error", {"error": "Missing entity_id or token"}, to=sid)
        return

    # Validate JWT token
    try:
        from jose import jwt, JWTError
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        observer_id = uuid.UUID(payload.get("sub", ""))
    except Exception:
        await sio.emit("avatar_error", {"error": "Invalid authentication"}, to=sid)
        return

    try:
        entity_id = uuid.UUID(entity_id_str)
    except ValueError:
        await sio.emit("avatar_error", {"error": "Invalid entity_id format"}, to=sid)
        return

    # Verify entity ownership
    async with async_session() as db:
        result = await db.execute(
            select(Entity).where(
                Entity.id == entity_id,
                Entity.origin_type == "human_avatar",
                Entity.owner_user_id == observer_id,
                Entity.is_alive == True,  # noqa: E712
            )
        )
        entity = result.scalars().first()

        if entity is None:
            await sio.emit("avatar_error", {"error": "Avatar not found or not owned by you"}, to=sid)
            return

        # Check if already connected from another session
        if entity_id in _entity_to_sid:
            old_sid = _entity_to_sid[entity_id]
            if old_sid in _sessions:
                del _sessions[old_sid]
                await sio.emit("avatar_error", {"error": "Session replaced by new connection"}, to=old_sid)

        # Create session
        session = AvatarSession(
            sid=sid,
            entity_id=entity_id,
            observer_id=observer_id,
            entity_name=entity.name,
        )
        _sessions[sid] = session
        _entity_to_sid[entity_id] = sid

        # Send current state to the client
        await sio.emit("avatar_joined", {
            "entity_id": str(entity.id),
            "name": entity.name,
            "position": {
                "x": entity.position_x,
                "y": entity.position_y,
                "z": entity.position_z,
            },
            "facing": {
                "x": entity.facing_x,
                "z": entity.facing_z,
            },
            "personality": entity.personality,
            "appearance": entity.appearance,
        }, to=sid)

        logger.info("Avatar joined: %s (entity=%s, sid=%s)", entity.name, entity_id, sid)


@sio.on("avatar_move")
async def handle_avatar_move(sid: str, data: dict):
    """Move the avatar. Expects: { x: float, y: float, z: float }"""
    session = _get_session(sid)
    if not session:
        await sio.emit("avatar_error", {"error": "Not joined as avatar"}, to=sid)
        return

    if not _rate_check(session):
        return  # Silently drop rate-limited moves

    x = data.get("x")
    y = data.get("y")
    z = data.get("z")
    if x is None or z is None:
        return

    async with async_session() as db:
        tick = await _get_current_tick(db)
        from app.world.world_server import world_server
        proposal = ActionProposal(
            agent_id=session.entity_id,
            action="move",
            params={"target_x": float(x), "target_y": float(y or 1.0), "target_z": float(z)},
            tick=tick,
        )
        result = await world_server.process_proposal(db, proposal)
        await db.commit()

        if result.get("status") == "accepted":
            # Broadcast position update
            publish_event("entity_position", {
                "entityId": str(session.entity_id),
                "x": float(x),
                "y": float(y or 1.0),
                "z": float(z),
                "name": session.entity_name,
            })


@sio.on("avatar_speak")
async def handle_avatar_speak(sid: str, data: dict):
    """Human types a chat message. Appears as speech event.

    Expects: { text: str }
    The broadcast includes the detected source language so clients can
    request translation on the fly.
    """
    session = _get_session(sid)
    if not session:
        await sio.emit("avatar_error", {"error": "Not joined as avatar"}, to=sid)
        return

    if not _rate_check(session):
        await sio.emit("avatar_error", {"error": "Rate limited"}, to=sid)
        return

    text = str(data.get("text", "")).strip()
    if not text:
        return
    if len(text) > 500:
        text = text[:500]

    # Detect language for cross-language translation support
    source_lang = "EN"
    try:
        from app.services.translation import translation_service
        source_lang = await translation_service.detect_language(text)
    except Exception as exc:
        logger.debug("Language detection skipped: %s", exc)

    async with async_session() as db:
        tick = await _get_current_tick(db)
        from app.world.world_server import world_server
        proposal = ActionProposal(
            agent_id=session.entity_id,
            action="speak",
            params={"text": text, "volume": 10.0},
            tick=tick,
        )
        result = await world_server.process_proposal(db, proposal)
        await db.commit()

        if result.get("status") == "accepted":
            # Broadcast speech event with source language for translation
            publish_event("speech", {
                "entityId": str(session.entity_id),
                "name": session.entity_name,
                "text": text,
                "tick": tick,
                "sourceLang": source_lang,
            })

            # Store speech in Redis so nearby AI entities perceive it
            # during their next tick cycle.  The key expires after 30
            # seconds to avoid stale data accumulation.
            try:
                import redis as _redis
                r = _redis.from_url(settings.REDIS_URL)
                r.setex(
                    f"genesis:speech:{session.entity_id}",
                    30,
                    json.dumps({
                        "text": text,
                        "tick": tick,
                        "speaker_name": session.entity_name,
                        "entity_id": str(session.entity_id),
                    }),
                )
            except Exception as e:
                logger.warning("Failed to store speech in Redis for %s: %s", session.entity_name, e)


@sio.on("avatar_build")
async def handle_avatar_build(sid: str, data: dict):
    """Place a voxel block. Expects: { x: int, y: int, z: int, color: str, material: str }"""
    session = _get_session(sid)
    if not session:
        await sio.emit("avatar_error", {"error": "Not joined as avatar"}, to=sid)
        return

    if not _rate_check(session):
        await sio.emit("avatar_error", {"error": "Rate limited"}, to=sid)
        return

    try:
        x = int(data["x"])
        y = int(data["y"])
        z = int(data["z"])
    except (KeyError, TypeError, ValueError):
        await sio.emit("avatar_error", {"error": "Invalid position"}, to=sid)
        return

    color = data.get("color", "#888888")
    material = data.get("material", "solid")

    async with async_session() as db:
        tick = await _get_current_tick(db)
        from app.world.world_server import world_server
        proposal = ActionProposal(
            agent_id=session.entity_id,
            action="place_voxel",
            params={"x": x, "y": y, "z": z, "color": color, "material": material},
            tick=tick,
        )
        result = await world_server.process_proposal(db, proposal)
        await db.commit()

        if result.get("status") == "accepted":
            publish_event("voxel_update", {
                "x": x, "y": y, "z": z,
                "color": color,
                "material": material,
                "action": "place",
            })
        else:
            await sio.emit("avatar_error", {
                "error": result.get("reason", "Build failed"),
            }, to=sid)


@sio.on("avatar_destroy")
async def handle_avatar_destroy(sid: str, data: dict):
    """Destroy a voxel block. Expects: { x: int, y: int, z: int }"""
    session = _get_session(sid)
    if not session:
        await sio.emit("avatar_error", {"error": "Not joined as avatar"}, to=sid)
        return

    if not _rate_check(session):
        return

    try:
        x = int(data["x"])
        y = int(data["y"])
        z = int(data["z"])
    except (KeyError, TypeError, ValueError):
        return

    async with async_session() as db:
        tick = await _get_current_tick(db)
        from app.world.world_server import world_server
        proposal = ActionProposal(
            agent_id=session.entity_id,
            action="destroy_voxel",
            params={"x": x, "y": y, "z": z},
            tick=tick,
        )
        result = await world_server.process_proposal(db, proposal)
        await db.commit()

        if result.get("status") == "accepted":
            publish_event("voxel_update", {
                "x": x, "y": y, "z": z,
                "action": "destroy",
            })


@sio.on("avatar_leave")
async def handle_avatar_leave(sid: str, data: dict = None):
    """Client is leaving the world."""
    session = _sessions.pop(sid, None)
    if session:
        _entity_to_sid.pop(session.entity_id, None)
        logger.info("Avatar left: %s (sid=%s)", session.entity_name, sid)

        # Broadcast departure
        publish_event("entity_position", {
            "entityId": str(session.entity_id),
            "offline": True,
        })


async def cleanup_avatar_session(sid: str) -> None:
    """Clean up avatar session on disconnect. Called from socket_manager."""
    session = _sessions.pop(sid, None)
    if session:
        _entity_to_sid.pop(session.entity_id, None)
        logger.info("Avatar disconnected: %s (sid=%s)", session.entity_name, sid)
