"""
STRUCT CODE Service — Type diagnosis, consultation, and data access.

Provides:
- Local JSON data access (types, questions) with bilingual support (ja/en)
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

# Cached data keyed by language
_types_cache: dict[str, dict] = {}
_questions_cache: dict[str, dict] = {}


def _load_types(lang: str = "ja") -> dict:
    if lang not in _types_cache:
        suffix = "_en" if lang == "en" else ""
        path = DATA_DIR / f"comprehensive_types{suffix}.json"
        if not path.exists():
            # Fallback to Japanese if translation file missing
            path = DATA_DIR / "comprehensive_types.json"
        with open(path, "r", encoding="utf-8") as f:
            _types_cache[lang] = json.load(f)
    return _types_cache[lang]


def _load_questions(lang: str = "ja") -> dict:
    if lang not in _questions_cache:
        suffix = "_en" if lang == "en" else ""
        path = DATA_DIR / f"question_full_map{suffix}.json"
        if not path.exists():
            path = DATA_DIR / "question_full_map.json"
        with open(path, "r", encoding="utf-8") as f:
            _questions_cache[lang] = json.load(f)
    return _questions_cache[lang]


# ═══════════════════════════════════════════════════════════════════════════
# DATA ACCESS (local JSON)
# ═══════════════════════════════════════════════════════════════════════════

def get_questions(lang: str = "ja") -> list[dict]:
    """Return all 25 questions formatted for frontend."""
    questions = _load_questions(lang)
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


def get_all_types(lang: str = "ja") -> list[dict]:
    """Return summary of all 24 types."""
    types = _load_types(lang)
    result = []
    for code, info in types.items():
        result.append({
            "code": code,
            "name": info.get("name", ""),
            "archetype": info.get("archetype", ""),
        })
    return result


def get_type_info(type_code: str, lang: str = "ja") -> dict | None:
    """Get full type details by code."""
    types = _load_types(lang)
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
    """Call STRUCT CODE Dynamic API for diagnosis.

    Uses /api/v2/dynamic/diagnosis which returns natal/current structures,
    design gap, axis states, and temporal data.
    No fallback — returns None on failure so caller can raise proper error.

    Returns:
        API response dict or None on failure.
    """
    url = f"{settings.struct_code_url}/api/v2/dynamic/diagnosis"
    payload = {
        "birth_date": birth_date,
        "birth_location": birth_location,
        "answers": answers,
    }

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(url, json=payload)

            if response.status_code == 200:
                data = response.json()
                data["_api_version"] = "dynamic"
                return data

            logger.error(f"STRUCT CODE API error: {response.status_code} — {response.text[:500]}")
            return None

    except Exception as e:
        logger.error(f"STRUCT CODE API unreachable: {e}")
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

CONSULTATION_SYSTEM_PROMPT_JA = """あなたはSTRUCT CODE性格診断の専門カウンセラーです。

ユーザーのタイプ情報:
- カレントタイプ（現在の状態）: {type_name} ({type_code})
- アーキタイプ: {archetype}
- 特徴: {description}
- 意思決定スタイル: {decision_making_style}
- 選択パターン: {choice_pattern}
- 対人関係: {interpersonal_dynamics}
- 成長パス: {growth_path}
- 盲点: {blindspot}
- 現在の5軸スコア (0-1000): 起動={ax0}, 判断={ax1}, 選択={ax2}, 共鳴={ax3}, 自覚={ax4}
{extra_context}
この情報を基に、ユーザーの質問にパーソナライズされた深い洞察を提供してください。
ネイタルタイプ（本来の構造）とカレントタイプ（現在の時期的影響を含む状態）の違いや、各軸の状態（活性化・安定・抑制）を踏まえたアドバイスを心がけてください。
温かみがありつつも具体的なアドバイスを心がけてください。
回答は日本語で、400-800文字程度にしてください。"""

CONSULTATION_SYSTEM_PROMPT_EN = """You are an expert counselor specializing in STRUCT CODE personality diagnosis.

User's Type Information:
- Current Type (present state): {type_name} ({type_code})
- Archetype: {archetype}
- Description: {description}
- Decision-Making Style: {decision_making_style}
- Choice Pattern: {choice_pattern}
- Interpersonal Dynamics: {interpersonal_dynamics}
- Growth Path: {growth_path}
- Blindspot: {blindspot}
- Current 5-Axis Scores (0-1000): Activation={ax0}, Judgment={ax1}, Choice={ax2}, Resonance={ax3}, Awareness={ax4}
{extra_context}
Based on this information, provide personalized and deep insights in response to the user's question.
Consider the difference between the Natal Type (innate structure) and Current Type (reflecting temporal influences), and incorporate each axis's state (activation/stable/suppression) into your advice.
Be warm yet specific in your advice.
Keep your response between 200-400 words."""


async def consult(
    type_code: str,
    axes: list[float],
    question: str,
    struct_result: dict | None = None,
    lang: str = "ja",
) -> str | None:
    """Call Claude API for STRUCT CODE consultation.

    Returns answer text or None on failure.
    """
    if not settings.claude_api_key:
        logger.warning("Consultation skipped: no Claude API key")
        return None

    type_info = get_type_info(type_code, lang=lang)
    if not type_info:
        return None

    ax = axes if len(axes) >= 5 else [0.5] * 5
    # Display axes in 0-1000 scale
    ax_display = [round(v * 1000) for v in ax]

    # Build extra context from struct_result
    extra_context = ""
    if struct_result:
        # Natal type info
        natal = struct_result.get("natal")
        if natal:
            natal_type = natal.get("type", "")
            natal_name = natal.get("type_name", "")
            natal_axes = natal.get("axes", [])
            natal_display = [round(v * 1000) for v in natal_axes] if natal_axes else []
            if lang == "en":
                extra_context += f"- Natal Type (innate): {natal_name} ({natal_type})\n"
                if natal_display:
                    extra_context += f"- Natal 5-Axis Scores (0-1000): Act={natal_display[0]}, Jdg={natal_display[1]}, Chc={natal_display[2]}, Res={natal_display[3]}, Awa={natal_display[4]}\n"
            else:
                extra_context += f"- ネイタルタイプ（本来の構造）: {natal_name} ({natal_type})\n"
                if natal_display:
                    extra_context += f"- ネイタル5軸スコア (0-1000): 起動={natal_display[0]}, 判断={natal_display[1]}, 選択={natal_display[2]}, 共鳴={natal_display[3]}, 自覚={natal_display[4]}\n"

        # Axis states (activation/stable/suppression)
        axis_states = struct_result.get("axis_states", [])
        if axis_states:
            state_labels_ja = {"activation": "活性化", "stable": "安定", "suppression": "抑制"}
            state_labels_en = {"activation": "Activation", "stable": "Stable", "suppression": "Suppression"}
            labels = state_labels_en if lang == "en" else state_labels_ja
            states_str = ", ".join(
                f"{s.get('axis', '')}: {labels.get(s.get('state', ''), s.get('state', ''))}"
                for s in axis_states
            )
            if lang == "en":
                extra_context += f"- Axis States: {states_str}\n"
            else:
                extra_context += f"- 軸の状態: {states_str}\n"

        # Design gap
        design_gap = struct_result.get("design_gap", {})
        if design_gap:
            gap_items = []
            for axis_name, gap_val in design_gap.items():
                gap_items.append(f"{axis_name}: {gap_val:+.3f}")
            if lang == "en":
                extra_context += f"- Design Gap (Current - Natal): {', '.join(gap_items)}\n"
            else:
                extra_context += f"- Design Gap（現在-本来の差分）: {', '.join(gap_items)}\n"

        # Temporal theme
        temporal = struct_result.get("temporal")
        if temporal:
            theme = temporal.get("current_theme", "")
            theme_desc = temporal.get("theme_description", "")
            if theme:
                if lang == "en":
                    extra_context += f"- Current Period Theme: {theme}\n"
                    if theme_desc:
                        extra_context += f"  {theme_desc[:200]}\n"
                else:
                    extra_context += f"- 現在の時期テーマ: {theme}\n"
                    if theme_desc:
                        extra_context += f"  {theme_desc[:200]}\n"

        # TOP3 candidates
        top_candidates = struct_result.get("top_candidates", [])
        if top_candidates:
            if lang == "en":
                lines = ["- TOP 3 Candidates:"]
                for i, c in enumerate(top_candidates[:3], 1):
                    lines.append(f"  #{i}: {c.get('name', '')} ({c.get('code', '')}) — {c.get('archetype', '')} — Match: {c.get('score', 0) * 100:.1f}%")
            else:
                lines = ["- TOP3候補:"]
                for i, c in enumerate(top_candidates[:3], 1):
                    lines.append(f"  #{i}: {c.get('name', '')} ({c.get('code', '')}) — {c.get('archetype', '')} — 一致度: {c.get('score', 0) * 100:.1f}%")
            extra_context += "\n".join(lines) + "\n"

        birth_date = struct_result.get("birth_date")
        birth_location = struct_result.get("birth_location")
        if birth_date or birth_location:
            if lang == "en":
                extra_context += f"- Birth: {birth_date or '?'}, {birth_location or '?'}\n"
            else:
                extra_context += f"- 生年月日: {birth_date or '?'}, 出生地: {birth_location or '?'}\n"

        struct_code = struct_result.get("struct_code")
        if struct_code:
            extra_context += f"- STRUCT CODE: {struct_code}\n"

    if extra_context:
        extra_context = "\n" + extra_context

    prompt_template = CONSULTATION_SYSTEM_PROMPT_EN if lang == "en" else CONSULTATION_SYSTEM_PROMPT_JA
    system = prompt_template.format(
        type_name=type_info["name"],
        type_code=type_code,
        archetype=type_info["archetype"],
        description=type_info["description"][:500],
        decision_making_style=type_info["decision_making_style"][:300],
        choice_pattern=type_info["choice_pattern"][:300],
        interpersonal_dynamics=type_info["interpersonal_dynamics"][:300],
        growth_path=type_info["growth_path"][:300],
        blindspot=type_info["blindspot"][:300],
        ax0=ax_display[0], ax1=ax_display[1], ax2=ax_display[2], ax3=ax_display[3], ax4=ax_display[4],
        extra_context=extra_context,
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
