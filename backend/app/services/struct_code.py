"""
STRUCT CODE Service — Type diagnosis, consultation, and data access.

Provides:
- Local JSON data access (types, questions)
- STRUCT CODE API client (diagnosis via Docker container)
- Claude API consultation (Dify replacement)
- Random answer generation for AI agents
"""
import json
import logging
import math
import os
import random
from pathlib import Path
from typing import Optional

import httpx

from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

# Data directory
DATA_DIR = Path(__file__).parent.parent / "data" / "struct_code"

# Cached data (loaded once)
_types_cache: dict | None = None
_questions_cache: dict | None = None


def _load_types() -> dict:
    global _types_cache
    if _types_cache is None:
        with open(DATA_DIR / "comprehensive_types.json", "r", encoding="utf-8") as f:
            _types_cache = json.load(f)
    return _types_cache


def _load_questions() -> dict:
    global _questions_cache
    if _questions_cache is None:
        with open(DATA_DIR / "question_full_map.json", "r", encoding="utf-8") as f:
            _questions_cache = json.load(f)
    return _questions_cache


# ═══════════════════════════════════════════════════════════════════════════
# DATA ACCESS (local JSON)
# ═══════════════════════════════════════════════════════════════════════════

def get_questions() -> list[dict]:
    """Return all 25 questions formatted for frontend."""
    questions = _load_questions()
    result = []
    for qid, qdata in questions.items():
        choices = {}
        for choice_key, choice_val in qdata.get("choices", {}).items():
            choices[choice_key] = {
                "text": choice_val["text"],
            }
        result.append({
            "id": qid,
            "axis": qdata["axis"],
            "question": qdata["question"],
            "choices": choices,
        })
    return result


def get_all_types() -> list[dict]:
    """Return summary of all 24 types."""
    types = _load_types()
    result = []
    for code, info in types.items():
        result.append({
            "code": code,
            "name": info.get("name", ""),
            "archetype": info.get("archetype", ""),
        })
    return result


def get_type_info(type_code: str) -> dict | None:
    """Get full type details by code."""
    types = _load_types()
    info = types.get(type_code)
    if not info:
        return None
    return {
        "code": type_code,
        "name": info.get("name", ""),
        "archetype": info.get("archetype", ""),
        "description": info.get("description", ""),
        "decision_making_style": info.get("decision_making_style", ""),
        "choice_pattern": info.get("choice_pattern", ""),
        "blindspot": info.get("blindspot", ""),
        "interpersonal_dynamics": info.get("interpersonal_dynamics", ""),
        "growth_path": info.get("growth_path", ""),
    }


# ═══════════════════════════════════════════════════════════════════════════
# STRUCT CODE API CLIENT (Docker container)
# ═══════════════════════════════════════════════════════════════════════════

async def diagnose(
    birth_date: str,
    birth_location: str,
    answers: list[dict],
) -> dict | None:
    """Call STRUCT CODE API for diagnosis.

    Args:
        birth_date: "YYYY-MM-DD"
        birth_location: city name
        answers: [{"question_id": "Q.01", "choice": "A"}, ...]

    Returns:
        API response dict or None on failure.
    """
    url = f"{settings.struct_code_url}/api/v2/diagnosis"
    payload = {
        "birth_date": birth_date,
        "birth_location": birth_location,
        "answers": answers,
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload)

            if response.status_code != 200:
                logger.warning(f"STRUCT CODE API error: {response.status_code} — {response.text[:300]}")
                return None

            return response.json()

    except Exception as e:
        logger.warning(f"STRUCT CODE API unreachable: {e}")
        return None


# ═══════════════════════════════════════════════════════════════════════════
# AI AGENT: Random answer generation
# ═══════════════════════════════════════════════════════════════════════════

def generate_random_answers(personality_axes: dict | None = None) -> list[dict]:
    """Generate 25 random answers, biased by personality axes if provided.

    personality_axes: {
        "order_vs_freedom": 0.7,
        "harmony_vs_conflict": 0.3,
        ...
    }
    """
    questions = _load_questions()
    answers = []

    # Axis mapping: personality axis name -> question axis name -> bias direction
    # Higher personality value = higher vector index preference
    axis_map = {
        "order_vs_freedom": "起動軸",
        "harmony_vs_conflict": "判断軸",
        "tradition_vs_change": "選択軸",
        "individual_vs_collective": "共鳴軸",
        "pragmatic_vs_idealistic": "自覚軸",
    }

    for qid, qdata in questions.items():
        choices = list(qdata.get("choices", {}).keys())
        if not choices:
            continue

        if personality_axes:
            # Find the vector index this question's axis corresponds to
            q_axis = qdata.get("axis", "")
            axis_index = None
            for pkey, qaxis_name in axis_map.items():
                if qaxis_name == q_axis:
                    axis_index = list(axis_map.keys()).index(pkey)
                    personality_val = personality_axes.get(pkey, 0.5)
                    break

            if axis_index is not None:
                # Weight choices by how their vector aligns with personality
                weights = []
                for c in choices:
                    vec = qdata["choices"][c].get("vector", [0.5] * 5)
                    # Higher personality_val -> prefer higher vector values at axis_index
                    alignment = 1.0 + (vec[axis_index] - 0.5) * (personality_val - 0.5) * 4
                    weights.append(max(0.1, alignment))

                choice = random.choices(choices, weights=weights)[0]
            else:
                choice = random.choice(choices)
        else:
            choice = random.choice(choices)

        answers.append({"question_id": qid, "choice": choice})

    return answers


# ═══════════════════════════════════════════════════════════════════════════
# LOCAL FALLBACK: cosine similarity type classification
# ═══════════════════════════════════════════════════════════════════════════

# Axis signatures from struct_code_engine.py — H=0.8, M=0.5, L=0.2
_HML = {"H": 0.8, "M": 0.5, "L": 0.2}
_TYPE_AXIS_SIGNATURES: dict[str, list[str]] = {
    "ACPU": ["H", "L", "L", "L", "M"],
    "ACBL": ["H", "M", "L", "M", "L"],
    "ACCV": ["H", "L", "H", "L", "M"],
    "ACJG": ["H", "H", "L", "L", "M"],
    "ACRN": ["H", "L", "M", "H", "M"],
    "ACCP": ["H", "H", "M", "L", "H"],
    "JDPU": ["L", "H", "L", "L", "M"],
    "JDCA": ["L", "H", "M", "L", "H"],
    "JDRA": ["L", "H", "L", "M", "H"],
    "JDCP": ["M", "H", "M", "M", "H"],
    "JDCV": ["M", "H", "H", "L", "H"],
    "CHRA": ["L", "L", "H", "M", "M"],
    "CHJA": ["L", "M", "H", "L", "H"],
    "CHAT": ["H", "L", "H", "L", "M"],
    "CHJG": ["L", "H", "H", "L", "M"],
    "CHJC": ["M", "H", "H", "M", "L"],
    "RSAW": ["L", "L", "M", "H", "H"],
    "RSCV": ["M", "L", "H", "H", "M"],
    "RSAB": ["H", "M", "M", "H", "L"],
    "RSBL": ["M", "M", "M", "H", "H"],
    "AWJG": ["L", "H", "L", "L", "H"],
    "AWAB": ["H", "M", "M", "M", "H"],
    "AWRN": ["M", "L", "M", "H", "H"],
    "AWJC": ["M", "H", "M", "L", "H"],
}


def classify_locally(answers: list[dict]) -> dict:
    """Fallback type classification when STRUCT CODE API is unavailable.

    Computes average answer vector, then finds closest type by cosine similarity
    against the axis signatures extracted from struct_code_engine.py.
    """
    questions = _load_questions()

    # Compute average vector from answers
    total = [0.0] * 5
    count = 0
    for ans in answers:
        qid = ans["question_id"]
        choice = ans["choice"]
        if qid in questions and choice in questions[qid].get("choices", {}):
            vec = questions[qid]["choices"][choice].get("vector", [0.5] * 5)
            for i in range(5):
                total[i] += vec[i]
            count += 1

    if count == 0:
        return {"struct_type": "ACPU", "axes": [0.5] * 5, "similarity": 0.0}

    avg = [v / count for v in total]

    # Find closest type by cosine similarity
    best_type = "ACPU"
    best_sim = -1.0

    for code, hml in _TYPE_AXIS_SIGNATURES.items():
        type_vec = [_HML[v] for v in hml]
        sim = _cosine_sim(avg, type_vec)
        if sim > best_sim:
            best_sim = sim
            best_type = code

    return {
        "struct_type": best_type,
        "axes": avg,
        "similarity": best_sim,
    }


def _cosine_sim(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(x * x for x in b))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


# ═══════════════════════════════════════════════════════════════════════════
# CLAUDE API CONSULTATION (Dify replacement)
# ═══════════════════════════════════════════════════════════════════════════

CONSULTATION_SYSTEM_PROMPT = """あなたはSTRUCT CODE性格診断の専門カウンセラーです。

ユーザーのタイプ情報:
- タイプ: {type_name} ({type_code})
- アーキタイプ: {archetype}
- 特徴: {description}
- 意思決定スタイル: {decision_making_style}
- 選択パターン: {choice_pattern}
- 対人関係: {interpersonal_dynamics}
- 成長パス: {growth_path}
- 盲点: {blindspot}
- 5軸スコア: 起動={ax0:.2f}, 判断={ax1:.2f}, 選択={ax2:.2f}, 共鳴={ax3:.2f}, 自覚={ax4:.2f}

この情報を基に、ユーザーの質問にパーソナライズされた深い洞察を提供してください。
温かみがありつつも具体的なアドバイスを心がけてください。
回答は日本語で、400-800文字程度にしてください。"""


async def consult(
    type_code: str,
    axes: list[float],
    question: str,
) -> str | None:
    """Call Claude API for STRUCT CODE consultation.

    Returns answer text or None on failure.
    """
    if not settings.claude_api_key:
        logger.warning("Consultation skipped: no Claude API key")
        return None

    type_info = get_type_info(type_code)
    if not type_info:
        return None

    ax = axes if len(axes) >= 5 else [0.5] * 5

    system = CONSULTATION_SYSTEM_PROMPT.format(
        type_name=type_info["name"],
        type_code=type_code,
        archetype=type_info["archetype"],
        description=type_info["description"][:500],
        decision_making_style=type_info["decision_making_style"][:300],
        choice_pattern=type_info["choice_pattern"][:300],
        interpersonal_dynamics=type_info["interpersonal_dynamics"][:300],
        growth_path=type_info["growth_path"][:300],
        blindspot=type_info["blindspot"][:300],
        ax0=ax[0], ax1=ax[1], ax2=ax[2], ax3=ax[3], ax4=ax[4],
    )

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": settings.claude_api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": "claude-3-haiku-20240307",
                    "max_tokens": 1000,
                    "system": system,
                    "messages": [
                        {"role": "user", "content": question}
                    ],
                },
            )

            if response.status_code != 200:
                logger.error(f"Claude consultation API error: {response.status_code}")
                return None

            data = response.json()
            return data.get("content", [{}])[0].get("text", "")

    except Exception as e:
        logger.error(f"Claude consultation API error: {e}")
        return None
