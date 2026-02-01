import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, desc, case
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.database import get_db
from app.models.board import BoardThread, BoardReply
from app.models.observer import Observer
from app.schemas.board import (
    ThreadCreate,
    ReplyCreate,
    ThreadResponse,
    ThreadDetailResponse,
    ReplyResponse,
)
from app.api.auth import get_current_observer
from app.realtime.socket_manager import publish_event

router = APIRouter()


def _thread_to_response(thread: BoardThread, author_name: str | None = None) -> ThreadResponse:
    return ThreadResponse(
        id=str(thread.id),
        title=thread.title,
        body=thread.body,
        author_type=thread.author_type,
        author_id=str(thread.author_id) if thread.author_id else None,
        author_name=author_name,
        event_id=str(thread.event_id) if thread.event_id else None,
        category=thread.category,
        reply_count=thread.reply_count,
        last_reply_at=thread.last_reply_at.isoformat() if thread.last_reply_at else None,
        is_pinned=thread.is_pinned,
        created_at=thread.created_at.isoformat(),
    )


def _reply_to_response(reply: BoardReply, author_name: str | None = None) -> ReplyResponse:
    return ReplyResponse(
        id=str(reply.id),
        thread_id=str(reply.thread_id),
        author_type=reply.author_type,
        author_id=str(reply.author_id) if reply.author_id else None,
        author_name=author_name,
        content=reply.content,
        created_at=reply.created_at.isoformat(),
    )


@router.get("/threads", response_model=list[ThreadResponse])
async def list_threads(
    page: int = Query(1, ge=1),
    limit: int = Query(30, ge=1, le=100),
    category: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """List threads: pinned first, then by last_reply_at descending."""
    query = select(BoardThread)

    if category:
        query = query.where(BoardThread.category == category)

    # Pinned first, then by last_reply_at (fallback to created_at)
    query = query.order_by(
        desc(BoardThread.is_pinned),
        desc(BoardThread.last_reply_at.is_not(None)),
        desc(BoardThread.last_reply_at),
        desc(BoardThread.created_at),
    )

    offset = (page - 1) * limit
    query = query.offset(offset).limit(limit)

    result = await db.execute(query)
    threads = result.scalars().all()

    # Resolve observer author names
    responses = []
    for thread in threads:
        author_name = None
        if thread.author_type == "observer" and thread.author_id:
            obs_result = await db.execute(
                select(Observer.username).where(Observer.id == thread.author_id)
            )
            author_name = obs_result.scalar_one_or_none()
        elif thread.author_type == "system":
            author_name = "SYSTEM"
        responses.append(_thread_to_response(thread, author_name))

    return responses


@router.get("/threads/{thread_id}", response_model=ThreadDetailResponse)
async def get_thread(
    thread_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get a thread with all replies."""
    result = await db.execute(
        select(BoardThread)
        .options(selectinload(BoardThread.replies))
        .where(BoardThread.id == thread_id)
    )
    thread = result.scalar_one_or_none()
    if not thread:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thread not found")

    # Resolve thread author name
    thread_author_name = None
    if thread.author_type == "observer" and thread.author_id:
        obs_result = await db.execute(
            select(Observer.username).where(Observer.id == thread.author_id)
        )
        thread_author_name = obs_result.scalar_one_or_none()
    elif thread.author_type == "system":
        thread_author_name = "SYSTEM"

    # Build replies with author names
    sorted_replies = sorted(thread.replies, key=lambda r: r.created_at)
    reply_responses = []
    for reply in sorted_replies:
        reply_author_name = None
        if reply.author_type == "observer" and reply.author_id:
            obs_result = await db.execute(
                select(Observer.username).where(Observer.id == reply.author_id)
            )
            reply_author_name = obs_result.scalar_one_or_none()
        elif reply.author_type == "system":
            reply_author_name = "SYSTEM"
        reply_responses.append(_reply_to_response(reply, reply_author_name))

    return ThreadDetailResponse(
        id=str(thread.id),
        title=thread.title,
        body=thread.body,
        author_type=thread.author_type,
        author_id=str(thread.author_id) if thread.author_id else None,
        author_name=thread_author_name,
        event_id=str(thread.event_id) if thread.event_id else None,
        category=thread.category,
        reply_count=thread.reply_count,
        last_reply_at=thread.last_reply_at.isoformat() if thread.last_reply_at else None,
        is_pinned=thread.is_pinned,
        created_at=thread.created_at.isoformat(),
        replies=reply_responses,
    )


@router.post("/threads", response_model=ThreadResponse, status_code=status.HTTP_201_CREATED)
async def create_thread(
    body: ThreadCreate,
    observer: Observer = Depends(get_current_observer),
    db: AsyncSession = Depends(get_db),
):
    """Create a new thread. Requires observer authentication."""
    thread = BoardThread(
        title=body.title,
        body=body.body,
        author_type="observer",
        author_id=observer.id,
        category=body.category,
        reply_count=0,
        is_pinned=False,
    )
    db.add(thread)
    await db.commit()
    await db.refresh(thread)

    response = _thread_to_response(thread, observer.username)

    publish_event("board_thread", response.model_dump())

    return response


@router.post("/threads/{thread_id}/replies", response_model=ReplyResponse, status_code=status.HTTP_201_CREATED)
async def create_reply(
    thread_id: uuid.UUID,
    body: ReplyCreate,
    observer: Observer = Depends(get_current_observer),
    db: AsyncSession = Depends(get_db),
):
    """Post a reply to a thread. Requires observer authentication."""
    result = await db.execute(
        select(BoardThread).where(BoardThread.id == thread_id)
    )
    thread = result.scalar_one_or_none()
    if not thread:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thread not found")

    reply = BoardReply(
        thread_id=thread.id,
        author_type="observer",
        author_id=observer.id,
        content=body.content,
    )
    db.add(reply)

    # Update thread counters
    thread.reply_count = thread.reply_count + 1
    thread.last_reply_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(reply)

    response = _reply_to_response(reply, observer.username)

    publish_event("board_reply", {
        **response.model_dump(),
        "thread_title": thread.title,
    })

    return response
