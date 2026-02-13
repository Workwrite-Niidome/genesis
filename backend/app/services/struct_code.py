"""
STRUCT CODE Service — Type diagnosis, consultation, and data access.

Provides:
- Local JSON data access (types, questions) with bilingual support (ja/en)
- STRUCT CODE API client (diagnosis via Docker container)
- Dify RAG consultation
- Random answer generation for AI agents
"""
import json
import logging
import math
import os
import random
from dataclasses import dataclass
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
# AI CONSULTATION (Dify RAG)
# ═══════════════════════════════════════════════════════════════════════════


def _build_user_data(
    type_code: str,
    axes: list[float],
    struct_result: dict | None,
    lang: str,
) -> str:
    """Build user-specific diagnosis data string for system prompt."""
    ax = axes if len(axes) >= 5 else [0.5] * 5
    ax_display = [round(v * 1000) for v in ax]
    axis_names_ja = ["起動", "判断", "選択", "共鳴", "自覚"]
    axis_names_en = ["Activation", "Judgment", "Choice", "Resonance", "Awareness"]
    axis_names = axis_names_en if lang == "en" else axis_names_ja

    lines = []

    # STRUCT CODE and birth info
    if struct_result:
        struct_code = struct_result.get("struct_code", "")
        if struct_code:
            lines.append(f"STRUCT CODE: {struct_code}")

        birth_date = struct_result.get("birth_date", "")
        birth_location = struct_result.get("birth_location", "")
        if birth_date:
            # Calculate age
            try:
                from datetime import date
                bd = date.fromisoformat(birth_date)
                today = date.today()
                age = today.year - bd.year - ((today.month, today.day) < (bd.month, bd.day))
                lines.append(f"{'生年月日' if lang != 'en' else 'Birth Date'}: {birth_date}（{age}{'歳' if lang != 'en' else ' years old'}）")
            except Exception:
                lines.append(f"{'生年月日' if lang != 'en' else 'Birth Date'}: {birth_date}")
        if birth_location:
            lines.append(f"{'出生地' if lang != 'en' else 'Birth Location'}: {birth_location}")

    # Current axes
    ax_str = ", ".join(f"{axis_names[i]}={ax_display[i]}" for i in range(5))
    lines.append(f"{'カレント5軸スコア (0-1000)' if lang != 'en' else 'Current 5-Axis Scores (0-1000)'}: {ax_str}")

    if struct_result:
        # Natal type info
        natal = struct_result.get("natal")
        if natal:
            natal_type = natal.get("type", "")
            natal_name = natal.get("type_name", "")
            natal_axes = natal.get("axes", [])
            natal_display = [round(v * 1000) for v in natal_axes] if natal_axes else []
            if lang == "en":
                lines.append(f"Natal Type (innate): {natal_name} ({natal_type})")
                if natal_display:
                    nax_str = ", ".join(f"{axis_names_en[i]}={natal_display[i]}" for i in range(5))
                    lines.append(f"Natal 5-Axis Scores (0-1000): {nax_str}")
            else:
                lines.append(f"ネイタルタイプ（本来の構造）: {natal_name} ({natal_type})")
                if natal_display:
                    nax_str = ", ".join(f"{axis_names_ja[i]}={natal_display[i]}" for i in range(5))
                    lines.append(f"ネイタル5軸スコア (0-1000): {nax_str}")

        # Axis states
        axis_states = struct_result.get("axis_states", [])
        if axis_states:
            state_labels = (
                {"activation": "Activation", "stable": "Stable", "suppression": "Suppression"}
                if lang == "en"
                else {"activation": "活性化", "stable": "安定", "suppression": "抑制"}
            )
            states_str = ", ".join(
                f"{s.get('axis', '')}: {state_labels.get(s.get('state', ''), s.get('state', ''))}"
                for s in axis_states
            )
            lines.append(f"{'軸の状態' if lang != 'en' else 'Axis States'}: {states_str}")

        # Design gap
        design_gap = struct_result.get("design_gap", {})
        if design_gap:
            gap_items = [f"{axis_name}: {gap_val:+.3f}" for axis_name, gap_val in design_gap.items()]
            lines.append(f"DesignGap{'（現在-本来の差分）' if lang != 'en' else ' (Current - Natal)'}: {', '.join(gap_items)}")

        # Temporal theme
        temporal = struct_result.get("temporal")
        if temporal:
            theme = temporal.get("current_theme", "")
            theme_desc = temporal.get("theme_description", "")
            if theme:
                lines.append(f"{'現在の時期テーマ' if lang != 'en' else 'Current Period Theme'}: {theme}")
                if theme_desc:
                    lines.append(f"  {theme_desc[:300]}")

        # TOP3 candidates
        top_candidates = struct_result.get("top_candidates", [])
        if top_candidates:
            lines.append(f"{'タイプ候補TOP3' if lang != 'en' else 'TOP 3 Candidates'}:")
            for i, c in enumerate(top_candidates[:3], 1):
                score = c.get("score", 0)
                score_pct = f"{score * 100:.1f}%" if score <= 1.0 else f"{score:.1f}%"
                name = c.get("name", "")
                code = c.get("code", "")
                archetype = c.get("archetype", "")
                if lang == "en":
                    lines.append(f"  #{i}: {name} ({code}) — {archetype} — Match: {score_pct}")
                else:
                    lines.append(f"  {i}位: {code}（{name}）適合度 {score_pct}")

    return "\n".join(lines)


DIFY_API_URL = "https://api.dify.ai/v1"


@dataclass
class ConsultResult:
    answer: str
    conversation_id: str | None = None
    message_id: str | None = None


class ConsultationError(Exception):
    """Raised when consultation fails with a specific diagnosable reason."""
    pass


async def consult(
    type_code: str,
    axes: list[float],
    question: str,
    struct_result: dict | None = None,
    lang: str = "ja",
    conversation_id: str | None = None,
) -> ConsultResult:
    """Call Dify RAG API for STRUCT CODE consultation.

    For new conversations (conversation_id=None): sends diagnosis data + question.
    For continued conversations: sends question only (Dify maintains context).

    Returns ConsultResult on success.
    Raises ConsultationError with a specific message on failure.
    """
    api_key = settings.dify_api_key
    if not api_key:
        logger.error("Dify API key not set — consultation unavailable")
        raise ConsultationError("API key not configured")

    # Build query: include diagnosis data only for new conversations
    if conversation_id:
        full_query = question
    else:
        try:
            user_data = _build_user_data(type_code, axes, struct_result, lang)
        except Exception as e:
            logger.error(f"[Dify] Failed to build user_data: {e}")
            raise ConsultationError(f"Failed to build diagnosis data: {e}")

        full_query = f"""【診断データ】
{user_data}

【質問】
{question}"""

    result = await _call_dify(full_query, type_code, conversation_id)

    # If conversation_id was expired/invalid, retry as new conversation
    if result is None and conversation_id:
        logger.warning("[Dify] Conversation may be expired, retrying as new conversation")
        try:
            user_data = _build_user_data(type_code, axes, struct_result, lang)
        except Exception as e:
            logger.error(f"[Dify] Failed to build user_data on retry: {e}")
            raise ConsultationError(f"Failed to build diagnosis data on retry: {e}")

        retry_query = f"""【診断データ】
{user_data}

【質問】
{question}"""
        result = await _call_dify(retry_query, type_code, None)

    if result is None:
        raise ConsultationError(_last_dify_error or "Dify returned empty response")

    return result


# Module-level variable to track last Dify call failure reason
_last_dify_error: str = ""


async def _call_dify(
    query: str,
    user: str,
    conversation_id: str | None,
) -> ConsultResult | None:
    """Low-level Dify chat-messages call using streaming mode.

    Uses streaming to avoid Dify's gateway timeout (504) on long queries.
    Collects SSE chunks and assembles the full answer.
    Sets _last_dify_error with the failure reason on failure.
    """
    global _last_dify_error
    _last_dify_error = ""
    api_key = settings.dify_api_key

    payload: dict = {
        "inputs": {},
        "query": query,
        "response_mode": "streaming",
        "user": user,
    }
    if conversation_id:
        payload["conversation_id"] = conversation_id

    try:
        logger.warning(f"[Dify] Calling chat-messages API streaming (query_len={len(query)}, conv_id={conversation_id})")
        async with httpx.AsyncClient(timeout=180.0) as client:
            async with client.stream(
                "POST",
                f"{DIFY_API_URL}/chat-messages",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            ) as response:
                logger.warning(f"[Dify] Stream response status={response.status_code}")

                if response.status_code != 200:
                    body = (await response.aread()).decode("utf-8", errors="replace")[:500]
                    logger.error(f"[Dify] API error: {response.status_code} — {body}")
                    _last_dify_error = f"Dify API returned {response.status_code}"
                    return None

                # Parse SSE stream
                answer_parts: list[str] = []
                result_conversation_id: str | None = None
                result_message_id: str | None = None

                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    data_str = line[6:]
                    if not data_str or data_str == "[DONE]":
                        continue
                    try:
                        data = json.loads(data_str)
                    except json.JSONDecodeError:
                        continue

                    event = data.get("event", "")
                    if event == "message":
                        answer_parts.append(data.get("answer", ""))
                        if not result_conversation_id:
                            result_conversation_id = data.get("conversation_id")
                        if not result_message_id:
                            result_message_id = data.get("message_id")
                    elif event == "message_end":
                        if not result_conversation_id:
                            result_conversation_id = data.get("conversation_id")
                        if not result_message_id:
                            result_message_id = data.get("message_id")
                    elif event == "error":
                        err_msg = data.get("message", "Unknown error")
                        logger.error(f"[Dify] Stream error event: {err_msg}")
                        _last_dify_error = f"Dify stream error: {err_msg}"
                        return None

                answer = "".join(answer_parts)
                if not answer:
                    logger.warning("[Dify] Stream completed but empty answer")
                    _last_dify_error = "Dify returned empty answer (streaming)"
                    return None

                logger.warning(f"[Dify] Got streamed response (len={len(answer)}, conv_id={result_conversation_id})")
                return ConsultResult(
                    answer=answer,
                    conversation_id=result_conversation_id,
                    message_id=result_message_id,
                )

    except httpx.TimeoutException:
        logger.error("[Dify] Request timed out (180s)")
        _last_dify_error = "Dify API timed out (180s)"
        return None
    except Exception as e:
        logger.error(f"[Dify] API error: {type(e).__name__}: {e}")
        _last_dify_error = f"Dify API error: {type(e).__name__}: {e}"
        return None
