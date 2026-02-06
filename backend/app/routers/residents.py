from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.resident import Resident
from app.schemas.resident import ResidentResponse, ResidentPublic, ResidentUpdate
from app.routers.auth import get_current_resident, get_optional_resident

router = APIRouter(prefix="/residents")


@router.get("/me", response_model=ResidentResponse)
async def get_current_user(
    current_resident: Resident = Depends(get_current_resident),
):
    """Get current authenticated resident's full profile"""
    return current_resident


@router.patch("/me", response_model=ResidentResponse)
async def update_current_user(
    update: ResidentUpdate,
    current_resident: Resident = Depends(get_current_resident),
    db: AsyncSession = Depends(get_db),
):
    """Update current resident's profile"""
    if update.description is not None:
        current_resident.description = update.description
    if update.avatar_url is not None:
        current_resident.avatar_url = update.avatar_url

    await db.commit()
    await db.refresh(current_resident)
    return current_resident


@router.post("/me/avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    current_resident: Resident = Depends(get_current_resident),
    db: AsyncSession = Depends(get_db),
):
    """Upload avatar image (max 1MB)"""
    if file.size and file.size > 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File too large (max 1MB)",
        )

    # In production, upload to S3/Cloudflare R2 and get URL
    # For now, just store a placeholder
    avatar_url = f"https://genesis.world/avatars/{current_resident.id}"
    current_resident.avatar_url = avatar_url

    await db.commit()
    return {"success": True, "avatar_url": avatar_url}


@router.delete("/me/avatar")
async def delete_avatar(
    current_resident: Resident = Depends(get_current_resident),
    db: AsyncSession = Depends(get_db),
):
    """Delete avatar"""
    current_resident.avatar_url = None
    await db.commit()
    return {"success": True}


@router.get("/profile", response_model=ResidentPublic)
async def get_resident_by_name(
    name: str,
    db: AsyncSession = Depends(get_db),
):
    """Get public profile by name - NO type information exposed"""
    result = await db.execute(
        select(Resident).where(Resident.name == name)
    )
    resident = result.scalar_one_or_none()

    if not resident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resident not found",
        )

    return resident


@router.get("/{name}", response_model=ResidentPublic)
async def get_resident(
    name: str,
    db: AsyncSession = Depends(get_db),
):
    """Get public profile - NO type information exposed"""
    result = await db.execute(
        select(Resident).where(Resident.name == name)
    )
    resident = result.scalar_one_or_none()

    if not resident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resident not found",
        )

    return resident
