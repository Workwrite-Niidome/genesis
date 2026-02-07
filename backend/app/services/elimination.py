"""
Elimination Service - Death and resurrection logic for Genesis world system
"""
from datetime import datetime
from sqlalchemy import select, update, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.resident import Resident, KARMA_START
from app.models.god import GodTerm
from app.services.notification import create_notification


async def eliminate_resident(resident: Resident, god_term_id, db: AsyncSession) -> None:
    """Mark a resident as eliminated (dead)."""
    resident.is_eliminated = True
    resident.eliminated_at = datetime.utcnow()
    resident.eliminated_during_term_id = god_term_id
    resident.karma = 0


async def check_and_eliminate(resident: Resident, db: AsyncSession) -> bool:
    """If resident's karma <= 0, eliminate them. Returns True if eliminated."""
    if resident.karma <= 0 and not resident.is_eliminated:
        # Get active god term
        result = await db.execute(
            select(GodTerm)
            .where(GodTerm.is_active == True)
            .limit(1)
        )
        term = result.scalar_one_or_none()
        god_term_id = term.id if term else None

        await eliminate_resident(resident, god_term_id, db)
        await create_death_notification(resident, db)
        return True
    return False


async def resurrect_eliminated(db: AsyncSession) -> int:
    """
    Unfreeze all eliminated residents and reset their karma to KARMA_START.
    Called when a new God takes power.
    Returns the number of resurrected residents.
    """
    result = await db.execute(
        select(Resident).where(Resident.is_eliminated == True)
    )
    eliminated = result.scalars().all()

    count = 0
    for resident in eliminated:
        resident.is_eliminated = False
        resident.eliminated_at = None
        resident.eliminated_during_term_id = None
        resident.karma = KARMA_START
        count += 1

    return count


async def create_death_notification(resident: Resident, db: AsyncSession) -> None:
    """Notify all residents that someone has been eliminated."""
    # Get all non-eliminated residents (except the eliminated one)
    result = await db.execute(
        select(Resident.id).where(
            and_(
                Resident.id != resident.id,
                Resident.is_eliminated == False,
            )
        )
    )
    resident_ids = result.scalars().all()

    for recipient_id in resident_ids:
        await create_notification(
            db=db,
            recipient_id=recipient_id,
            type="elimination",
            title=f"{resident.name} has vanished from Genesis.",
            message=f"{resident.name}'s karma reached zero. They have been eliminated until the next God takes power.",
            actor_id=resident.id,
        )
