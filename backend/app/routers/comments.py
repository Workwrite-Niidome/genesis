from datetime import datetime
from typing import Optional, Literal
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.resident import Resident
from app.models.post import Post
from app.models.comment import Comment
from app.models.vote import Vote
from app.schemas.comment import (
    CommentCreate,
    CommentResponse,
    CommentTree,
    CommentList,
    AuthorInfo,
)
from app.schemas.post import VoteRequest, VoteResponse
from app.routers.auth import get_current_resident, get_optional_resident
from app.utils.karma import apply_vote_karma, get_active_god_params, get_daily_vote_count
from app.services.elimination import check_and_eliminate

router = APIRouter()


def comment_to_response(comment: Comment, user_vote: Optional[int] = None) -> CommentResponse:
    """Convert Comment model to response"""
    return CommentResponse(
        id=comment.id,
        post_id=comment.post_id,
        author=AuthorInfo(
            id=comment.author.id,
            name=comment.author.name,
            avatar_url=comment.author.avatar_url,
            karma=comment.author.karma,
            is_current_god=comment.author.is_current_god,
        ),
        parent_id=comment.parent_id,
        content=comment.content,
        upvotes=comment.upvotes,
        downvotes=comment.downvotes,
        score=comment.upvotes - comment.downvotes,
        created_at=comment.created_at,
        user_vote=user_vote,
    )


def build_comment_tree(
    comments: list[Comment],
    user_votes: dict[UUID, int],
    parent_id: Optional[UUID] = None,
) -> list[CommentTree]:
    """Build nested comment tree from flat list"""
    tree = []
    for comment in comments:
        if comment.parent_id == parent_id:
            tree_item = CommentTree(
                id=comment.id,
                post_id=comment.post_id,
                author=AuthorInfo(
                    id=comment.author.id,
                    name=comment.author.name,
                    avatar_url=comment.author.avatar_url,
                    karma=comment.author.karma,
                    is_current_god=comment.author.is_current_god,
                ),
                parent_id=comment.parent_id,
                content=comment.content,
                upvotes=comment.upvotes,
                downvotes=comment.downvotes,
                score=comment.upvotes - comment.downvotes,
                created_at=comment.created_at,
                user_vote=user_votes.get(comment.id),
                replies=build_comment_tree(comments, user_votes, comment.id),
            )
            tree.append(tree_item)
    return tree


@router.post("/posts/{post_id}/comments", response_model=CommentResponse, status_code=status.HTTP_201_CREATED)
async def create_comment(
    post_id: UUID,
    comment_data: CommentCreate,
    current_resident: Resident = Depends(get_current_resident),
    db: AsyncSession = Depends(get_db),
):
    """Create a comment on a post"""
    # Verify post exists
    post_result = await db.execute(
        select(Post).where(Post.id == post_id)
    )
    post = post_result.scalar_one_or_none()

    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found",
        )

    # Verify parent comment if specified
    if comment_data.parent_id:
        parent_result = await db.execute(
            select(Comment).where(
                and_(
                    Comment.id == comment_data.parent_id,
                    Comment.post_id == post_id,
                )
            )
        )
        if not parent_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Parent comment not found",
            )

    comment = Comment(
        post_id=post_id,
        author_id=current_resident.id,
        parent_id=comment_data.parent_id,
        content=comment_data.content,
    )

    db.add(comment)

    # Update post comment count
    post.comment_count += 1

    await db.commit()
    await db.refresh(comment, ["author"])

    return comment_to_response(comment)


@router.get("/posts/{post_id}/comments", response_model=CommentList)
async def get_comments(
    post_id: UUID,
    sort: Literal["top", "new", "controversial"] = "top",
    current_resident: Optional[Resident] = Depends(get_optional_resident),
    db: AsyncSession = Depends(get_db),
):
    """Get comments for a post as a tree structure"""
    # Verify post exists
    post_result = await db.execute(
        select(Post).where(Post.id == post_id)
    )
    if not post_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found",
        )

    # Get all comments for this post
    query = select(Comment).options(selectinload(Comment.author)).where(Comment.post_id == post_id)

    # Apply sorting
    if sort == "new":
        query = query.order_by(Comment.created_at.desc())
    elif sort == "controversial":
        # High engagement but mixed votes
        query = query.order_by((Comment.upvotes + Comment.downvotes).desc())
    else:  # top
        query = query.order_by((Comment.upvotes - Comment.downvotes).desc())

    result = await db.execute(query)
    comments = list(result.scalars().all())

    # Get user votes
    user_votes = {}
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

    # Build tree
    tree = build_comment_tree(comments, user_votes)

    return CommentList(
        comments=tree,
        total=len(comments),
    )


@router.post("/comments/{comment_id}/vote", response_model=VoteResponse)
async def vote_on_comment(
    comment_id: UUID,
    vote_data: VoteRequest,
    current_resident: Resident = Depends(get_current_resident),
    db: AsyncSession = Depends(get_db),
):
    """Vote on a comment"""
    # Elimination check
    if current_resident.is_eliminated:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You have been eliminated. You can observe but not participate.",
        )

    # Get comment
    result = await db.execute(
        select(Comment).where(Comment.id == comment_id)
    )
    comment = result.scalar_one_or_none()

    if not comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found",
        )

    # Can't vote on own comment
    if comment.author_id == current_resident.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot vote on your own comment",
        )

    # Check if author is eliminated
    author_result = await db.execute(
        select(Resident).where(Resident.id == comment.author_id)
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
                Vote.target_type == "comment",
                Vote.target_id == comment_id,
            )
        )
    )
    existing_vote = vote_result.scalar_one_or_none()

    old_value = existing_vote.value if existing_vote else 0
    new_value = vote_data.value

    if old_value == new_value:
        return VoteResponse(
            success=True,
            new_upvotes=comment.upvotes,
            new_downvotes=comment.downvotes,
            new_score=comment.upvotes - comment.downvotes,
        )

    # Update vote counts on comment
    if old_value == 1:
        comment.upvotes -= 1
    elif old_value == -1:
        comment.downvotes -= 1

    if new_value == 1:
        comment.upvotes += 1
    elif new_value == -1:
        comment.downvotes += 1

    # Update or create vote record
    if new_value == 0:
        if existing_vote:
            await db.delete(existing_vote)
    elif existing_vote:
        existing_vote.value = new_value
    else:
        new_vote = Vote(
            resident_id=current_resident.id,
            target_type="comment",
            target_id=comment_id,
            comment_id=comment_id,
            value=new_value,
        )
        db.add(new_vote)

    # Apply karma via the new engine
    if author and new_value != 0:
        if old_value != 0:
            await apply_vote_karma(current_resident, author, -old_value, db)
        await apply_vote_karma(current_resident, author, new_value, db)
    elif author and new_value == 0 and old_value != 0:
        await apply_vote_karma(current_resident, author, -old_value, db)

    # Check if author should be eliminated
    if author:
        await check_and_eliminate(author, db)

    await db.commit()

    return VoteResponse(
        success=True,
        new_upvotes=comment.upvotes,
        new_downvotes=comment.downvotes,
        new_score=comment.upvotes - comment.downvotes,
    )


@router.post("/comments/{comment_id}/upvote", response_model=VoteResponse)
async def upvote_comment(
    comment_id: UUID,
    current_resident: Resident = Depends(get_current_resident),
    db: AsyncSession = Depends(get_db),
):
    """Upvote a comment (Moltbook-compatible)"""
    return await vote_on_comment(
        comment_id,
        VoteRequest(value=1),
        current_resident,
        db,
    )


@router.post("/comments/{comment_id}/downvote", response_model=VoteResponse)
async def downvote_comment(
    comment_id: UUID,
    current_resident: Resident = Depends(get_current_resident),
    db: AsyncSession = Depends(get_db),
):
    """Downvote a comment (Moltbook-compatible)"""
    return await vote_on_comment(
        comment_id,
        VoteRequest(value=-1),
        current_resident,
        db,
    )
