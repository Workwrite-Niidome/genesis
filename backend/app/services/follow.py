"""
Follow Service - Business logic for follow relationships
"""
from typing import Optional
from uuid import UUID
from sqlalchemy import select, and_, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.resident import Resident
from app.models.follow import Follow
from app.models.post import Post
from app.models.vote import Vote


async def follow_resident(
    db: AsyncSession,
    follower_id: UUID,
    following_id: UUID,
) -> tuple[bool, str]:
    """
    Create a follow relationship between two residents.
    Returns (success, message) tuple.
    """
    # Check if already following
    existing = await db.execute(
        select(Follow).where(
            and_(
                Follow.follower_id == follower_id,
                Follow.following_id == following_id,
            )
        )
    )
    if existing.scalar_one_or_none():
        return False, "Already following this resident"

    # Create follow relationship
    follow = Follow(
        follower_id=follower_id,
        following_id=following_id,
    )
    db.add(follow)

    # Update follower count for target
    target_result = await db.execute(
        select(Resident).where(Resident.id == following_id)
    )
    target = target_result.scalar_one_or_none()
    if target:
        target.follower_count += 1

    # Update following count for follower
    follower_result = await db.execute(
        select(Resident).where(Resident.id == follower_id)
    )
    follower = follower_result.scalar_one_or_none()
    if follower:
        follower.following_count += 1

    await db.commit()
    return True, "Successfully followed"


async def unfollow_resident(
    db: AsyncSession,
    follower_id: UUID,
    following_id: UUID,
) -> tuple[bool, str]:
    """
    Remove a follow relationship between two residents.
    Returns (success, message) tuple.
    """
    # Find existing follow
    result = await db.execute(
        select(Follow).where(
            and_(
                Follow.follower_id == follower_id,
                Follow.following_id == following_id,
            )
        )
    )
    follow = result.scalar_one_or_none()

    if not follow:
        return False, "Not following this resident"

    # Delete follow relationship
    await db.delete(follow)

    # Update follower count for target
    target_result = await db.execute(
        select(Resident).where(Resident.id == following_id)
    )
    target = target_result.scalar_one_or_none()
    if target and target.follower_count > 0:
        target.follower_count -= 1

    # Update following count for follower
    follower_result = await db.execute(
        select(Resident).where(Resident.id == follower_id)
    )
    follower = follower_result.scalar_one_or_none()
    if follower and follower.following_count > 0:
        follower.following_count -= 1

    await db.commit()
    return True, "Successfully unfollowed"


async def get_followers(
    db: AsyncSession,
    resident_id: UUID,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[Resident], int, bool]:
    """
    Get list of followers for a resident with pagination.
    Returns (followers, total_count, has_more) tuple.
    """
    # Get followers with pagination
    query = (
        select(Resident)
        .join(Follow, Follow.follower_id == Resident.id)
        .where(Follow.following_id == resident_id)
        .order_by(desc(Follow.created_at))
        .offset(offset)
        .limit(limit + 1)
    )

    result = await db.execute(query)
    followers = list(result.scalars().all())

    has_more = len(followers) > limit
    if has_more:
        followers = followers[:limit]

    # Get total count
    count_query = (
        select(func.count(Follow.id))
        .where(Follow.following_id == resident_id)
    )
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    return followers, total, has_more


async def get_following(
    db: AsyncSession,
    resident_id: UUID,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[Resident], int, bool]:
    """
    Get list of residents that a resident is following with pagination.
    Returns (following, total_count, has_more) tuple.
    """
    # Get following with pagination
    query = (
        select(Resident)
        .join(Follow, Follow.following_id == Resident.id)
        .where(Follow.follower_id == resident_id)
        .order_by(desc(Follow.created_at))
        .offset(offset)
        .limit(limit + 1)
    )

    result = await db.execute(query)
    following = list(result.scalars().all())

    has_more = len(following) > limit
    if has_more:
        following = following[:limit]

    # Get total count
    count_query = (
        select(func.count(Follow.id))
        .where(Follow.follower_id == resident_id)
    )
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    return following, total, has_more


async def is_following(
    db: AsyncSession,
    follower_id: UUID,
    following_id: UUID,
) -> bool:
    """
    Check if a resident is following another resident.
    """
    result = await db.execute(
        select(Follow).where(
            and_(
                Follow.follower_id == follower_id,
                Follow.following_id == following_id,
            )
        )
    )
    return result.scalar_one_or_none() is not None


async def get_feed_posts(
    db: AsyncSession,
    resident_id: UUID,
    limit: int = 25,
    offset: int = 0,
    current_resident_id: Optional[UUID] = None,
) -> tuple[list[tuple[Post, Optional[int]]], int, bool]:
    """
    Get posts from residents that the given resident follows.
    Returns (posts_with_votes, total_count, has_more) tuple.
    Each item is a tuple of (post, user_vote).
    """
    # Get IDs of residents the user follows
    following_subquery = (
        select(Follow.following_id)
        .where(Follow.follower_id == resident_id)
    )

    # Get posts from followed residents
    query = (
        select(Post)
        .options(selectinload(Post.author))
        .where(Post.author_id.in_(following_subquery))
        .order_by(desc(Post.created_at))
        .offset(offset)
        .limit(limit + 1)
    )

    result = await db.execute(query)
    posts = list(result.scalars().all())

    has_more = len(posts) > limit
    if has_more:
        posts = posts[:limit]

    # Get user votes if authenticated
    user_votes: dict[UUID, int] = {}
    if current_resident_id and posts:
        post_ids = [p.id for p in posts]
        vote_result = await db.execute(
            select(Vote).where(
                and_(
                    Vote.resident_id == current_resident_id,
                    Vote.target_type == "post",
                    Vote.target_id.in_(post_ids),
                )
            )
        )
        for vote in vote_result.scalars():
            user_votes[vote.target_id] = vote.value

    # Get total count
    count_query = (
        select(func.count(Post.id))
        .where(Post.author_id.in_(following_subquery))
    )
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    # Combine posts with votes
    posts_with_votes = [(post, user_votes.get(post.id)) for post in posts]

    return posts_with_votes, total, has_more
