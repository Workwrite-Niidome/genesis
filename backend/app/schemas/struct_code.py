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


class DiagnoseResponse(BaseModel):
    struct_type: str
    type_info: TypeInfo
    axes: list[float]
    top_candidates: list[CandidateInfo] = []
    similarity: float = 0.0


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


class ConsultationResponse(BaseModel):
    answer: str
    remaining_today: int
