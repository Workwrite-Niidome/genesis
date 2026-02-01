from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.core.history_manager import history_manager

router = APIRouter()


@router.get("/ticks")
async def list_ticks(
    offset: int = Query(0, ge=0),
    limit: int = Query(50, le=100),
    db: AsyncSession = Depends(get_db),
):
    ticks = await history_manager.get_ticks(db, offset=offset, limit=limit)
    return [
        {
            "id": str(t.id),
            "tick_number": t.tick_number,
            "ai_count": t.ai_count,
            "concept_count": t.concept_count,
            "significant_events": t.significant_events,
            "processing_time_ms": t.processing_time_ms,
            "created_at": t.created_at.isoformat(),
        }
        for t in ticks
    ]


@router.get("/ticks/{tick_number}")
async def get_tick(tick_number: int, db: AsyncSession = Depends(get_db)):
    tick = await history_manager.get_tick(db, tick_number)
    if not tick:
        return {"error": "Tick not found"}
    return {
        "id": str(tick.id),
        "tick_number": tick.tick_number,
        "world_snapshot": tick.world_snapshot,
        "ai_count": tick.ai_count,
        "concept_count": tick.concept_count,
        "significant_events": tick.significant_events,
        "processing_time_ms": tick.processing_time_ms,
        "created_at": tick.created_at.isoformat(),
    }


@router.get("/events")
async def list_events(
    event_type: str | None = Query(None),
    min_importance: float = Query(0.0, ge=0.0, le=1.0),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, le=100),
    db: AsyncSession = Depends(get_db),
):
    events = await history_manager.get_events(
        db,
        event_type=event_type,
        min_importance=min_importance,
        offset=offset,
        limit=limit,
    )
    return [
        {
            "id": str(e.id),
            "event_type": e.event_type,
            "importance": e.importance,
            "title": e.title,
            "description": e.description,
            "tick_number": e.tick_number,
            "created_at": e.created_at.isoformat(),
        }
        for e in events
    ]


@router.get("/timeline")
async def get_timeline(
    limit: int = Query(100, le=500),
    db: AsyncSession = Depends(get_db),
):
    return await history_manager.get_timeline(db, limit=limit)


@router.get("/god-feed")
async def get_god_feed(
    limit: int = Query(20, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Public endpoint for God AI observations (no admin auth required)."""
    from app.core.god_ai import god_ai_manager
    feed = await god_ai_manager.get_god_feed(db, limit=limit)
    return {"feed": feed}
