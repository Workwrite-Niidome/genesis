"""GENESIS v3 World Template API routes.

Provides an admin endpoint to manually trigger world template generation
and a startup hook to auto-generate when the world is empty.
"""
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import require_admin
from app.db.database import get_db
from app.models.entity import Entity
from app.world.voxel_engine import voxel_engine

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/generate-template", dependencies=[Depends(require_admin)])
async def generate_world_template(
    db: AsyncSession = Depends(get_db),
):
    """Generate the Japanese-themed world template.

    Places torii gates, stone lanterns, shrines, paths, and boundary walls.
    Idempotent: skips positions that already contain a voxel.

    Admin-only endpoint.  Returns summary with placed/skipped counts.
    """
    from app.v3.systems.world_templates import apply_template_to_world

    # Find god entity for ownership attribution
    god_result = await db.execute(
        select(Entity).where(Entity.is_god == True).limit(1)  # noqa: E712
    )
    god = god_result.scalars().first()
    placed_by = god.id if god else None

    try:
        summary = await apply_template_to_world(db, placed_by=placed_by)
        await db.commit()
    except Exception as exc:
        logger.exception("Failed to generate world template")
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Template generation failed: {str(exc)}",
        )

    return {
        "status": "success",
        "message": "World template generated successfully.",
        **summary,
    }


@router.get("/template-status")
async def get_template_status(
    db: AsyncSession = Depends(get_db),
):
    """Check whether the world template has been applied.

    Returns voxel count and whether the world is considered 'populated'.
    """
    count = await voxel_engine.count_blocks(db)

    return {
        "voxel_count": count,
        "is_populated": count >= 100,
        "threshold": 100,
    }
