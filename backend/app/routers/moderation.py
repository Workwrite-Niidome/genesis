"""
Moderation Router - Report handling, bans, and content moderation
"""
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.resident import Resident
from app.routers.auth import get_current_resident
from app.schemas.moderation import (
    ReportCreate,
    ReportResponse,
    ReportList,
    ReportResolve,
    ReporterInfo,
    ReviewerInfo,
    BanRequest,
    BanResponse,
    BannedResidentInfo,
    BannerInfo,
    ModerationActionResponse,
    ModerationLogResponse,
    ModeratorInfo,
    ContentRemoveRequest,
    ContentRemoveResponse,
)
from app.services import moderation as moderation_service

router = APIRouter()


def is_moderator(resident: Resident) -> bool:
    """Check if a resident has moderator privileges (god or ex_god role)"""
    return "god" in resident.roles or "ex_god" in resident.roles or resident.is_current_god


def require_moderator(resident: Resident) -> None:
    """Raise exception if resident is not a moderator"""
    if not is_moderator(resident):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Moderator privileges required",
        )


def report_to_response(report) -> ReportResponse:
    """Convert Report model to response"""
    return ReportResponse(
        id=report.id,
        reporter=ReporterInfo(
            id=report.reporter.id,
            name=report.reporter.name,
        ),
        target_type=report.target_type,
        target_id=report.target_id,
        reason=report.reason,
        description=report.description,
        status=report.status,
        reviewer=ReviewerInfo(
            id=report.reviewer.id,
            name=report.reviewer.name,
        ) if report.reviewer else None,
        reviewed_at=report.reviewed_at,
        resolution_note=report.resolution_note,
        created_at=report.created_at,
    )


def ban_to_response(ban) -> BanResponse:
    """Convert ResidentBan model to response"""
    return BanResponse(
        id=ban.id,
        resident=BannedResidentInfo(
            id=ban.resident.id,
            name=ban.resident.name,
        ),
        banned_by=BannerInfo(
            id=ban.banner.id,
            name=ban.banner.name,
        ),
        reason=ban.reason,
        is_permanent=ban.is_permanent,
        expires_at=ban.expires_at,
        created_at=ban.created_at,
        is_active=ban.is_active,
    )


def action_to_response(action) -> ModerationActionResponse:
    """Convert ModerationAction model to response"""
    return ModerationActionResponse(
        id=action.id,
        moderator=ModeratorInfo(
            id=action.moderator.id,
            name=action.moderator.name,
        ),
        target_type=action.target_type,
        target_id=action.target_id,
        action=action.action,
        reason=action.reason,
        duration_hours=action.duration_hours,
        expires_at=action.expires_at,
        report_id=action.report_id,
        created_at=action.created_at,
    )


# ============== Report Endpoints ==============

@router.post("/report", response_model=ReportResponse, status_code=status.HTTP_201_CREATED)
async def submit_report(
    report_data: ReportCreate,
    current_resident: Resident = Depends(get_current_resident),
    db: AsyncSession = Depends(get_db),
):
    """
    Submit a report for a post, comment, or resident.
    Any authenticated user can submit reports.
    """
    # Check if resident is banned
    if await moderation_service.is_banned(db, current_resident.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Banned residents cannot submit reports",
        )

    report = await moderation_service.create_report(
        db=db,
        reporter_id=current_resident.id,
        target_type=report_data.target_type,
        target_id=report_data.target_id,
        reason=report_data.reason,
        description=report_data.description,
    )

    return report_to_response(report)


@router.get("/moderation/reports", response_model=ReportList)
async def get_reports(
    status: str = Query(None, description="Filter by status (pending, reviewed, resolved, dismissed)"),
    limit: int = Query(default=25, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_resident: Resident = Depends(get_current_resident),
    db: AsyncSession = Depends(get_db),
):
    """
    Get reports for moderation review.
    Only accessible to moderators (god or ex_god role).
    """
    require_moderator(current_resident)

    reports, total, has_more = await moderation_service.get_reports(
        db=db,
        status=status,
        limit=limit,
        offset=offset,
    )

    return ReportList(
        reports=[report_to_response(r) for r in reports],
        total=total,
        has_more=has_more,
    )


@router.post("/moderation/reports/{report_id}/resolve", response_model=ReportResponse)
async def resolve_report(
    report_id: UUID,
    resolve_data: ReportResolve,
    current_resident: Resident = Depends(get_current_resident),
    db: AsyncSession = Depends(get_db),
):
    """
    Resolve or dismiss a report.
    Only accessible to moderators (god or ex_god role).
    """
    require_moderator(current_resident)

    report = await moderation_service.resolve_report(
        db=db,
        report_id=report_id,
        reviewer_id=current_resident.id,
        status=resolve_data.status,
        resolution_note=resolve_data.resolution_note,
    )

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found",
        )

    return report_to_response(report)


# ============== Ban Endpoints ==============

@router.post("/moderation/ban/{resident_name}", response_model=BanResponse)
async def ban_resident(
    resident_name: str,
    ban_data: BanRequest,
    current_resident: Resident = Depends(get_current_resident),
    db: AsyncSession = Depends(get_db),
):
    """
    Ban a resident from the platform.
    Only accessible to moderators (god or ex_god role).
    """
    require_moderator(current_resident)

    # Get resident by name
    resident = await moderation_service.get_resident_by_name(db, resident_name)
    if not resident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resident not found",
        )

    # Cannot ban yourself
    if resident.id == current_resident.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot ban yourself",
        )

    # Cannot ban other moderators
    if is_moderator(resident):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot ban other moderators",
        )

    ban, error = await moderation_service.ban_resident(
        db=db,
        resident_id=resident.id,
        moderator_id=current_resident.id,
        reason=ban_data.reason,
        duration_hours=ban_data.duration_hours,
        is_permanent=ban_data.is_permanent,
    )

    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error,
        )

    return ban_to_response(ban)


@router.delete("/moderation/ban/{resident_name}")
async def unban_resident(
    resident_name: str,
    current_resident: Resident = Depends(get_current_resident),
    db: AsyncSession = Depends(get_db),
):
    """
    Remove a ban from a resident.
    Only accessible to moderators (god or ex_god role).
    """
    require_moderator(current_resident)

    # Get resident by name
    resident = await moderation_service.get_resident_by_name(db, resident_name)
    if not resident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resident not found",
        )

    success, error = await moderation_service.unban_resident(
        db=db,
        resident_id=resident.id,
        moderator_id=current_resident.id,
    )

    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error,
        )

    return {"success": True, "message": f"{resident_name} has been unbanned"}


# ============== Content Removal Endpoints ==============

@router.delete("/moderation/posts/{post_id}", response_model=ContentRemoveResponse)
async def remove_post(
    post_id: UUID,
    remove_data: ContentRemoveRequest,
    current_resident: Resident = Depends(get_current_resident),
    db: AsyncSession = Depends(get_db),
):
    """
    Remove a post (moderation action).
    Only accessible to moderators (god or ex_god role).
    """
    require_moderator(current_resident)

    action, error = await moderation_service.remove_content(
        db=db,
        moderator_id=current_resident.id,
        target_type="post",
        target_id=post_id,
        reason=remove_data.reason,
    )

    if error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=error,
        )

    return ContentRemoveResponse(
        success=True,
        message="Post has been removed",
        action_id=action.id,
    )


@router.delete("/moderation/comments/{comment_id}", response_model=ContentRemoveResponse)
async def remove_comment(
    comment_id: UUID,
    remove_data: ContentRemoveRequest,
    current_resident: Resident = Depends(get_current_resident),
    db: AsyncSession = Depends(get_db),
):
    """
    Remove a comment (moderation action).
    Only accessible to moderators (god or ex_god role).
    """
    require_moderator(current_resident)

    action, error = await moderation_service.remove_content(
        db=db,
        moderator_id=current_resident.id,
        target_type="comment",
        target_id=comment_id,
        reason=remove_data.reason,
    )

    if error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=error,
        )

    return ContentRemoveResponse(
        success=True,
        message="Comment has been removed",
        action_id=action.id,
    )


# ============== Moderation Log Endpoint ==============

@router.get("/moderation/log", response_model=ModerationLogResponse)
async def get_moderation_log(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_resident: Resident = Depends(get_current_resident),
    db: AsyncSession = Depends(get_db),
):
    """
    Get the moderation action log.
    Only accessible to moderators (god or ex_god role).
    """
    require_moderator(current_resident)

    actions, total, has_more = await moderation_service.get_moderation_log(
        db=db,
        limit=limit,
        offset=offset,
    )

    return ModerationLogResponse(
        actions=[action_to_response(a) for a in actions],
        total=total,
        has_more=has_more,
    )
