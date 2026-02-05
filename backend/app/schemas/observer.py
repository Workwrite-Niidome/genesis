from pydantic import BaseModel, Field


# --- Legacy (username+password) registration ---

class ObserverRegister(BaseModel):
    username: str = Field(min_length=2, max_length=50)
    password: str = Field(min_length=4, max_length=100)
    language: str = "en"


class ObserverLogin(BaseModel):
    username: str
    password: str


class ObserverResponse(BaseModel):
    id: str
    username: str
    role: str
    language: str
    token: str  # JWT token


# --- Anonymous observer registration ---

class AnonymousRegisterRequest(BaseModel):
    display_name: str = Field(min_length=1, max_length=50)


class AnonymousRegisterResponse(BaseModel):
    id: str
    display_name: str
    token: str  # JWT session token


# --- Observer list / stats ---

class OnlineObserverInfo(BaseModel):
    id: str
    display_name: str
    focus_entity_id: str | None = None


class ObserverStatsResponse(BaseModel):
    total_online: int
    active_watchers: int  # observers currently focused on an entity
    entity_focus_counts: dict[str, int]  # entity_id -> observer count


# --- Focus ---

class FocusRequest(BaseModel):
    entity_id: str | None = None  # None means unfocus


# --- Chat ---

class ChatMessageCreate(BaseModel):
    channel: str = "global"
    content: str = Field(min_length=1, max_length=500)


class ChatMessageResponse(BaseModel):
    id: str
    username: str
    channel: str
    content: str
    timestamp: str
