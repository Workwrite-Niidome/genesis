import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.concept import Concept

router = APIRouter()


@router.get("")
async def list_concepts(
    offset: int = Query(0, ge=0),
    limit: int = Query(50, le=100),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Concept).order_by(Concept.created_at.desc()).offset(offset).limit(limit)
    )
    concepts = result.scalars().all()
    return [
        {
            "id": str(c.id),
            "creator_id": str(c.creator_id) if c.creator_id else None,
            "name": c.name,
            "definition": c.definition,
            "effects": c.effects,
            "adoption_count": c.adoption_count,
            "tick_created": c.tick_created,
            "created_at": c.created_at.isoformat(),
        }
        for c in concepts
    ]


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
        "definition": concept.definition,
        "effects": concept.effects,
        "adoption_count": concept.adoption_count,
        "tick_created": concept.tick_created,
        "created_at": concept.created_at.isoformat(),
    }
