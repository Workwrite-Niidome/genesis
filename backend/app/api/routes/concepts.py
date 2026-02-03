import uuid
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.ai import AI
from app.models.concept import Concept

router = APIRouter()


@router.get("")
async def list_concepts(
    offset: int = Query(0, ge=0),
    limit: int = Query(50, le=100),
    category: str | None = Query(None),
    creator_id: uuid.UUID | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    query = select(Concept).order_by(Concept.created_at.desc())
    if category:
        query = query.where(Concept.category == category)
    if creator_id:
        query = query.where(Concept.creator_id == creator_id)
    query = query.offset(offset).limit(limit)

    result = await db.execute(query)
    concepts = result.scalars().all()

    # Batch fetch creator names
    creator_ids = [c.creator_id for c in concepts if c.creator_id]
    creator_names = {}
    if creator_ids:
        ai_result = await db.execute(select(AI.id, AI.name).where(AI.id.in_(creator_ids)))
        creator_names = {row[0]: row[1] for row in ai_result.all()}

    return [
        {
            "id": str(c.id),
            "creator_id": str(c.creator_id) if c.creator_id else None,
            "creator_name": creator_names.get(c.creator_id) if c.creator_id else None,
            "name": c.name,
            "category": c.category,
            "definition": c.definition,
            "effects": c.effects,
            "adoption_count": c.adoption_count,
            "tick_created": c.tick_created,
            "created_at": c.created_at.isoformat(),
        }
        for c in concepts
    ]


@router.get("/graph")
async def get_concept_graph(db: AsyncSession = Depends(get_db)):
    """Return concept nodes and co-adoption edges for graph visualization."""
    # Get all concepts
    result = await db.execute(select(Concept).order_by(Concept.adoption_count.desc()).limit(100))
    concepts = list(result.scalars().all())

    if not concepts:
        return {"nodes": [], "edges": []}

    concept_ids = {str(c.id) for c in concepts}

    nodes = [
        {
            "id": str(c.id),
            "name": c.name,
            "category": c.category,
            "adoption_count": c.adoption_count,
            "definition": c.definition,
        }
        for c in concepts
    ]

    # Build co-adoption edges: concepts adopted by the same AI
    # Get all alive AIs and their adopted concepts
    ai_result = await db.execute(select(AI).where(AI.is_alive == True))
    ais = list(ai_result.scalars().all())

    edge_weights: dict[tuple[str, str], int] = defaultdict(int)
    for ai in ais:
        adopted = ai.state.get("adopted_concepts", [])
        # Filter to concepts that exist in our node set
        adopted = [cid for cid in adopted if cid in concept_ids]
        # Generate all pairs
        for i in range(len(adopted)):
            for j in range(i + 1, len(adopted)):
                a, b = adopted[i], adopted[j]
                key = (min(a, b), max(a, b))
                edge_weights[key] += 1

    edges = [
        {"source": src, "target": tgt, "weight": w}
        for (src, tgt), w in edge_weights.items()
    ]

    return {"nodes": nodes, "edges": edges}


@router.get("/{concept_id}/members")
async def get_concept_members(concept_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Return all AIs that belong to this organization concept."""
    # Verify concept exists
    concept_result = await db.execute(select(Concept).where(Concept.id == concept_id))
    concept = concept_result.scalar_one_or_none()
    if not concept:
        raise HTTPException(status_code=404, detail="Concept not found")

    # Scan all AIs (alive + dead) for membership
    ai_result = await db.execute(select(AI))
    ais = list(ai_result.scalars().all())

    members = []
    concept_id_str = str(concept_id)
    for ai in ais:
        orgs = ai.state.get("organizations", [])
        for org in orgs:
            if org.get("id") == concept_id_str:
                members.append({
                    "id": str(ai.id),
                    "name": ai.name,
                    "role": org.get("role", "member"),
                    "is_alive": ai.is_alive,
                    "personality_traits": ai.personality_traits or [],
                    "appearance": ai.appearance or {},
                })
                break

    return members


@router.get("/{concept_id}")
async def get_concept(concept_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Concept).where(Concept.id == concept_id))
    concept = result.scalar_one_or_none()
    if not concept:
        raise HTTPException(status_code=404, detail="Concept not found")
    return {
        "id": str(concept.id),
        "creator_id": str(concept.creator_id) if concept.creator_id else None,
        "name": concept.name,
        "category": concept.category,
        "definition": concept.definition,
        "effects": concept.effects,
        "adoption_count": concept.adoption_count,
        "tick_created": concept.tick_created,
        "created_at": concept.created_at.isoformat(),
    }
