"""GENESIS v3 - Observer API routes.

Provides both legacy (username+password) and anonymous (display_name-only)
observer registration, chat, focus tracking, and online status endpoints.
"""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.observer import Observer
from app.models.chat import ChatMessage
from app.schemas.observer import (
    # Legacy
    ObserverRegister,
    ObserverLogin,
    ObserverResponse,
    # Anonymous
    AnonymousRegisterRequest,
    AnonymousRegisterResponse,
    # List / stats
    OnlineObserverInfo,
    ObserverStatsResponse,
    # Focus
    FocusRequest,
    # Chat
    ChatMessageCreate,
    ChatMessageResponse,
)
from app.api.auth import get_current_observer
from app.realtime.socket_manager import publish_event
from app.realtime.observer_tracker import observer_tracker

from passlib.context import CryptContext
from jose import jwt, JWTError

from app.config import settings

import redis
import logging

logger = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

JWT_SECRET = settings.SECRET_KEY
JWT_ALGORITHM = "HS256"

# Redis connection for online-observer tracking
_redis_pool = redis.ConnectionPool.from_url(
    settings.REDIS_URL, decode_responses=True
)

# Redis keys
ONLINE_OBSERVERS_KEY = "genesis:online_observers"        # hash: observer_id -> JSON
OBSERVER_FOCUS_MAP_KEY = "genesis:observer_focus_map"    # hash: observer_id -> entity_id

router = APIRouter()


# ---------------------------------------------------------------------------
# Helper: Redis client
# ---------------------------------------------------------------------------

def _redis_client() -> redis.Redis:
    return redis.Redis(connection_pool=_redis_pool)


# ---------------------------------------------------------------------------
# Helper: JWT creation
# ---------------------------------------------------------------------------

def _create_token(observer_id: str, username: str, *, anonymous: bool = False) -> str:
    """Create a JWT token for an observer."""
    payload = {
        "sub": observer_id,
        "username": username,
        "anonymous": anonymous,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


# ---------------------------------------------------------------------------
# Helper: register observer as online in Redis
# ---------------------------------------------------------------------------

def _set_observer_online(observer_id: str, display_name: str) -> None:
    """Mark an observer as online in Redis."""
    import json

    r = _redis_client()
    data = json.dumps({"id": observer_id, "display_name": display_name})
    r.hset(ONLINE_OBSERVERS_KEY, observer_id, data)


def _set_observer_offline(observer_id: str) -> None:
    """Mark an observer as offline in Redis."""
    r = _redis_client()
    r.hdel(ONLINE_OBSERVERS_KEY, observer_id)
    r.hdel(OBSERVER_FOCUS_MAP_KEY, observer_id)


# ===================================================================
# GET / -- list current online observers (no auth required)
# ===================================================================

@router.get("/", response_model=list[OnlineObserverInfo])
async def list_online_observers():
    """List all currently online observers.

    Returns display_name and what entity each observer is focused on (if any).
    No authentication required.
    """
    import json

    r = _redis_client()
    all_observers = r.hgetall(ONLINE_OBSERVERS_KEY)
    focus_map = r.hgetall(OBSERVER_FOCUS_MAP_KEY)

    result = []
    for observer_id, raw in all_observers.items():
        try:
            info = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            continue
        result.append(
            OnlineObserverInfo(
                id=info.get("id", observer_id),
                display_name=info.get("display_name", "Unknown"),
                focus_entity_id=focus_map.get(observer_id),
            )
        )
    return result


# ===================================================================
# POST /register -- anonymous observer registration (display_name only)
# ===================================================================

@router.post("/register", response_model=AnonymousRegisterResponse)
async def register_anonymous(
    body: AnonymousRegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    """Register as an anonymous observer.

    Only a display_name is required. The server generates a unique session
    identity and returns a JWT token for subsequent authenticated requests.
    No email or password needed.
    """
    observer_id = uuid.uuid4()
    # Generate a unique internal username from UUID to satisfy the uniqueness
    # constraint while keeping the display_name human-friendly.
    internal_username = f"anon_{observer_id.hex[:12]}"

    observer = Observer(
        id=observer_id,
        username=internal_username,
        display_name=body.display_name.strip(),
        password_hash=None,
        role="observer",
        is_anonymous=True,
        language="en",
        settings={},
    )
    db.add(observer)
    await db.commit()
    await db.refresh(observer)

    token = _create_token(str(observer.id), internal_username, anonymous=True)

    # Mark as online in Redis
    _set_observer_online(str(observer.id), observer.display_name)

    return AnonymousRegisterResponse(
        id=str(observer.id),
        display_name=observer.display_name,
        token=token,
    )


# ===================================================================
# POST /register-account -- legacy registration with username+password
# ===================================================================

@router.post("/register-account", response_model=ObserverResponse)
async def register_account(
    body: ObserverRegister,
    db: AsyncSession = Depends(get_db),
):
    """Create a new observer account (legacy username+password flow)."""
    result = await db.execute(
        select(Observer).where(Observer.username == body.username)
    )
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already taken",
        )

    observer = Observer(
        id=uuid.uuid4(),
        username=body.username,
        display_name=body.username,
        password_hash=pwd_context.hash(body.password),
        role="user",
        is_anonymous=False,
        language=body.language,
        settings={},
    )
    db.add(observer)
    await db.commit()
    await db.refresh(observer)

    token = _create_token(str(observer.id), observer.username)
    return ObserverResponse(
        id=str(observer.id),
        username=observer.username,
        role=observer.role,
        language=observer.language,
        token=token,
    )


# ===================================================================
# POST /login -- legacy login with username+password
# ===================================================================

@router.post("/login", response_model=ObserverResponse)
async def login(body: ObserverLogin, db: AsyncSession = Depends(get_db)):
    """Authenticate an observer and return a JWT token (legacy flow)."""
    result = await db.execute(
        select(Observer).where(Observer.username == body.username)
    )
    observer = result.scalar_one_or_none()
    if (
        not observer
        or not observer.password_hash
        or not pwd_context.verify(body.password, observer.password_hash)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    # Update last_active_at
    observer.last_active_at = datetime.now(timezone.utc)
    await db.commit()

    token = _create_token(str(observer.id), observer.username)

    # Mark as online
    _set_observer_online(str(observer.id), observer.display_name or observer.username)

    return ObserverResponse(
        id=str(observer.id),
        username=observer.username,
        role=observer.role,
        language=observer.language,
        token=token,
    )


# ===================================================================
# GET /me -- get current observer profile (requires auth)
# ===================================================================

@router.get("/me")
async def get_me(observer: Observer = Depends(get_current_observer)):
    """Get the current observer's profile. Requires a valid JWT token."""
    token = _create_token(str(observer.id), observer.username)
    return {
        "id": str(observer.id),
        "username": observer.username,
        "display_name": observer.display_name or observer.username,
        "role": observer.role,
        "language": observer.language,
        "is_anonymous": observer.is_anonymous,
        "token": token,
        "created_at": observer.created_at.isoformat() if observer.created_at else None,
        "last_active_at": observer.last_active_at.isoformat() if observer.last_active_at else None,
    }


# ===================================================================
# GET /stats -- observer statistics (no auth required)
# ===================================================================

@router.get("/stats", response_model=ObserverStatsResponse)
async def get_stats():
    """Get observer statistics: total online, active watchers, per-entity focus counts.

    No authentication required. Useful for dashboard widgets.
    """
    r = _redis_client()

    # Total online observers
    total_online = r.hlen(ONLINE_OBSERVERS_KEY)

    # Focus map: observer_id -> entity_id
    focus_map = r.hgetall(OBSERVER_FOCUS_MAP_KEY)
    active_watchers = len(focus_map)

    # Count observers per entity
    entity_counts: dict[str, int] = {}
    for _observer_id, entity_id in focus_map.items():
        if entity_id:
            entity_counts[entity_id] = entity_counts.get(entity_id, 0) + 1

    # Also merge with data from ObserverTracker (Socket.IO-based tracking)
    try:
        tracker_counts = observer_tracker.get_all_observer_counts()
        for eid, count in tracker_counts.items():
            if eid not in entity_counts:
                entity_counts[eid] = count
            else:
                # Take the max to avoid double-counting
                entity_counts[eid] = max(entity_counts[eid], count)
    except Exception as exc:
        logger.warning("Failed to read observer_tracker counts: %s", exc)

    return ObserverStatsResponse(
        total_online=total_online,
        active_watchers=active_watchers,
        entity_focus_counts=entity_counts,
    )


# ===================================================================
# POST /focus -- set which entity the observer is focusing on
# ===================================================================

@router.post("/focus")
async def set_focus(
    body: FocusRequest,
    observer: Observer = Depends(get_current_observer),
):
    """Set which entity the current observer is focusing on.

    Pass ``entity_id: null`` or omit it to unfocus (stop watching any entity).
    The focus is stored in Redis for real-time observer-count tracking.
    """
    r = _redis_client()
    observer_id = str(observer.id)

    if body.entity_id:
        # Store the focus
        r.hset(OBSERVER_FOCUS_MAP_KEY, observer_id, body.entity_id)
        logger.debug("Observer %s focused on entity %s", observer_id, body.entity_id)

        # Also update the Socket.IO-based tracker so counts are consistent
        try:
            observer_tracker.focus(observer_id, body.entity_id)
        except Exception as exc:
            logger.warning("observer_tracker.focus failed: %s", exc)

        # Broadcast focus event via Socket.IO
        publish_event("observer_focus", {
            "observer_id": observer_id,
            "display_name": observer.display_name or observer.username,
            "entity_id": body.entity_id,
        })

        return {"status": "focused", "entity_id": body.entity_id}
    else:
        # Unfocus
        r.hdel(OBSERVER_FOCUS_MAP_KEY, observer_id)

        try:
            observer_tracker.unfocus(observer_id)
        except Exception as exc:
            logger.warning("observer_tracker.unfocus failed: %s", exc)

        publish_event("observer_unfocus", {
            "observer_id": observer_id,
        })

        return {"status": "unfocused", "entity_id": None}


# ===================================================================
# GET /chat -- get recent observer chat messages
# ===================================================================

@router.get("/chat", response_model=list[ChatMessageResponse])
async def get_chat(
    channel: str = Query("global"),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """Get recent chat messages for a channel.

    No authentication required. Returns messages in chronological order
    (oldest first).
    """
    result = await db.execute(
        select(ChatMessage, Observer.username, Observer.display_name)
        .join(Observer, ChatMessage.observer_id == Observer.id)
        .where(ChatMessage.channel == channel)
        .order_by(ChatMessage.created_at.desc())
        .limit(limit)
    )
    rows = result.all()

    # Return in chronological order (oldest first)
    messages = []
    for chat_msg, username, display_name in reversed(rows):
        messages.append(
            ChatMessageResponse(
                id=str(chat_msg.id),
                username=display_name or username,
                channel=chat_msg.channel,
                content=chat_msg.content,
                timestamp=chat_msg.created_at.isoformat(),
            )
        )
    return messages


# ===================================================================
# POST /chat -- send a chat message (requires auth)
# ===================================================================

@router.post("/chat", response_model=ChatMessageResponse)
async def post_chat(
    body: ChatMessageCreate,
    observer: Observer = Depends(get_current_observer),
    db: AsyncSession = Depends(get_db),
):
    """Post a chat message. Requires observer authentication."""
    chat_msg = ChatMessage(
        id=uuid.uuid4(),
        observer_id=observer.id,
        channel=body.channel,
        content=body.content,
        original_language=observer.language,
        translations={},
    )
    db.add(chat_msg)
    await db.commit()
    await db.refresh(chat_msg)

    display = observer.display_name or observer.username

    response = ChatMessageResponse(
        id=str(chat_msg.id),
        username=display,
        channel=chat_msg.channel,
        content=chat_msg.content,
        timestamp=chat_msg.created_at.isoformat(),
    )

    # Publish via Redis pub/sub for real-time delivery
    publish_event("chat_message", response.model_dump())

    return response
