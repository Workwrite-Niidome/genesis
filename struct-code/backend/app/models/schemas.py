from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import date

class BirthInfoRequest(BaseModel):
    birth_date: str  # YYYY-MM-DD format
    birth_location: str

class QuestionChoice(BaseModel):
    text: str
    vector: List[float]

class QuestionData(BaseModel):
    axis: str
    question: str
    choices: Dict[str, QuestionChoice]

class QuestionResponse(BaseModel):
    id: str
    axis: str
    question: str
    choices: Dict[str, str]  # choice_id -> text

class AnswerData(BaseModel):
    question_id: str
    choice: str  # A, B, C, D

class QuestionnaireRequest(BaseModel):
    birth_date: str
    birth_location: str
    answers: List[AnswerData]

class DiagnosisRequest(BaseModel):
    birth_date: str
    birth_location: str
    answers: List[AnswerData]

class TypeDetail(BaseModel):
    code: str
    label: str
    summary: str
    decision_style: str
    choice_pattern: str
    risk_note: str
    relation_hint: str
    growth_tip: str
    vector: List[float]
    character_icon: Optional[str] = None

class DiagnosisResponse(BaseModel):
    struct_type: str
    struct_code: str
    similarity_score: float
    symbolic_time: str
    symbolic_meaning: str
    type_detail: TypeDetail
    top_candidates: List[Dict[str, Any]]
    vectors: Dict[str, Any]  # List[float] or Dict[str, float] for planetary positions
    interpretation_prompt: str