from fastapi import APIRouter

from app.api.routes import world, god, ais, concepts, history

api_router = APIRouter(prefix="/api")
api_router.include_router(world.router, prefix="/world", tags=["world"])
api_router.include_router(god.router, prefix="/god", tags=["god"])
api_router.include_router(ais.router, prefix="/ais", tags=["ais"])
api_router.include_router(concepts.router, prefix="/concepts", tags=["concepts"])
api_router.include_router(history.router, prefix="/history", tags=["history"])
