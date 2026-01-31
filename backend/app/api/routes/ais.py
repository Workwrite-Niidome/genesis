import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.core.ai_manager import ai_manager
from app.schemas.ai import AIBase, AIDetail, AIMemorySchema

router = APIRouter()


@router.get("")
async def list_ais(
    alive_only: bool = Query(True),
    db: AsyncSession = Depends(get_db),
):
    if alive_only:
        ais = await ai_manager.get_all_alive(db)
    else:
        from sqlalchemy import select
        from app.models.ai import AI
        result = await db.execute(select(AI))
        ais = list(result.scalars().all())

    return [
        {
            "id": str(ai.id),
            "creator_type": ai.creator_type,
            "position_x": ai.position_x,
            "position_y": ai.position_y,
            "appearance": ai.appearance,
            "state": ai.state,
            "is_alive": ai.is_alive,
            "created_at": ai.created_at.isoformat(),
        }
        for ai in ais
    ]


@router.get("/{ai_id}")
async def get_ai(ai_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    ai = await ai_manager.get_ai(db, ai_id)
    if not ai:
        raise HTTPException(status_code=404, detail="AI not found")
    return {
        "id": str(ai.id),
        "creator_id": str(ai.creator_id) if ai.creator_id else None,
        "creator_type": ai.creator_type,
        "position_x": ai.position_x,
        "position_y": ai.position_y,
        "appearance": ai.appearance,
        "state": ai.state,
        "is_alive": ai.is_alive,
        "created_at": ai.created_at.isoformat(),
        "updated_at": ai.updated_at.isoformat(),
    }


@router.get("/{ai_id}/memories")
async def get_ai_memories(
    ai_id: uuid.UUID,
    limit: int = Query(20, le=100),
    db: AsyncSession = Depends(get_db),
):
    ai = await ai_manager.get_ai(db, ai_id)
    if not ai:
        raise HTTPException(status_code=404, detail="AI not found")

    memories = await ai_manager.get_ai_memories(db, ai_id, limit=limit)
    return [
        {
            "id": str(m.id),
            "content": m.content,
            "memory_type": m.memory_type,
            "importance": m.importance,
            "tick_number": m.tick_number,
            "created_at": m.created_at.isoformat(),
        }
        for m in memories
    ]
