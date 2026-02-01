from fastapi import APIRouter, Depends

from app.api.auth import require_admin
from app.api.routes import world, god, ais, concepts, history, thoughts, deploy, interactions, artifacts

api_router = APIRouter(prefix="/api")
api_router.include_router(world.router, prefix="/world", tags=["world"])
api_router.include_router(
    god.router,
    prefix="/god",
    tags=["god"],
    dependencies=[Depends(require_admin)],
)
api_router.include_router(ais.router, prefix="/ais", tags=["ais"])
api_router.include_router(concepts.router, prefix="/concepts", tags=["concepts"])
api_router.include_router(history.router, prefix="/history", tags=["history"])
api_router.include_router(thoughts.router, prefix="/thoughts", tags=["thoughts"])
api_router.include_router(deploy.router, prefix="/deploy", tags=["deploy"])
api_router.include_router(interactions.router, prefix="/interactions", tags=["interactions"])
api_router.include_router(artifacts.router, prefix="/artifacts", tags=["artifacts"])
