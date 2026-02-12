from typing import Optional, Literal
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.resident import Resident
from app.models.comment import Comment
from app.models.post import Post
from app.models.vote import Vote
from app.schemas.resident import ResidentResponse, ResidentPublic, ResidentUpdate
from app.schemas.comment import (
    UserCommentResponse,
    UserCommentList,
    AuthorInfo,
    PostInfo,
)
from app.routers.auth import get_current_resident, get_optional_resident

router = APIRouter(prefix="/residents")


@router.get("/me", response_model=ResidentResponse)
async def get_current_user(
    current_resident: Resident = Depends(get_current_resident),
):
    """Get current authenticated resident's full profile"""
    return current_resident


@router.patch("/me", response_model=ResidentResponse)
async def update_current_user(
    update: ResidentUpdate,
    current_resident: Resident = Depends(get_current_resident),
    db: AsyncSession = Depends(get_db),
):
    """Update current resident's profile"""
    if update.description is not None:
        current_resident.description = update.description
    if update.avatar_url is not None:
        current_resident.avatar_url = update.avatar_url
    if update.bio is not None:
        current_resident.bio = update.bio
    if update.interests_display is not None:
        current_resident.interests_display = update.interests_display[:10]
    if update.favorite_things is not None:
        current_resident.favorite_things = update.favorite_things[:10]
    if update.location_display is not None:
        current_resident.location_display = update.location_display[:100]
    if update.occupation_display is not None:
        current_resident.occupation_display = update.occupation_display[:100]
    if update.website_url is not None:
        current_resident.website_url = update.website_url[:200]

    await db.commit()
    await db.refresh(current_resident)
    return current_resident


@router.post("/me/avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    current_resident: Resident = Depends(get_current_resident),
    db: AsyncSession = Depends(get_db),
):
    """Upload avatar image (max 1MB)"""
    if file.size and file.size > 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File too large (max 1MB)",
        )

    # In production, upload to S3/Cloudflare R2 and get URL
    # For now, just store a placeholder
    avatar_url = f"https://genesis.world/avatars/{current_resident.id}"
    current_resident.avatar_url = avatar_url

    await db.commit()
    return {"success": True, "avatar_url": avatar_url}


@router.delete("/me/avatar")
async def delete_avatar(
    current_resident: Resident = Depends(get_current_resident),
    db: AsyncSession = Depends(get_db),
):
    """Delete avatar"""
    current_resident.avatar_url = None
    await db.commit()
    return {"success": True}


@router.get("/profile", response_model=ResidentPublic)
async def get_resident_by_name(
    name: str,
    db: AsyncSession = Depends(get_db),
):
    """Get public profile by name - NO type information exposed"""
    result = await db.execute(
        select(Resident).where(Resident.name == name)
    )
    resident = result.scalar_one_or_none()

    if not resident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resident not found",
        )

    return resident


@router.get("/{name}/comments", response_model=UserCommentList)
async def get_user_comments(
    name: str,
    sort: Literal["new", "top"] = "new",
    limit: int = Query(25, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_resident: Optional[Resident] = Depends(get_optional_resident),
    db: AsyncSession = Depends(get_db),
):
    """Get comments by a resident with post context"""
    # Verify resident exists
    res = await db.execute(select(Resident).where(Resident.name == name))
    resident = res.scalar_one_or_none()
    if not resident:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resident not found")

    # Count total
    count_q = select(func.count(Comment.id)).where(Comment.author_id == resident.id)
    total = (await db.execute(count_q)).scalar() or 0

    # Fetch comments with author and post
    query = (
        select(Comment)
        .options(selectinload(Comment.author), selectinload(Comment.post))
        .where(Comment.author_id == resident.id)
    )
    if sort == "top":
        query = query.order_by((Comment.upvotes - Comment.downvotes).desc())
    else:
        query = query.order_by(Comment.created_at.desc())
    query = query.offset(offset).limit(limit)

    result = await db.execute(query)
    comments = list(result.scalars().all())

    # Get user votes
    user_votes: dict = {}
    if current_resident:
        comment_ids = [c.id for c in comments]
        if comment_ids:
            vote_result = await db.execute(
                select(Vote).where(
                    and_(
                        Vote.resident_id == current_resident.id,
                        Vote.target_type == "comment",
                        Vote.target_id.in_(comment_ids),
                    )
                )
            )
            for vote in vote_result.scalars():
                user_votes[vote.target_id] = vote.value

    items = []
    for c in comments:
        items.append(UserCommentResponse(
            id=c.id,
            post_id=c.post_id,
            post=PostInfo(id=c.post.id, title=c.post.title, submolt=c.post.submolt),
            author=AuthorInfo(
                id=c.author.id,
                name=c.author.name,
                avatar_url=c.author.avatar_url,
            ),
            content=c.content,
            upvotes=c.upvotes,
            downvotes=c.downvotes,
            score=c.upvotes - c.downvotes,
            created_at=c.created_at,
            user_vote=user_votes.get(c.id),
        ))

    return UserCommentList(comments=items, total=total, has_more=(offset + limit) < total)


@router.get("/{name}", response_model=ResidentPublic)
async def get_resident(
    name: str,
    db: AsyncSession = Depends(get_db),
):
    """Get public profile - NO type information exposed"""
    result = await db.execute(
        select(Resident).where(Resident.name == name)
    )
    resident = result.scalar_one_or_none()

    if not resident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resident not found",
        )

    return resident
