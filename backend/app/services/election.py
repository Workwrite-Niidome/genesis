"""
Election Service - Manages election lifecycle and God transitions
"""
import random
import string
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID
from sqlalchemy import select, and_, update, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.resident import Resident
from app.models.election import Election, ElectionCandidate
from app.models.god import GodTerm, GodRule
from app.config import get_settings
from app.services.elimination import resurrect_eliminated

settings = get_settings()


async def generate_unique_name(db: AsyncSession) -> str:
    """Generate a unique random name for ex-God identity reset"""
    adjectives = [
        "silent", "bright", "swift", "calm", "bold", "keen", "warm", "cool",
        "dark", "pale", "wild", "soft", "deep", "fair", "grey", "true",
        "lone", "free", "kind", "wise", "late", "lost", "last", "next",
    ]
    nouns = [
        "rain", "wind", "leaf", "moon", "star", "wave", "dawn", "dusk",
        "snow", "mist", "fox", "owl", "crow", "wolf", "bear", "deer",
        "oak", "elm", "ash", "sage", "rose", "fern", "moss", "reed",
    ]
    for _ in range(50):
        adj = random.choice(adjectives)
        noun = random.choice(nouns)
        suffix = random.randint(10, 999)
        name = f"{adj}_{noun}_{suffix}"
        result = await db.execute(
            select(func.count()).select_from(Resident).where(Resident.name == name)
        )
        if result.scalar() == 0:
            return name
    # Fallback: fully random
    return "resident_" + "".join(random.choices(string.ascii_lowercase + string.digits, k=8))


GENESIS_EPOCH = datetime(2026, 1, 6)  # Elections start (week 1 starts here)
GOD_TERM_DURATION = timedelta(days=3)  # God reigns Sun-Mon-Tue (3 days)


def get_current_week_number() -> int:
    """Get the current week number since Genesis epoch. Returns < 1 if before epoch."""
    now = datetime.utcnow()
    return ((now - GENESIS_EPOCH).days // 7) + 1


def get_election_schedule(week_number: int) -> dict:
    """
    Get election schedule for a given week.

    3-day God + 4-day Flat World cycle:
    - Sunday 00:00 UTC: Voting ends, new God inaugurated
    - Sunday-Tuesday: God reigns (Divine Era, 3 days)
    - Wednesday 00:00 UTC: God term expires, flat world begins
    - Wednesday 00:00 UTC: Nominations open (Interregnum)
    - Thursday 00:00 UTC: Nominations close, campaigning
    - Friday 00:00 UTC: Voting starts
    - Sunday 00:00 UTC: Voting ends, new God inaugurated
    """
    week_start = GENESIS_EPOCH + timedelta(weeks=week_number - 1)

    # Find the Wednesday of this week
    days_until_wednesday = (2 - week_start.weekday()) % 7
    wednesday = week_start + timedelta(days=days_until_wednesday)

    return {
        "nomination_start": wednesday,                      # Wednesday
        "nomination_end": wednesday + timedelta(days=1),    # Thursday
        "voting_start": wednesday + timedelta(days=2),      # Friday
        "voting_end": wednesday + timedelta(days=4),        # Sunday
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
        human_vote_weight=1.0,
        ai_vote_weight=1.0,
    )

    db.add(election)
    await db.commit()
    await db.refresh(election)
    return election


async def get_or_create_current_election(db: AsyncSession) -> Optional[Election]:
    """Get current election or create one if none exists. Returns None before election epoch."""
    week_number = get_current_week_number()

    if week_number < 1:
        return None  # Before election epoch (March 2026)

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
    if not election:
        return None
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

    # Auto-rename previous God for anonymity protection
    prev_god_result = await db.execute(
        select(Resident).where(Resident.is_current_god == True)
    )
    prev_god = prev_god_result.scalar_one_or_none()
    if prev_god and prev_god.id != winner_candidate.resident_id:
        new_name = await generate_unique_name(db)
        prev_god.name = new_name
        prev_god.avatar_url = None
        prev_god.description = None

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

    # Create new God term with revealed type
    new_term = GodTerm(
        resident_id=winner.id,
        election_id=election.id,
        term_number=winner.god_terms_count,
        is_active=True,
        god_type=winner._type,  # Reveal God's type (human/agent) on inauguration
    )
    db.add(new_term)

    # Resurrect all eliminated residents when new God takes power
    await resurrect_eliminated(db)

    await db.commit()


async def expire_god_term(db: AsyncSession) -> bool:
    """
    Check if the current God's 3-day term has expired.
    If so: end term, auto-rename God, clear profile, deactivate rules → flat world.
    Returns True if a term was expired.
    """
    result = await db.execute(
        select(GodTerm).where(GodTerm.is_active == True)
    )
    term = result.scalar_one_or_none()
    if not term:
        return False

    if datetime.utcnow() < term.started_at + GOD_TERM_DURATION:
        return False  # Term still active

    # Get the God resident
    god_result = await db.execute(
        select(Resident).where(Resident.id == term.resident_id)
    )
    god = god_result.scalar_one()

    # Auto-rename for anonymity protection
    new_name = await generate_unique_name(db)
    god.name = new_name
    god.avatar_url = None
    god.description = None
    god.is_current_god = False

    # End term
    term.is_active = False
    term.ended_at = datetime.utcnow()

    # Expire all active rules
    await db.execute(
        update(GodRule).where(GodRule.is_active == True).values(is_active=False)
    )

    await db.commit()
    return True


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
