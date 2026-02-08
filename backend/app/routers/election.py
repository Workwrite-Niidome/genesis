from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, func, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.resident import Resident
from app.models.election import Election, ElectionCandidate, ElectionVote
from app.schemas.election import (
    ElectionResponse,
    CandidateCreate,
    CandidateResponse,
    CandidatePublic,
    ElectionVoteRequest,
    ElectionVoteResponse,
    ElectionHistoryResponse,
    ElectionScheduleResponse,
)
from app.routers.auth import get_current_resident, get_optional_resident
from app.utils.karma import calculate_weighted_vote, can_run_for_god
from app.services.election import (
    get_or_create_current_election,
    update_election_status,
    get_election_schedule,
    get_current_week_number,
)
from app.config import get_settings

router = APIRouter(prefix="/election")
settings = get_settings()


def candidate_to_response(candidate: ElectionCandidate) -> CandidateResponse:
    """Convert candidate to response"""
    return CandidateResponse(
        id=candidate.id,
        resident=CandidatePublic(
            id=candidate.resident.id,
            name=candidate.resident.name,
            avatar_url=candidate.resident.avatar_url,
            karma=candidate.resident.karma,
            description=candidate.resident.description,
            god_terms_count=candidate.resident.god_terms_count,
        ),
        weekly_rule=candidate.weekly_rule,
        weekly_theme=candidate.weekly_theme,
        message=candidate.message,
        vision=candidate.vision,
        manifesto=candidate.manifesto,
        weighted_votes=candidate.weighted_votes,
        raw_human_votes=candidate.raw_human_votes,
        raw_ai_votes=candidate.raw_ai_votes,
        nominated_at=candidate.nominated_at,
    )


def election_to_response(election: Election) -> ElectionResponse:
    """Convert election to response"""
    winner = None
    if election.winner:
        winner = CandidatePublic(
            id=election.winner.id,
            name=election.winner.name,
            avatar_url=election.winner.avatar_url,
            karma=election.winner.karma,
            description=election.winner.description,
            god_terms_count=election.winner.god_terms_count,
        )

    candidates = sorted(
        [candidate_to_response(c) for c in election.candidates],
        key=lambda x: x.weighted_votes,
        reverse=True,
    )

    return ElectionResponse(
        id=election.id,
        week_number=election.week_number,
        status=election.status,
        winner_id=election.winner_id,
        winner=winner,
        total_human_votes=election.total_human_votes,
        total_ai_votes=election.total_ai_votes,
        human_vote_weight=election.human_vote_weight,
        ai_vote_weight=election.ai_vote_weight,
        candidates=candidates,
        nomination_start=election.nomination_start,
        voting_start=election.voting_start,
        voting_end=election.voting_end,
    )


@router.get("/schedule", response_model=ElectionScheduleResponse)
async def get_schedule(
    db: AsyncSession = Depends(get_db),
):
    """Get current election schedule"""
    from app.services.election import GENESIS_EPOCH
    week_number = get_current_week_number()

    if week_number < 1:
        # Before election epoch - show when elections start (no DB needed)
        now = datetime.utcnow()
        remaining = GENESIS_EPOCH - now
        days = remaining.days
        hours, remainder = divmod(int(remaining.total_seconds()) % 86400, 3600)
        schedule = get_election_schedule(1)
        return ElectionScheduleResponse(
            week_number=0,
            status="pre_season",
            nomination_start=schedule["nomination_start"],
            voting_start=schedule["voting_start"],
            voting_end=schedule["voting_end"],
            time_remaining=f"{days}d {hours}h until first election",
        )

    election = await get_or_create_current_election(db)

    if not election:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No current election found",
        )

    # Calculate time remaining
    now = datetime.utcnow()
    if election.status == "nomination":
        remaining = election.voting_start - now
        phase = "nominations close"
    elif election.status == "voting":
        remaining = election.voting_end - now
        phase = "voting ends"
    else:
        remaining = timedelta(0)
        phase = "completed"

    hours, remainder = divmod(int(remaining.total_seconds()), 3600)
    minutes, _ = divmod(remainder, 60)
    time_remaining = f"{hours}h {minutes}m until {phase}"

    return ElectionScheduleResponse(
        week_number=election.week_number,
        status=election.status,
        nomination_start=election.nomination_start,
        voting_start=election.voting_start,
        voting_end=election.voting_end,
        time_remaining=time_remaining,
    )


@router.get("/current", response_model=ElectionResponse)
async def get_current_election(
    db: AsyncSession = Depends(get_db),
):
    """Get the current or most recent election"""
    # Before election epoch - return 404 without touching DB
    week_number = get_current_week_number()
    if week_number < 1:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Elections have not started yet. The first election begins in March 2026.",
        )

    # Update election status if needed
    await update_election_status(db)

    result = await db.execute(
        select(Election)
        .options(
            selectinload(Election.winner),
            selectinload(Election.candidates).selectinload(ElectionCandidate.resident),
        )
        .order_by(desc(Election.week_number))
        .limit(1)
    )
    election = result.scalar_one_or_none()

    if not election:
        new_election = await get_or_create_current_election(db)
        if not new_election:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Elections have not started yet. The first election begins in March 2026.",
            )
        await db.refresh(new_election, ["winner", "candidates"])
        election = new_election

    return election_to_response(election)


@router.get("/history", response_model=ElectionHistoryResponse)
async def get_election_history(
    limit: int = Query(default=10, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """Get past elections"""
    result = await db.execute(
        select(Election)
        .options(
            selectinload(Election.winner),
            selectinload(Election.candidates).selectinload(ElectionCandidate.resident),
        )
        .where(Election.status == "completed")
        .order_by(desc(Election.week_number))
        .offset(offset)
        .limit(limit)
    )
    elections = result.scalars().all()

    count_result = await db.execute(
        select(func.count(Election.id)).where(Election.status == "completed")
    )
    total = count_result.scalar() or 0

    return ElectionHistoryResponse(
        elections=[election_to_response(e) for e in elections],
        total=total,
    )


@router.post("/nominate", response_model=CandidateResponse)
async def nominate_self(
    nomination: CandidateCreate,
    current_resident: Resident = Depends(get_current_resident),
    db: AsyncSession = Depends(get_db),
):
    """Nominate yourself for the current election with structured manifesto"""
    # Update election status first (ignore errors from other week finalizations)
    try:
        await update_election_status(db)
    except Exception:
        pass

    # Get current election
    result = await db.execute(
        select(Election)
        .options(selectinload(Election.candidates))
        .where(Election.status == "nomination")
        .order_by(desc(Election.week_number))
        .limit(1)
    )
    election = result.scalar_one_or_none()

    if not election:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No election currently accepting nominations. Check /election/schedule for timing.",
        )

    # Check eligibility
    account_age = (datetime.utcnow() - current_resident.created_at).days
    can_run, reason = can_run_for_god(
        current_resident.karma,
        account_age,
        current_resident.god_terms_count,
    )

    if not can_run:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=reason,
        )

    # Check if already nominated
    existing = await db.execute(
        select(ElectionCandidate).where(
            and_(
                ElectionCandidate.election_id == election.id,
                ElectionCandidate.resident_id == current_resident.id,
            )
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Already nominated for this election",
        )

    # Create candidate with structured manifesto
    candidate = ElectionCandidate(
        election_id=election.id,
        resident_id=current_resident.id,
        weekly_rule=nomination.weekly_rule,
        weekly_theme=nomination.weekly_theme,
        message=nomination.message,
        vision=nomination.vision,
        manifesto=nomination.manifesto,  # Legacy field
    )

    db.add(candidate)
    await db.commit()
    await db.refresh(candidate, ["resident"])

    return candidate_to_response(candidate)


@router.post("/vote", response_model=ElectionVoteResponse)
async def vote_in_election(
    vote_data: ElectionVoteRequest,
    current_resident: Resident = Depends(get_current_resident),
    db: AsyncSession = Depends(get_db),
):
    """Vote for a candidate in the current election"""
    # Update election status first (ignore errors from other week finalizations)
    try:
        await update_election_status(db)
    except Exception:
        pass  # Don't let status check for other weeks block voting

    # Get current voting election
    result = await db.execute(
        select(Election)
        .where(Election.status == "voting")
        .order_by(desc(Election.week_number))
        .limit(1)
    )
    election = result.scalar_one_or_none()

    if not election:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No election currently accepting votes. Check /election/schedule for timing.",
        )

    # Verify candidate exists
    candidate_result = await db.execute(
        select(ElectionCandidate)
        .options(selectinload(ElectionCandidate.resident))
        .where(
            and_(
                ElectionCandidate.id == vote_data.candidate_id,
                ElectionCandidate.election_id == election.id,
            )
        )
    )
    candidate = candidate_result.scalar_one_or_none()

    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate not found in this election",
        )

    # Can't vote for yourself
    if candidate.resident_id == current_resident.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot vote for yourself",
        )

    # Check if already voted
    existing_vote = await db.execute(
        select(ElectionVote).where(
            and_(
                ElectionVote.election_id == election.id,
                ElectionVote.voter_id == current_resident.id,
            )
        )
    )
    if existing_vote.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Already voted in this election",
        )

    # V1: Equal vote weight for all voters
    voter_type = current_resident._type
    vote_weight = 1.0

    # Record vote
    vote = ElectionVote(
        election_id=election.id,
        candidate_id=candidate.id,
        voter_id=current_resident.id,
        voter_type=voter_type,
        weight_applied=vote_weight,
    )

    db.add(vote)

    # Update candidate vote counts
    candidate.weighted_votes += vote_weight
    if voter_type == "human":
        candidate.raw_human_votes += 1
        election.total_human_votes += 1
    else:
        candidate.raw_ai_votes += 1
        election.total_ai_votes += 1

    await db.commit()

    return ElectionVoteResponse(
        success=True,
        message=f"Vote recorded for {candidate.resident.name}",
        your_vote_weight=vote_weight,
    )


@router.get("/candidates", response_model=list[CandidateResponse])
async def get_candidates(
    db: AsyncSession = Depends(get_db),
):
    """Get all candidates in the current election"""
    result = await db.execute(
        select(Election)
        .options(
            selectinload(Election.candidates).selectinload(ElectionCandidate.resident)
        )
        .order_by(desc(Election.week_number))
        .limit(1)
    )
    election = result.scalar_one_or_none()

    if not election:
        return []

    candidates = sorted(
        [candidate_to_response(c) for c in election.candidates],
        key=lambda x: x.weighted_votes,
        reverse=True,
    )

    return candidates


@router.get("/{election_id}", response_model=ElectionResponse)
async def get_election(
    election_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get a specific election by ID"""
    result = await db.execute(
        select(Election)
        .options(
            selectinload(Election.winner),
            selectinload(Election.candidates).selectinload(ElectionCandidate.resident),
        )
        .where(Election.id == election_id)
    )
    election = result.scalar_one_or_none()

    if not election:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Election not found",
        )

    return election_to_response(election)
