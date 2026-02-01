from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.core.god_ai import god_ai_manager
from app.core.ai_manager import ai_manager
from app.schemas.god import GodAIState, GodMessageRequest, GodMessageResponse

router = APIRouter()


@router.get("/state")
async def get_god_state(db: AsyncSession = Depends(get_db)):
    god = await god_ai_manager.get_or_create(db)
    return {
        "id": str(god.id),
        "state": god.state,
        "current_message": god.current_message,
        "is_active": god.is_active,
        "created_at": god.created_at.isoformat(),
        "updated_at": god.updated_at.isoformat(),
    }


@router.post("/message")
async def send_message_to_god(
    request: GodMessageRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await god_ai_manager.send_message(db, request.message)
    return result


@router.get("/history")
async def get_god_history(db: AsyncSession = Depends(get_db)):
    history = await god_ai_manager.get_conversation_history(db)
    return {"history": history}


class SpawnAIRequest(BaseModel):
    count: int = 1


@router.post("/spawn")
async def god_spawn_ai(
    request: SpawnAIRequest,
    db: AsyncSession = Depends(get_db),
):
    """God AI fallback: manually spawn AIs when nothing emerges from the void."""
    god = await god_ai_manager.get_or_create(db)
    if god.state.get("phase") == "pre_genesis":
        return {"success": False, "message": "Genesis has not been performed yet."}

    spawned = []
    for _ in range(min(request.count, 10)):
        ai = await ai_manager.create_ai(db, creator_type="god", tick_number=0)
        spawned.append({
            "id": str(ai.id),
            "position": {"x": ai.position_x, "y": ai.position_y},
            "appearance": ai.appearance,
        })

    return {"success": True, "spawned": spawned, "count": len(spawned)}
