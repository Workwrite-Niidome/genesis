import uuid
from datetime import datetime
from pydantic import BaseModel
from typing import Optional


class AIBase(BaseModel):
    id: uuid.UUID
    creator_type: str
    position_x: float
    position_y: float
    appearance: dict
    state: dict
    is_alive: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class AIDetail(AIBase):
    creator_id: Optional[uuid.UUID] = None
    updated_at: datetime


class AIMemorySchema(BaseModel):
    id: uuid.UUID
    content: str
    memory_type: str
    importance: float
    tick_number: int
    created_at: datetime

    model_config = {"from_attributes": True}


class ConceptSchema(BaseModel):
    id: uuid.UUID
    creator_id: Optional[uuid.UUID] = None
    name: str
    definition: str
    effects: dict
    adoption_count: int
    tick_created: int
    created_at: datetime

    model_config = {"from_attributes": True}
