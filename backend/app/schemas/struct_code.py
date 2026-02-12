"""STRUCT CODE API schemas — diagnosis, consultation, types."""
from typing import Optional
from pydantic import BaseModel, Field


class AnswerItem(BaseModel):
    question_id: str = Field(..., example="Q.01")
    choice: str = Field(..., example="A")


class DiagnoseRequest(BaseModel):
    birth_date: str = Field(..., example="1990-01-15", description="YYYY-MM-DD")
    birth_location: str = Field(..., example="東京", description="City name")
    answers: list[AnswerItem]


class TypeInfo(BaseModel):
    code: str
    name: str
    archetype: str
    description: str = ""
    decision_making_style: str = ""
    choice_pattern: str = ""
    blindspot: str = ""
    interpersonal_dynamics: str = ""
    growth_path: str = ""


class CandidateInfo(BaseModel):
    code: str
    name: str = ""
    archetype: str = ""
    score: float = 0.0


class StructureInfo(BaseModel):
    """Natal or Current structure data."""
    type: str
    type_name: str = ""
    axes: list[float] = []
    axes_display: dict[str, int] = {}
    description: str = ""


class AxisState(BaseModel):
    """State of a single axis: activation/stable/suppression."""
    axis: str
    state: str  # "activation" | "stable" | "suppression"
    gap: float = 0.0


class TemporalInfo(BaseModel):
    """Time-based theme and transit data."""
    current_theme: str = ""
    theme_description: str = ""
    active_transits: list[dict] = []
    future_outlook: list[dict] = []


class DiagnoseResponse(BaseModel):
    struct_type: str
    struct_code: str = ""
    type_info: TypeInfo
    axes: list[float]
    top_candidates: list[CandidateInfo] = []
    similarity: float = 0.0
    # Dynamic API fields
    natal: Optional[StructureInfo] = None
    current: Optional[StructureInfo] = None
    design_gap: dict[str, float] = {}
    axis_states: list[AxisState] = []
    temporal: Optional[TemporalInfo] = None


class TypeSummary(BaseModel):
    code: str
    name: str
    archetype: str


class QuestionChoice(BaseModel):
    text: str


class QuestionItem(BaseModel):
    id: str
    axis: str
    question: str
    choices: dict[str, QuestionChoice]


class ConsultationRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    session_id: str | None = None  # Existing session to continue


class ConsultationResponse(BaseModel):
    answer: str
    remaining_today: int
    session_id: str           # Genesis session UUID
    conversation_id: str      # Dify conversation ID


class ConsultationMessageSchema(BaseModel):
    id: str
    role: str
    content: str
    created_at: str


class ConsultationSessionSummary(BaseModel):
    id: str
    title: str
    message_count: int
    created_at: str
    updated_at: str


class ConsultationSessionDetail(BaseModel):
    id: str
    title: str
    message_count: int
    messages: list[ConsultationMessageSchema]
    created_at: str
    updated_at: str
