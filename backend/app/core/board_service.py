"""Board service: manages automatic thread creation for world events."""

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.board import BoardThread
from app.models.event import Event

logger = logging.getLogger(__name__)


async def create_event_thread(
    db: AsyncSession,
    event: Event,
    *,
    category: str | None = None,
) -> BoardThread | None:
    """Create a board thread linked to a world event.

    Called automatically when significant events occur (concept creation,
    artifact creation, organization formation, notable AI deaths).
    """
    try:
        thread = BoardThread(
            title=event.title,
            body=event.description,
            author_type="system",
            author_id=None,
            event_id=event.id,
            category=category or event.event_type,
            reply_count=0,
            is_pinned=False,
        )
        db.add(thread)
        await db.flush()

        # Emit socket event for real-time board updates
        try:
            from app.realtime.socket_manager import publish_event
            publish_event("board_thread", {
                "id": str(thread.id),
                "title": thread.title,
                "body": thread.body,
                "author_type": thread.author_type,
                "author_id": None,
                "author_name": None,
                "event_id": str(event.id) if event.id else None,
                "category": thread.category,
                "reply_count": 0,
                "last_reply_at": None,
                "is_pinned": False,
                "created_at": thread.created_at.isoformat() if thread.created_at else None,
            })
        except Exception as e:
            logger.warning(f"Failed to emit board_thread socket event: {e}")

        logger.info(f"Auto-thread created: '{event.title}' (event_type={event.event_type})")
        return thread

    except Exception as e:
        logger.error(f"Failed to create event thread: {e}")
        return None
