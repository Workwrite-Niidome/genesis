"""
Moderation System Schemas
"""
from datetime import datetime
from typing import Optional, Literal
from uuid import UUID
from pydantic import BaseModel, Field


# Report Schemas
class ReportCreate(BaseModel):
    """Create a new report"""
    target_type: Literal["post", "comment", "resident"] = Field(
        ..., description="Type of content being reported"
    )
    target_id: UUID = Field(..., description="ID of the content being reported")
    reason: Literal["spam", "harassment", "hate", "misinformation", "other"] = Field(
        ..., description="Reason for the report"
    )
    description: Optional[str] = Field(
        None, max_length=1000, description="Additional details about the report"
    )


class ReporterInfo(BaseModel):
    """Reporter information"""
    id: UUID
    name: str

    class Config:
        from_attributes = True


class ReviewerInfo(BaseModel):
    """Reviewer information"""
    id: UUID
    name: str

    class Config:
        from_attributes = True


class ReportResponse(BaseModel):
    """Report response"""
    id: UUID
    reporter: ReporterInfo
    target_type: str
    target_id: UUID
    reason: str
    description: Optional[str]
    status: str
    reviewer: Optional[ReviewerInfo] = None
    reviewed_at: Optional[datetime] = None
    resolution_note: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ReportList(BaseModel):
    """Paginated list of reports"""
    reports: list[ReportResponse]
    total: int
    has_more: bool


class ReportResolve(BaseModel):
    """Resolve a report"""
    status: Literal["resolved", "dismissed"] = Field(
        ..., description="Resolution status"
    )
    resolution_note: Optional[str] = Field(
        None, max_length=500, description="Note explaining the resolution"
    )


# Ban Schemas
class BanRequest(BaseModel):
    """Request to ban a resident"""
    reason: str = Field(..., min_length=1, max_length=500, description="Reason for the ban")
    duration_hours: Optional[int] = Field(
        None, ge=1, le=8760, description="Ban duration in hours (max 1 year). Omit for permanent ban."
    )
    is_permanent: bool = Field(default=False, description="Whether the ban is permanent")


class BannerInfo(BaseModel):
    """Banner (moderator) information"""
    id: UUID
    name: str

    class Config:
        from_attributes = True


class BannedResidentInfo(BaseModel):
    """Banned resident information"""
    id: UUID
    name: str

    class Config:
        from_attributes = True


class BanResponse(BaseModel):
    """Ban response"""
    id: UUID
    resident: BannedResidentInfo
    banned_by: BannerInfo
    reason: Optional[str]
    is_permanent: bool
    expires_at: Optional[datetime]
    created_at: datetime
    is_active: bool

    class Config:
        from_attributes = True


# Moderation Action Schemas
class ModeratorInfo(BaseModel):
    """Moderator information"""
    id: UUID
    name: str

    class Config:
        from_attributes = True


class ModerationActionResponse(BaseModel):
    """Moderation action response"""
    id: UUID
    moderator: ModeratorInfo
    target_type: str
    target_id: UUID
    action: str
    reason: Optional[str]
    duration_hours: Optional[int]
    expires_at: Optional[datetime]
    report_id: Optional[UUID]
    created_at: datetime

    class Config:
        from_attributes = True


class ModerationLogResponse(BaseModel):
    """Paginated list of moderation actions"""
    actions: list[ModerationActionResponse]
    total: int
    has_more: bool


# Content Removal
class ContentRemoveRequest(BaseModel):
    """Request to remove content"""
    reason: str = Field(..., min_length=1, max_length=500, description="Reason for removal")


class ContentRemoveResponse(BaseModel):
    """Response after content removal"""
    success: bool
    message: str
    action_id: UUID
