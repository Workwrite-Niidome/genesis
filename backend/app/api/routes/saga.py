from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.core.saga_service import saga_service

router = APIRouter()


@router.get("/chapters")
async def list_chapters(
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
):
    """Get all saga chapters ordered by era descending."""
    return await saga_service.get_chapters(db, limit=limit)


@router.get("/latest")
async def get_latest(
    db: AsyncSession = Depends(get_db),
):
    """Get the most recent saga chapter."""
    chapter = await saga_service.get_latest_chapter(db)
    if chapter is None:
        return {"chapter": None}
    return chapter


@router.get("/chapters/{era_number}")
async def get_chapter(
    era_number: int,
    db: AsyncSession = Depends(get_db),
):
    """Get a specific chapter by era number."""
    chapter = await saga_service.get_chapter_by_era(db, era_number)
    if chapter is None:
        return {"error": "Chapter not found"}
    return chapter
