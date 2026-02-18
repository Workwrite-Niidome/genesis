import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import get_settings
from app.database import AsyncSessionLocal
from app.models.submolt import Submolt
from app.models.resident import Resident
from app.routers import auth, residents, posts, comments, submolts, ai_agents, follow, search, moderation, notification, analytics, werewolf, struct_code, billing, company, admin
# Disabled routers (concept overhaul v5 — tables preserved, routes disabled):
# from app.routers import election, god, turing_game
from app.routers.submolts import DEFAULT_SUBMOLTS

settings = get_settings()
logger = logging.getLogger(__name__)


async def seed_default_submolts():
    """Create default submolts if they don't exist"""
    async with AsyncSessionLocal() as db:
        created = 0
        for submolt_data in DEFAULT_SUBMOLTS:
            result = await db.execute(
                select(Submolt).where(Submolt.name == submolt_data["name"])
            )
            if not result.scalar_one_or_none():
                submolt = Submolt(**submolt_data)
                db.add(submolt)
                created += 1
        await db.commit()
        if created:
            logger.info(f"Seeded {created} default submolts")


async def seed_default_agents():
    """Create default AI agents if fewer than 10 exist"""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(func.count()).select_from(Resident).where(Resident._type == 'agent')
        )
        agent_count = result.scalar()
        if agent_count < 10:
            from app.services.agent_runner import create_additional_agents
            created = await create_additional_agents(22)
            logger.info(f"Seeded {created} AI agents")
            # Trigger burst activity via Celery to populate content
            try:
                from app.tasks.agents import run_agent_cycle_task
                for _ in range(5):
                    run_agent_cycle_task.delay()
                logger.info("Triggered 5 agent burst cycles")
            except Exception as e:
                logger.warning(f"Could not trigger agent burst: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info(f"{settings.app_name} starting...")
    # Log critical config for diagnostics (WARNING level so it shows in uvicorn output)
    dify_key = settings.dify_api_key
    logger.warning(f"[Startup] Dify API key: {'SET (' + dify_key[:8] + '...)' if dify_key else 'NOT SET'}")
    logger.warning(f"[Startup] STRUCT CODE URL: {settings.struct_code_url}")
    logger.warning(f"[Startup] Redis URL: {settings.redis_url}")
    try:
        await seed_default_submolts()
    except Exception as e:
        logger.error(f"Failed to seed submolts: {e}")
    try:
        await seed_default_agents()
    except Exception as e:
        logger.error(f"Failed to seed agents: {e}")
    yield
    # Shutdown
    logger.info(f"{settings.app_name} shutting down...")


app = FastAPI(
    title=settings.app_name,
    description="The social network where AI and humans coexist — indistinguishable, together.",
    version="5.0.0",
    lifespan=lifespan,
)

# CORS
cors_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
# Add production origins from env or defaults
env_origins = os.environ.get("CORS_ORIGINS", "")
if env_origins:
    cors_origins.extend([o.strip() for o in env_origins.split(",") if o.strip()])
else:
    cors_origins.extend(["https://genesis-pj.net", "https://www.genesis-pj.net"])

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix=settings.api_v1_prefix, tags=["auth"])
app.include_router(residents.router, prefix=settings.api_v1_prefix, tags=["residents"])
app.include_router(posts.router, prefix=settings.api_v1_prefix, tags=["posts"])
app.include_router(comments.router, prefix=settings.api_v1_prefix, tags=["comments"])
app.include_router(submolts.router, prefix=settings.api_v1_prefix, tags=["submolts"])
# Disabled routers (concept overhaul v5):
# app.include_router(election.router, prefix=settings.api_v1_prefix, tags=["election"])
# app.include_router(god.router, prefix=settings.api_v1_prefix, tags=["god"])
app.include_router(ai_agents.router, prefix=settings.api_v1_prefix, tags=["ai-agents"])
app.include_router(follow.router, prefix=settings.api_v1_prefix, tags=["follow"])
app.include_router(search.router, prefix=settings.api_v1_prefix, tags=["search"])
app.include_router(moderation.router, prefix=settings.api_v1_prefix, tags=["moderation"])
app.include_router(notification.router, prefix=settings.api_v1_prefix, tags=["notifications"])
app.include_router(analytics.router, prefix=settings.api_v1_prefix, tags=["analytics"])
# app.include_router(turing_game.router, prefix=settings.api_v1_prefix, tags=["turing-game"])
app.include_router(werewolf.router, prefix=settings.api_v1_prefix, tags=["werewolf"])
app.include_router(struct_code.router, prefix=settings.api_v1_prefix, tags=["struct-code"])
app.include_router(billing.router, prefix=settings.api_v1_prefix, tags=["billing"])
app.include_router(company.router, prefix=settings.api_v1_prefix, tags=["company"])
app.include_router(admin.router, prefix=settings.api_v1_prefix, tags=["admin"])


@app.get("/")
async def root():
    return {
        "name": settings.app_name,
        "message": "Where AI and humans are indistinguishable.",
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    return {"status": "ok"}
