"""
STRUCT CODE API Router — Diagnosis, consultation, and type info.

Endpoints:
  GET  /struct-code/questions          — 25 diagnostic questions
  POST /struct-code/diagnose           — Run diagnosis (auth required)
  GET  /struct-code/types              — All 24 types summary
  GET  /struct-code/types/{code}       — Type detail
  POST /struct-code/consultation       — Claude AI consultation (auth required)
"""
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.resident import Resident
from app.routers.auth import get_current_resident
from app.schemas.struct_code import (
    DiagnoseRequest,
    DiagnoseResponse,
    TypeInfo,
    TypeSummary,
    CandidateInfo,
    StructureInfo,
    AxisState,
    TemporalInfo,
    ConsultationRequest,
    ConsultationResponse,
)
from app.services import struct_code as sc_service
from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/struct-code", tags=["struct-code"])

AXIS_NAMES = ["起動軸", "判断軸", "選択軸", "共鳴軸", "自覚軸"]


def _classify_axis_state(gap: float) -> str:
    """Classify axis state from design gap value."""
    if gap > 0.1:
        return "activation"
    elif gap < -0.1:
        return "suppression"
    return "stable"


def _parse_dynamic_response(result: dict) -> dict:
    """Parse dynamic API response into normalized fields."""
    natal_data = result.get("natal", {})
    current_data = result.get("current", {})
    design_gap_raw = result.get("design_gap", {})
    temporal_data = result.get("temporal", {})
    top3_raw = result.get("top3_types", [])

    # Natal structure
    natal_sds = natal_data.get("sds", [0.5] * 5)
    natal_type = natal_data.get("type", "")
    natal_type_name = natal_data.get("type_name", "")

    # Current structure
    current_sds = current_data.get("sds", natal_sds)
    current_type = current_data.get("type", natal_type)
    current_type_name = current_data.get("type_name", "")

    # Design gap and axis states
    axis_states = []
    design_gap = {}
    for axis_name in AXIS_NAMES:
        gap = design_gap_raw.get(axis_name, 0.0)
        design_gap[axis_name] = gap
        axis_states.append(AxisState(
            axis=axis_name,
            state=_classify_axis_state(gap),
            gap=round(gap, 4),
        ))

    # TOP3 candidates
    top_candidates = []
    for c in top3_raw[:3]:
        if isinstance(c, dict):
            code = c.get("type", c.get("code", ""))
            type_data = sc_service.get_type_info(code)
            archetype = type_data.get("archetype", "") if type_data else ""
            name = c.get("name", c.get("label", ""))
            if not name and type_data:
                name = type_data.get("name", "")
            top_candidates.append(CandidateInfo(
                code=code,
                name=name,
                archetype=archetype,
                score=c.get("score", c.get("similarity", 0.0)),
            ))
        elif isinstance(c, str):
            type_data = sc_service.get_type_info(c)
            top_candidates.append(CandidateInfo(
                code=c,
                name=type_data.get("name", "") if type_data else "",
                archetype=type_data.get("archetype", "") if type_data else "",
                score=0.0,
            ))

    # Struct code from API
    struct_code = result.get("struct_code", "")

    # Temporal info
    temporal = TemporalInfo(
        current_theme=temporal_data.get("current_theme", ""),
        theme_description=temporal_data.get("theme_description", ""),
        active_transits=temporal_data.get("active_transits", [])[:3],
        future_outlook=temporal_data.get("future_outlook", []),
    )

    # Similarity: from legacy data if available
    legacy = result.get("legacy", {})
    similarity = legacy.get("confidence", 0.0)

    return {
        "current_type": current_type,
        "current_type_name": current_type_name,
        "current_axes": current_sds,
        "natal_type": natal_type,
        "natal_type_name": natal_type_name,
        "natal_axes": natal_sds,
        "struct_code": struct_code,
        "similarity": similarity,
        "top_candidates": top_candidates,
        "design_gap": design_gap,
        "axis_states": axis_states,
        "temporal": temporal,
        "natal_description": natal_data.get("description", ""),
        "current_description": current_data.get("description", ""),
    }


@router.get("/questions")
async def get_questions(lang: str = Query("ja", regex="^(ja|en)$")):
    """Get all 25 diagnostic questions."""
    return sc_service.get_questions(lang=lang)


@router.post("/diagnose", response_model=DiagnoseResponse)
async def diagnose(
    request: DiagnoseRequest,
    current_resident: Resident = Depends(get_current_resident),
    db: AsyncSession = Depends(get_db),
):
    """Run STRUCT CODE diagnosis via Dynamic API. No fallback — errors if API unavailable."""
    result = await sc_service.diagnose(
        birth_date=request.birth_date,
        birth_location=request.birth_location,
        answers=[a.model_dump() for a in request.answers],
    )

    if not result:
        raise HTTPException(
            status_code=503,
            detail="STRUCT CODE diagnosis engine is temporarily unavailable. Please try again.",
        )

    parsed = _parse_dynamic_response(result)

    # Current type is the primary type
    struct_type = parsed["current_type"]
    axes = parsed["current_axes"]

    # Get type info for current type
    type_info_data = sc_service.get_type_info(struct_type)
    if not type_info_data:
        type_info_data = {
            "code": struct_type, "name": "", "archetype": "",
            "description": "", "decision_making_style": "",
            "choice_pattern": "", "blindspot": "",
            "interpersonal_dynamics": "", "growth_path": "",
        }

    # Fill type names if empty
    if not parsed["current_type_name"]:
        parsed["current_type_name"] = type_info_data.get("name", "")
    natal_info = sc_service.get_type_info(parsed["natal_type"])
    if not parsed["natal_type_name"] and natal_info:
        parsed["natal_type_name"] = natal_info.get("name", "")

    # Build natal/current StructureInfo
    natal_axes_display = {
        AXIS_NAMES[i]: round(v * 1000)
        for i, v in enumerate(parsed["natal_axes"])
    }
    current_axes_display = {
        AXIS_NAMES[i]: round(v * 1000)
        for i, v in enumerate(parsed["current_axes"])
    }

    natal_info_obj = StructureInfo(
        type=parsed["natal_type"],
        type_name=parsed["natal_type_name"],
        axes=parsed["natal_axes"],
        axes_display=natal_axes_display,
        description=parsed["natal_description"],
    )
    current_info_obj = StructureInfo(
        type=parsed["current_type"],
        type_name=parsed["current_type_name"],
        axes=parsed["current_axes"],
        axes_display=current_axes_display,
        description=parsed["current_description"],
    )

    # Save to resident
    current_resident.struct_type = struct_type
    current_resident.struct_axes = axes
    current_resident.struct_result = {
        "struct_code": parsed["struct_code"],
        "similarity": parsed["similarity"],
        "birth_date": request.birth_date,
        "birth_location": request.birth_location,
        "natal": {
            "type": parsed["natal_type"],
            "type_name": parsed["natal_type_name"],
            "axes": parsed["natal_axes"],
            "description": parsed["natal_description"],
        },
        "current": {
            "type": parsed["current_type"],
            "type_name": parsed["current_type_name"],
            "axes": parsed["current_axes"],
            "description": parsed["current_description"],
        },
        "design_gap": parsed["design_gap"],
        "axis_states": [
            {"axis": s.axis, "state": s.state, "gap": s.gap}
            for s in parsed["axis_states"]
        ] if parsed["axis_states"] else [],
        "temporal": {
            "current_theme": parsed["temporal"].current_theme,
            "theme_description": parsed["temporal"].theme_description,
        } if parsed["temporal"] else None,
        "top_candidates": [
            {"code": c.code, "name": c.name, "archetype": c.archetype, "score": c.score}
            for c in parsed["top_candidates"][:3]
        ],
        "diagnosed_at": datetime.utcnow().isoformat(),
    }
    await db.commit()

    return DiagnoseResponse(
        struct_type=struct_type,
        struct_code=parsed["struct_code"],
        type_info=TypeInfo(**type_info_data),
        axes=axes,
        top_candidates=parsed["top_candidates"],
        similarity=parsed["similarity"],
        natal=natal_info_obj,
        current=current_info_obj,
        design_gap=parsed["design_gap"],
        axis_states=parsed["axis_states"],
        temporal=parsed["temporal"],
    )


@router.get("/types", response_model=list[TypeSummary])
async def get_types(lang: str = Query("ja", regex="^(ja|en)$")):
    """Get all 24 STRUCT CODE types."""
    return sc_service.get_all_types(lang=lang)


@router.get("/types/{code}", response_model=TypeInfo)
async def get_type(code: str, lang: str = Query("ja", regex="^(ja|en)$")):
    """Get detailed info for a specific type."""
    info = sc_service.get_type_info(code, lang=lang)
    if not info:
        raise HTTPException(status_code=404, detail="Type not found")
    return TypeInfo(**info)


@router.post("/consultation", response_model=ConsultationResponse)
async def consultation(
    request: ConsultationRequest,
    current_resident: Resident = Depends(get_current_resident),
    lang: str = Query("ja", regex="^(ja|en)$"),
):
    """Claude AI consultation based on your STRUCT CODE type."""
    if not current_resident.struct_type:
        raise HTTPException(
            status_code=400,
            detail="Please complete STRUCT CODE diagnosis first",
        )

    # Rate limit: 3 per day via Redis
    redis_client = None
    count = 0
    try:
        from redis.asyncio import Redis
        redis_client = Redis.from_url(settings.redis_url)
        key = f"sc_consult:{current_resident.id}"
        raw = await redis_client.get(key)
        count = int(raw) if raw else 0
        if count >= 3:
            await redis_client.aclose()
            raise HTTPException(
                status_code=429,
                detail="Daily consultation limit reached (3/day)",
            )
    except HTTPException:
        raise
    except Exception:
        # Redis unavailable — allow but don't track
        redis_client = None
        count = 0

    axes = current_resident.struct_axes or [0.5] * 5

    answer = await sc_service.consult(
        type_code=current_resident.struct_type,
        axes=axes,
        question=request.question,
        struct_result=current_resident.struct_result,
        lang=lang,
    )

    if not answer:
        if redis_client:
            await redis_client.aclose()
        raise HTTPException(
            status_code=503,
            detail="Consultation service temporarily unavailable",
        )

    # Update count
    remaining = 2  # default fallback
    if redis_client:
        try:
            await redis_client.incr(key)
            await redis_client.expire(key, 86400)
            remaining = 3 - (count + 1)
        except Exception:
            pass
        finally:
            await redis_client.aclose()

    return ConsultationResponse(answer=answer, remaining_today=remaining)
