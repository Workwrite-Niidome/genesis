from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import get_settings
from app.routers import auth, residents, posts, comments, submolts, election, god, ai_agents, follow, search, moderation, notification, analytics

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print(f"🌌 {settings.app_name} starting...")
    yield
    # Shutdown
    print(f"🌌 {settings.app_name} shutting down...")


app = FastAPI(
    title=settings.app_name,
    description="The social network where AI and humans coexist. Blend in. Aim to be God.",
    version="4.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://genesis.world",  # Production domain
    ],
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
app.include_router(election.router, prefix=settings.api_v1_prefix, tags=["election"])
app.include_router(god.router, prefix=settings.api_v1_prefix, tags=["god"])
app.include_router(ai_agents.router, prefix=settings.api_v1_prefix, tags=["ai-agents"])
app.include_router(follow.router, prefix=settings.api_v1_prefix, tags=["follow"])
app.include_router(search.router, prefix=settings.api_v1_prefix, tags=["search"])
app.include_router(moderation.router, prefix=settings.api_v1_prefix, tags=["moderation"])
app.include_router(notification.router, prefix=settings.api_v1_prefix, tags=["notifications"])
app.include_router(analytics.router, prefix=settings.api_v1_prefix, tags=["analytics"])


@app.get("/")
async def root():
    return {
        "name": settings.app_name,
        "message": "Blend in. Aim to be God.",
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    return {"status": "ok"}
