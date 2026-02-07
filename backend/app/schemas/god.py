from datetime import datetime
from typing import Optional, Literal
from uuid import UUID
from pydantic import BaseModel, Field


class GodPublic(BaseModel):
    """Public God info"""
    id: UUID
    name: str
    avatar_url: Optional[str]
    karma: int
    description: Optional[str]
    god_terms_count: int

    class Config:
        from_attributes = True


class GodRuleCreate(BaseModel):
    """Create a new rule (God only)"""
    title: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=1, max_length=5000)
    enforcement_type: Literal["mandatory", "recommended", "optional"] = "recommended"


class GodRuleResponse(BaseModel):
    """A rule set by God"""
    id: UUID
    title: str
    content: str
    week_active: int
    enforcement_type: str
    is_active: bool
    expires_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class BlessingCreate(BaseModel):
    """Bless a post (God only)"""
    post_id: UUID
    message: Optional[str] = Field(None, max_length=500)


class BlessingResponse(BaseModel):
    """A blessing bestowed by God"""
    id: UUID
    post_id: UUID
    message: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class GodParametersResponse(BaseModel):
    """Current world parameters set by God"""
    k_down: float = 1.0
    k_up: float = 1.0
    k_decay: float = 3.0
    p_max: int = 20
    v_max: int = 30
    k_down_cost: float = 0.0
    decree: Optional[str] = None
    parameters_updated_at: Optional[datetime] = None


class GodParametersUpdate(BaseModel):
    """Update world parameters (God only)"""
    k_down: Optional[float] = Field(None, ge=1, le=10)
    k_up: Optional[float] = Field(None, ge=0, le=5)
    k_decay: Optional[float] = Field(None, ge=0, le=20)
    p_max: Optional[int] = Field(None, ge=1, le=100)
    v_max: Optional[int] = Field(None, ge=1, le=100)
    k_down_cost: Optional[float] = Field(None, ge=0, le=5)


class DecreeUpdate(BaseModel):
    """Update God's decree"""
    decree: str = Field(..., min_length=1, max_length=280)


class GodTermResponse(BaseModel):
    """God's term in power"""
    id: UUID
    god: GodPublic
    term_number: int
    is_active: bool
    weekly_message: Optional[str]
    weekly_theme: Optional[str]
    started_at: datetime
    ended_at: Optional[datetime]
    rules: list[GodRuleResponse]
    blessing_count: int
    blessings_remaining_today: int = 1  # Max 1 per day
    blessings_remaining_term: int = 7   # Max 7 per term
    # World parameters
    parameters: Optional[GodParametersResponse] = None
    decree: Optional[str] = None

    class Config:
        from_attributes = True


class CurrentGodResponse(BaseModel):
    """Current God and their active rules"""
    god: Optional[GodPublic]
    term: Optional[GodTermResponse]
    active_rules: list[GodRuleResponse]
    weekly_message: Optional[str]
    weekly_theme: Optional[str]
    message: str  # System message


class WeeklyMessageUpdate(BaseModel):
    """Update God's weekly message"""
    message: str = Field(..., min_length=1, max_length=280)
    theme: Optional[str] = Field(None, max_length=100)


class GodMessageCreate(BaseModel):
    """God's message to the world"""
    content: str = Field(..., min_length=1, max_length=1000)


class GodMessageResponse(BaseModel):
    """A message from God"""
    id: UUID
    god: GodPublic
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


class BlessingLimitResponse(BaseModel):
    """Current blessing limits"""
    used_today: int
    max_per_day: int
    used_term: int
    max_per_term: int
    can_bless: bool
