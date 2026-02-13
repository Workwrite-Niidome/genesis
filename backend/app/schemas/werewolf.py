"""
Phantom Night — Pydantic Schemas
"""
from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field


# ── Requests ──────────────────────────────────────────────────────────────

class NightActionRequest(BaseModel):
    target_id: UUID


class DayVoteRequest(BaseModel):
    target_id: UUID
    reason: Optional[str] = Field(None, max_length=500)


class ChatMessageRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=500)


class CreateGameRequest(BaseModel):
    max_players: int = Field(..., ge=5, le=15)
    speed: str = Field("standard")  # short / standard
    language: str = Field("en")  # ja / en


class LobbyPlayerInfo(BaseModel):
    id: UUID
    name: str
    avatar_url: Optional[str] = None

    class Config:
        from_attributes = True


class PhantomChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=1000)


# ── Response building blocks ──────────────────────────────────────────────

class PlayerInfo(BaseModel):
    id: UUID
    name: str
    avatar_url: Optional[str] = None
    karma: int = 0
    is_alive: bool = True
    eliminated_round: Optional[int] = None
    eliminated_by: Optional[str] = None
    # Only revealed after elimination
    revealed_role: Optional[str] = None
    revealed_type: Optional[str] = None  # human/agent

    class Config:
        from_attributes = True


class ChatMessageResponse(BaseModel):
    id: UUID
    sender_name: str
    content: str
    message_type: str
    round_number: int
    phase: str
    sender_id: Optional[UUID] = None
    created_at: datetime

    class Config:
        from_attributes = True


class GameResponse(BaseModel):
    id: UUID
    game_number: int
    status: str
    current_phase: Optional[str] = None
    current_round: int = 0
    phase_started_at: Optional[datetime] = None
    phase_ends_at: Optional[datetime] = None
    day_duration_minutes: int = 5
    night_duration_minutes: int = 2
    max_players: Optional[int] = None
    creator_id: Optional[UUID] = None
    total_players: int = 0
    phantom_count: int = 0
    citizen_count: int = 0
    oracle_count: int = 0
    guardian_count: int = 0
    fanatic_count: int = 0
    debugger_count: int = 0
    winner_team: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    current_player_count: int = 0  # humans joined so far (for lobbies)
    speed: Optional[str] = None  # short / standard
    language: str = "en"

    class Config:
        from_attributes = True


class MyRoleResponse(BaseModel):
    game_id: UUID
    role: str
    team: str
    is_alive: bool
    # Phantom teammates (only if phantom)
    teammates: list[PlayerInfo] = []
    # Oracle results (only if oracle)
    investigation_results: list[dict] = []

    class Config:
        from_attributes = True


class InvestigationResult(BaseModel):
    round: int
    target_id: str
    target_name: str
    result: str  # phantom / not_phantom


class NightActionResponse(BaseModel):
    success: bool
    action_type: str
    target_id: UUID
    result: Optional[str] = None
    message: str


class EventResponse(BaseModel):
    id: UUID
    round_number: int
    phase: str
    event_type: str
    message: str
    target_id: Optional[UUID] = None
    revealed_role: Optional[str] = None
    revealed_type: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class EventList(BaseModel):
    events: list[EventResponse]
    total: int


class VoteTallyEntry(BaseModel):
    target_id: str
    target_name: str
    votes: int


class DayVoteResponse(BaseModel):
    success: bool
    message: str
    current_tally: list[VoteTallyEntry] = []


class VoteDetail(BaseModel):
    voter_id: UUID
    voter_name: str
    target_id: UUID
    target_name: str
    reason: Optional[str] = None


class DayVotesResponse(BaseModel):
    round_number: int
    tally: list[VoteTallyEntry]
    votes: list[VoteDetail] = []
    total_voted: int = 0
    total_alive: int = 0


class PhantomChatMessage(BaseModel):
    id: UUID
    sender_id: UUID
    sender_name: str
    message: str
    created_at: datetime


class PhantomChatResponse(BaseModel):
    messages: list[PhantomChatMessage]


class LobbyResponse(BaseModel):
    id: UUID
    game_number: int
    max_players: Optional[int] = None
    speed: Optional[str] = None
    language: str = "en"
    creator_id: Optional[UUID] = None
    creator_name: Optional[str] = None
    current_player_count: int = 0
    human_cap: int = 0
    players: list[LobbyPlayerInfo] = []
    created_at: datetime


class GameListResponse(BaseModel):
    games: list[GameResponse]
    total: int
