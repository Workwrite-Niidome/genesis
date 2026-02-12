"""
STRUCT CODE API Router — Diagnosis, consultation, and type info.

Endpoints:
  GET  /struct-code/questions                    — 25 diagnostic questions
  POST /struct-code/diagnose                     — Run diagnosis (auth required)
  GET  /struct-code/types                        — All 24 types summary
  GET  /struct-code/types/{code}                 — Type detail
  POST /struct-code/consultation                 — AI consultation (auth required)
  GET  /struct-code/consultation/sessions        — List consultation sessions
  GET  /struct-code/consultation/sessions/{id}   — Session detail with messages
"""
import logging
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.resident import Resident
from app.models.consultation import ConsultationSession, ConsultationMessage
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
    ConsultationSessionSummary,
    ConsultationSessionDetail,
    ConsultationMessageSchema,
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

    # Struct code: use API value, or generate as TYPE-XXX-XXX-XXX-XXX-XXX (0-1000 scale)
    struct_code = result.get("struct_code", "")
    if not struct_code:
        axis_scores = "-".join(str(round(a * 1000)).zfill(3) for a in current_sds)
        struct_code = f"{current_type}-{axis_scores}"

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
    db: AsyncSession = Depends(get_db),
    lang: str = Query("ja", regex="^(ja|en)$"),
):
    """AI consultation based on your STRUCT CODE type. Supports conversation continuation."""
    if not current_resident.struct_type:
        raise HTTPException(
            status_code=400,
            detail="Please complete STRUCT CODE diagnosis first",
        )

    # Admin accounts exempt from rate limit
    RATE_LIMIT_EXEMPT = {"82417b60"}  # Administrator
    resident_id_prefix = str(current_resident.id)[:8]
    is_exempt = resident_id_prefix in RATE_LIMIT_EXEMPT
    logger.warning(f"[Consultation] resident_id={current_resident.id}, prefix={resident_id_prefix}, is_exempt={is_exempt}")

    # Rate limit: 3 per day via Redis
    redis_client = None
    count = 0
    try:
        from redis.asyncio import Redis
        redis_client = Redis.from_url(settings.redis_url)
        key = f"sc_consult:{current_resident.id}"
        raw = await redis_client.get(key)
        count = int(raw) if raw else 0
        logger.warning(f"[Consultation] count={count}, is_exempt={is_exempt}, will_block={count >= 3 and not is_exempt}")
        if count >= 3 and not is_exempt:
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

    # Look up or create session
    session = None
    dify_conversation_id = None
    if request.session_id:
        try:
            session_uuid = uuid.UUID(request.session_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid session_id")
        result = await db.execute(
            select(ConsultationSession).where(
                ConsultationSession.id == session_uuid,
                ConsultationSession.resident_id == current_resident.id,
            )
        )
        session = result.scalar_one_or_none()
        if session:
            dify_conversation_id = session.dify_conversation_id

    axes = current_resident.struct_axes or [0.5] * 5

    try:
        consult_result = await sc_service.consult(
            type_code=current_resident.struct_type,
            axes=axes,
            question=request.question,
            struct_result=current_resident.struct_result,
            lang=lang,
            conversation_id=dify_conversation_id,
        )
    except Exception:
        if redis_client:
            await redis_client.aclose()
        raise HTTPException(
            status_code=503,
            detail="Consultation service temporarily unavailable",
        )

    if not consult_result:
        if redis_client:
            await redis_client.aclose()
        raise HTTPException(
            status_code=503,
            detail="Consultation service temporarily unavailable",
        )

    # Create session if new
    if not session:
        # Generate title from first ~30 chars of question
        title = request.question[:50].strip()
        if len(request.question) > 50:
            title += "..."
        session = ConsultationSession(
            resident_id=current_resident.id,
            dify_conversation_id=consult_result.conversation_id,
            title=title,
            message_count=0,
        )
        db.add(session)
        await db.flush()
    elif consult_result.conversation_id and session.dify_conversation_id != consult_result.conversation_id:
        # Update conversation_id if Dify returned a new one (retry case)
        session.dify_conversation_id = consult_result.conversation_id

    # Save user message
    user_msg = ConsultationMessage(
        session_id=session.id,
        role="user",
        content=request.question,
    )
    db.add(user_msg)

    # Save assistant message
    assistant_msg = ConsultationMessage(
        session_id=session.id,
        role="assistant",
        content=consult_result.answer,
        dify_message_id=consult_result.message_id,
    )
    db.add(assistant_msg)

    # Update session counters
    session.message_count = (session.message_count or 0) + 2
    session.updated_at = datetime.utcnow()

    await db.flush()

    # Only count successful consultations
    remaining = 2  # default fallback
    if redis_client:
        try:
            await redis_client.incr(key)
            await redis_client.expire(key, 86400)
            remaining = 999 if is_exempt else 3 - (count + 1)
        except Exception:
            pass
        finally:
            await redis_client.aclose()
    elif is_exempt:
        remaining = 999

    return ConsultationResponse(
        answer=consult_result.answer,
        remaining_today=remaining,
        session_id=str(session.id),
        conversation_id=consult_result.conversation_id or "",
    )


@router.get("/consultation/sessions", response_model=list[ConsultationSessionSummary])
async def list_sessions(
    current_resident: Resident = Depends(get_current_resident),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(20, ge=1, le=50),
    offset: int = Query(0, ge=0),
):
    """List consultation sessions for the current resident, newest first."""
    result = await db.execute(
        select(ConsultationSession)
        .where(ConsultationSession.resident_id == current_resident.id)
        .order_by(ConsultationSession.updated_at.desc())
        .limit(limit)
        .offset(offset)
    )
    sessions = result.scalars().all()
    return [
        ConsultationSessionSummary(
            id=str(s.id),
            title=s.title or "New Consultation",
            message_count=s.message_count or 0,
            created_at=s.created_at.isoformat() if s.created_at else "",
            updated_at=s.updated_at.isoformat() if s.updated_at else "",
        )
        for s in sessions
    ]


@router.get("/consultation/sessions/{session_id}", response_model=ConsultationSessionDetail)
async def get_session(
    session_id: str,
    current_resident: Resident = Depends(get_current_resident),
    db: AsyncSession = Depends(get_db),
):
    """Get session detail with all messages."""
    try:
        session_uuid = uuid.UUID(session_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid session_id")

    result = await db.execute(
        select(ConsultationSession).where(
            ConsultationSession.id == session_uuid,
            ConsultationSession.resident_id == current_resident.id,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Fetch messages
    msg_result = await db.execute(
        select(ConsultationMessage)
        .where(ConsultationMessage.session_id == session.id)
        .order_by(ConsultationMessage.created_at.asc())
    )
    messages = msg_result.scalars().all()

    return ConsultationSessionDetail(
        id=str(session.id),
        title=session.title or "New Consultation",
        message_count=session.message_count or 0,
        messages=[
            ConsultationMessageSchema(
                id=str(m.id),
                role=m.role,
                content=m.content,
                created_at=m.created_at.isoformat() if m.created_at else "",
            )
            for m in messages
        ],
        created_at=session.created_at.isoformat() if session.created_at else "",
        updated_at=session.updated_at.isoformat() if session.updated_at else "",
    )
