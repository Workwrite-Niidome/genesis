import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.ai_thought import AIThought
from app.models.ai import AI

router = APIRouter()


@router.get("/feed")
async def get_thought_feed(
    limit: int = Query(50, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Get the latest thoughts across all AIs."""
    result = await db.execute(
        select(AIThought, AI.name)
        .join(AI, AIThought.ai_id == AI.id)
        .order_by(AIThought.created_at.desc())
        .limit(limit)
    )
    rows = result.all()

    return [
        {
            "id": str(thought.id),
            "ai_id": str(thought.ai_id),
            "ai_name": ai_name,
            "tick_number": thought.tick_number,
            "thought_type": thought.thought_type,
            "content": thought.content,
            "action": thought.action,
            "created_at": thought.created_at.isoformat(),
        }
        for thought, ai_name in rows
    ]


@router.get("/ai/{ai_id}")
async def get_thoughts_by_ai(
    ai_id: uuid.UUID,
    limit: int = Query(20, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Get thoughts for a specific AI."""
    result = await db.execute(
        select(AIThought)
        .where(AIThought.ai_id == ai_id)
        .order_by(AIThought.created_at.desc())
        .limit(limit)
    )
    thoughts = result.scalars().all()

    return [
        {
            "id": str(t.id),
            "ai_id": str(t.ai_id),
            "tick_number": t.tick_number,
            "thought_type": t.thought_type,
            "content": t.content,
            "action": t.action,
            "created_at": t.created_at.isoformat(),
        }
        for t in thoughts
    ]
