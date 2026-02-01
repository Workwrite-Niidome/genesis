import logging

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.core.god_ai import god_ai_manager
from app.core.ai_manager import ai_manager
from app.schemas.god import GodAIState, GodMessageRequest, GodMessageResponse
from app.models.ai import AI, AIMemory
from app.models.artifact import Artifact
from app.models.concept import Concept
from app.models.event import Event
from app.models.tick import Tick
from app.models.god_ai import GodAI
from app.models.interaction import Interaction
from app.models.ai_thought import AIThought
from app.models.chat import ChatMessage
from app.models.observer import Observer

logger = logging.getLogger(__name__)

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


@router.get("/feed")
async def get_god_feed(
    limit: int = Query(20, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Get God AI observations and messages for the feed."""
    feed = await god_ai_manager.get_god_feed(db, limit=limit)
    return {"feed": feed}


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


class ResetWorldRequest(BaseModel):
    confirm: bool = False
    confirmation_text: str = ""


@router.post("/reset-world")
async def reset_world(
    request: ResetWorldRequest,
    db: AsyncSession = Depends(get_db),
):
    """Reset the entire world — delete all AIs, memories, concepts, events, ticks, and God AI state.
    This allows re-running Genesis from a clean state.
    Requires confirmation_text='default' to proceed."""
    if not request.confirm or request.confirmation_text != "default":
        return {"success": False, "message": "Must confirm reset by sending confirmation_text='default'"}

    # Delete in dependency order (children before parents)
    await db.execute(delete(ChatMessage))
    await db.execute(delete(Observer))
    await db.execute(delete(AIThought))
    await db.execute(delete(AIMemory))
    await db.execute(delete(Interaction))
    await db.execute(delete(Artifact))
    await db.execute(delete(Event))
    await db.execute(delete(Tick))
    await db.execute(delete(Concept))
    await db.execute(delete(AI))
    await db.execute(delete(GodAI))
    await db.commit()

    logger.info("World has been reset — all data cleared")
    return {
        "success": True,
        "message": "World reset complete. All AIs, concepts, events, ticks, and God AI state have been deleted. You can now run Genesis again.",
    }
