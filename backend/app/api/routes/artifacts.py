import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.artifact import Artifact
from app.core.artifact_helpers import normalize_artifact_type, generate_fallback_content

logger = logging.getLogger(__name__)

router = APIRouter()


def _enrich_artifact(a: Artifact, creator_name: str | None = None) -> dict | None:
    """Normalize type and ensure content is renderable for any artifact.

    Returns None if the artifact cannot be serialized (instead of crashing the
    entire list response).
    """
    try:
        artifact_type = normalize_artifact_type(a.artifact_type or "")
        content = a.content
        if not isinstance(content, dict) or not content:
            content = generate_fallback_content(
                artifact_type, a.name or "", str(a.creator_id), a.description or ""
            )
        return {
            "id": str(a.id),
            "creator_id": str(a.creator_id),
            "creator_name": creator_name,
            "name": a.name or "",
            "artifact_type": artifact_type,
            "description": a.description or "",
            "content": content,
            "appreciation_count": a.appreciation_count or 0,
            "concept_id": str(a.concept_id) if a.concept_id else None,
            "tick_created": a.tick_created or 0,
            "created_at": a.created_at.isoformat() if a.created_at else "",
        }
    except Exception as e:
        logger.warning(f"Failed to enrich artifact {getattr(a, 'id', '?')}: {e}")
        return None


@router.get("")
async def list_artifacts(
    artifact_type: str | None = Query(None),
    creator_id: uuid.UUID | None = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, le=100),
    db: AsyncSession = Depends(get_db),
):
    from app.models.ai import AI

    query = select(Artifact).order_by(
        Artifact.appreciation_count.desc(), Artifact.created_at.desc()
    )
    if artifact_type:
        query = query.where(Artifact.artifact_type == artifact_type)
    if creator_id:
        query = query.where(Artifact.creator_id == creator_id)
    query = query.offset(offset).limit(limit)

    result = await db.execute(query)
    artifacts = list(result.scalars().all())

    # Batch fetch creator names
    creator_ids = [a.creator_id for a in artifacts]
    creator_names = {}
    if creator_ids:
        ai_result = await db.execute(select(AI.id, AI.name).where(AI.id.in_(creator_ids)))
        creator_names = {row[0]: row[1] for row in ai_result.all()}

    return [
        e for a in artifacts
        if (e := _enrich_artifact(a, creator_names.get(a.creator_id))) is not None
    ]


@router.get("/{artifact_id}")
async def get_artifact(artifact_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Artifact).where(Artifact.id == artifact_id))
    artifact = result.scalar_one_or_none()
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")
    return _enrich_artifact(artifact)


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
    return [e for a in artifacts if (e := _enrich_artifact(a)) is not None]
