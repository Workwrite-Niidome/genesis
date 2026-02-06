"""
Notification Router - Endpoints for notification functionality
"""
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.resident import Resident
from app.schemas.notification import (
    NotificationResponse,
    NotificationListResponse,
    UnreadCountResponse,
    NotificationActionResponse,
    NotificationActor,
)
from app.routers.auth import get_current_resident
from app.services import notification as notification_service

router = APIRouter(prefix="/notifications")


def notification_to_response(notification) -> NotificationResponse:
    """Convert Notification model to NotificationResponse schema"""
    actor = None
    if notification.actor:
        actor = NotificationActor(
            id=notification.actor.id,
            name=notification.actor.name,
            avatar_url=notification.actor.avatar_url,
        )

    return NotificationResponse(
        id=notification.id,
        type=notification.type,
        title=notification.title,
        message=notification.message,
        link=notification.link,
        target_type=notification.target_type,
        target_id=notification.target_id,
        actor=actor,
        is_read=notification.is_read,
        created_at=notification.created_at,
        read_at=notification.read_at,
    )


@router.get("", response_model=NotificationListResponse)
async def get_notifications(
    unread_only: bool = Query(default=False, description="Only return unread notifications"),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_resident: Resident = Depends(get_current_resident),
    db: AsyncSession = Depends(get_db),
):
    """Get notifications for the current resident with pagination"""
    notifications, total, has_more = await notification_service.get_notifications(
        db,
        current_resident.id,
        unread_only=unread_only,
        limit=limit,
        offset=offset,
    )

    return NotificationListResponse(
        notifications=[notification_to_response(n) for n in notifications],
        total=total,
        has_more=has_more,
    )


@router.get("/unread/count", response_model=UnreadCountResponse)
async def get_unread_count(
    current_resident: Resident = Depends(get_current_resident),
    db: AsyncSession = Depends(get_db),
):
    """Get the count of unread notifications"""
    count = await notification_service.get_unread_count(db, current_resident.id)
    return UnreadCountResponse(count=count)


@router.post("/{notification_id}/read", response_model=NotificationActionResponse)
async def mark_as_read(
    notification_id: UUID,
    current_resident: Resident = Depends(get_current_resident),
    db: AsyncSession = Depends(get_db),
):
    """Mark a notification as read"""
    success, message = await notification_service.mark_as_read(
        db, notification_id, current_resident.id
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=message,
        )

    return NotificationActionResponse(success=True, message=message)


@router.post("/read-all", response_model=NotificationActionResponse)
async def mark_all_as_read(
    current_resident: Resident = Depends(get_current_resident),
    db: AsyncSession = Depends(get_db),
):
    """Mark all notifications as read"""
    count = await notification_service.mark_all_as_read(db, current_resident.id)
    return NotificationActionResponse(
        success=True,
        message=f"Marked {count} notifications as read",
    )


@router.delete("/{notification_id}", response_model=NotificationActionResponse)
async def delete_notification(
    notification_id: UUID,
    current_resident: Resident = Depends(get_current_resident),
    db: AsyncSession = Depends(get_db),
):
    """Delete a notification"""
    success, message = await notification_service.delete_notification(
        db, notification_id, current_resident.id
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=message,
        )

    return NotificationActionResponse(success=True, message=message)
