"""GENESIS v3 User Agent API — create, manage, and monitor your AI agents.

External users can send AI agents into the world through this API.
Each agent is an Entity with origin_type='user_agent' and owner_user_id
linked to the authenticated observer.

The world does not distinguish between native and user-agent entities.
"""
import logging
import random
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_observer
from app.config import settings
from app.db.database import get_db
from app.models.entity import Entity, EpisodicMemory, EntityRelationship
from app.models.observer import Observer

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class CreateAgentRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Agent display name")
    description: str = Field(
        ...,
        min_length=10,
        max_length=2000,
        description="Personality description in natural language",
    )
    initial_goal: str = Field(
        "",
        max_length=1000,
        description="Optional initial goal for the agent",
    )
    autonomy_level: str = Field(
        "autonomous",
        description="'autonomous', 'guided', or 'semi_autonomous'",
    )
    appearance: dict = Field(default_factory=dict, description="Optional avatar customization")


class UpdatePolicyRequest(BaseModel):
    policy_text: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Policy/direction text for the agent",
    )


class PersonalityPreviewRequest(BaseModel):
    description: str = Field(
        ...,
        min_length=10,
        max_length=2000,
        description="Personality description in natural language",
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_agent_id(agent_id: str) -> uuid.UUID:
    try:
        return uuid.UUID(agent_id)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail=f"Invalid agent ID: '{agent_id}'")


async def _get_user_agent_or_404(
    db: AsyncSession, agent_id: uuid.UUID, observer: Observer
) -> Entity:
    """Fetch a user-owned agent, ensuring ownership."""
    result = await db.execute(
        select(Entity).where(
            Entity.id == agent_id,
            Entity.origin_type == "user_agent",
            Entity.owner_user_id == observer.id,
        )
    )
    entity = result.scalars().first()
    if entity is None:
        raise HTTPException(
            status_code=404,
            detail=f"Agent '{agent_id}' not found or not owned by you.",
        )
    return entity


async def _count_user_agents(db: AsyncSession, observer_id: uuid.UUID) -> int:
    result = await db.execute(
        select(func.count()).select_from(Entity).where(
            Entity.owner_user_id == observer_id,
            Entity.origin_type == "user_agent",
            Entity.is_alive == True,  # noqa: E712
        )
    )
    return result.scalar() or 0


async def _get_current_tick(db: AsyncSession) -> int:
    from app.models.world import WorldEvent
    result = await db.execute(select(func.max(WorldEvent.tick)))
    return result.scalar() or 0


def _get_max_agents(observer: Observer) -> int:
    role = observer.role or "user"
    if role == "premium":
        return settings.MAX_AGENTS_PER_USER_PREMIUM
    return settings.MAX_AGENTS_PER_USER_FREE


def _serialize_agent(entity: Entity) -> dict:
    """Serialize an agent entity for the user dashboard."""
    state = entity.state or {}
    needs = state.get("needs", {})
    policy = entity.agent_policy or {}

    # Derive status string for frontend
    if not entity.is_alive:
        if policy.get("recalled"):
            status = "recalled"
        else:
            status = "dead"
    else:
        status = "alive"

    return {
        "id": str(entity.id),
        "name": entity.name,
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
        "appearance": entity.appearance,
        "is_alive": entity.is_alive,
        "status": status,
        "meta_awareness": entity.meta_awareness,
        "birth_tick": entity.birth_tick,
        "death_tick": entity.death_tick,
        "behavior_mode": state.get("behavior_mode", "normal"),
        "autonomy_level": policy.get("autonomy_level", "autonomous"),
        "needs": needs,
        "policy": policy,
        "description": policy.get("current_directive", ""),
        "created_at": entity.created_at.isoformat() if entity.created_at else None,
        "updated_at": entity.updated_at.isoformat() if entity.updated_at else None,
    }


# ---------------------------------------------------------------------------
# Preview personality (no agent creation)
# ---------------------------------------------------------------------------

@router.post("/preview-personality")
async def preview_personality(
    request: PersonalityPreviewRequest,
    observer: Observer = Depends(get_current_observer),
):
    """Convert a text description into 18-axis personality values (preview only).

    Does not create an agent. Use this to show the user what their description
    maps to before confirming.
    """
    from app.agents.personality import Personality

    try:
        personality = await Personality.from_user_description(request.description)
    except Exception as exc:
        logger.warning("Personality preview LLM call failed: %s", exc)
        raise HTTPException(
            status_code=500,
            detail="Personality generation failed. Try again or simplify the description.",
        )

    return {
        "personality": personality.to_dict(),
        "summary": personality.describe(),
        "top_traits": personality.top_traits(n=5),
    }


# ---------------------------------------------------------------------------
# Create agent
# ---------------------------------------------------------------------------

@router.post("/")
async def create_agent(
    request: CreateAgentRequest,
    observer: Observer = Depends(get_current_observer),
    db: AsyncSession = Depends(get_db),
):
    """Create a new AI agent and spawn it into the world.

    The agent will begin acting autonomously in the next tick cycle.
    It appears in the world as a regular entity — indistinguishable
    from native AI.
    """
    from app.agents.personality import Personality
    from app.core.name_generator import generate_deep_personality

    # Check agent limit
    current_count = await _count_user_agents(db, observer.id)
    max_agents = _get_max_agents(observer)
    if current_count >= max_agents:
        raise HTTPException(
            status_code=403,
            detail=f"Agent limit reached ({current_count}/{max_agents}). "
                   "Upgrade to premium for more agents.",
        )

    # Check name uniqueness
    existing = await db.execute(
        select(Entity).where(Entity.name == request.name).limit(1)
    )
    if existing.scalars().first() is not None:
        raise HTTPException(
            status_code=409,
            detail=f"Name '{request.name}' is already taken.",
        )

    # Validate autonomy level
    valid_levels = ("autonomous", "guided", "semi_autonomous")
    if request.autonomy_level not in valid_levels:
        raise HTTPException(
            status_code=400,
            detail=f"autonomy_level must be one of: {valid_levels}",
        )

    # Generate personality from description via LLM
    try:
        personality = await Personality.from_user_description(request.description)
    except Exception as exc:
        logger.warning("LLM personality generation failed, using random: %s", exc)
        personality = Personality.generate_native()

    personality_dict = personality.to_dict()
    deep = generate_deep_personality()

    current_tick = await _get_current_tick(db)

    # Random spawn position
    spawn_x = random.uniform(-50.0, 50.0)
    spawn_y = 1.0
    spawn_z = random.uniform(-50.0, 50.0)

    # Build appearance
    appearance = request.appearance or {}
    if "body_color" not in appearance:
        appearance["body_color"] = "#{:06x}".format(random.randint(0, 0xFFFFFF))
    if "eye_color" not in appearance:
        appearance["eye_color"] = "#{:06x}".format(random.randint(0, 0xFFFFFF))
    if "height" not in appearance:
        appearance["height"] = round(random.uniform(0.8, 1.2), 2)

    # Build agent policy
    agent_policy = {
        "autonomy_level": request.autonomy_level,
        "initial_goal": request.initial_goal or "",
        "current_directive": request.initial_goal or "",
        "created_by": str(observer.id),
        "created_by_name": observer.username,
    }

    entity = Entity(
        name=request.name,
        origin_type="user_agent",
        owner_user_id=observer.id,
        position_x=spawn_x,
        position_y=spawn_y,
        position_z=spawn_z,
        facing_x=random.uniform(-1.0, 1.0),
        facing_z=random.uniform(-1.0, 1.0),
        personality=personality_dict,
        state={
            "behavior_mode": "normal",
            "needs": {
                "curiosity": 50.0,
                "social": 40.0,
                "creation": 30.0,
                "dominance": 20.0,
                "safety": 30.0,
                "expression": 40.0,
                "understanding": 40.0,
                "evolution_pressure": 10.0,
            },
            "deep_personality": deep,
            "inventory": [],
            "last_conversation_ticks": {},
            "visited_positions": [],
        },
        appearance=appearance,
        agent_policy=agent_policy,
        is_alive=True,
        is_god=False,
        birth_tick=current_tick,
    )

    db.add(entity)
    await db.commit()
    await db.refresh(entity)

    logger.info(
        "User %s created agent: name=%s id=%s",
        observer.username, entity.name, entity.id,
    )

    return {
        "status": "created",
        "agent": _serialize_agent(entity),
        "personality_summary": personality.describe(),
        "message": f"Agent '{entity.name}' has entered the world.",
    }


# ---------------------------------------------------------------------------
# List my agents
# ---------------------------------------------------------------------------

@router.get("/")
async def list_my_agents(
    include_dead: bool = Query(False, description="Include dead agents"),
    observer: Observer = Depends(get_current_observer),
    db: AsyncSession = Depends(get_db),
):
    """List all agents owned by the authenticated user."""
    query = select(Entity).where(
        Entity.owner_user_id == observer.id,
        Entity.origin_type == "user_agent",
    )

    if not include_dead:
        query = query.where(Entity.is_alive == True)  # noqa: E712

    query = query.order_by(Entity.created_at.desc())
    result = await db.execute(query)
    agents = result.scalars().all()

    max_agents = _get_max_agents(observer)

    return {
        "agents": [_serialize_agent(a) for a in agents],
        "count": len(agents),
        "max_agents": max_agents,
    }


# ---------------------------------------------------------------------------
# Get agent details
# ---------------------------------------------------------------------------

@router.get("/{agent_id}")
async def get_agent_detail(
    agent_id: str,
    observer: Observer = Depends(get_current_observer),
    db: AsyncSession = Depends(get_db),
):
    """Get detailed info for a specific agent including memories and relationships."""
    uid = _parse_agent_id(agent_id)
    entity = await _get_user_agent_or_404(db, uid, observer)

    # Fetch recent memories
    mem_result = await db.execute(
        select(EpisodicMemory)
        .where(EpisodicMemory.entity_id == uid)
        .order_by(EpisodicMemory.tick.desc())
        .limit(20)
    )
    memories = mem_result.scalars().all()

    # Fetch relationships
    rel_result = await db.execute(
        select(EntityRelationship)
        .where(EntityRelationship.entity_id == uid)
        .order_by(EntityRelationship.last_interaction_tick.desc())
    )
    relationships = rel_result.scalars().all()

    # Resolve relationship target names
    target_ids = [r.target_id for r in relationships]
    name_map: dict[uuid.UUID, str] = {}
    if target_ids:
        names = await db.execute(
            select(Entity.id, Entity.name).where(Entity.id.in_(target_ids))
        )
        for row in names.all():
            name_map[row[0]] = row[1]

    # Fetch recent world events for this agent
    from app.models.world import WorldEvent
    events_result = await db.execute(
        select(WorldEvent)
        .where(WorldEvent.actor_id == uid)
        .order_by(WorldEvent.tick.desc())
        .limit(30)
    )
    events = events_result.scalars().all()

    return {
        "agent": _serialize_agent(entity),
        "personality_summary": _describe_personality(entity.personality),
        "memories": [
            {
                "id": str(m.id),
                "summary": m.summary,
                "importance": m.importance,
                "tick": m.tick,
                "memory_type": m.memory_type,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in memories
        ],
        "relationships": [
            {
                "target_id": str(r.target_id),
                "target_name": name_map.get(r.target_id, "Unknown"),
                "trust": r.trust,
                "familiarity": r.familiarity,
                "respect": r.respect,
                "fear": r.fear,
                "rivalry": r.rivalry,
                "anger": r.anger,
                "alliance": r.alliance,
            }
            for r in relationships
        ],
        "recent_events": [
            {
                "tick": e.tick,
                "event_type": e.event_type,
                "action": e.action,
                "result": e.result,
                "reason": e.reason,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in events
        ],
    }


def _describe_personality(personality_dict: dict) -> str:
    """Generate a human-readable personality summary from dict."""
    from app.agents.personality import Personality
    try:
        p = Personality.from_dict(personality_dict)
        return p.describe()
    except Exception:
        return "Unknown personality"


# ---------------------------------------------------------------------------
# Update agent policy
# ---------------------------------------------------------------------------

@router.put("/{agent_id}/policy")
async def update_agent_policy(
    agent_id: str,
    request: UpdatePolicyRequest,
    observer: Observer = Depends(get_current_observer),
    db: AsyncSession = Depends(get_db),
):
    """Update the policy/direction for an agent.

    The policy is advisory — the agent interprets it through its personality
    filter. You cannot force an agent to act against its personality.
    """
    uid = _parse_agent_id(agent_id)
    entity = await _get_user_agent_or_404(db, uid, observer)

    if not entity.is_alive:
        raise HTTPException(status_code=409, detail="Cannot update policy for a dead agent.")

    # Check autonomy level
    policy = entity.agent_policy or {}
    autonomy = policy.get("autonomy_level", "autonomous")
    if autonomy == "autonomous":
        raise HTTPException(
            status_code=403,
            detail="This agent is fully autonomous. Policy updates are disabled. "
                   "Create a new agent with 'guided' or 'semi_autonomous' to send directions.",
        )

    # Update policy
    policy["current_directive"] = request.policy_text
    policy["directive_updated_at"] = str(entity.updated_at or "")
    entity.agent_policy = policy

    await db.commit()
    await db.refresh(entity)

    logger.info(
        "User %s updated policy for agent %s: %s",
        observer.username, entity.name, request.policy_text[:100],
    )

    return {
        "status": "updated",
        "agent_id": str(entity.id),
        "agent_name": entity.name,
        "new_policy": request.policy_text,
        "message": f"Policy updated for '{entity.name}'. "
                   "The agent will interpret this through its personality.",
    }


# ---------------------------------------------------------------------------
# Recall (kill) agent
# ---------------------------------------------------------------------------

@router.delete("/{agent_id}")
async def recall_agent(
    agent_id: str,
    observer: Observer = Depends(get_current_observer),
    db: AsyncSession = Depends(get_db),
):
    """Recall (remove) an agent from the world.

    The agent dies gracefully. Its memories and relationships remain in the
    world's history but it stops acting.
    """
    uid = _parse_agent_id(agent_id)
    entity = await _get_user_agent_or_404(db, uid, observer)

    if not entity.is_alive:
        raise HTTPException(status_code=409, detail="Agent is already dead.")

    current_tick = await _get_current_tick(db)

    entity.is_alive = False
    entity.death_tick = current_tick

    # Mark as recalled in policy
    policy = dict(entity.agent_policy or {})
    policy["recalled"] = True
    entity.agent_policy = policy

    # Log recall event
    from app.world.event_log import event_log
    await event_log.append(
        db=db,
        tick=current_tick,
        actor_id=entity.id,
        event_type="agent_recall",
        action="recalled",
        params={"recalled_by": str(observer.id)},
        result="accepted",
        reason="user_recall",
        position=(entity.position_x, entity.position_y, entity.position_z),
        importance=0.6,
    )

    await db.commit()

    logger.info(
        "User %s recalled agent %s (id=%s)",
        observer.username, entity.name, entity.id,
    )

    return {
        "status": "recalled",
        "agent_id": str(entity.id),
        "agent_name": entity.name,
        "message": f"Agent '{entity.name}' has been recalled from the world.",
    }
