"""GENESIS v3 World State & Voxel Data API routes.

Provides endpoints for querying world state, voxel data within bounding boxes,
structures, zones, world events, and admin controls (genesis, speed, pause).
"""
import logging
import uuid

import redis
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import require_admin
from app.config import settings
from app.db.database import get_db
from app.models.entity import Entity
from app.models.world import Structure, VoxelBlock, WorldEvent, Zone
from app.world.event_log import event_log
from app.world.voxel_engine import voxel_engine

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class SpeedRequest(BaseModel):
    speed: float


class PauseRequest(BaseModel):
    paused: bool


# ---------------------------------------------------------------------------
# Read endpoints
# ---------------------------------------------------------------------------

@router.get("/state")
async def get_world_state(db: AsyncSession = Depends(get_db)):
    """Get current world state: tick, entity count, voxel count, god info."""
    # Count entities
    entity_count_result = await db.execute(
        select(func.count()).select_from(Entity)
    )
    entity_count = entity_count_result.scalar() or 0

    alive_count_result = await db.execute(
        select(func.count()).select_from(Entity).where(Entity.is_alive == True)  # noqa: E712
    )
    alive_count = alive_count_result.scalar() or 0

    # Count voxels
    voxel_count = await voxel_engine.count_blocks(db)

    # Get latest tick from world_events
    latest_tick_result = await db.execute(
        select(func.max(WorldEvent.tick))
    )
    latest_tick = latest_tick_result.scalar() or 0

    # Find god entity
    god_result = await db.execute(
        select(Entity).where(Entity.is_god == True).limit(1)  # noqa: E712
    )
    god_entity = god_result.scalars().first()

    god_info = None
    if god_entity:
        god_info = {
            "id": str(god_entity.id),
            "name": god_entity.name,
            "state": god_entity.state,
        }

    # Check Redis for pause/speed state
    is_paused = False
    time_speed = 1.0
    try:
        r = redis.from_url(settings.REDIS_URL)
        raw_paused = r.get("genesis:is_paused")
        if raw_paused is not None:
            is_paused = raw_paused.decode("utf-8") == "1"
        raw_speed = r.get("genesis:time_speed")
        if raw_speed is not None:
            time_speed = float(raw_speed.decode("utf-8"))
    except Exception:
        logger.warning("Could not read pause/speed from Redis; using defaults")

    # Count structures and zones
    structure_count_result = await db.execute(
        select(func.count()).select_from(Structure)
    )
    structure_count = structure_count_result.scalar() or 0

    zone_count_result = await db.execute(
        select(func.count()).select_from(Zone)
    )
    zone_count = zone_count_result.scalar() or 0

    return {
        "tick": latest_tick,
        "entity_count": entity_count,
        "alive_entity_count": alive_count,
        "voxel_count": voxel_count,
        "structure_count": structure_count,
        "zone_count": zone_count,
        "is_paused": is_paused,
        "time_speed": time_speed,
        "god": god_info,
    }


@router.get("/voxels")
async def get_voxels(
    min_x: int = Query(-100, description="Minimum X coordinate"),
    max_x: int = Query(100, description="Maximum X coordinate"),
    min_y: int = Query(-50, description="Minimum Y coordinate"),
    max_y: int = Query(50, description="Maximum Y coordinate"),
    min_z: int = Query(-100, description="Minimum Z coordinate"),
    max_z: int = Query(100, description="Maximum Z coordinate"),
    db: AsyncSession = Depends(get_db),
):
    """Get voxels in a bounding box. Returns list of {x, y, z, color, material}."""
    # Enforce a maximum query volume to prevent abuse
    volume = (max_x - min_x) * (max_y - min_y) * (max_z - min_z)
    if volume > 8_000_000:
        raise HTTPException(
            status_code=400,
            detail="Bounding box too large. Maximum query volume is 8,000,000 (200x200x200).",
        )

    if min_x > max_x or min_y > max_y or min_z > max_z:
        raise HTTPException(
            status_code=400,
            detail="min values must be <= max values for each axis.",
        )

    blocks = await voxel_engine.get_blocks_in_range(
        db,
        min_pos=(min_x, min_y, min_z),
        max_pos=(max_x, max_y, max_z),
    )

    return [
        {
            "id": block.id,
            "x": block.x,
            "y": block.y,
            "z": block.z,
            "color": block.color,
            "material": block.material,
            "has_collision": block.has_collision,
            "placed_by": str(block.placed_by) if block.placed_by else None,
            "structure_id": str(block.structure_id) if block.structure_id else None,
            "placed_tick": block.placed_tick,
        }
        for block in blocks
    ]


@router.get("/structures")
async def get_structures(db: AsyncSession = Depends(get_db)):
    """Get all named structures."""
    result = await db.execute(
        select(Structure).order_by(Structure.created_at.desc())
    )
    structures = result.scalars().all()

    return [
        {
            "id": str(s.id),
            "name": s.name,
            "owner_id": str(s.owner_id) if s.owner_id else None,
            "structure_type": s.structure_type,
            "bounds": {
                "min": {"x": s.min_x, "y": s.min_y, "z": s.min_z},
                "max": {"x": s.max_x, "y": s.max_y, "z": s.max_z},
            },
            "properties": s.properties,
            "created_tick": s.created_tick,
            "created_at": s.created_at.isoformat() if s.created_at else None,
        }
        for s in structures
    ]


@router.get("/zones")
async def get_zones(db: AsyncSession = Depends(get_db)):
    """Get all zones."""
    result = await db.execute(
        select(Zone).order_by(Zone.created_at.desc())
    )
    zones = result.scalars().all()

    return [
        {
            "id": str(z.id),
            "name": z.name,
            "owner_id": str(z.owner_id) if z.owner_id else None,
            "zone_type": z.zone_type,
            "bounds": {
                "min": {"x": z.min_x, "y": z.min_y, "z": z.min_z},
                "max": {"x": z.max_x, "y": z.max_y, "z": z.max_z},
            },
            "rules": z.rules,
            "created_tick": z.created_tick,
            "created_at": z.created_at.isoformat() if z.created_at else None,
        }
        for z in zones
    ]


@router.get("/events")
async def get_events(
    limit: int = Query(50, ge=1, le=500, description="Number of events to return"),
    db: AsyncSession = Depends(get_db),
):
    """Get recent world events, newest first."""
    events = await event_log.get_recent_events(db, limit=limit)

    return [
        {
            "id": e.id,
            "tick": e.tick,
            "actor_id": str(e.actor_id) if e.actor_id else None,
            "event_type": e.event_type,
            "action": e.action,
            "params": e.params,
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
        for e in events
    ]


# ---------------------------------------------------------------------------
# Admin write endpoints
# ---------------------------------------------------------------------------

@router.post("/genesis", dependencies=[Depends(require_admin)])
async def perform_genesis(db: AsyncSession = Depends(get_db)):
    """Run the creation sequence. Creates the world, spawns the god entity, etc.

    This is an admin-only operation that initializes or resets the world.
    """
    try:
        from app.god.genesis_creation import run_genesis
        from app.god.god_ai import god_ai_manager
    except ImportError:
        # Fallback: create a minimal god entity if the god module is not available
        logger.warning("god module not found; performing minimal genesis")
        return await _minimal_genesis(db)

    god = await god_ai_manager.get_or_create(db)
    result = await run_genesis(db, god)
    return result


async def _minimal_genesis(db: AsyncSession) -> dict:
    """Fallback genesis that creates a god entity if none exists."""
    # Check if a god entity already exists
    god_result = await db.execute(
        select(Entity).where(Entity.is_god == True).limit(1)  # noqa: E712
    )
    god = god_result.scalars().first()

    if god:
        return {
            "status": "already_exists",
            "message": "A god entity already exists.",
            "god_id": str(god.id),
            "god_name": god.name,
        }

    # Create god entity
    god = Entity(
        name="GENESIS",
        origin_type="native",
        is_god=True,
        is_alive=True,
        position_x=0.0,
        position_y=50.0,
        position_z=0.0,
        personality={},
        state={"role": "creator", "phase": "genesis"},
        appearance={"form": "divine", "color": "#FFD700"},
    )
    db.add(god)
    await db.commit()

    return {
        "status": "created",
        "message": "Genesis complete. The world has a creator.",
        "god_id": str(god.id),
        "god_name": god.name,
    }


@router.post("/speed", dependencies=[Depends(require_admin)])
async def set_speed(request: SpeedRequest):
    """Set time speed multiplier via Redis.

    Accepted range: 0.1 to 10.0.
    """
    if not (0.1 <= request.speed <= 10.0):
        raise HTTPException(
            status_code=400,
            detail="Speed must be between 0.1 and 10.0",
        )

    try:
        r = redis.from_url(settings.REDIS_URL)
        r.set("genesis:time_speed", str(request.speed))
    except Exception as exc:
        logger.error("Failed to set speed in Redis: %s", exc)
        raise HTTPException(
            status_code=503,
            detail="Could not connect to Redis to set speed.",
        )

    return {"success": True, "speed": request.speed}


@router.post("/pause", dependencies=[Depends(require_admin)])
async def set_pause(request: PauseRequest):
    """Pause or resume the world simulation via Redis."""
    try:
        r = redis.from_url(settings.REDIS_URL)
        r.set("genesis:is_paused", "1" if request.paused else "0")
    except Exception as exc:
        logger.error("Failed to set pause state in Redis: %s", exc)
        raise HTTPException(
            status_code=503,
            detail="Could not connect to Redis to set pause state.",
        )

    return {"success": True, "paused": request.paused}
