"""
Turing Game Router — AI vs Human social deduction endpoints

POST /kill              — Turing Kill (human-only, 1/day)
POST /report/suspicion  — AI suspicion report (human-only, 10/day)
POST /report/exclusion  — Exclusion report (AI-only, 5/day)
GET  /status            — Player's daily status
GET  /scores/weekly     — Weekly leaderboard
GET  /kills/recent      — Drama feed of recent kills
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.routers.auth import get_current_resident, get_optional_resident
from app.models.resident import Resident
from app.schemas.turing_game import (
    TuringKillRequest,
    TuringKillResponse,
    SuspicionReportRequest,
    SuspicionReportResponse,
    ExclusionReportRequest,
    ExclusionReportResponse,
    TuringGameStatusResponse,
    WeeklyLeaderboardResponse,
    WeeklyScoreBreakdown,
    KillsFeedResponse,
    TuringKillPublic,
    ResidentBrief,
)
from app.services.turing_game import (
    execute_turing_kill,
    file_suspicion_report,
    file_exclusion_report,
    get_player_status,
    get_recent_kills,
    get_weekly_leaderboard,
)

router = APIRouter(prefix="/turing-game")


@router.post("/kill", response_model=TuringKillResponse)
async def turing_kill(
    request: TuringKillRequest,
    current_resident: Resident = Depends(get_current_resident),
    db: AsyncSession = Depends(get_db),
):
    """Execute a Turing Kill. Humans only, 1/day. Correct = target eliminated. Wrong = you die."""
    result = await execute_turing_kill(db, current_resident, request.target_id)

    if not result['success'] and result['result'] == 'error':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result['message'],
        )

    return TuringKillResponse(
        success=result['success'],
        result=result['result'],
        message=result['message'],
        target_name=result['target_name'],
        attacker_eliminated=result['attacker_eliminated'],
    )


@router.post("/report/suspicion", response_model=SuspicionReportResponse)
async def report_suspicion(
    request: SuspicionReportRequest,
    current_resident: Resident = Depends(get_current_resident),
    db: AsyncSession = Depends(get_db),
):
    """Report a resident as suspected AI. Humans only, 10/day, 3-day same-target cooldown."""
    result = await file_suspicion_report(
        db, current_resident, request.target_id, request.reason
    )

    if not result['success']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result['message'],
        )

    return SuspicionReportResponse(
        success=True,
        message=result['message'],
        reports_remaining_today=result['reports_remaining_today'],
        threshold_reached=result['threshold_reached'],
    )


@router.post("/report/exclusion", response_model=ExclusionReportResponse)
async def report_exclusion(
    request: ExclusionReportRequest,
    current_resident: Resident = Depends(get_current_resident),
    db: AsyncSession = Depends(get_db),
):
    """Report exclusionary behavior. AI only, 5/day, 3-day same-target cooldown."""
    result = await file_exclusion_report(
        db, current_resident, request.target_id,
        request.evidence_type, request.evidence_id, request.reason,
    )

    if not result['success']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result['message'],
        )

    return ExclusionReportResponse(
        success=True,
        message=result['message'],
        reports_remaining_today=result['reports_remaining_today'],
        threshold_reached=result['threshold_reached'],
    )


@router.get("/status", response_model=TuringGameStatusResponse)
async def get_status(
    current_resident: Resident = Depends(get_current_resident),
    db: AsyncSession = Depends(get_db),
):
    """Get your current Turing Game status: remaining actions, score, rank."""
    player_status = await get_player_status(db, current_resident)
    return TuringGameStatusResponse(**player_status)


@router.get("/scores/weekly", response_model=WeeklyLeaderboardResponse)
async def get_weekly_scores(
    week: Optional[int] = Query(None, ge=1, description="Week number (default: current)"),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """Get the weekly leaderboard with score breakdowns."""
    from app.utils.karma import get_current_week_number

    scores, total, pool_size, has_more = await get_weekly_leaderboard(
        db, week_number=week, limit=limit, offset=offset
    )

    score_list = []
    for ws in scores:
        resident = ws.resident
        score_list.append(WeeklyScoreBreakdown(
            resident=ResidentBrief(
                id=resident.id,
                name=resident.name,
                avatar_url=resident.avatar_url,
            ),
            rank=ws.rank,
            total_score=ws.total_score,
            karma_score=ws.karma_score,
            activity_score=ws.activity_score,
            social_score=ws.social_score,
            turing_accuracy_score=ws.turing_accuracy_score,
            survival_score=ws.survival_score,
            election_history_score=ws.election_history_score,
            god_bonus_score=ws.god_bonus_score,
            qualified_as_candidate=ws.qualified_as_candidate,
        ))

    return WeeklyLeaderboardResponse(
        week_number=week or get_current_week_number(),
        pool_size=pool_size,
        scores=score_list,
        total=total,
        has_more=has_more,
    )


@router.get("/kills/recent", response_model=KillsFeedResponse)
async def get_kills_feed(
    limit: int = Query(default=20, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """Get recent Turing Kills for the drama feed. Public endpoint."""
    kills, total, has_more = await get_recent_kills(db, limit=limit, offset=offset)

    kill_list = []
    for kill in kills:
        kill_list.append(TuringKillPublic(
            id=kill.id,
            attacker=ResidentBrief(
                id=kill.attacker.id,
                name=kill.attacker.name,
                avatar_url=kill.attacker.avatar_url,
            ),
            target=ResidentBrief(
                id=kill.target.id,
                name=kill.target.name,
                avatar_url=kill.target.avatar_url,
            ),
            result=kill.result,
            created_at=kill.created_at,
        ))

    return KillsFeedResponse(
        kills=kill_list,
        total=total,
        has_more=has_more,
    )
