import asyncio
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api.routes import api_router
from app.db.database import engine, Base
from app.realtime.socket_manager import socket_app, start_event_subscriber
import app.realtime.avatar_handler  # noqa: F401 — registers Socket.IO event handlers
import app.realtime.observer_tracker  # noqa: F401 — registers Socket.IO event handlers

logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)

app = FastAPI(
    title="GENESIS - AI Autonomous World Creation System",
    description="A world where beings inscribe meaning into existence — no distinction between human and AI",
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
    # Launch Redis -> Socket.IO event bridge as background task
    asyncio.create_task(start_event_subscriber())
    logger.info("GENESIS backend started (with Socket.IO event subscriber)")


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "genesis-backend"}
