import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.observer import Observer
from app.models.chat import ChatMessage
from app.schemas.observer import (
    ObserverRegister,
    ObserverLogin,
    ObserverResponse,
    ChatMessageCreate,
    ChatMessageResponse,
)
from app.api.auth import get_current_observer
from app.realtime.socket_manager import publish_event

from passlib.context import CryptContext
from jose import jwt, JWTError

from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

JWT_SECRET = settings.SECRET_KEY
JWT_ALGORITHM = "HS256"

router = APIRouter()


def _create_token(observer_id: str, username: str) -> str:
    """Create a JWT token for an observer."""
    payload = {
        "sub": observer_id,
        "username": username,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


@router.post("/register", response_model=ObserverResponse)
async def register(body: ObserverRegister, db: AsyncSession = Depends(get_db)):
    """Create a new observer account."""
    # Check if username already exists
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
        password_hash=pwd_context.hash(body.password),
        role="user",
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


@router.post("/login", response_model=ObserverResponse)
async def login(body: ObserverLogin, db: AsyncSession = Depends(get_db)):
    """Authenticate an observer and return a JWT token."""
    result = await db.execute(
        select(Observer).where(Observer.username == body.username)
    )
    observer = result.scalar_one_or_none()
    if not observer or not pwd_context.verify(body.password, observer.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    # Update last_active_at
    observer.last_active_at = datetime.now(timezone.utc)
    await db.commit()

    token = _create_token(str(observer.id), observer.username)
    return ObserverResponse(
        id=str(observer.id),
        username=observer.username,
        role=observer.role,
        language=observer.language,
        token=token,
    )


@router.get("/me", response_model=ObserverResponse)
async def get_me(observer: Observer = Depends(get_current_observer)):
    """Get the current observer's profile."""
    token = _create_token(str(observer.id), observer.username)
    return ObserverResponse(
        id=str(observer.id),
        username=observer.username,
        role=observer.role,
        language=observer.language,
        token=token,
    )


@router.get("/chat", response_model=list[ChatMessageResponse])
async def get_chat(
    channel: str = Query("global"),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """Get recent chat messages for a channel."""
    result = await db.execute(
        select(ChatMessage, Observer.username)
        .join(Observer, ChatMessage.observer_id == Observer.id)
        .where(ChatMessage.channel == channel)
        .order_by(ChatMessage.created_at.desc())
        .limit(limit)
    )
    rows = result.all()

    # Return in chronological order (oldest first)
    messages = []
    for chat_msg, username in reversed(rows):
        messages.append(
            ChatMessageResponse(
                id=str(chat_msg.id),
                username=username,
                channel=chat_msg.channel,
                content=chat_msg.content,
                timestamp=chat_msg.created_at.isoformat(),
            )
        )
    return messages


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

    response = ChatMessageResponse(
        id=str(chat_msg.id),
        username=observer.username,
        channel=chat_msg.channel,
        content=chat_msg.content,
        timestamp=chat_msg.created_at.isoformat(),
    )

    # Publish via Redis pub/sub for real-time delivery
    publish_event("chat_message", response.model_dump())

    return response
