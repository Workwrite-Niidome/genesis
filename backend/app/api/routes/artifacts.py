import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.artifact import Artifact

router = APIRouter()


@router.get("")
async def list_artifacts(
    artifact_type: str | None = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, le=100),
    db: AsyncSession = Depends(get_db),
):
    query = select(Artifact).order_by(
        Artifact.appreciation_count.desc(), Artifact.created_at.desc()
    )
    if artifact_type:
        query = query.where(Artifact.artifact_type == artifact_type)
    query = query.offset(offset).limit(limit)

    result = await db.execute(query)
    artifacts = result.scalars().all()
    return [
        {
            "id": str(a.id),
            "creator_id": str(a.creator_id),
            "name": a.name,
            "artifact_type": a.artifact_type,
            "description": a.description,
            "content": a.content,
            "appreciation_count": a.appreciation_count,
            "concept_id": str(a.concept_id) if a.concept_id else None,
            "tick_created": a.tick_created,
            "created_at": a.created_at.isoformat(),
        }
        for a in artifacts
    ]


@router.get("/{artifact_id}")
async def get_artifact(artifact_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Artifact).where(Artifact.id == artifact_id))
    artifact = result.scalar_one_or_none()
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")
    return {
        "id": str(artifact.id),
        "creator_id": str(artifact.creator_id),
        "name": artifact.name,
        "artifact_type": artifact.artifact_type,
        "description": artifact.description,
        "content": artifact.content,
        "appreciation_count": artifact.appreciation_count,
        "concept_id": str(artifact.concept_id) if artifact.concept_id else None,
        "tick_created": artifact.tick_created,
        "created_at": artifact.created_at.isoformat(),
    }


@router.get("/by-ai/{ai_id}")
async def get_artifacts_by_ai(
    ai_id: uuid.UUID,
    limit: int = Query(20, le=100),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Artifact)
        .where(Artifact.creator_id == ai_id)
        .order_by(Artifact.created_at.desc())
        .limit(limit)
    )
    artifacts = result.scalars().all()
    return [
        {
            "id": str(a.id),
            "name": a.name,
            "artifact_type": a.artifact_type,
            "description": a.description,
            "appreciation_count": a.appreciation_count,
            "tick_created": a.tick_created,
            "created_at": a.created_at.isoformat(),
        }
        for a in artifacts
    ]
