from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.api.auth import require_admin
from app.config import settings
from app.core.world_engine import world_engine
from app.core.god_ai import god_ai_manager
from app.schemas.world import WorldState, WorldStats, WorldSettings, GenesisRequest, SpeedRequest, PauseRequest

router = APIRouter()


@router.get("/state", response_model=dict)
async def get_world_state(db: AsyncSession = Depends(get_db)):
    return await world_engine.get_world_state(db)


@router.get("/stats", response_model=dict)
async def get_world_stats(db: AsyncSession = Depends(get_db)):
    return await world_engine.get_world_stats(db)


@router.post("/genesis", dependencies=[Depends(require_admin)])
async def perform_genesis(
    request: GenesisRequest,
    db: AsyncSession = Depends(get_db),
):
    if not request.confirm:
        return {"success": False, "message": "Genesis not confirmed"}
    result = await god_ai_manager.perform_genesis(db)
    return result


@router.post("/speed", dependencies=[Depends(require_admin)])
async def set_speed(request: SpeedRequest):
    """Set the world simulation speed multiplier via Redis."""
    import redis
    r = redis.from_url(settings.REDIS_URL)
    r.set("genesis:time_speed", str(request.speed))
    return {"success": True, "speed": request.speed}


@router.post("/pause", dependencies=[Depends(require_admin)])
async def set_pause(request: PauseRequest):
    """Pause or unpause the world simulation via Redis."""
    import redis
    r = redis.from_url(settings.REDIS_URL)
    r.set("genesis:is_paused", "1" if request.paused else "0")
    return {"success": True, "paused": request.paused}
