"""GENESIS v3 Avatar API — create and manage human avatar entities.

Humans enter the world by creating an avatar entity, then connecting
via WebSocket for real-time interaction. The avatar is an Entity with
origin_type='human_avatar' — indistinguishable from AI in the world.
"""
import logging
import random
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_observer
from app.db.database import get_db
from app.models.entity import Entity
from app.models.observer import Observer

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class CreateAvatarRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    appearance: dict = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _get_current_tick(db: AsyncSession) -> int:
    from app.models.world import WorldEvent
    result = await db.execute(select(func.max(WorldEvent.tick)))
    return result.scalar() or 0


# ---------------------------------------------------------------------------
# Create avatar (one-time setup before WebSocket join)
# ---------------------------------------------------------------------------

@router.post("/create")
async def create_avatar(
    request: CreateAvatarRequest,
    observer: Observer = Depends(get_current_observer),
    db: AsyncSession = Depends(get_db),
):
    """Create a human avatar entity in the world.

    The avatar is a regular Entity with origin_type='human_avatar'.
    After creation, the client connects via WebSocket and sends
    'avatar_join' with the entity_id to start playing.

    Each observer can have at most one active avatar.
    """
    # Check for existing alive avatar
    existing = await db.execute(
        select(Entity).where(
            Entity.owner_user_id == observer.id,
            Entity.origin_type == "human_avatar",
            Entity.is_alive == True,  # noqa: E712
        ).limit(1)
    )
    existing_avatar = existing.scalars().first()
    if existing_avatar is not None:
        # Return existing avatar instead of creating a new one
        return {
            "status": "exists",
            "entity_id": str(existing_avatar.id),
            "name": existing_avatar.name,
            "message": "You already have an active avatar. Connect via WebSocket.",
        }

    # Check name uniqueness
    name_check = await db.execute(
        select(Entity).where(Entity.name == request.name).limit(1)
    )
    if name_check.scalars().first() is not None:
        raise HTTPException(status_code=409, detail=f"Name '{request.name}' is already taken.")

    current_tick = await _get_current_tick(db)

    # Build appearance
    appearance = request.appearance or {}
    if "body_color" not in appearance:
        appearance["body_color"] = "#{:06x}".format(random.randint(0, 0xFFFFFF))
    if "eye_color" not in appearance:
        appearance["eye_color"] = "#{:06x}".format(random.randint(0, 0xFFFFFF))
    if "height" not in appearance:
        appearance["height"] = 1.0

    # Human avatars get a neutral personality (the human IS the personality)
    personality = {
        "order_vs_chaos": 0.5,
        "cooperation_vs_competition": 0.5,
        "curiosity": 0.5,
        "aggression": 0.3,
        "empathy": 0.5,
        "creativity": 0.5,
        "self_preservation": 0.5,
        "ambition": 0.5,
        "honesty": 0.5,
        "loyalty": 0.5,
        "patience": 0.5,
        "humor": 0.5,
        "verbosity": 0.5,
        "politeness": 0.5,
        "risk_taking": 0.5,
        "leadership": 0.5,
        "aesthetic_sense": 0.5,
        "planning_horizon": 0.5,
    }

    # Spawn position
    spawn_x = random.uniform(-30.0, 30.0)
    spawn_z = random.uniform(-30.0, 30.0)

    entity = Entity(
        name=request.name,
        origin_type="human_avatar",
        owner_user_id=observer.id,
        position_x=spawn_x,
        position_y=1.0,
        position_z=spawn_z,
        facing_x=0.0,
        facing_z=1.0,
        personality=personality,
        state={
            "behavior_mode": "normal",
            "needs": {},
            "inventory": [],
            "is_human_controlled": True,
        },
        appearance=appearance,
        is_alive=True,
        is_god=False,
        birth_tick=current_tick,
    )

    db.add(entity)
    await db.commit()
    await db.refresh(entity)

    logger.info("Avatar created: %s (observer=%s)", entity.name, observer.username)

    return {
        "status": "created",
        "entity_id": str(entity.id),
        "name": entity.name,
        "position": {
            "x": entity.position_x,
            "y": entity.position_y,
            "z": entity.position_z,
        },
        "message": "Avatar created. Connect via WebSocket and send 'avatar_join'.",
    }


# ---------------------------------------------------------------------------
# Get my avatar
# ---------------------------------------------------------------------------

@router.get("/me")
async def get_my_avatar(
    observer: Observer = Depends(get_current_observer),
    db: AsyncSession = Depends(get_db),
):
    """Get the current observer's avatar, if any."""
    result = await db.execute(
        select(Entity).where(
            Entity.owner_user_id == observer.id,
            Entity.origin_type == "human_avatar",
            Entity.is_alive == True,  # noqa: E712
        ).limit(1)
    )
    entity = result.scalars().first()

    if entity is None:
        return {"has_avatar": False, "avatar": None}

    return {
        "has_avatar": True,
        "avatar": {
            "entity_id": str(entity.id),
            "name": entity.name,
            "position": {
                "x": entity.position_x,
                "y": entity.position_y,
                "z": entity.position_z,
            },
            "appearance": entity.appearance,
            "created_at": entity.created_at.isoformat() if entity.created_at else None,
        },
    }


# ---------------------------------------------------------------------------
# Leave / destroy avatar
# ---------------------------------------------------------------------------

@router.post("/leave")
async def leave_world(
    observer: Observer = Depends(get_current_observer),
    db: AsyncSession = Depends(get_db),
):
    """Remove the observer's avatar from the world.

    The entity is killed gracefully. It can be recreated later.
    """
    result = await db.execute(
        select(Entity).where(
            Entity.owner_user_id == observer.id,
            Entity.origin_type == "human_avatar",
            Entity.is_alive == True,  # noqa: E712
        ).limit(1)
    )
    entity = result.scalars().first()

    if entity is None:
        raise HTTPException(status_code=404, detail="No active avatar found.")

    current_tick = await _get_current_tick(db)

    entity.is_alive = False
    entity.death_tick = current_tick

    await db.commit()

    logger.info("Avatar left: %s (observer=%s)", entity.name, observer.username)

    return {
        "status": "left",
        "entity_id": str(entity.id),
        "name": entity.name,
        "message": f"Avatar '{entity.name}' has left the world.",
    }
