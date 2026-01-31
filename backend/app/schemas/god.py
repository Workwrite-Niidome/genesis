import uuid
from datetime import datetime
from pydantic import BaseModel
from typing import Optional


class GodAIState(BaseModel):
    id: uuid.UUID
    state: dict
    current_message: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class GodMessageRequest(BaseModel):
    message: str


class GodMessageResponse(BaseModel):
    admin_message: str
    god_response: str
    timestamp: datetime


class GodConversationEntry(BaseModel):
    role: str  # 'admin' or 'god'
    content: str
    timestamp: datetime
