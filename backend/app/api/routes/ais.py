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
            "name": ai.name,
            "creator_type": ai.creator_type,
            "position_x": ai.position_x,
            "position_y": ai.position_y,
            "appearance": ai.appearance,
            "state": ai.state,
            "personality_traits": ai.personality_traits or [],
            "is_alive": ai.is_alive,
            "created_at": ai.created_at.isoformat(),
        }
        for ai in ais
    ]


@router.get("/ranking")
async def get_ranking(
    limit: int = Query(20, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Get AI ranking by age (oldest first)."""
    from sqlalchemy import select as sa_select, func as sa_func
    from app.models.ai import AI as AIModel, AIMemory

    result = await db.execute(
        sa_select(AIModel).where(AIModel.is_alive == True)
    )
    ais_list = list(result.scalars().all())

    # Count memories per AI
    mem_result = await db.execute(
        sa_select(AIMemory.ai_id, sa_func.count(AIMemory.id))
        .group_by(AIMemory.ai_id)
    )
    memory_counts = {row[0]: row[1] for row in mem_result.all()}

    # Sort by age (oldest first)
    ranked = sorted(
        ais_list,
        key=lambda a: a.state.get("age", 0),
        reverse=True,
    )[:limit]

    return [
        {
            "id": str(ai.id),
            "name": ai.name,
            "age": ai.state.get("age", 0),
            "memory_count": memory_counts.get(ai.id, 0),
            "personality_traits": ai.personality_traits or [],
            "appearance": ai.appearance,
            "is_alive": ai.is_alive,
            "relationships_count": len(ai.state.get("relationships", {})),
            "adopted_concepts_count": len(ai.state.get("adopted_concepts", [])),
        }
        for ai in ranked
    ]


@router.get("/{ai_id}")
async def get_ai(ai_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    ai = await ai_manager.get_ai(db, ai_id)
    if not ai:
        raise HTTPException(status_code=404, detail="AI not found")
    # Get recent thoughts for this AI
    from sqlalchemy import select as sa_select
    from app.models.ai_thought import AIThought
    thought_result = await db.execute(
        sa_select(AIThought)
        .where(AIThought.ai_id == ai_id)
        .order_by(AIThought.created_at.desc())
        .limit(10)
    )
    recent_thoughts = [
        {
            "id": str(t.id),
            "thought_type": t.thought_type,
            "content": t.content,
            "tick_number": t.tick_number,
            "created_at": t.created_at.isoformat(),
        }
        for t in thought_result.scalars().all()
    ]

    return {
        "id": str(ai.id),
        "name": ai.name,
        "creator_id": str(ai.creator_id) if ai.creator_id else None,
        "creator_type": ai.creator_type,
        "position_x": ai.position_x,
        "position_y": ai.position_y,
        "appearance": ai.appearance,
        "state": ai.state,
        "personality_traits": ai.personality_traits or [],
        "is_alive": ai.is_alive,
        "created_at": ai.created_at.isoformat(),
        "updated_at": ai.updated_at.isoformat(),
        "recent_thoughts": recent_thoughts,
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
