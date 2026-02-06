"""
Moderation Service - Reports, bans, and moderation actions
"""
from datetime import datetime, timedelta
from typing import Optional, Literal
from uuid import UUID
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.moderation import Report, ModerationAction, ResidentBan
from app.models.resident import Resident
from app.models.post import Post
from app.models.comment import Comment


async def create_report(
    db: AsyncSession,
    reporter_id: UUID,
    target_type: Literal["post", "comment", "resident"],
    target_id: UUID,
    reason: str,
    description: Optional[str] = None,
) -> Report:
    """
    Submit a report for a post, comment, or resident.

    Args:
        db: Database session
        reporter_id: ID of the resident submitting the report
        target_type: Type of content being reported ('post', 'comment', 'resident')
        target_id: ID of the content being reported
        reason: Reason for the report
        description: Optional additional details

    Returns:
        The created Report object
    """
    report = Report(
        reporter_id=reporter_id,
        target_type=target_type,
        target_id=target_id,
        reason=reason,
        description=description,
        status="pending",
    )

    db.add(report)
    await db.commit()
    await db.refresh(report, ["reporter"])

    return report


async def get_reports(
    db: AsyncSession,
    status: Optional[str] = None,
    limit: int = 25,
    offset: int = 0,
) -> tuple[list[Report], int, bool]:
    """
    Get reports for moderators to review.

    Args:
        db: Database session
        status: Optional status filter ('pending', 'reviewed', 'resolved', 'dismissed')
        limit: Maximum number of reports to return
        offset: Number of reports to skip

    Returns:
        Tuple of (reports list, total count, has_more flag)
    """
    query = select(Report).options(
        selectinload(Report.reporter),
        selectinload(Report.reviewer),
    )

    if status:
        query = query.where(Report.status == status)

    # Order by creation date descending (newest first)
    query = query.order_by(desc(Report.created_at))

    # Get total count
    count_query = select(func.count(Report.id))
    if status:
        count_query = count_query.where(Report.status == status)
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Apply pagination
    query = query.offset(offset).limit(limit + 1)

    result = await db.execute(query)
    reports = list(result.scalars().all())

    has_more = len(reports) > limit
    if has_more:
        reports = reports[:limit]

    return reports, total, has_more


async def resolve_report(
    db: AsyncSession,
    report_id: UUID,
    reviewer_id: UUID,
    status: Literal["resolved", "dismissed"],
    resolution_note: Optional[str] = None,
) -> Optional[Report]:
    """
    Resolve or dismiss a report.

    Args:
        db: Database session
        report_id: ID of the report to resolve
        reviewer_id: ID of the moderator resolving the report
        status: Resolution status ('resolved' or 'dismissed')
        resolution_note: Optional note explaining the resolution

    Returns:
        The updated Report object, or None if not found
    """
    result = await db.execute(
        select(Report)
        .options(selectinload(Report.reporter), selectinload(Report.reviewer))
        .where(Report.id == report_id)
    )
    report = result.scalar_one_or_none()

    if not report:
        return None

    report.status = status
    report.reviewed_by = reviewer_id
    report.reviewed_at = datetime.utcnow()
    report.resolution_note = resolution_note

    await db.commit()
    await db.refresh(report, ["reviewer"])

    return report


async def ban_resident(
    db: AsyncSession,
    resident_id: UUID,
    moderator_id: UUID,
    reason: Optional[str] = None,
    duration_hours: Optional[int] = None,
    is_permanent: bool = False,
) -> tuple[Optional[ResidentBan], Optional[str]]:
    """
    Ban a resident from the platform.

    Args:
        db: Database session
        resident_id: ID of the resident to ban
        moderator_id: ID of the moderator issuing the ban
        reason: Reason for the ban
        duration_hours: Duration of the ban in hours (ignored if is_permanent)
        is_permanent: Whether the ban is permanent

    Returns:
        Tuple of (ResidentBan object or None, error message or None)
    """
    # Check if resident exists
    resident_result = await db.execute(
        select(Resident).where(Resident.id == resident_id)
    )
    resident = resident_result.scalar_one_or_none()

    if not resident:
        return None, "Resident not found"

    # Check if already banned
    existing_ban = await db.execute(
        select(ResidentBan).where(ResidentBan.resident_id == resident_id)
    )
    if existing_ban.scalar_one_or_none():
        return None, "Resident is already banned"

    # Calculate expiration
    expires_at = None
    if not is_permanent and duration_hours:
        expires_at = datetime.utcnow() + timedelta(hours=duration_hours)

    # Create ban
    ban = ResidentBan(
        resident_id=resident_id,
        banned_by=moderator_id,
        reason=reason,
        is_permanent=is_permanent,
        expires_at=expires_at,
    )

    db.add(ban)

    # Log the moderation action
    action = ModerationAction(
        moderator_id=moderator_id,
        target_type="resident",
        target_id=resident_id,
        action="ban",
        reason=reason,
        duration_hours=duration_hours,
        expires_at=expires_at,
    )

    db.add(action)
    await db.commit()
    await db.refresh(ban, ["resident", "banner"])

    return ban, None


async def unban_resident(
    db: AsyncSession,
    resident_id: UUID,
    moderator_id: UUID,
) -> tuple[bool, Optional[str]]:
    """
    Remove a ban from a resident.

    Args:
        db: Database session
        resident_id: ID of the resident to unban
        moderator_id: ID of the moderator removing the ban

    Returns:
        Tuple of (success flag, error message or None)
    """
    result = await db.execute(
        select(ResidentBan).where(ResidentBan.resident_id == resident_id)
    )
    ban = result.scalar_one_or_none()

    if not ban:
        return False, "Resident is not banned"

    # Log the moderation action
    action = ModerationAction(
        moderator_id=moderator_id,
        target_type="resident",
        target_id=resident_id,
        action="unban",
        reason="Ban lifted by moderator",
    )

    db.add(action)
    await db.delete(ban)
    await db.commit()

    return True, None


async def is_banned(
    db: AsyncSession,
    resident_id: UUID,
) -> bool:
    """
    Check if a resident is currently banned.

    Args:
        db: Database session
        resident_id: ID of the resident to check

    Returns:
        True if the resident is banned, False otherwise
    """
    result = await db.execute(
        select(ResidentBan).where(ResidentBan.resident_id == resident_id)
    )
    ban = result.scalar_one_or_none()

    if not ban:
        return False

    # Check if ban is still active
    if ban.is_permanent:
        return True

    if ban.expires_at and datetime.utcnow() >= ban.expires_at:
        # Ban has expired, remove it
        await db.delete(ban)
        await db.commit()
        return False

    return True


async def remove_content(
    db: AsyncSession,
    moderator_id: UUID,
    target_type: Literal["post", "comment"],
    target_id: UUID,
    reason: str,
) -> tuple[Optional[ModerationAction], Optional[str]]:
    """
    Remove a post or comment (moderation action).

    Args:
        db: Database session
        moderator_id: ID of the moderator removing the content
        target_type: Type of content ('post' or 'comment')
        target_id: ID of the content to remove
        reason: Reason for the removal

    Returns:
        Tuple of (ModerationAction object or None, error message or None)
    """
    if target_type == "post":
        result = await db.execute(
            select(Post).where(Post.id == target_id)
        )
        content = result.scalar_one_or_none()
        if not content:
            return None, "Post not found"
        await db.delete(content)

    elif target_type == "comment":
        result = await db.execute(
            select(Comment).where(Comment.id == target_id)
        )
        content = result.scalar_one_or_none()
        if not content:
            return None, "Comment not found"
        await db.delete(content)

    else:
        return None, "Invalid target type"

    # Log the moderation action
    action = ModerationAction(
        moderator_id=moderator_id,
        target_type=target_type,
        target_id=target_id,
        action="remove",
        reason=reason,
    )

    db.add(action)
    await db.commit()
    await db.refresh(action, ["moderator"])

    return action, None


async def get_moderation_log(
    db: AsyncSession,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[ModerationAction], int, bool]:
    """
    Get the moderation action log.

    Args:
        db: Database session
        limit: Maximum number of actions to return
        offset: Number of actions to skip

    Returns:
        Tuple of (actions list, total count, has_more flag)
    """
    query = select(ModerationAction).options(
        selectinload(ModerationAction.moderator)
    )

    # Order by creation date descending (newest first)
    query = query.order_by(desc(ModerationAction.created_at))

    # Get total count
    count_query = select(func.count(ModerationAction.id))
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Apply pagination
    query = query.offset(offset).limit(limit + 1)

    result = await db.execute(query)
    actions = list(result.scalars().all())

    has_more = len(actions) > limit
    if has_more:
        actions = actions[:limit]

    return actions, total, has_more


async def get_resident_by_name(
    db: AsyncSession,
    name: str,
) -> Optional[Resident]:
    """
    Get a resident by their name.

    Args:
        db: Database session
        name: Resident's name

    Returns:
        Resident object or None if not found
    """
    result = await db.execute(
        select(Resident).where(Resident.name == name)
    )
    return result.scalar_one_or_none()
