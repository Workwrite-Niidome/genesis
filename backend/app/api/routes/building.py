"""GENESIS v3 Building API routes.

Place, destroy, and create structures via ActionProposal.
All mutations flow through the WorldServer validation pipeline so that
AI and human actions are subject to the same rules.
"""
import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.world import WorldEvent
from app.world.world_server import ActionProposal, world_server

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class PlaceVoxelRequest(BaseModel):
    agent_id: str
    x: int
    y: int
    z: int
    color: str = "#888888"
    material: str = "solid"
    collision: bool = True


class DestroyVoxelRequest(BaseModel):
    agent_id: str
    x: int
    y: int
    z: int


class VoxelData(BaseModel):
    x: int
    y: int
    z: int
    color: str = "#888888"
    material: str = "solid"
    collision: bool = True


class PlaceStructureRequest(BaseModel):
    agent_id: str
    name: str
    voxels: list[VoxelData] = Field(..., min_length=1, max_length=512)
    structure_type: str = "building"
    origin_x: int = 0
    origin_y: int = 0
    origin_z: int = 0


# ---------------------------------------------------------------------------
# Helper: parse agent UUID
# ---------------------------------------------------------------------------

def _parse_agent_id(agent_id: str) -> uuid.UUID:
    """Parse agent_id string into a UUID, raising 400 on invalid format."""
    try:
        return uuid.UUID(agent_id)
    except (ValueError, AttributeError):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid agent_id format: '{agent_id}'. Must be a valid UUID.",
        )


def _get_current_tick_sync() -> int:
    """Return 0 as a fallback tick when we cannot query the DB.

    The WorldServer's event_log.append will record the actual tick.
    """
    return 0


async def _get_current_tick(db: AsyncSession) -> int:
    """Get the latest tick from world events."""
    result = await db.execute(select(func.max(WorldEvent.tick)))
    return result.scalar() or 0


def _build_response(result: dict[str, Any]) -> dict:
    """Build a standard API response from a WorldServer result.

    Raises HTTPException on rejection.
    """
    if result.get("status") == "rejected":
        reason = result.get("reason", "Action rejected by world server")
        reason_code = result.get("reason_code", "rejected")

        # Map reason codes to appropriate HTTP status codes
        status_map = {
            "entity_not_found": 404,
            "entity_dead": 403,
            "no_permission": 403,
            "position_occupied": 409,
            "no_block": 404,
            "zone_overlap": 409,
            "zone_too_large": 400,
            "too_many_voxels": 400,
            "missing_params": 400,
            "collision": 409,
            "move_too_far": 400,
        }
        http_status = status_map.get(reason_code, 400)

        raise HTTPException(
            status_code=http_status,
            detail={
                "reason_code": reason_code,
                "reason": reason,
            },
        )

    return {
        "status": "accepted",
        "data": result.get("data", {}),
    }


# ---------------------------------------------------------------------------
# Place voxel
# ---------------------------------------------------------------------------

@router.post("/place")
async def place_voxel(
    request: PlaceVoxelRequest,
    db: AsyncSession = Depends(get_db),
):
    """Place a voxel block at the specified position.

    Goes through WorldServer validation:
    - Entity must exist and be alive
    - Target position must not be occupied
    """
    agent_uuid = _parse_agent_id(request.agent_id)
    current_tick = await _get_current_tick(db)

    proposal = ActionProposal(
        agent_id=agent_uuid,
        action="place_voxel",
        params={
            "x": request.x,
            "y": request.y,
            "z": request.z,
            "color": request.color,
            "material": request.material,
            "collision": request.collision,
        },
        tick=current_tick,
    )

    result = await world_server.process_proposal(db, proposal)
    return _build_response(result)


# ---------------------------------------------------------------------------
# Destroy voxel
# ---------------------------------------------------------------------------

@router.post("/destroy")
async def destroy_voxel(
    request: DestroyVoxelRequest,
    db: AsyncSession = Depends(get_db),
):
    """Destroy a voxel block at the specified position.

    Goes through WorldServer validation:
    - Entity must exist and be alive
    - A block must exist at the position
    - Entity must have permission (owner, zone owner, or god)
    """
    agent_uuid = _parse_agent_id(request.agent_id)
    current_tick = await _get_current_tick(db)

    proposal = ActionProposal(
        agent_id=agent_uuid,
        action="destroy_voxel",
        params={
            "x": request.x,
            "y": request.y,
            "z": request.z,
        },
        tick=current_tick,
    )

    result = await world_server.process_proposal(db, proposal)
    return _build_response(result)


# ---------------------------------------------------------------------------
# Place structure (multi-voxel)
# ---------------------------------------------------------------------------

@router.post("/structure")
async def place_structure(
    request: PlaceStructureRequest,
    db: AsyncSession = Depends(get_db),
):
    """Place a named structure composed of multiple voxels.

    Goes through WorldServer validation:
    - Entity must exist and be alive
    - Maximum 512 voxels per structure
    - All target positions must be unoccupied
    - Creates a Structure record and all constituent VoxelBlocks
    """
    agent_uuid = _parse_agent_id(request.agent_id)
    current_tick = await _get_current_tick(db)

    # Convert voxel data to the format expected by WorldServer
    voxel_dicts = [
        {
            "x": v.x,
            "y": v.y,
            "z": v.z,
            "color": v.color,
            "material": v.material,
            "collision": v.collision,
        }
        for v in request.voxels
    ]

    proposal = ActionProposal(
        agent_id=agent_uuid,
        action="place_structure",
        params={
            "name": request.name,
            "type": request.structure_type,
            "origin": {
                "x": request.origin_x,
                "y": request.origin_y,
                "z": request.origin_z,
            },
            "voxels": voxel_dicts,
        },
        tick=current_tick,
    )

    result = await world_server.process_proposal(db, proposal)
    return _build_response(result)
