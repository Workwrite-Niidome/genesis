from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.core.world_engine import world_engine
from app.core.god_ai import god_ai_manager
from app.schemas.world import WorldState, WorldStats, WorldSettings, GenesisRequest

router = APIRouter()


@router.get("/state", response_model=dict)
async def get_world_state(db: AsyncSession = Depends(get_db)):
    return await world_engine.get_world_state(db)


@router.get("/stats", response_model=dict)
async def get_world_stats(db: AsyncSession = Depends(get_db)):
    return await world_engine.get_world_stats(db)


@router.post("/genesis")
async def perform_genesis(
    request: GenesisRequest,
    db: AsyncSession = Depends(get_db),
):
    if not request.confirm:
        return {"success": False, "message": "Genesis not confirmed"}
    result = await god_ai_manager.perform_genesis(db)
    return result
