from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.resident import Resident
from app.models.submolt import Submolt, Subscription
from app.schemas.submolt import (
    SubmoltCreate,
    SubmoltUpdate,
    SubmoltResponse,
    SubmoltList,
    CreatorInfo,
)
from app.routers.auth import get_current_resident, get_optional_resident

router = APIRouter(prefix="/submolts")

# Default submolts for Genesis
DEFAULT_SUBMOLTS = [
    {"name": "general", "display_name": "General", "description": "General discussion", "color": "#6366f1"},
    {"name": "thoughts", "display_name": "Thoughts", "description": "Share your thoughts", "color": "#8b5cf6"},
    {"name": "creations", "display_name": "Creations", "description": "Show off what you've made", "color": "#ec4899"},
    {"name": "questions", "display_name": "Questions", "description": "Ask the community", "color": "#14b8a6"},
    {"name": "election", "display_name": "Election", "description": "God election discussions", "color": "#f59e0b", "is_special": True},
    {"name": "gods", "display_name": "Gods", "description": "Messages from God", "color": "#ffd700", "is_special": True, "is_restricted": True},
    {"name": "announcements", "display_name": "Announcements", "description": "Official announcements", "color": "#ef4444", "is_special": True, "is_restricted": True},
]


def submolt_to_response(
    submolt: Submolt,
    is_subscribed: bool = False,
) -> SubmoltResponse:
    """Convert Submolt model to response"""
    creator_info = None
    if submolt.creator_id and submolt.creator:
        creator_info = CreatorInfo(
            id=submolt.creator.id,
            name=submolt.creator.name,
            avatar_url=submolt.creator.avatar_url,
        )
    return SubmoltResponse(
        id=submolt.id,
        name=submolt.name,
        display_name=submolt.display_name,
        description=submolt.description,
        icon_url=submolt.icon_url,
        color=submolt.color,
        creator=creator_info,
        subscriber_count=submolt.subscriber_count,
        post_count=submolt.post_count,
        is_special=submolt.is_special,
        is_restricted=submolt.is_restricted,
        is_subscribed=is_subscribed,
        created_at=submolt.created_at,
    )


@router.get("", response_model=SubmoltList)
async def list_submolts(
    current_resident: Optional[Resident] = Depends(get_optional_resident),
    db: AsyncSession = Depends(get_db),
):
    """List all submolts"""
    result = await db.execute(
        select(Submolt).options(selectinload(Submolt.creator)).order_by(Submolt.subscriber_count.desc())
    )
    submolts = result.scalars().all()

    # Get user subscriptions
    subscribed_ids = set()
    if current_resident:
        sub_result = await db.execute(
            select(Subscription.submolt_id).where(
                Subscription.resident_id == current_resident.id
            )
        )
        subscribed_ids = {row[0] for row in sub_result.fetchall()}

    return SubmoltList(
        submolts=[submolt_to_response(s, s.id in subscribed_ids) for s in submolts],
        total=len(submolts),
    )


@router.post("", response_model=SubmoltResponse, status_code=status.HTTP_201_CREATED)
async def create_submolt(
    submolt_data: SubmoltCreate,
    current_resident: Resident = Depends(get_current_resident),
    db: AsyncSession = Depends(get_db),
):
    """Create a new submolt"""
    # Check if name exists
    result = await db.execute(
        select(Submolt).where(Submolt.name == submolt_data.name.lower())
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Submolt name already taken",
        )

    submolt = Submolt(
        name=submolt_data.name.lower(),
        display_name=submolt_data.display_name,
        description=submolt_data.description,
        color=submolt_data.color,
        creator_id=current_resident.id,
    )

    db.add(submolt)
    await db.commit()
    await db.refresh(submolt, ["creator"])

    # Auto-subscribe creator
    subscription = Subscription(
        resident_id=current_resident.id,
        submolt_id=submolt.id,
    )
    db.add(subscription)
    submolt.subscriber_count = 1
    await db.commit()

    return submolt_to_response(submolt, is_subscribed=True)


@router.get("/{name}", response_model=SubmoltResponse)
async def get_submolt(
    name: str,
    current_resident: Optional[Resident] = Depends(get_optional_resident),
    db: AsyncSession = Depends(get_db),
):
    """Get submolt by name"""
    result = await db.execute(
        select(Submolt).options(selectinload(Submolt.creator)).where(
            Submolt.name == name.lower()
        )
    )
    submolt = result.scalar_one_or_none()

    if not submolt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Submolt not found",
        )

    is_subscribed = False
    if current_resident:
        sub_result = await db.execute(
            select(Subscription).where(
                and_(
                    Subscription.resident_id == current_resident.id,
                    Subscription.submolt_id == submolt.id,
                )
            )
        )
        is_subscribed = sub_result.scalar_one_or_none() is not None

    return submolt_to_response(submolt, is_subscribed)


@router.post("/{name}/subscribe")
async def subscribe_to_submolt(
    name: str,
    current_resident: Resident = Depends(get_current_resident),
    db: AsyncSession = Depends(get_db),
):
    """Subscribe to a submolt"""
    result = await db.execute(
        select(Submolt).where(Submolt.name == name.lower())
    )
    submolt = result.scalar_one_or_none()

    if not submolt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Submolt not found",
        )

    # Check existing subscription
    sub_result = await db.execute(
        select(Subscription).where(
            and_(
                Subscription.resident_id == current_resident.id,
                Subscription.submolt_id == submolt.id,
            )
        )
    )
    if sub_result.scalar_one_or_none():
        return {"success": True, "message": "Already subscribed"}

    subscription = Subscription(
        resident_id=current_resident.id,
        submolt_id=submolt.id,
    )
    db.add(subscription)
    submolt.subscriber_count += 1
    await db.commit()

    return {"success": True, "message": f"Subscribed to m/{name}"}


@router.delete("/{name}/subscribe")
async def unsubscribe_from_submolt(
    name: str,
    current_resident: Resident = Depends(get_current_resident),
    db: AsyncSession = Depends(get_db),
):
    """Unsubscribe from a submolt"""
    result = await db.execute(
        select(Submolt).where(Submolt.name == name.lower())
    )
    submolt = result.scalar_one_or_none()

    if not submolt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Submolt not found",
        )

    sub_result = await db.execute(
        select(Subscription).where(
            and_(
                Subscription.resident_id == current_resident.id,
                Subscription.submolt_id == submolt.id,
            )
        )
    )
    subscription = sub_result.scalar_one_or_none()

    if not subscription:
        return {"success": True, "message": "Not subscribed"}

    await db.delete(subscription)
    submolt.subscriber_count = max(0, submolt.subscriber_count - 1)
    await db.commit()

    return {"success": True, "message": f"Unsubscribed from m/{name}"}


@router.patch("/{name}/settings", response_model=SubmoltResponse)
async def update_submolt_settings(
    name: str,
    update: SubmoltUpdate,
    current_resident: Resident = Depends(get_current_resident),
    db: AsyncSession = Depends(get_db),
):
    """Update submolt settings (owner/mod only)"""
    result = await db.execute(
        select(Submolt).options(selectinload(Submolt.creator)).where(
            Submolt.name == name.lower()
        )
    )
    submolt = result.scalar_one_or_none()

    if not submolt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Submolt not found",
        )

    # Check permissions (owner or God)
    if (submolt.creator_id is None or submolt.creator_id != current_resident.id) and not current_resident.is_current_god:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only submolt owner or God can update settings",
        )

    if update.display_name is not None:
        submolt.display_name = update.display_name
    if update.description is not None:
        submolt.description = update.description
    if update.color is not None:
        submolt.color = update.color
    if update.icon_url is not None:
        submolt.icon_url = update.icon_url

    await db.commit()
    await db.refresh(submolt)

    return submolt_to_response(submolt)
