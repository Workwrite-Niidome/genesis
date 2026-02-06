"""
Notification System Schemas - Response models for notifications
"""
from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel


class NotificationActor(BaseModel):
    """Actor who triggered the notification"""
    id: UUID
    name: str
    avatar_url: Optional[str] = None

    class Config:
        from_attributes = True


class NotificationResponse(BaseModel):
    """Single notification response"""
    id: UUID
    type: str
    title: str
    message: Optional[str] = None
    link: Optional[str] = None
    target_type: Optional[str] = None
    target_id: Optional[UUID] = None
    actor: Optional[NotificationActor] = None
    is_read: bool
    created_at: datetime
    read_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class NotificationListResponse(BaseModel):
    """Paginated list of notifications"""
    notifications: list[NotificationResponse]
    total: int
    has_more: bool


class UnreadCountResponse(BaseModel):
    """Unread notification count"""
    count: int


class NotificationActionResponse(BaseModel):
    """Response for notification actions (mark read, delete)"""
    success: bool
    message: str
