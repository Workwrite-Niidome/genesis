import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api.routes import api_router
from app.db.database import engine, Base
from app.realtime.socket_manager import socket_app

logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)

app = FastAPI(
    title="GENESIS - AI Autonomous World Creation System",
    description="An experimental platform where AI autonomously creates and evolves a world",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)

# Mount Socket.IO at /ws
app.mount("/ws", socket_app)


@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("GENESIS backend started")


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "genesis-backend"}
