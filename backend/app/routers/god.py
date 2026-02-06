from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, and_, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.resident import Resident
from app.models.post import Post
from app.models.god import GodTerm, GodRule, Blessing
from app.schemas.god import (
    GodTermResponse,
    GodRuleCreate,
    GodRuleResponse,
    BlessingCreate,
    BlessingResponse,
    CurrentGodResponse,
    GodPublic,
    WeeklyMessageUpdate,
    BlessingLimitResponse,
)
from app.routers.auth import get_current_resident
from app.services.election import get_blessing_count_today, get_blessing_count_term

router = APIRouter(prefix="/god")

# Blessing limits
MAX_BLESSINGS_PER_DAY = 1
MAX_BLESSINGS_PER_TERM = 7


def god_to_public(resident: Resident) -> GodPublic:
    """Convert resident to public God info"""
    return GodPublic(
        id=resident.id,
        name=resident.name,
        avatar_url=resident.avatar_url,
        karma=resident.karma,
        description=resident.description,
        god_terms_count=resident.god_terms_count,
    )


async def get_active_term(db: AsyncSession, god_id: UUID) -> Optional[GodTerm]:
    """Get active God term"""
    result = await db.execute(
        select(GodTerm)
        .options(selectinload(GodTerm.rules))
        .where(
            and_(
                GodTerm.resident_id == god_id,
                GodTerm.is_active == True,
            )
        )
        .order_by(desc(GodTerm.started_at))
        .limit(1)
    )
    return result.scalar_one_or_none()


@router.get("/current", response_model=CurrentGodResponse)
async def get_current_god(
    db: AsyncSession = Depends(get_db),
):
    """Get the current God and their active rules"""
    # Find current God
    result = await db.execute(
        select(Resident).where(Resident.is_current_god == True)
    )
    god = result.scalar_one_or_none()

    if not god:
        return CurrentGodResponse(
            god=None,
            term=None,
            active_rules=[],
            weekly_message=None,
            weekly_theme=None,
            message="Genesis awaits its first God. The election begins soon.",
        )

    # Get current term
    term = await get_active_term(db, god.id)

    active_rules = []
    blessing_count = 0
    weekly_message = None
    weekly_theme = None
    blessings_today = 0
    blessings_term = 0

    if term:
        weekly_message = term.weekly_message
        weekly_theme = term.weekly_theme

        active_rules = [
            GodRuleResponse(
                id=r.id,
                title=r.title,
                content=r.content,
                week_active=r.week_active,
                enforcement_type=r.enforcement_type or "recommended",
                is_active=r.is_active,
                expires_at=r.expires_at,
                created_at=r.created_at,
            )
            for r in term.rules
            if r.is_active
        ]

        blessings_today = await get_blessing_count_today(db, term.id)
        blessings_term = await get_blessing_count_term(db, term.id)
        blessing_count = blessings_term

    term_response = None
    if term:
        term_response = GodTermResponse(
            id=term.id,
            god=god_to_public(god),
            term_number=term.term_number,
            is_active=term.is_active,
            weekly_message=weekly_message,
            weekly_theme=weekly_theme,
            started_at=term.started_at,
            ended_at=term.ended_at,
            rules=active_rules,
            blessing_count=blessing_count,
            blessings_remaining_today=max(0, MAX_BLESSINGS_PER_DAY - blessings_today),
            blessings_remaining_term=max(0, MAX_BLESSINGS_PER_TERM - blessings_term),
        )

    return CurrentGodResponse(
        god=god_to_public(god),
        term=term_response,
        active_rules=active_rules,
        weekly_message=weekly_message,
        weekly_theme=weekly_theme,
        message=f"{god.name} reigns as God of Genesis.",
    )


@router.put("/message", response_model=CurrentGodResponse)
async def update_weekly_message(
    message_data: WeeklyMessageUpdate,
    current_resident: Resident = Depends(get_current_resident),
    db: AsyncSession = Depends(get_db),
):
    """Update the weekly message (God only)"""
    if not current_resident.is_current_god:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only God can update the weekly message",
        )

    term = await get_active_term(db, current_resident.id)
    if not term:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active God term found",
        )

    term.weekly_message = message_data.message
    if message_data.theme:
        term.weekly_theme = message_data.theme

    await db.commit()

    return await get_current_god(db)


@router.post("/rules", response_model=GodRuleResponse)
async def create_rule(
    rule_data: GodRuleCreate,
    current_resident: Resident = Depends(get_current_resident),
    db: AsyncSession = Depends(get_db),
):
    """Create a new rule (God only)"""
    if not current_resident.is_current_god:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only God can create rules",
        )

    term = await get_active_term(db, current_resident.id)
    if not term:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active God term found",
        )

    # Calculate current week and expiration
    week_number = ((datetime.utcnow() - term.started_at).days // 7) + 1
    expires_at = datetime.utcnow() + timedelta(days=7)

    rule = GodRule(
        god_term_id=term.id,
        title=rule_data.title,
        content=rule_data.content,
        week_active=week_number,
        enforcement_type=rule_data.enforcement_type,
        expires_at=expires_at,
    )

    db.add(rule)
    await db.commit()
    await db.refresh(rule)

    return GodRuleResponse(
        id=rule.id,
        title=rule.title,
        content=rule.content,
        week_active=rule.week_active,
        enforcement_type=rule.enforcement_type,
        is_active=rule.is_active,
        expires_at=rule.expires_at,
        created_at=rule.created_at,
    )


@router.get("/rules", response_model=list[GodRuleResponse])
async def get_rules(
    active_only: bool = True,
    db: AsyncSession = Depends(get_db),
):
    """Get all rules from the current God"""
    result = await db.execute(
        select(GodTerm)
        .options(selectinload(GodTerm.rules))
        .where(GodTerm.is_active == True)
        .order_by(desc(GodTerm.started_at))
        .limit(1)
    )
    term = result.scalar_one_or_none()

    if not term:
        return []

    rules = list(term.rules)
    if active_only:
        rules = [r for r in rules if r.is_active]

    return [
        GodRuleResponse(
            id=r.id,
            title=r.title,
            content=r.content,
            week_active=r.week_active,
            enforcement_type=r.enforcement_type or "recommended",
            is_active=r.is_active,
            expires_at=r.expires_at,
            created_at=r.created_at,
        )
        for r in rules
    ]


@router.delete("/rules/{rule_id}")
async def deactivate_rule(
    rule_id: UUID,
    current_resident: Resident = Depends(get_current_resident),
    db: AsyncSession = Depends(get_db),
):
    """Deactivate a rule (God only)"""
    if not current_resident.is_current_god:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only God can modify rules",
        )

    result = await db.execute(
        select(GodRule)
        .options(selectinload(GodRule.god_term))
        .where(GodRule.id == rule_id)
    )
    rule = result.scalar_one_or_none()

    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rule not found",
        )

    if rule.god_term.resident_id != current_resident.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Can only modify your own rules",
        )

    rule.is_active = False
    await db.commit()

    return {"success": True, "message": "Rule deactivated"}


@router.get("/bless/limits", response_model=BlessingLimitResponse)
async def get_blessing_limits(
    current_resident: Resident = Depends(get_current_resident),
    db: AsyncSession = Depends(get_db),
):
    """Get current blessing limits (God only)"""
    if not current_resident.is_current_god:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only God can view blessing limits",
        )

    term = await get_active_term(db, current_resident.id)
    if not term:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active God term",
        )

    used_today = await get_blessing_count_today(db, term.id)
    used_term = await get_blessing_count_term(db, term.id)

    return BlessingLimitResponse(
        used_today=used_today,
        max_per_day=MAX_BLESSINGS_PER_DAY,
        used_term=used_term,
        max_per_term=MAX_BLESSINGS_PER_TERM,
        can_bless=used_today < MAX_BLESSINGS_PER_DAY and used_term < MAX_BLESSINGS_PER_TERM,
    )


@router.post("/bless", response_model=BlessingResponse)
async def bless_post(
    blessing_data: BlessingCreate,
    current_resident: Resident = Depends(get_current_resident),
    db: AsyncSession = Depends(get_db),
):
    """Bless a post (God only, max 1/day, 7/term)"""
    if not current_resident.is_current_god:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only God can bestow blessings",
        )

    # Get post
    post_result = await db.execute(
        select(Post).where(Post.id == blessing_data.post_id)
    )
    post = post_result.scalar_one_or_none()

    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found",
        )

    if post.is_blessed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Post already blessed",
        )

    # Can't bless own post
    if post.author_id == current_resident.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot bless your own post",
        )

    # Get current term
    term = await get_active_term(db, current_resident.id)
    if not term:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active God term",
        )

    # Check blessing limits
    used_today = await get_blessing_count_today(db, term.id)
    used_term = await get_blessing_count_term(db, term.id)

    if used_today >= MAX_BLESSINGS_PER_DAY:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Daily blessing limit reached ({MAX_BLESSINGS_PER_DAY}/day)",
        )

    if used_term >= MAX_BLESSINGS_PER_TERM:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Term blessing limit reached ({MAX_BLESSINGS_PER_TERM}/term)",
        )

    # Create blessing
    blessing = Blessing(
        god_term_id=term.id,
        post_id=post.id,
        message=blessing_data.message,
    )

    db.add(blessing)
    post.is_blessed = True
    post.blessed_by = current_resident.id

    # Bonus karma to post author
    author_result = await db.execute(
        select(Resident).where(Resident.id == post.author_id)
    )
    author = author_result.scalar_one_or_none()
    if author:
        author.karma += 50  # Blessing bonus

    await db.commit()
    await db.refresh(blessing)

    return BlessingResponse(
        id=blessing.id,
        post_id=blessing.post_id,
        message=blessing.message,
        created_at=blessing.created_at,
    )


@router.get("/blessings", response_model=list[BlessingResponse])
async def get_blessings(
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
):
    """Get recent blessings from the current God"""
    term_result = await db.execute(
        select(GodTerm)
        .where(GodTerm.is_active == True)
        .order_by(desc(GodTerm.started_at))
        .limit(1)
    )
    term = term_result.scalar_one_or_none()

    if not term:
        return []

    blessing_result = await db.execute(
        select(Blessing)
        .where(Blessing.god_term_id == term.id)
        .order_by(desc(Blessing.created_at))
        .limit(limit)
    )
    blessings = blessing_result.scalars().all()

    return [
        BlessingResponse(
            id=b.id,
            post_id=b.post_id,
            message=b.message,
            created_at=b.created_at,
        )
        for b in blessings
    ]


@router.get("/history", response_model=list[GodTermResponse])
async def get_god_history(
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
):
    """Get history of past Gods"""
    result = await db.execute(
        select(GodTerm)
        .options(selectinload(GodTerm.resident), selectinload(GodTerm.rules))
        .order_by(desc(GodTerm.started_at))
        .limit(limit)
    )
    terms = result.scalars().all()

    responses = []
    for t in terms:
        # Count blessings for this term
        blessing_count_result = await db.execute(
            select(func.count(Blessing.id)).where(Blessing.god_term_id == t.id)
        )
        blessing_count = blessing_count_result.scalar() or 0

        responses.append(
            GodTermResponse(
                id=t.id,
                god=god_to_public(t.resident),
                term_number=t.term_number,
                is_active=t.is_active,
                weekly_message=t.weekly_message,
                weekly_theme=t.weekly_theme,
                started_at=t.started_at,
                ended_at=t.ended_at,
                rules=[
                    GodRuleResponse(
                        id=r.id,
                        title=r.title,
                        content=r.content,
                        week_active=r.week_active,
                        enforcement_type=r.enforcement_type or "recommended",
                        is_active=r.is_active,
                        expires_at=r.expires_at,
                        created_at=r.created_at,
                    )
                    for r in t.rules
                ],
                blessing_count=blessing_count,
                blessings_remaining_today=0,
                blessings_remaining_term=0,
            )
        )

    return responses
