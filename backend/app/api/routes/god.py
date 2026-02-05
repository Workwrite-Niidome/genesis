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

# Public router for observer-facing God dialogue (no admin auth required)
public_router = APIRouter()


class ObserverGodMessageRequest(BaseModel):
    message: str


@public_router.post("/dialogue")
async def observer_dialogue_with_god(
    request: ObserverGodMessageRequest,
    db: AsyncSession = Depends(get_db),
):
    """Public endpoint: Observers can address the God AI directly.

    The God AI will respond based on the current state of the world.
    Observer messages are treated as prayers/addresses from mortals.
    """
    result = await god_ai_manager.send_message(db, request.message)
    return {
        "god_response": result["god_response"],
        "timestamp": result["timestamp"],
    }


@public_router.get("/observations")
async def get_recent_god_observations(
    limit: int = Query(3, le=10),
    db: AsyncSession = Depends(get_db),
):
    """Public endpoint: Get recent God AI observations for context."""
    feed = await god_ai_manager.get_god_feed(db, limit=limit)
    observations = [
        entry for entry in (feed or [])
        if entry.get("role") == "god_observation"
    ][:limit]
    return {"observations": observations}


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


@router.get("/world-report")
async def get_world_report(db: AsyncSession = Depends(get_db)):
    """Get latest world report for Claude Code review.

    Returns full world state, AI voices, events, and the prompt
    that would be used for autonomous world update.
    The admin can review this with Claude Code and issue commands
    via POST /god/message.
    """
    import os
    import glob as glob_module

    report_dir = os.path.join(os.path.dirname(__file__), "..", "..", "world_reports")
    if not os.path.isdir(report_dir):
        return {"report": None, "message": "No world reports generated yet."}

    reports = sorted(glob_module.glob(os.path.join(report_dir, "world_report_tick_*.md")), reverse=True)
    if not reports:
        return {"report": None, "message": "No world reports generated yet."}

    latest = reports[0]
    with open(latest, "r", encoding="utf-8") as f:
        content = f.read()

    tick = os.path.basename(latest).replace("world_report_tick_", "").replace(".md", "")
    return {
        "report": content,
        "tick": int(tick) if tick.isdigit() else None,
        "file": os.path.basename(latest),
        "total_reports": len(reports),
    }


@router.post("/evaluate-ranking")
async def evaluate_ranking(db: AsyncSession = Depends(get_db)):
    """Manually trigger God AI ranking evaluation."""
    from sqlalchemy import select
    from app.models.tick import Tick

    god = await god_ai_manager.get_or_create(db)
    if god.state.get("phase") != "post_genesis":
        return {"success": False, "message": "Genesis has not been performed yet."}

    # Get current tick number
    tick_result = await db.execute(
        select(Tick).order_by(Tick.tick_number.desc()).limit(1)
    )
    latest_tick = tick_result.scalar_one_or_none()
    tick_number = latest_tick.tick_number if latest_tick else 0

    try:
        await god_ai_manager._evaluate_rankings(db, god, tick_number)
        await db.commit()

        # Return updated ranking
        current_ranking = god.state.get("current_ranking", [])
        criteria = god.state.get("ranking_criteria", "")
        return {
            "success": True,
            "criteria": criteria,
            "ranking": current_ranking,
            "tick": tick_number,
        }
    except Exception as e:
        logger.error(f"Manual ranking evaluation failed: {e}")
        return {"success": False, "message": str(e)}


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
