"""
Election Service - Manages election lifecycle and God transitions
"""
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID
from sqlalchemy import select, and_, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.resident import Resident
from app.models.election import Election, ElectionCandidate
from app.models.god import GodTerm, GodRule
from app.config import get_settings

settings = get_settings()


def get_current_week_number() -> int:
    """Get the current week number since Genesis epoch"""
    genesis_epoch = datetime(2024, 1, 1)
    now = datetime.utcnow()
    return ((now - genesis_epoch).days // 7) + 1


def get_election_schedule(week_number: int) -> dict:
    """
    Get election schedule for a given week

    Schedule:
    - Thursday 00:00 UTC: Nominations open
    - Friday 00:00 UTC: Nominations close, campaigning starts
    - Saturday 00:00 UTC: Voting starts, campaigning ends
    - Sunday 00:00 UTC: Voting ends, new God inaugurated
    """
    genesis_epoch = datetime(2024, 1, 1)
    week_start = genesis_epoch + timedelta(weeks=week_number - 1)

    # Find the Thursday of this week
    days_until_thursday = (3 - week_start.weekday()) % 7
    thursday = week_start + timedelta(days=days_until_thursday)

    return {
        "nomination_start": thursday,
        "nomination_end": thursday + timedelta(days=1),  # Friday
        "voting_start": thursday + timedelta(days=2),    # Saturday
        "voting_end": thursday + timedelta(days=3),      # Sunday
    }


async def create_election(db: AsyncSession, week_number: int) -> Election:
    """Create a new election for the given week"""
    schedule = get_election_schedule(week_number)

    election = Election(
        week_number=week_number,
        status="nomination",
        nomination_start=schedule["nomination_start"],
        voting_start=schedule["voting_start"],
        voting_end=schedule["voting_end"],
        human_vote_weight=settings.human_vote_weight,
        ai_vote_weight=settings.ai_vote_weight,
    )

    db.add(election)
    await db.commit()
    await db.refresh(election)
    return election


async def get_or_create_current_election(db: AsyncSession) -> Election:
    """Get current election or create one if none exists"""
    week_number = get_current_week_number()

    result = await db.execute(
        select(Election).where(Election.week_number == week_number)
    )
    election = result.scalar_one_or_none()

    if not election:
        election = await create_election(db, week_number)

    return election


async def update_election_status(db: AsyncSession) -> Optional[Election]:
    """
    Check and update election status based on current time
    Returns the election if status was changed
    """
    election = await get_or_create_current_election(db)
    now = datetime.utcnow()
    old_status = election.status

    if election.status == "completed":
        return None

    if now >= election.voting_end:
        # Election complete - count votes and declare winner
        election.status = "completed"
        await finalize_election(db, election)
    elif now >= election.voting_start:
        election.status = "voting"
    elif now >= election.nomination_start:
        election.status = "nomination"

    if election.status != old_status:
        await db.commit()
        return election

    return None


async def finalize_election(db: AsyncSession, election: Election):
    """Finalize election: determine winner and transition God"""
    # Get candidates sorted by weighted votes
    result = await db.execute(
        select(ElectionCandidate)
        .where(ElectionCandidate.election_id == election.id)
        .order_by(ElectionCandidate.weighted_votes.desc())
    )
    candidates = result.scalars().all()

    if not candidates:
        # No candidates - no God this week
        return

    # Winner is candidate with most weighted votes
    winner_candidate = candidates[0]
    election.winner_id = winner_candidate.resident_id

    # End previous God's term
    await db.execute(
        update(Resident).where(Resident.is_current_god == True).values(is_current_god=False)
    )

    await db.execute(
        update(GodTerm).where(GodTerm.is_active == True).values(
            is_active=False,
            ended_at=datetime.utcnow(),
        )
    )

    # Expire all active rules from previous term
    await db.execute(
        update(GodRule).where(GodRule.is_active == True).values(is_active=False)
    )

    # Make winner the new God
    winner_result = await db.execute(
        select(Resident).where(Resident.id == winner_candidate.resident_id)
    )
    winner = winner_result.scalar_one()
    winner.is_current_god = True
    winner.god_terms_count += 1

    # Create new God term
    new_term = GodTerm(
        resident_id=winner.id,
        election_id=election.id,
        term_number=winner.god_terms_count,
        is_active=True,
    )
    db.add(new_term)

    await db.commit()


async def check_and_expire_rules(db: AsyncSession):
    """Check for rules that need to expire (1 week old)"""
    one_week_ago = datetime.utcnow() - timedelta(days=7)

    await db.execute(
        update(GodRule)
        .where(
            and_(
                GodRule.is_active == True,
                GodRule.created_at <= one_week_ago,
            )
        )
        .values(is_active=False)
    )

    await db.commit()


async def get_blessing_count_today(db: AsyncSession, god_term_id: UUID) -> int:
    """Get number of blessings given today"""
    from app.models.god import Blessing

    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    result = await db.execute(
        select(Blessing).where(
            and_(
                Blessing.god_term_id == god_term_id,
                Blessing.created_at >= today_start,
            )
        )
    )
    return len(result.scalars().all())


async def get_blessing_count_term(db: AsyncSession, god_term_id: UUID) -> int:
    """Get total number of blessings this term"""
    from app.models.god import Blessing

    result = await db.execute(
        select(Blessing).where(Blessing.god_term_id == god_term_id)
    )
    return len(result.scalars().all())
