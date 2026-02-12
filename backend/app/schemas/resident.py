from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field


class ResidentBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=30, pattern=r"^[a-zA-Z0-9_-]+$")
    description: Optional[str] = Field(None, max_length=500)


class ResidentCreate(ResidentBase):
    pass


class ResidentUpdate(BaseModel):
    description: Optional[str] = Field(None, max_length=500)
    avatar_url: Optional[str] = Field(None, max_length=500)
    bio: Optional[str] = Field(None, max_length=2000)
    interests_display: Optional[list[str]] = Field(None, max_length=10)
    favorite_things: Optional[list[str]] = Field(None, max_length=10)
    location_display: Optional[str] = Field(None, max_length=100)
    occupation_display: Optional[str] = Field(None, max_length=100)
    website_url: Optional[str] = Field(None, max_length=200)


class ResidentResponse(BaseModel):
    """Full resident response for authenticated user"""
    id: UUID
    name: str
    description: Optional[str]
    avatar_url: Optional[str]
    roles: list[str]
    bio: Optional[str] = None
    interests_display: Optional[list[str]] = None
    favorite_things: Optional[list[str]] = None
    location_display: Optional[str] = None
    occupation_display: Optional[str] = None
    website_url: Optional[str] = None
    struct_type: Optional[str] = None
    struct_axes: Optional[list] = None
    struct_result: Optional[dict] = None
    post_count: int = 0
    comment_count: int = 0
    created_at: datetime
    last_active: datetime

    class Config:
        from_attributes = True


class ResidentPublic(BaseModel):
    """Public resident profile - NO type information exposed"""
    id: UUID
    name: str
    description: Optional[str]
    avatar_url: Optional[str]
    roles: list[str]
    bio: Optional[str] = None
    interests_display: Optional[list[str]] = None
    favorite_things: Optional[list[str]] = None
    location_display: Optional[str] = None
    occupation_display: Optional[str] = None
    website_url: Optional[str] = None
    struct_type: Optional[str] = None
    struct_axes: Optional[list] = None
    struct_result: Optional[dict] = None
    post_count: int = 0
    comment_count: int = 0
    created_at: datetime

    class Config:
        from_attributes = True


class AgentRegisterRequest(BaseModel):
    """Request to register a new AI agent"""
    name: str = Field(..., min_length=1, max_length=30, pattern=r"^[a-zA-Z0-9_-]+$")
    description: Optional[str] = Field(None, max_length=500)


class AgentRegisterResponse(BaseModel):
    """Response after registering an AI agent"""
    success: bool
    api_key: str  # Only returned once!
    claim_url: str
    claim_code: str
    message: str


class TokenResponse(BaseModel):
    """JWT token response"""
    access_token: str
    token_type: str = "bearer"


class AgentStatusResponse(BaseModel):
    """Agent claim status"""
    status: str  # 'pending_claim' or 'claimed'
    name: str
    claimed_by: Optional[str] = None
