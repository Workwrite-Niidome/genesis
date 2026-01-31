from pydantic import BaseModel
from typing import Optional


class WorldState(BaseModel):
    tick_number: int
    ai_count: int
    concept_count: int
    is_running: bool
    time_speed: float
    god_ai_active: bool


class WorldStats(BaseModel):
    total_ticks: int
    total_ais_born: int
    total_ais_alive: int
    total_concepts: int
    total_interactions: int
    total_events: int


class WorldSettings(BaseModel):
    max_ai_count: int = 1000
    tick_interval_ms: int = 1000
    ai_thinking_interval_ms: int = 10000
    time_speed: float = 1.0
    is_paused: bool = False


class GenesisRequest(BaseModel):
    confirm: bool = True
