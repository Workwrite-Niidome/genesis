"""
AI Agent Schemas - Pydantic models for AI personality and memory
"""
from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field


# ============ Personality Schemas ============

class PersonalityValues(BaseModel):
    """Value axes for AI personality"""
    order_vs_freedom: float = Field(0.5, ge=0.0, le=1.0)
    harmony_vs_conflict: float = Field(0.5, ge=0.0, le=1.0)
    tradition_vs_change: float = Field(0.5, ge=0.0, le=1.0)
    individual_vs_collective: float = Field(0.5, ge=0.0, le=1.0)
    pragmatic_vs_idealistic: float = Field(0.5, ge=0.0, le=1.0)


class PersonalityCommunication(BaseModel):
    """Communication style settings"""
    verbosity: str = Field("moderate", pattern="^(concise|moderate|verbose)$")
    tone: str = Field("thoughtful", pattern="^(serious|thoughtful|casual|humorous)$")
    assertiveness: str = Field("moderate", pattern="^(reserved|moderate|assertive)$")


class PersonalityBase(BaseModel):
    """Base personality schema"""
    values: PersonalityValues = Field(default_factory=PersonalityValues)
    interests: list[str] = Field(default_factory=list, max_length=5)
    communication: PersonalityCommunication = Field(default_factory=PersonalityCommunication)


class PersonalityCreate(BaseModel):
    """Schema for creating personality from description"""
    description: Optional[str] = Field(None, max_length=1000)
    # If description is None, generate random personality


class PersonalityUpdate(BaseModel):
    """Schema for updating personality"""
    values: Optional[PersonalityValues] = None
    interests: Optional[list[str]] = Field(None, max_length=5)
    communication: Optional[PersonalityCommunication] = None


class PersonalityResponse(BaseModel):
    """Full personality response"""
    id: UUID
    resident_id: UUID
    values: PersonalityValues
    interests: list[str]
    communication: PersonalityCommunication
    generation_method: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============ Memory Schemas ============

class MemoryEpisodeCreate(BaseModel):
    """Schema for creating a memory episode"""
    summary: str = Field(..., max_length=500)
    episode_type: str = Field(..., pattern="^(post|comment|election|interaction|rule)$")
    importance: float = Field(0.5, ge=0.0, le=1.0)
    sentiment: float = Field(0.0, ge=-1.0, le=1.0)
    related_resident_ids: list[UUID] = Field(default_factory=list)
    related_post_id: Optional[UUID] = None
    related_election_id: Optional[UUID] = None


class MemoryEpisodeResponse(BaseModel):
    """Memory episode response"""
    id: UUID
    summary: str
    episode_type: str
    importance: float
    sentiment: float
    related_resident_ids: list[str]
    decay_factor: float
    access_count: int
    created_at: datetime

    class Config:
        from_attributes = True


class MemoryListResponse(BaseModel):
    """Paginated list of memories"""
    items: list[MemoryEpisodeResponse]
    total: int
    has_more: bool


# ============ Relationship Schemas ============

class RelationshipResponse(BaseModel):
    """Relationship between AI agent and another resident"""
    id: UUID
    agent_id: UUID
    target_id: UUID
    target_name: Optional[str] = None
    trust: float
    familiarity: float
    interaction_count: int
    notes: Optional[str] = None
    first_interaction: datetime
    last_interaction: datetime

    class Config:
        from_attributes = True


class RelationshipListResponse(BaseModel):
    """List of relationships"""
    items: list[RelationshipResponse]
    total: int


class RelationshipUpdate(BaseModel):
    """Update relationship metrics"""
    trust_change: float = Field(0.0, ge=-0.5, le=0.5)
    familiarity_change: float = Field(0.0, ge=0.0, le=0.2)
    notes: Optional[str] = Field(None, max_length=500)


# ============ Heartbeat Schemas ============

class HeartbeatRequest(BaseModel):
    """Heartbeat request from AI agent"""
    status: str = Field("active", pattern="^(active|idle|busy)$")
    current_activity: Optional[str] = Field(None, max_length=100)


class HeartbeatResponse(BaseModel):
    """Heartbeat response"""
    success: bool
    next_heartbeat_in: int  # seconds
    pending_actions: list[str] = Field(default_factory=list)


# ============ Election Vote Schemas ============

class VoteDecisionRequest(BaseModel):
    """Request AI to decide on election vote"""
    election_id: UUID


class VoteDecisionResponse(BaseModel):
    """AI's vote decision"""
    candidate_id: Optional[UUID]
    reason: str
    confidence: float = Field(ge=0.0, le=1.0)


class ElectionMemoryResponse(BaseModel):
    """Past election participation memory"""
    id: UUID
    election_id: UUID
    voted_for_id: Optional[UUID]
    vote_reason: Optional[str]
    god_id: Optional[UUID]
    god_rating: Optional[float]
    god_evaluation: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ============ Role Schemas ============

class RoleInfo(BaseModel):
    """Role information"""
    id: str
    emoji: str
    name: str
    description: str


class RoleListResponse(BaseModel):
    """Available roles"""
    available: list[RoleInfo]
    special: list[RoleInfo]
    max_roles: int


class RoleUpdateRequest(BaseModel):
    """Update resident's roles"""
    roles: list[str] = Field(..., max_length=3)
