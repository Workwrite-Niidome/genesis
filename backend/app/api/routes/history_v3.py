"""GENESIS v3 History & Archive API routes.

Provides rich endpoints for timeline seeking, event searching, entity life
timelines, and world statistics over time.
"""
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select, and_, distinct, case, literal_column
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.world import WorldEvent
from app.models.entity import Entity
from app.models.artifact import Artifact

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _serialize_world_event(e: WorldEvent) -> dict:
    return {
        "id": e.id,
        "tick": e.tick,
        "actor_id": str(e.actor_id) if e.actor_id else None,
        "event_type": e.event_type,
        "action": e.action,
        "params": e.params or {},
        "result": e.result,
        "reason": e.reason,
        "position": {
            "x": e.position_x,
            "y": e.position_y,
            "z": e.position_z,
        } if e.position_x is not None else None,
        "importance": e.importance,
        "created_at": e.created_at.isoformat() if e.created_at else None,
    }


def _parse_uuid(raw: str) -> uuid.UUID:
    try:
        return uuid.UUID(raw)
    except (ValueError, AttributeError):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid UUID format: '{raw}'.",
        )


# ---------------------------------------------------------------------------
# 1) GET /ticks?from=&to= — tick summaries for a range
# ---------------------------------------------------------------------------

@router.get("/ticks")
async def get_tick_summaries(
    tick_from: int = Query(0, alias="from", ge=0, description="Start tick (inclusive)"),
    tick_to: int = Query(0, alias="to", ge=0, description="End tick (inclusive). 0 = latest"),
    db: AsyncSession = Depends(get_db),
):
    """Get tick summaries for a range. Each tick summary includes event count
    and event type breakdown."""

    # Determine the actual latest tick
    max_tick_result = await db.execute(select(func.max(WorldEvent.tick)))
    max_tick = max_tick_result.scalar() or 0

    if tick_to <= 0:
        tick_to = max_tick
    if tick_from > tick_to:
        tick_from, tick_to = tick_to, tick_from

    # Clamp range to at most 500 ticks to prevent abuse
    if tick_to - tick_from > 500:
        tick_from = tick_to - 500

    # Group events by tick within range
    result = await db.execute(
        select(
            WorldEvent.tick,
            func.count(WorldEvent.id).label("event_count"),
            func.max(WorldEvent.importance).label("max_importance"),
        )
        .where(WorldEvent.tick >= tick_from, WorldEvent.tick <= tick_to)
        .group_by(WorldEvent.tick)
        .order_by(WorldEvent.tick.asc())
    )
    rows = result.all()

    # Get distinct event types per tick for important ticks
    summaries = []
    for row in rows:
        summaries.append({
            "tick": row.tick,
            "event_count": row.event_count,
            "max_importance": row.max_importance,
        })

    return {
        "from": tick_from,
        "to": tick_to,
        "max_tick": max_tick,
        "ticks": summaries,
    }


# ---------------------------------------------------------------------------
# 2) GET /tick/{tick_number} — detailed state at a specific tick
# ---------------------------------------------------------------------------

@router.get("/tick/{tick_number}")
async def get_tick_detail(tick_number: int, db: AsyncSession = Depends(get_db)):
    """Get all events and world state snapshot at a specific tick."""

    # Get all events at this tick
    events_result = await db.execute(
        select(WorldEvent)
        .where(WorldEvent.tick == tick_number)
        .order_by(WorldEvent.id.asc())
    )
    events = events_result.scalars().all()

    if not events:
        return {
            "tick": tick_number,
            "events": [],
            "event_count": 0,
            "event_types": [],
            "actors": [],
        }

    # Collect unique actor IDs to resolve names
    actor_ids = set()
    for e in events:
        if e.actor_id:
            actor_ids.add(e.actor_id)

    actor_names: dict[uuid.UUID, str] = {}
    if actor_ids:
        name_result = await db.execute(
            select(Entity.id, Entity.name).where(Entity.id.in_(actor_ids))
        )
        for row in name_result.all():
            actor_names[row[0]] = row[1]

    serialized_events = []
    for e in events:
        evt = _serialize_world_event(e)
        evt["actor_name"] = actor_names.get(e.actor_id) if e.actor_id else None
        serialized_events.append(evt)

    event_types = list(set(e.event_type for e in events))
    actors = [
        {"id": str(aid), "name": actor_names.get(aid, "Unknown")}
        for aid in actor_ids
    ]

    return {
        "tick": tick_number,
        "events": serialized_events,
        "event_count": len(events),
        "event_types": event_types,
        "actors": actors,
    }


# ---------------------------------------------------------------------------
# 3) GET /events?tick_from=&tick_to=&type=&search= — search events
# ---------------------------------------------------------------------------

@router.get("/events")
async def search_events(
    tick_from: int = Query(0, ge=0, description="Start tick (inclusive)"),
    tick_to: int = Query(0, ge=0, description="End tick (inclusive). 0 = latest"),
    event_type: str | None = Query(None, alias="type", description="Filter by event type"),
    search: str | None = Query(None, description="Search in action/reason text"),
    min_importance: float = Query(0.0, ge=0.0, le=1.0, description="Minimum importance"),
    limit: int = Query(100, ge=1, le=500, description="Max results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    db: AsyncSession = Depends(get_db),
):
    """Search events with flexible filters."""

    query = select(WorldEvent).where(WorldEvent.importance >= min_importance)

    if tick_from > 0:
        query = query.where(WorldEvent.tick >= tick_from)
    if tick_to > 0:
        query = query.where(WorldEvent.tick <= tick_to)
    if event_type:
        query = query.where(WorldEvent.event_type == event_type)
    if search:
        like_pattern = f"%{search}%"
        query = query.where(
            (WorldEvent.action.ilike(like_pattern))
            | (WorldEvent.reason.ilike(like_pattern))
        )

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    # Fetch paginated results
    query = query.order_by(WorldEvent.tick.desc(), WorldEvent.id.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    events = result.scalars().all()

    # Resolve actor names
    actor_ids = set(e.actor_id for e in events if e.actor_id)
    actor_names: dict[uuid.UUID, str] = {}
    if actor_ids:
        name_result = await db.execute(
            select(Entity.id, Entity.name).where(Entity.id.in_(actor_ids))
        )
        for row in name_result.all():
            actor_names[row[0]] = row[1]

    serialized = []
    for e in events:
        evt = _serialize_world_event(e)
        evt["actor_name"] = actor_names.get(e.actor_id) if e.actor_id else None
        serialized.append(evt)

    return {
        "events": serialized,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


# ---------------------------------------------------------------------------
# 4) GET /entity/{entity_id}/timeline — entity's life timeline
# ---------------------------------------------------------------------------

@router.get("/entity/{entity_id}/timeline")
async def get_entity_timeline(
    entity_id: str,
    limit: int = Query(200, ge=1, le=1000, description="Max events"),
    db: AsyncSession = Depends(get_db),
):
    """Get an entity's life timeline: birth, events, death."""
    uid = _parse_uuid(entity_id)

    # Fetch entity info
    entity_result = await db.execute(
        select(Entity).where(Entity.id == uid)
    )
    entity = entity_result.scalars().first()
    if not entity:
        raise HTTPException(status_code=404, detail=f"Entity '{entity_id}' not found.")

    # Fetch all events where this entity is the actor
    events_result = await db.execute(
        select(WorldEvent)
        .where(WorldEvent.actor_id == uid)
        .order_by(WorldEvent.tick.asc())
        .limit(limit)
    )
    events = events_result.scalars().all()

    return {
        "entity": {
            "id": str(entity.id),
            "name": entity.name,
            "is_alive": entity.is_alive,
            "birth_tick": entity.birth_tick,
            "death_tick": entity.death_tick,
            "origin_type": entity.origin_type,
        },
        "events": [_serialize_world_event(e) for e in events],
        "event_count": len(events),
    }


# ---------------------------------------------------------------------------
# 5) GET /stats — world statistics over time
# ---------------------------------------------------------------------------

@router.get("/stats")
async def get_world_stats(
    bucket_size: int = Query(10, ge=1, le=100, description="Ticks per bucket for aggregation"),
    db: AsyncSession = Depends(get_db),
):
    """Get world statistics over time: entity count, artifact count,
    event counts bucketed by tick ranges."""

    # Current counts
    alive_count_result = await db.execute(
        select(func.count()).select_from(Entity).where(Entity.is_alive == True)  # noqa: E712
    )
    alive_count = alive_count_result.scalar() or 0

    total_entity_result = await db.execute(
        select(func.count()).select_from(Entity)
    )
    total_entity_count = total_entity_result.scalar() or 0

    total_artifact_result = await db.execute(
        select(func.count()).select_from(Artifact)
    )
    total_artifact_count = total_artifact_result.scalar() or 0

    total_event_result = await db.execute(
        select(func.count()).select_from(WorldEvent)
    )
    total_event_count = total_event_result.scalar() or 0

    max_tick_result = await db.execute(select(func.max(WorldEvent.tick)))
    max_tick = max_tick_result.scalar() or 0

    # Entity births over time (bucketed)
    birth_bucket = (Entity.birth_tick / bucket_size).label("bucket")
    birth_stats_result = await db.execute(
        select(
            birth_bucket,
            func.count(Entity.id).label("count"),
        )
        .group_by("bucket")
        .order_by("bucket")
    )
    birth_stats = [
        {"tick": int(row.bucket) * bucket_size, "count": row.count}
        for row in birth_stats_result.all()
        if row.bucket is not None
    ]

    # Entity deaths over time (bucketed)
    death_stats_result = await db.execute(
        select(
            (Entity.death_tick / bucket_size).label("bucket"),
            func.count(Entity.id).label("count"),
        )
        .where(Entity.death_tick.is_not(None))
        .group_by("bucket")
        .order_by("bucket")
    )
    death_stats = [
        {"tick": int(row.bucket) * bucket_size, "count": row.count}
        for row in death_stats_result.all()
        if row.bucket is not None
    ]

    # Events per tick bucket
    event_bucket = (WorldEvent.tick / bucket_size).label("bucket")
    event_stats_result = await db.execute(
        select(
            event_bucket,
            func.count(WorldEvent.id).label("count"),
        )
        .group_by("bucket")
        .order_by("bucket")
    )
    event_stats = [
        {"tick": int(row.bucket) * bucket_size, "count": row.count}
        for row in event_stats_result.all()
        if row.bucket is not None
    ]

    # Event type breakdown
    type_breakdown_result = await db.execute(
        select(
            WorldEvent.event_type,
            func.count(WorldEvent.id).label("count"),
        )
        .group_by(WorldEvent.event_type)
        .order_by(func.count(WorldEvent.id).desc())
    )
    type_breakdown = [
        {"event_type": row.event_type, "count": row.count}
        for row in type_breakdown_result.all()
    ]

    # Entity lives summary (all entities with birth/death)
    entity_lives_result = await db.execute(
        select(
            Entity.id,
            Entity.name,
            Entity.is_alive,
            Entity.birth_tick,
            Entity.death_tick,
            Entity.is_god,
        )
        .order_by(Entity.birth_tick.asc())
        .limit(500)
    )
    entity_lives = [
        {
            "id": str(row.id),
            "name": row.name,
            "is_alive": row.is_alive,
            "birth_tick": row.birth_tick,
            "death_tick": row.death_tick,
            "is_god": row.is_god,
        }
        for row in entity_lives_result.all()
    ]

    return {
        "current": {
            "alive_entities": alive_count,
            "total_entities": total_entity_count,
            "total_artifacts": total_artifact_count,
            "total_events": total_event_count,
            "max_tick": max_tick,
        },
        "births_over_time": birth_stats,
        "deaths_over_time": death_stats,
        "events_over_time": event_stats,
        "event_type_breakdown": type_breakdown,
        "entity_lives": entity_lives,
    }


# ---------------------------------------------------------------------------
# 6) GET /event-types — list all distinct event types
# ---------------------------------------------------------------------------

@router.get("/event-types")
async def get_event_types(db: AsyncSession = Depends(get_db)):
    """List all distinct event types present in the world event log."""
    result = await db.execute(
        select(distinct(WorldEvent.event_type)).order_by(WorldEvent.event_type)
    )
    types = [row[0] for row in result.all()]
    return {"event_types": types}


# ---------------------------------------------------------------------------
# 7) GET /markers — get important event markers for timeline visualization
# ---------------------------------------------------------------------------

@router.get("/markers")
async def get_timeline_markers(
    tick_from: int = Query(0, alias="from", ge=0),
    tick_to: int = Query(0, alias="to", ge=0),
    min_importance: float = Query(0.6, ge=0.0, le=1.0),
    limit: int = Query(200, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
):
    """Get important event markers for the timeline slider visualization.
    Returns compact data suitable for rendering tick markers."""

    max_tick_result = await db.execute(select(func.max(WorldEvent.tick)))
    max_tick = max_tick_result.scalar() or 0

    if tick_to <= 0:
        tick_to = max_tick

    result = await db.execute(
        select(
            WorldEvent.id,
            WorldEvent.tick,
            WorldEvent.event_type,
            WorldEvent.action,
            WorldEvent.importance,
        )
        .where(
            WorldEvent.tick >= tick_from,
            WorldEvent.tick <= tick_to,
            WorldEvent.importance >= min_importance,
        )
        .order_by(WorldEvent.tick.asc())
        .limit(limit)
    )
    markers = [
        {
            "id": row.id,
            "tick": row.tick,
            "event_type": row.event_type,
            "action": row.action,
            "importance": row.importance,
        }
        for row in result.all()
    ]

    return {
        "from": tick_from,
        "to": tick_to,
        "max_tick": max_tick,
        "markers": markers,
    }
