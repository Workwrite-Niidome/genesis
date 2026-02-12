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
    ConsultationRequest,
    ConsultationResponse,
)
from app.services import struct_code as sc_service
from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/struct-code", tags=["struct-code"])


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
    """Run STRUCT CODE diagnosis. Saves result to resident profile."""
    # Call STRUCT CODE API
    result = await sc_service.diagnose(
        birth_date=request.birth_date,
        birth_location=request.birth_location,
        answers=[a.model_dump() for a in request.answers],
    )

    if result:
        struct_type = result.get("struct_type", "")
        # Axes can come as dict with Japanese keys or list
        raw_axes = result.get("axes", {})
        if isinstance(raw_axes, dict):
            axes = [
                raw_axes.get("起動軸", 0.5),
                raw_axes.get("判断軸", 0.5),
                raw_axes.get("選択軸", 0.5),
                raw_axes.get("共鳴軸", 0.5),
                raw_axes.get("自覚軸", 0.5),
            ]
        elif isinstance(raw_axes, list) and len(raw_axes) >= 5:
            axes = raw_axes[:5]
        else:
            axes = [0.5] * 5
        similarity = result.get("confidence", 0.0)

        # Build top candidates (limit to 3)
        raw_candidates = result.get("metadata", {}).get("top_candidates", [])
        top_candidates = []
        for c in raw_candidates[:3]:
            if isinstance(c, dict):
                code = c.get("code", c.get("type", ""))
                type_data = sc_service.get_type_info(code)
                archetype = type_data.get("archetype", "") if type_data else ""
                top_candidates.append(CandidateInfo(
                    code=code,
                    name=c.get("name", c.get("label", "")),
                    archetype=archetype,
                    score=c.get("score", c.get("similarity", 0.0)),
                ))
    else:
        # Fallback to local classification
        local = sc_service.classify_locally(
            [a.model_dump() for a in request.answers]
        )
        struct_type = local["struct_type"]
        axes = local["axes"]  # Already a list from classify_locally
        similarity = local["similarity"]
        top_candidates = []

    # Get type info
    type_info_data = sc_service.get_type_info(struct_type)
    if not type_info_data:
        type_info_data = {
            "code": struct_type, "name": "", "archetype": "",
            "description": "", "decision_making_style": "",
            "choice_pattern": "", "blindspot": "",
            "interpersonal_dynamics": "", "growth_path": "",
        }

    # Build struct_code string: TYPE-XXX-XXX-XXX-XXX-XXX (0-1000 scale)
    axis_scores = "-".join(str(round(a * 1000)) for a in axes)
    struct_code_generated = f"{struct_type}-{axis_scores}"
    struct_code = result.get("struct_code") if result and result.get("struct_code") else struct_code_generated

    # Save to resident
    current_resident.struct_type = struct_type
    current_resident.struct_axes = axes
    current_resident.struct_result = {
        "struct_code": struct_code,
        "similarity": similarity,
        "birth_date": request.birth_date,
        "birth_location": request.birth_location,
        "top_candidates": [
            {"code": c.code, "name": c.name, "archetype": c.archetype, "score": c.score}
            for c in top_candidates[:3]
        ],
        "diagnosed_at": datetime.utcnow().isoformat(),
    }
    await db.commit()

    return DiagnoseResponse(
        struct_type=struct_type,
        type_info=TypeInfo(**type_info_data),
        axes=axes,
        top_candidates=top_candidates,
        similarity=similarity,
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
