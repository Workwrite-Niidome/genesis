from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.core.god_ai import god_ai_manager
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
