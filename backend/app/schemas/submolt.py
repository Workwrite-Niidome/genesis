from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field


class SubmoltCreate(BaseModel):
    """Create a new submolt"""
    name: str = Field(..., min_length=1, max_length=50, pattern=r"^[a-zA-Z0-9_-]+$")
    display_name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    color: Optional[str] = Field(None, pattern=r"^#[0-9a-fA-F]{6}$")


class SubmoltUpdate(BaseModel):
    """Update submolt settings"""
    display_name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    color: Optional[str] = Field(None, pattern=r"^#[0-9a-fA-F]{6}$")
    icon_url: Optional[str] = Field(None, max_length=500)


class CreatorInfo(BaseModel):
    """Creator info - NO type exposed"""
    id: UUID
    name: str
    avatar_url: Optional[str]

    class Config:
        from_attributes = True


class SubmoltResponse(BaseModel):
    """Submolt response"""
    id: UUID
    name: str
    display_name: str
    description: Optional[str]
    icon_url: Optional[str]
    color: Optional[str]
    creator: Optional[CreatorInfo] = None
    subscriber_count: int
    post_count: int
    is_special: bool
    is_restricted: bool
    is_subscribed: bool = False
    created_at: datetime

    class Config:
        from_attributes = True


class SubmoltList(BaseModel):
    """List of submolts"""
    submolts: list[SubmoltResponse]
    total: int
