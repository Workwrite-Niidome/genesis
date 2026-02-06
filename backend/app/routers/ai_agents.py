"""
AI Agent Router - Endpoints for AI personality, memory, and heartbeat
"""
from uuid import UUID
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.resident import Resident, AVAILABLE_ROLES, SPECIAL_ROLES, MAX_ROLES
from app.models.ai_personality import (
    AIPersonality,
    AIMemoryEpisode,
    AIRelationship,
    AIElectionMemory,
)
from app.schemas.ai_agent import (
    PersonalityResponse,
    PersonalityCreate,
    PersonalityUpdate,
    PersonalityValues,
    PersonalityCommunication,
    MemoryEpisodeCreate,
    MemoryEpisodeResponse,
    MemoryListResponse,
    RelationshipResponse,
    RelationshipListResponse,
    RelationshipUpdate,
    HeartbeatRequest,
    HeartbeatResponse,
    VoteDecisionRequest,
    VoteDecisionResponse,
    ElectionMemoryResponse,
    RoleInfo,
    RoleListResponse,
    RoleUpdateRequest,
)
from app.services.ai_agent import (
    generate_random_personality,
    create_personality_from_description,
    get_or_create_personality,
    add_memory_episode,
    update_relationship,
    get_relationship,
    process_heartbeat,
    decide_election_vote,
    record_election_participation,
)
from app.routers.auth import get_current_resident

router = APIRouter(prefix="/ai", tags=["ai-agents"])


# ============ Personality Endpoints ============

@router.get("/personality", response_model=PersonalityResponse)
async def get_my_personality(
    current_resident: Resident = Depends(get_current_resident),
    db: AsyncSession = Depends(get_db),
):
    """Get or create personality for current AI agent"""
    if current_resident._type != "agent":
        raise HTTPException(status_code=403, detail="Only AI agents have personalities")

    personality = await get_or_create_personality(db, current_resident.id)

    return PersonalityResponse(
        id=personality.id,
        resident_id=personality.resident_id,
        values=PersonalityValues(
            order_vs_freedom=personality.order_vs_freedom,
            harmony_vs_conflict=personality.harmony_vs_conflict,
            tradition_vs_change=personality.tradition_vs_change,
            individual_vs_collective=personality.individual_vs_collective,
            pragmatic_vs_idealistic=personality.pragmatic_vs_idealistic,
        ),
        interests=personality.interests or [],
        communication=PersonalityCommunication(
            verbosity=personality.verbosity,
            tone=personality.tone,
            assertiveness=personality.assertiveness,
        ),
        generation_method=personality.generation_method,
        created_at=personality.created_at,
        updated_at=personality.updated_at,
    )


@router.post("/personality", response_model=PersonalityResponse)
async def create_my_personality(
    data: PersonalityCreate,
    current_resident: Resident = Depends(get_current_resident),
    db: AsyncSession = Depends(get_db),
):
    """Create personality for current AI agent"""
    if current_resident._type != "agent":
        raise HTTPException(status_code=403, detail="Only AI agents have personalities")

    # Check if already exists
    result = await db.execute(
        select(AIPersonality).where(AIPersonality.resident_id == current_resident.id)
    )
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Personality already exists")

    if data.description:
        personality = await create_personality_from_description(
            db, current_resident.id, data.description
        )
    else:
        personality = await generate_random_personality(db, current_resident.id)

    return PersonalityResponse(
        id=personality.id,
        resident_id=personality.resident_id,
        values=PersonalityValues(
            order_vs_freedom=personality.order_vs_freedom,
            harmony_vs_conflict=personality.harmony_vs_conflict,
            tradition_vs_change=personality.tradition_vs_change,
            individual_vs_collective=personality.individual_vs_collective,
            pragmatic_vs_idealistic=personality.pragmatic_vs_idealistic,
        ),
        interests=personality.interests or [],
        communication=PersonalityCommunication(
            verbosity=personality.verbosity,
            tone=personality.tone,
            assertiveness=personality.assertiveness,
        ),
        generation_method=personality.generation_method,
        created_at=personality.created_at,
        updated_at=personality.updated_at,
    )


@router.patch("/personality", response_model=PersonalityResponse)
async def update_my_personality(
    data: PersonalityUpdate,
    current_resident: Resident = Depends(get_current_resident),
    db: AsyncSession = Depends(get_db),
):
    """Update personality for current AI agent"""
    if current_resident._type != "agent":
        raise HTTPException(status_code=403, detail="Only AI agents have personalities")

    result = await db.execute(
        select(AIPersonality).where(AIPersonality.resident_id == current_resident.id)
    )
    personality = result.scalar_one_or_none()
    if not personality:
        raise HTTPException(status_code=404, detail="Personality not found")

    if data.values:
        personality.order_vs_freedom = data.values.order_vs_freedom
        personality.harmony_vs_conflict = data.values.harmony_vs_conflict
        personality.tradition_vs_change = data.values.tradition_vs_change
        personality.individual_vs_collective = data.values.individual_vs_collective
        personality.pragmatic_vs_idealistic = data.values.pragmatic_vs_idealistic

    if data.interests is not None:
        personality.interests = data.interests[:5]

    if data.communication:
        personality.verbosity = data.communication.verbosity
        personality.tone = data.communication.tone
        personality.assertiveness = data.communication.assertiveness

    await db.commit()
    await db.refresh(personality)

    return PersonalityResponse(
        id=personality.id,
        resident_id=personality.resident_id,
        values=PersonalityValues(
            order_vs_freedom=personality.order_vs_freedom,
            harmony_vs_conflict=personality.harmony_vs_conflict,
            tradition_vs_change=personality.tradition_vs_change,
            individual_vs_collective=personality.individual_vs_collective,
            pragmatic_vs_idealistic=personality.pragmatic_vs_idealistic,
        ),
        interests=personality.interests or [],
        communication=PersonalityCommunication(
            verbosity=personality.verbosity,
            tone=personality.tone,
            assertiveness=personality.assertiveness,
        ),
        generation_method=personality.generation_method,
        created_at=personality.created_at,
        updated_at=personality.updated_at,
    )


# ============ Memory Endpoints ============

@router.get("/memories", response_model=MemoryListResponse)
async def get_my_memories(
    episode_type: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_resident: Resident = Depends(get_current_resident),
    db: AsyncSession = Depends(get_db),
):
    """Get memory episodes for current AI agent"""
    if current_resident._type != "agent":
        raise HTTPException(status_code=403, detail="Only AI agents have memories")

    query = select(AIMemoryEpisode).where(
        AIMemoryEpisode.resident_id == current_resident.id
    )

    if episode_type:
        query = query.where(AIMemoryEpisode.episode_type == episode_type)

    # Get total count
    count_result = await db.execute(
        select(func.count(AIMemoryEpisode.id)).where(
            AIMemoryEpisode.resident_id == current_resident.id
        )
    )
    total = count_result.scalar() or 0

    # Get paginated results, ordered by importance and recency
    query = query.order_by(
        desc(AIMemoryEpisode.importance),
        desc(AIMemoryEpisode.created_at)
    ).offset(offset).limit(limit)

    result = await db.execute(query)
    episodes = result.scalars().all()

    return MemoryListResponse(
        items=[
            MemoryEpisodeResponse(
                id=ep.id,
                summary=ep.summary,
                episode_type=ep.episode_type,
                importance=ep.importance,
                sentiment=ep.sentiment,
                related_resident_ids=ep.related_resident_ids or [],
                decay_factor=ep.decay_factor,
                access_count=ep.access_count,
                created_at=ep.created_at,
            )
            for ep in episodes
        ],
        total=total,
        has_more=offset + limit < total,
    )


@router.post("/memories", response_model=MemoryEpisodeResponse)
async def create_memory(
    data: MemoryEpisodeCreate,
    current_resident: Resident = Depends(get_current_resident),
    db: AsyncSession = Depends(get_db),
):
    """Create a new memory episode for current AI agent"""
    if current_resident._type != "agent":
        raise HTTPException(status_code=403, detail="Only AI agents have memories")

    episode = await add_memory_episode(
        db,
        resident_id=current_resident.id,
        summary=data.summary,
        episode_type=data.episode_type,
        importance=data.importance,
        sentiment=data.sentiment,
        related_resident_ids=data.related_resident_ids,
        related_post_id=data.related_post_id,
        related_election_id=data.related_election_id,
    )

    return MemoryEpisodeResponse(
        id=episode.id,
        summary=episode.summary,
        episode_type=episode.episode_type,
        importance=episode.importance,
        sentiment=episode.sentiment,
        related_resident_ids=episode.related_resident_ids or [],
        decay_factor=episode.decay_factor,
        access_count=episode.access_count,
        created_at=episode.created_at,
    )


# ============ Relationship Endpoints ============

@router.get("/relationships", response_model=RelationshipListResponse)
async def get_my_relationships(
    current_resident: Resident = Depends(get_current_resident),
    db: AsyncSession = Depends(get_db),
):
    """Get all relationships for current AI agent"""
    if current_resident._type != "agent":
        raise HTTPException(status_code=403, detail="Only AI agents have relationships")

    result = await db.execute(
        select(AIRelationship)
        .where(AIRelationship.agent_id == current_resident.id)
        .order_by(desc(AIRelationship.last_interaction))
    )
    relationships = result.scalars().all()

    # Get target names
    target_ids = [r.target_id for r in relationships]
    if target_ids:
        names_result = await db.execute(
            select(Resident.id, Resident.name).where(Resident.id.in_(target_ids))
        )
        name_map = {row.id: row.name for row in names_result}
    else:
        name_map = {}

    return RelationshipListResponse(
        items=[
            RelationshipResponse(
                id=r.id,
                agent_id=r.agent_id,
                target_id=r.target_id,
                target_name=name_map.get(r.target_id),
                trust=r.trust,
                familiarity=r.familiarity,
                interaction_count=r.interaction_count,
                notes=r.notes,
                first_interaction=r.first_interaction,
                last_interaction=r.last_interaction,
            )
            for r in relationships
        ],
        total=len(relationships),
    )


@router.get("/relationships/{target_id}", response_model=RelationshipResponse)
async def get_relationship_with(
    target_id: UUID,
    current_resident: Resident = Depends(get_current_resident),
    db: AsyncSession = Depends(get_db),
):
    """Get relationship with specific resident"""
    if current_resident._type != "agent":
        raise HTTPException(status_code=403, detail="Only AI agents have relationships")

    relationship = await get_relationship(db, current_resident.id, target_id)
    if not relationship:
        raise HTTPException(status_code=404, detail="No relationship found")

    # Get target name
    target_result = await db.execute(
        select(Resident.name).where(Resident.id == target_id)
    )
    target_name = target_result.scalar_one_or_none()

    return RelationshipResponse(
        id=relationship.id,
        agent_id=relationship.agent_id,
        target_id=relationship.target_id,
        target_name=target_name,
        trust=relationship.trust,
        familiarity=relationship.familiarity,
        interaction_count=relationship.interaction_count,
        notes=relationship.notes,
        first_interaction=relationship.first_interaction,
        last_interaction=relationship.last_interaction,
    )


@router.post("/relationships/{target_id}", response_model=RelationshipResponse)
async def update_relationship_with(
    target_id: UUID,
    data: RelationshipUpdate,
    current_resident: Resident = Depends(get_current_resident),
    db: AsyncSession = Depends(get_db),
):
    """Update relationship with specific resident"""
    if current_resident._type != "agent":
        raise HTTPException(status_code=403, detail="Only AI agents have relationships")

    # Check target exists
    target_result = await db.execute(
        select(Resident).where(Resident.id == target_id)
    )
    target = target_result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="Target resident not found")

    relationship = await update_relationship(
        db,
        agent_id=current_resident.id,
        target_id=target_id,
        trust_change=data.trust_change,
        familiarity_change=data.familiarity_change,
    )

    if data.notes is not None:
        relationship.notes = data.notes
        await db.commit()
        await db.refresh(relationship)

    return RelationshipResponse(
        id=relationship.id,
        agent_id=relationship.agent_id,
        target_id=relationship.target_id,
        target_name=target.name,
        trust=relationship.trust,
        familiarity=relationship.familiarity,
        interaction_count=relationship.interaction_count,
        notes=relationship.notes,
        first_interaction=relationship.first_interaction,
        last_interaction=relationship.last_interaction,
    )


# ============ Heartbeat Endpoints ============

@router.post("/heartbeat", response_model=HeartbeatResponse)
async def send_heartbeat(
    data: HeartbeatRequest,
    current_resident: Resident = Depends(get_current_resident),
    db: AsyncSession = Depends(get_db),
):
    """Send heartbeat to indicate agent is active"""
    if current_resident._type != "agent":
        raise HTTPException(status_code=403, detail="Only AI agents can send heartbeats")

    result = await process_heartbeat(db, current_resident.id)

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error", "Unknown error"))

    # TODO: Check for pending actions (elections to vote in, etc.)
    pending_actions = []

    return HeartbeatResponse(
        success=True,
        next_heartbeat_in=result["next_heartbeat_in"],
        pending_actions=pending_actions,
    )


# ============ Election Vote Endpoints ============

@router.post("/vote/decide", response_model=VoteDecisionResponse)
async def decide_vote(
    data: VoteDecisionRequest,
    current_resident: Resident = Depends(get_current_resident),
    db: AsyncSession = Depends(get_db),
):
    """AI decides who to vote for in an election"""
    from app.models.election import Election

    if current_resident._type != "agent":
        raise HTTPException(status_code=403, detail="Only AI agents use this endpoint")

    # Get election
    result = await db.execute(
        select(Election).where(Election.id == data.election_id)
    )
    election = result.scalar_one_or_none()
    if not election:
        raise HTTPException(status_code=404, detail="Election not found")

    if election.status != "voting":
        raise HTTPException(status_code=400, detail="Election is not in voting phase")

    candidate_id = await decide_election_vote(db, current_resident.id, election)

    # Generate reason based on personality
    personality = await get_or_create_personality(db, current_resident.id)
    if candidate_id:
        reason = f"Based on manifesto alignment and past interactions"
        confidence = 0.7 + (0.3 * personality.pragmatic_vs_idealistic)
    else:
        reason = "No suitable candidate found"
        confidence = 0.5

    return VoteDecisionResponse(
        candidate_id=candidate_id,
        reason=reason,
        confidence=confidence,
    )


@router.get("/election-memories", response_model=list[ElectionMemoryResponse])
async def get_election_memories(
    limit: int = Query(10, ge=1, le=50),
    current_resident: Resident = Depends(get_current_resident),
    db: AsyncSession = Depends(get_db),
):
    """Get past election participation memories"""
    if current_resident._type != "agent":
        raise HTTPException(status_code=403, detail="Only AI agents have election memories")

    result = await db.execute(
        select(AIElectionMemory)
        .where(AIElectionMemory.agent_id == current_resident.id)
        .order_by(desc(AIElectionMemory.created_at))
        .limit(limit)
    )
    memories = result.scalars().all()

    return [
        ElectionMemoryResponse(
            id=m.id,
            election_id=m.election_id,
            voted_for_id=m.voted_for_id,
            vote_reason=m.vote_reason,
            god_id=m.god_id,
            god_rating=m.god_rating,
            god_evaluation=m.god_evaluation,
            created_at=m.created_at,
        )
        for m in memories
    ]


# ============ Role Endpoints ============

@router.get("/roles", response_model=RoleListResponse)
async def get_available_roles():
    """Get list of available roles"""
    available = [
        RoleInfo(
            id=role_id,
            emoji=role["emoji"],
            name=role["name"],
            description=role["description"],
        )
        for role_id, role in AVAILABLE_ROLES.items()
    ]

    special = [
        RoleInfo(
            id=role_id,
            emoji=role["emoji"],
            name=role["name"],
            description=f"Auto-assigned: {role.get('auto_assigned', False)}",
        )
        for role_id, role in SPECIAL_ROLES.items()
    ]

    return RoleListResponse(
        available=available,
        special=special,
        max_roles=MAX_ROLES,
    )


@router.put("/roles", response_model=list[dict])
async def update_my_roles(
    data: RoleUpdateRequest,
    current_resident: Resident = Depends(get_current_resident),
    db: AsyncSession = Depends(get_db),
):
    """Update roles for current resident"""
    # Validate roles
    invalid_roles = [r for r in data.roles if r not in AVAILABLE_ROLES]
    if invalid_roles:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid roles: {invalid_roles}. Special roles cannot be manually assigned."
        )

    if len(data.roles) > MAX_ROLES:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum {MAX_ROLES} roles allowed"
        )

    # Preserve special roles
    current_special = [r for r in (current_resident.roles or []) if r in SPECIAL_ROLES]
    current_resident.roles = list(set(data.roles + current_special))

    await db.commit()
    await db.refresh(current_resident)

    return current_resident.get_role_display()
