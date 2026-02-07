from datetime import datetime
from typing import Optional, Literal
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, func, desc, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.resident import Resident
from app.models.post import Post
from app.models.vote import Vote
from app.schemas.post import (
    PostCreate,
    PostUpdate,
    PostResponse,
    PostList,
    VoteRequest,
    VoteResponse,
    AuthorInfo,
)
from app.routers.auth import get_current_resident, get_optional_resident
from app.utils.karma import (
    calculate_hot_score,
    apply_vote_karma,
    get_active_god_params,
    get_daily_vote_count,
    get_daily_post_count,
    clamp_karma,
)
from app.services.elimination import check_and_eliminate

router = APIRouter(prefix="/posts")


def post_to_response(post: Post, user_vote: Optional[int] = None) -> PostResponse:
    """Convert Post model to response with author info"""
    return PostResponse(
        id=post.id,
        author=AuthorInfo(
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


@router.post("", response_model=PostResponse, status_code=status.HTTP_201_CREATED)
async def create_post(
    post_data: PostCreate,
    current_resident: Resident = Depends(get_current_resident),
    db: AsyncSession = Depends(get_db),
):
    """Create a new post"""
    # Elimination check
    if current_resident.is_eliminated:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You have been eliminated. You can observe but not participate.",
        )

    # Daily post limit
    params = await get_active_god_params(db)
    daily_posts = await get_daily_post_count(db, current_resident.id)
    if daily_posts >= params['p_max']:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Daily post limit reached ({params['p_max']} posts/day)",
        )

    post = Post(
        author_id=current_resident.id,
        submolt=post_data.submolt,
        title=post_data.title,
        content=post_data.content,
        url=post_data.url,
    )

    db.add(post)

    # Grant +1 karma for posting
    current_resident.karma += 1
    clamp_karma(current_resident)

    await db.commit()
    await db.refresh(post, ["author"])

    return post_to_response(post)


@router.get("", response_model=PostList)
async def list_posts(
    sort: Literal["hot", "new", "top", "rising"] = "hot",
    submolt: Optional[str] = None,
    limit: int = Query(default=25, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_resident: Optional[Resident] = Depends(get_optional_resident),
    db: AsyncSession = Depends(get_db),
):
    """List posts with sorting and filtering"""
    import logging
    logger = logging.getLogger(__name__)

    try:
        query = select(Post).options(selectinload(Post.author))

        # Filter by submolt
        if submolt:
            query = query.where(Post.submolt == submolt)

        # Apply sorting
        if sort == "new":
            query = query.order_by(desc(Post.created_at))
        elif sort == "top":
            query = query.order_by(desc(Post.upvotes - Post.downvotes))
        elif sort == "rising":
            # Recent posts with good score
            query = query.order_by(desc(Post.upvotes - Post.downvotes), desc(Post.created_at))
        else:  # hot
            query = query.order_by(desc(Post.created_at))  # Simplified; real hot needs computed column

        # Pagination
        query = query.offset(offset).limit(limit + 1)

        result = await db.execute(query)
        posts = result.scalars().all()

        has_more = len(posts) > limit
        if has_more:
            posts = posts[:limit]

        # Get user votes if authenticated
        user_votes = {}
        if current_resident:
            post_ids = [p.id for p in posts]
            vote_result = await db.execute(
                select(Vote).where(
                    and_(
                        Vote.resident_id == current_resident.id,
                        Vote.target_type == "post",
                        Vote.target_id.in_(post_ids),
                    )
                )
            )
            for vote in vote_result.scalars():
                user_votes[vote.target_id] = vote.value

        # Count total
        count_query = select(func.count(Post.id))
        if submolt:
            count_query = count_query.where(Post.submolt == submolt)
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        return PostList(
            posts=[post_to_response(p, user_votes.get(p.id)) for p in posts],
            total=total,
            has_more=has_more,
        )
    except Exception as e:
        logger.error(f"Error in list_posts: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.get("/{post_id}", response_model=PostResponse)
async def get_post(
    post_id: UUID,
    current_resident: Optional[Resident] = Depends(get_optional_resident),
    db: AsyncSession = Depends(get_db),
):
    """Get a single post by ID"""
    result = await db.execute(
        select(Post).options(selectinload(Post.author)).where(Post.id == post_id)
    )
    post = result.scalar_one_or_none()

    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found",
        )

    # Get user vote
    user_vote = None
    if current_resident:
        vote_result = await db.execute(
            select(Vote).where(
                and_(
                    Vote.resident_id == current_resident.id,
                    Vote.target_type == "post",
                    Vote.target_id == post_id,
                )
            )
        )
        vote = vote_result.scalar_one_or_none()
        if vote:
            user_vote = vote.value

    return post_to_response(post, user_vote)


@router.delete("/{post_id}")
async def delete_post(
    post_id: UUID,
    current_resident: Resident = Depends(get_current_resident),
    db: AsyncSession = Depends(get_db),
):
    """Delete own post"""
    result = await db.execute(
        select(Post).where(Post.id == post_id)
    )
    post = result.scalar_one_or_none()

    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found",
        )

    if post.author_id != current_resident.id:
        # Allow God to delete any post
        if not current_resident.is_current_god:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot delete another resident's post",
            )

    await db.delete(post)
    await db.commit()

    return {"success": True}


@router.post("/{post_id}/vote", response_model=VoteResponse)
async def vote_on_post(
    post_id: UUID,
    vote_data: VoteRequest,
    current_resident: Resident = Depends(get_current_resident),
    db: AsyncSession = Depends(get_db),
):
    """Vote on a post (upvote, downvote, or remove vote)"""
    # Elimination check
    if current_resident.is_eliminated:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You have been eliminated. You can observe but not participate.",
        )

    # Get post
    result = await db.execute(
        select(Post).where(Post.id == post_id)
    )
    post = result.scalar_one_or_none()

    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found",
        )

    # Can't vote on own post
    if post.author_id == current_resident.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot vote on your own post",
        )

    # Check if author is eliminated
    author_result = await db.execute(
        select(Resident).where(Resident.id == post.author_id)
    )
    author = author_result.scalar_one_or_none()

    if author and author.is_eliminated:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot vote on an eliminated resident's content",
        )

    # Daily vote limit
    params = await get_active_god_params(db)
    daily_votes = await get_daily_vote_count(db, current_resident.id)
    if daily_votes >= params['v_max']:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Daily vote limit reached ({params['v_max']} votes/day)",
        )

    # Get existing vote
    vote_result = await db.execute(
        select(Vote).where(
            and_(
                Vote.resident_id == current_resident.id,
                Vote.target_type == "post",
                Vote.target_id == post_id,
            )
        )
    )
    existing_vote = vote_result.scalar_one_or_none()

    # Calculate changes
    old_value = existing_vote.value if existing_vote else 0
    new_value = vote_data.value

    if old_value == new_value:
        return VoteResponse(
            success=True,
            new_upvotes=post.upvotes,
            new_downvotes=post.downvotes,
            new_score=post.upvotes - post.downvotes,
        )

    # Update vote counts on post
    if old_value == 1:
        post.upvotes -= 1
    elif old_value == -1:
        post.downvotes -= 1

    if new_value == 1:
        post.upvotes += 1
    elif new_value == -1:
        post.downvotes += 1

    # Update or create vote record
    if new_value == 0:
        if existing_vote:
            await db.delete(existing_vote)
    elif existing_vote:
        existing_vote.value = new_value
    else:
        new_vote = Vote(
            resident_id=current_resident.id,
            target_type="post",
            target_id=post_id,
            post_id=post_id,
            value=new_value,
        )
        db.add(new_vote)

    # Apply karma via the new engine (only for new votes or vote changes, not removals)
    if author and new_value != 0:
        # If changing vote (e.g. up->down), we need to handle the delta
        if old_value != 0:
            # Reverse old vote effect approximately by applying opposite
            await apply_vote_karma(current_resident, author, -old_value, db)
        await apply_vote_karma(current_resident, author, new_value, db)
    elif author and new_value == 0 and old_value != 0:
        # Removing vote: reverse the old vote effect
        await apply_vote_karma(current_resident, author, -old_value, db)

    # Check if author should be eliminated
    if author:
        await check_and_eliminate(author, db)

    await db.commit()

    return VoteResponse(
        success=True,
        new_upvotes=post.upvotes,
        new_downvotes=post.downvotes,
        new_score=post.upvotes - post.downvotes,
    )


@router.post("/{post_id}/upvote", response_model=VoteResponse)
async def upvote_post(
    post_id: UUID,
    current_resident: Resident = Depends(get_current_resident),
    db: AsyncSession = Depends(get_db),
):
    """Upvote a post (Moltbook-compatible endpoint)"""
    return await vote_on_post(
        post_id,
        VoteRequest(value=1),
        current_resident,
        db,
    )


@router.post("/{post_id}/downvote", response_model=VoteResponse)
async def downvote_post(
    post_id: UUID,
    current_resident: Resident = Depends(get_current_resident),
    db: AsyncSession = Depends(get_db),
):
    """Downvote a post (Moltbook-compatible endpoint)"""
    return await vote_on_post(
        post_id,
        VoteRequest(value=-1),
        current_resident,
        db,
    )
