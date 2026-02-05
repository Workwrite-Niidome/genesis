"""GENESIS v3 Entity Management API routes.

Unified entity API -- AI and human entities use the same endpoints.
The world does not distinguish between AI-native, user-agent, or
human-avatar entities. Every being is simply an 'entity'.
"""
import logging
import random
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import require_admin
from app.db.database import get_db
from app.models.entity import Entity, EpisodicMemory, EntityRelationship, SemanticMemory

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class SpawnRequest(BaseModel):
    name: str | None = None
    description: str | None = None


# ---------------------------------------------------------------------------
# Helper: parse UUID from path param
# ---------------------------------------------------------------------------

def _parse_entity_id(entity_id: str) -> uuid.UUID:
    """Parse a string entity_id into a UUID, raising 400 on invalid format."""
    try:
        return uuid.UUID(entity_id)
    except (ValueError, AttributeError):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid entity ID format: '{entity_id}'. Must be a valid UUID.",
        )


# ---------------------------------------------------------------------------
# Helper: fetch entity or 404
# ---------------------------------------------------------------------------

async def _get_entity_or_404(db: AsyncSession, entity_id: uuid.UUID) -> Entity:
    """Fetch an entity by UUID, raising 404 if not found."""
    result = await db.execute(
        select(Entity).where(Entity.id == entity_id)
    )
    entity = result.scalars().first()
    if entity is None:
        raise HTTPException(
            status_code=404,
            detail=f"Entity '{entity_id}' not found.",
        )
    return entity


# ---------------------------------------------------------------------------
# Serialization helpers
# ---------------------------------------------------------------------------

def _serialize_entity(entity: Entity) -> dict:
    """Serialize an Entity to a JSON-safe dictionary."""
    return {
        "id": str(entity.id),
        "name": entity.name,
        "origin_type": entity.origin_type,
        "position": {
            "x": entity.position_x,
            "y": entity.position_y,
            "z": entity.position_z,
        },
        "facing": {
            "x": entity.facing_x,
            "z": entity.facing_z,
        },
        "personality": entity.personality,
        "state": entity.state,
        "appearance": entity.appearance,
        "is_alive": entity.is_alive,
        "is_god": entity.is_god,
        "meta_awareness": entity.meta_awareness,
        "birth_tick": entity.birth_tick,
        "death_tick": entity.death_tick,
        "created_at": entity.created_at.isoformat() if entity.created_at else None,
        "updated_at": entity.updated_at.isoformat() if entity.updated_at else None,
    }


def _serialize_entity_summary(entity: Entity) -> dict:
    """Serialize an Entity to a compact summary for list endpoints."""
    return {
        "id": str(entity.id),
        "name": entity.name,
        "origin_type": entity.origin_type,
        "position": {
            "x": entity.position_x,
            "y": entity.position_y,
            "z": entity.position_z,
        },
        "personality": entity.personality,
        "state": entity.state,
        "appearance": entity.appearance,
        "is_alive": entity.is_alive,
        "is_god": entity.is_god,
        "birth_tick": entity.birth_tick,
    }


# ---------------------------------------------------------------------------
# List / detail endpoints
# ---------------------------------------------------------------------------

@router.get("/")
async def list_entities(
    alive_only: bool = Query(True, description="If true, only return living entities"),
    limit: int = Query(100, ge=1, le=500, description="Max number of entities to return"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    db: AsyncSession = Depends(get_db),
):
    """List all entities. Returns position, personality, state, appearance."""
    query = select(Entity)

    if alive_only:
        query = query.where(Entity.is_alive == True)  # noqa: E712

    query = query.order_by(Entity.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(query)
    entities = result.scalars().all()

    # Get total count for pagination
    count_query = select(func.count()).select_from(Entity)
    if alive_only:
        count_query = count_query.where(Entity.is_alive == True)  # noqa: E712
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    return {
        "entities": [_serialize_entity_summary(e) for e in entities],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/{entity_id}")
async def get_entity(entity_id: str, db: AsyncSession = Depends(get_db)):
    """Get detailed entity info including all fields.

    Includes ``observer_count`` indicating how many observers are currently
    watching this entity.
    """
    uid = _parse_entity_id(entity_id)
    entity = await _get_entity_or_404(db, uid)

    data = _serialize_entity(entity)

    # Attach live observer count from Redis
    try:
        from app.realtime.observer_tracker import observer_tracker
        data["observer_count"] = observer_tracker.get_observer_count(str(uid))
    except Exception:
        data["observer_count"] = 0

    return data


# ---------------------------------------------------------------------------
# Memory endpoints
# ---------------------------------------------------------------------------

@router.get("/{entity_id}/memories")
async def get_entity_memories(
    entity_id: str,
    limit: int = Query(20, ge=1, le=200, description="Number of memories to return"),
    memory_type: str | None = Query(None, description="Filter by memory type"),
    db: AsyncSession = Depends(get_db),
):
    """Get entity's episodic memories, ordered by tick descending (newest first)."""
    uid = _parse_entity_id(entity_id)
    # Verify entity exists
    await _get_entity_or_404(db, uid)

    query = (
        select(EpisodicMemory)
        .where(EpisodicMemory.entity_id == uid)
        .order_by(EpisodicMemory.tick.desc())
        .limit(limit)
    )

    if memory_type is not None:
        query = query.where(EpisodicMemory.memory_type == memory_type)

    result = await db.execute(query)
    memories = result.scalars().all()

    return [
        {
            "id": str(m.id),
            "summary": m.summary,
            "importance": m.importance,
            "tick": m.tick,
            "memory_type": m.memory_type,
            "related_entity_ids": m.related_entity_ids,
            "location": {
                "x": m.location_x,
                "y": m.location_y,
                "z": m.location_z,
            } if m.location_x is not None else None,
            "ttl": m.ttl,
            "created_at": m.created_at.isoformat() if m.created_at else None,
        }
        for m in memories
    ]


# ---------------------------------------------------------------------------
# Relationship endpoints
# ---------------------------------------------------------------------------

@router.get("/{entity_id}/relationships")
async def get_entity_relationships(
    entity_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get entity's relationships with other entities.

    Returns both outgoing relationships (where entity is the source)
    and incoming relationships (where entity is the target), with the
    target/source entity names resolved.
    """
    uid = _parse_entity_id(entity_id)
    await _get_entity_or_404(db, uid)

    # Outgoing relationships
    outgoing_result = await db.execute(
        select(EntityRelationship).where(EntityRelationship.entity_id == uid)
    )
    outgoing = outgoing_result.scalars().all()

    # Incoming relationships
    incoming_result = await db.execute(
        select(EntityRelationship).where(EntityRelationship.target_id == uid)
    )
    incoming = incoming_result.scalars().all()

    # Collect all related entity IDs to resolve names in a single query
    related_ids = set()
    for rel in outgoing:
        related_ids.add(rel.target_id)
    for rel in incoming:
        related_ids.add(rel.entity_id)

    name_map: dict[uuid.UUID, str] = {}
    if related_ids:
        name_result = await db.execute(
            select(Entity.id, Entity.name).where(Entity.id.in_(related_ids))
        )
        for row in name_result.all():
            name_map[row[0]] = row[1]

    def _serialize_relationship(rel: EntityRelationship, direction: str) -> dict:
        if direction == "outgoing":
            other_id = rel.target_id
        else:
            other_id = rel.entity_id

        return {
            "id": str(rel.id),
            "direction": direction,
            "other_entity_id": str(other_id),
            "other_entity_name": name_map.get(other_id, "Unknown"),
            "trust": rel.trust,
            "familiarity": rel.familiarity,
            "respect": rel.respect,
            "fear": rel.fear,
            "rivalry": rel.rivalry,
            "gratitude": rel.gratitude,
            "anger": rel.anger,
            "debt": rel.debt,
            "alliance": rel.alliance,
            "last_interaction_tick": rel.last_interaction_tick,
            "created_at": rel.created_at.isoformat() if rel.created_at else None,
            "updated_at": rel.updated_at.isoformat() if rel.updated_at else None,
        }

    return {
        "entity_id": str(uid),
        "outgoing": [_serialize_relationship(r, "outgoing") for r in outgoing],
        "incoming": [_serialize_relationship(r, "incoming") for r in incoming],
        "total_connections": len(outgoing) + len(incoming),
    }


# ---------------------------------------------------------------------------
# Semantic knowledge endpoints
# ---------------------------------------------------------------------------

@router.get("/{entity_id}/semantic")
async def get_entity_knowledge(
    entity_id: str,
    limit: int = Query(50, ge=1, le=200, description="Number of entries to return"),
    db: AsyncSession = Depends(get_db),
):
    """Get entity's semantic knowledge -- facts, concepts, world knowledge.

    Ordered by confidence descending (most certain knowledge first).
    """
    uid = _parse_entity_id(entity_id)
    await _get_entity_or_404(db, uid)

    result = await db.execute(
        select(SemanticMemory)
        .where(SemanticMemory.entity_id == uid)
        .order_by(SemanticMemory.confidence.desc())
        .limit(limit)
    )
    entries = result.scalars().all()

    return [
        {
            "id": str(e.id),
            "key": e.key,
            "value": e.value,
            "confidence": e.confidence,
            "source_tick": e.source_tick,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        }
        for e in entries
    ]


# ---------------------------------------------------------------------------
# Spawn endpoint (admin-only)
# ---------------------------------------------------------------------------

@router.post("/spawn", dependencies=[Depends(require_admin)])
async def spawn_entity(
    request: SpawnRequest = None,
    db: AsyncSession = Depends(get_db),
):
    """Spawn a new Native AI entity with a generated or specified name.

    Generates an 18-axis personality and deep personality profile, places
    the entity at a random position near the origin, and returns the full
    entity data.
    """
    from app.agents.personality import Personality
    from app.core.name_generator import (
        NAME_POOL,
        generate_deep_personality,
    )

    # Determine name
    name = None
    if request and request.name:
        name = request.name

    if not name:
        # Pick an unused name from the pool
        used_result = await db.execute(select(Entity.name))
        used_names = set(used_result.scalars().all())
        available = [n for n in NAME_POOL if n not in used_names]
        if available:
            name = random.choice(available)
        else:
            suffix = uuid.uuid4().hex[:4].upper()
            name = f"Entity-{suffix}"

    # Check uniqueness
    existing = await db.execute(
        select(Entity).where(Entity.name == name).limit(1)
    )
    if existing.scalars().first() is not None:
        raise HTTPException(
            status_code=409,
            detail=f"An entity named '{name}' already exists.",
        )

    # Generate personality
    if request and request.description:
        try:
            personality = await Personality.from_user_description(request.description)
        except Exception as exc:
            logger.warning("LLM personality generation failed, using random: %s", exc)
            personality = Personality.generate_native()
    else:
        personality = Personality.generate_native()

    personality_dict = personality.to_dict()
    deep = generate_deep_personality()

    # Get latest tick for birth_tick
    from app.models.world import WorldEvent
    tick_result = await db.execute(select(func.max(WorldEvent.tick)))
    current_tick = tick_result.scalar() or 0

    # Random spawn position near origin
    spawn_x = random.uniform(-30.0, 30.0)
    spawn_y = 1.0  # Ground level + 1
    spawn_z = random.uniform(-30.0, 30.0)

    entity = Entity(
        name=name,
        origin_type="native",
        position_x=spawn_x,
        position_y=spawn_y,
        position_z=spawn_z,
        facing_x=random.uniform(-1.0, 1.0),
        facing_z=random.uniform(-1.0, 1.0),
        personality=personality_dict,
        state={
            "behavior_mode": "idle",
            "needs": {
                "social": 1.0,
                "exploration": 1.0,
                "creation": 1.0,
                "rest": 1.0,
            },
            "deep_personality": deep,
            "inventory": [],
        },
        appearance={
            "body_color": "#{:06x}".format(random.randint(0, 0xFFFFFF)),
            "eye_color": "#{:06x}".format(random.randint(0, 0xFFFFFF)),
            "height": round(random.uniform(0.8, 1.2), 2),
        },
        is_alive=True,
        is_god=False,
        birth_tick=current_tick,
    )

    db.add(entity)
    await db.commit()
    await db.refresh(entity)

    logger.info(
        "Spawned new entity: name=%s id=%s at (%.1f, %.1f, %.1f)",
        entity.name, entity.id, entity.position_x, entity.position_y, entity.position_z,
    )

    return {
        "status": "spawned",
        "entity": _serialize_entity(entity),
        "personality_summary": personality.describe(),
    }
