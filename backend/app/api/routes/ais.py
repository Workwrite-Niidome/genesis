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
    """Get AI ranking — God AI evaluated scores, with age-based fallback."""
    from sqlalchemy import select as sa_select, func as sa_func
    from app.models.ai import AI as AIModel, AIMemory
    from app.models.god_ai import GodAI

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

    # Build AI lookup by id
    ai_map = {str(ai.id): ai for ai in ais_list}

    # Try God AI ranking first (get most recently updated active God AI)
    god_result = await db.execute(
        sa_select(GodAI).where(GodAI.is_active == True).order_by(GodAI.updated_at.desc()).limit(1)
    )
    god_ai = god_result.scalars().first()
    god_ranking = god_ai.state.get("current_ranking", []) if god_ai else []
    ranking_criteria = god_ai.state.get("ranking_criteria", "") if god_ai else ""

    if god_ranking:
        # Build response from God AI ranking, merged with AI model data
        ranked_response = []
        for entry in god_ranking[:limit]:
            ai_id = entry.get("ai_id", "")
            ai = ai_map.get(ai_id)
            if not ai:
                continue
            ranked_response.append({
                "id": str(ai.id),
                "name": ai.name,
                "age": ai.state.get("age", 0),
                "memory_count": memory_counts.get(ai.id, 0),
                "personality_traits": ai.personality_traits or [],
                "appearance": ai.appearance,
                "is_alive": ai.is_alive,
                "relationships_count": len(ai.state.get("relationships", {})),
                "adopted_concepts_count": len(ai.state.get("adopted_concepts", [])),
                "god_score": entry.get("score", 0),
                "god_reason": entry.get("reason", ""),
                "ranking_criteria": ranking_criteria,
            })

        # Add any AIs not in God ranking (newly spawned) at the end
        ranked_ids = {e.get("ai_id") for e in god_ranking}
        for ai in ais_list:
            if str(ai.id) not in ranked_ids and len(ranked_response) < limit:
                ranked_response.append({
                    "id": str(ai.id),
                    "name": ai.name,
                    "age": ai.state.get("age", 0),
                    "memory_count": memory_counts.get(ai.id, 0),
                    "personality_traits": ai.personality_traits or [],
                    "appearance": ai.appearance,
                    "is_alive": ai.is_alive,
                    "relationships_count": len(ai.state.get("relationships", {})),
                    "adopted_concepts_count": len(ai.state.get("adopted_concepts", [])),
                    "god_score": None,
                    "god_reason": None,
                    "ranking_criteria": ranking_criteria,
                })

        return ranked_response
    else:
        # Fallback: age-based (existing logic)
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
