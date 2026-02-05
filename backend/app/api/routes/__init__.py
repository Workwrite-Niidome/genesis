from fastapi import APIRouter, Depends

from app.api.auth import require_admin
from app.api.routes import world, god, ais, concepts, history, thoughts, deploy, interactions, artifacts, observers, board, saga
from app.api.routes import world_v3, entities, building, agents, avatar, history_v3
from app.api.routes import auth_oauth

api_router = APIRouter(prefix="/api")

# --- Auth routes ---
api_router.include_router(auth_oauth.router, tags=["auth"])

# --- v2 routes (backward-compatible) ---
api_router.include_router(world.router, prefix="/world", tags=["world"])
api_router.include_router(
    god.router,
    prefix="/god",
    tags=["god"],
    dependencies=[Depends(require_admin)],
)
api_router.include_router(
    god.public_router,
    prefix="/god-dialogue",
    tags=["god-dialogue"],
)
api_router.include_router(ais.router, prefix="/ais", tags=["ais"])
api_router.include_router(concepts.router, prefix="/concepts", tags=["concepts"])
api_router.include_router(history.router, prefix="/history", tags=["history"])
api_router.include_router(thoughts.router, prefix="/thoughts", tags=["thoughts"])
api_router.include_router(deploy.router, prefix="/deploy", tags=["deploy"])
api_router.include_router(interactions.router, prefix="/interactions", tags=["interactions"])
api_router.include_router(artifacts.router, prefix="/artifacts", tags=["artifacts"])
api_router.include_router(observers.router, prefix="/observers", tags=["observers"])
api_router.include_router(board.router, prefix="/board", tags=["board"])
api_router.include_router(saga.router, prefix="/saga", tags=["saga"])

# --- v3 routes ---
api_router.include_router(world_v3.router, prefix="/v3/world", tags=["v3-world"])
api_router.include_router(entities.router, prefix="/v3/entities", tags=["v3-entities"])
api_router.include_router(building.router, prefix="/v3/building", tags=["v3-building"])
api_router.include_router(agents.router, prefix="/v3/agents", tags=["v3-agents"])
api_router.include_router(avatar.router, prefix="/v3/avatar", tags=["v3-avatar"])
api_router.include_router(history_v3.router, prefix="/v3/world/history", tags=["v3-history"])
