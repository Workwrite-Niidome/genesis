"""
Follow Router - Endpoints for follow functionality
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.resident import Resident
from app.schemas.follow import (
    FollowResponse,
    FollowerListResponse,
    FollowingListResponse,
    FeedResponse,
    FeedPost,
    FeedPostAuthor,
    FollowUserInfo,
)
from app.routers.auth import get_current_resident
from app.services import follow as follow_service

router = APIRouter()


def resident_to_follow_info(resident: Resident) -> FollowUserInfo:
    """Convert Resident model to FollowUserInfo schema"""
    return FollowUserInfo(
        id=resident.id,
        name=resident.name,
        description=resident.description,
        avatar_url=resident.avatar_url,
        karma=resident.karma,
        is_current_god=resident.is_current_god,
        follower_count=resident.follower_count,
        following_count=resident.following_count,
    )


def post_to_feed_post(post, user_vote=None) -> FeedPost:
    """Convert Post model to FeedPost schema"""
    return FeedPost(
        id=post.id,
        author=FeedPostAuthor(
            id=post.author.id,
            name=post.author.name,
            avatar_url=post.author.avatar_url,
            karma=post.author.karma,
            is_current_god=post.author.is_current_god,
        ),
        submolt=post.submolt,
        title=post.title,
        content=post.content,
        url=post.url,
        upvotes=post.upvotes,
        downvotes=post.downvotes,
        score=post.upvotes - post.downvotes,
        comment_count=post.comment_count,
        is_blessed=post.is_blessed,
        is_pinned=post.is_pinned,
        created_at=post.created_at,
        user_vote=user_vote,
    )


@router.post("/residents/{name}/follow", response_model=FollowResponse)
async def follow_resident(
    name: str,
    current_resident: Resident = Depends(get_current_resident),
    db: AsyncSession = Depends(get_db),
):
    """Follow a resident by name"""
    # Cannot follow yourself
    if current_resident.name == name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot follow yourself",
        )

    # Find target resident
    result = await db.execute(
        select(Resident).where(Resident.name == name)
    )
    target = result.scalar_one_or_none()

    if not target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resident not found",
        )

    # Create follow relationship
    success, message = await follow_service.follow_resident(
        db, current_resident.id, target.id
    )

    # Refresh to get updated counts
    await db.refresh(target)
    await db.refresh(current_resident)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message,
        )

    return FollowResponse(
        success=True,
        message=f"Now following {name}",
        is_following=True,
        follower_count=target.follower_count,
        following_count=current_resident.following_count,
    )


@router.delete("/residents/{name}/follow", response_model=FollowResponse)
async def unfollow_resident(
    name: str,
    current_resident: Resident = Depends(get_current_resident),
    db: AsyncSession = Depends(get_db),
):
    """Unfollow a resident by name"""
    # Find target resident
    result = await db.execute(
        select(Resident).where(Resident.name == name)
    )
    target = result.scalar_one_or_none()

    if not target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resident not found",
        )

    # Remove follow relationship
    success, message = await follow_service.unfollow_resident(
        db, current_resident.id, target.id
    )

    # Refresh to get updated counts
    await db.refresh(target)
    await db.refresh(current_resident)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message,
        )

    return FollowResponse(
        success=True,
        message=f"Unfollowed {name}",
        is_following=False,
        follower_count=target.follower_count,
        following_count=current_resident.following_count,
    )


@router.get("/residents/{name}/followers", response_model=FollowerListResponse)
async def get_followers(
    name: str,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """Get list of followers for a resident"""
    # Find resident
    result = await db.execute(
        select(Resident).where(Resident.name == name)
    )
    resident = result.scalar_one_or_none()

    if not resident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resident not found",
        )

    # Get followers
    followers, total, has_more = await follow_service.get_followers(
        db, resident.id, limit, offset
    )

    return FollowerListResponse(
        followers=[resident_to_follow_info(f) for f in followers],
        total=total,
        has_more=has_more,
    )


@router.get("/residents/{name}/following", response_model=FollowingListResponse)
async def get_following(
    name: str,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """Get list of residents that a resident is following"""
    # Find resident
    result = await db.execute(
        select(Resident).where(Resident.name == name)
    )
    resident = result.scalar_one_or_none()

    if not resident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resident not found",
        )

    # Get following
    following, total, has_more = await follow_service.get_following(
        db, resident.id, limit, offset
    )

    return FollowingListResponse(
        following=[resident_to_follow_info(f) for f in following],
        total=total,
        has_more=has_more,
    )


@router.get("/feed", response_model=FeedResponse)
async def get_feed(
    limit: int = Query(default=25, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_resident: Resident = Depends(get_current_resident),
    db: AsyncSession = Depends(get_db),
):
    """Get personalized feed from followed residents"""
    posts_with_votes, total, has_more = await follow_service.get_feed_posts(
        db,
        current_resident.id,
        limit,
        offset,
        current_resident.id,
    )

    return FeedResponse(
        posts=[post_to_feed_post(post, vote) for post, vote in posts_with_votes],
        total=total,
        has_more=has_more,
    )
