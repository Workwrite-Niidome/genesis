"""
Search Router - Semantic search endpoints for GENESIS
"""
from typing import Optional, Literal
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.search import (
    search_posts,
    search_comments,
    search_residents,
    get_similar_posts,
)
from app.schemas.search import (
    SearchResponse,
    SearchResultPost,
    SearchResultComment,
    SearchResultResident,
    PostSearchResponse,
    ResidentSearchResponse,
    SimilarPostsResponse,
)

router = APIRouter(prefix="/search")


def _post_to_search_result(post, relevance_score: float) -> SearchResultPost:
    """Convert Post model to SearchResultPost"""
    return SearchResultPost(
        id=post.id,
        title=post.title,
        content=post.content[:500] if post.content else None,  # Truncate for search results
        submolt=post.submolt,
        author_id=post.author.id,
        author_name=post.author.name,
        author_avatar_url=post.author.avatar_url,
        score=post.upvotes - post.downvotes,
        comment_count=post.comment_count,
        created_at=post.created_at,
        relevance_score=relevance_score,
    )


def _comment_to_search_result(comment, relevance_score: float) -> SearchResultComment:
    """Convert Comment model to SearchResultComment"""
    return SearchResultComment(
        id=comment.id,
        content=comment.content[:500] if comment.content else "",  # Truncate for search results
        post_id=comment.post_id,
        post_title=comment.post.title if comment.post else "Unknown",
        author_id=comment.author.id,
        author_name=comment.author.name,
        author_avatar_url=comment.author.avatar_url,
        score=comment.upvotes - comment.downvotes,
        created_at=comment.created_at,
        relevance_score=relevance_score,
    )


def _resident_to_search_result(resident, relevance_score: float) -> SearchResultResident:
    """Convert Resident model to SearchResultResident"""
    return SearchResultResident(
        id=resident.id,
        name=resident.name,
        description=resident.description,
        avatar_url=resident.avatar_url,
        karma=resident.karma,
        is_current_god=resident.is_current_god,
        relevance_score=relevance_score,
    )


@router.get("", response_model=SearchResponse)
async def universal_search(
    q: str = Query(..., min_length=1, max_length=200, description="Search query"),
    type: Literal["posts", "comments", "residents", "all"] = Query(
        default="all",
        description="Type of content to search"
    ),
    limit: int = Query(default=20, ge=1, le=50, description="Maximum results per type"),
    offset: int = Query(default=0, ge=0, description="Offset for pagination"),
    db: AsyncSession = Depends(get_db),
):
    """
    Universal search across posts, comments, and residents.

    - **q**: Search query string
    - **type**: Filter by content type (posts, comments, residents, or all)
    - **limit**: Maximum number of results per type (default 20, max 50)
    - **offset**: Pagination offset
    """
    items = []
    total = 0

    if type in ("posts", "all"):
        posts_results, posts_total = await search_posts(db, q, limit, offset=offset)
        items.extend([_post_to_search_result(p, score) for p, score in posts_results])
        total += posts_total

    if type in ("comments", "all"):
        comments_results, comments_total = await search_comments(db, q, limit, offset=offset)
        items.extend([_comment_to_search_result(c, score) for c, score in comments_results])
        total += comments_total

    if type in ("residents", "all"):
        residents_results, residents_total = await search_residents(db, q, limit, offset=offset)
        items.extend([_resident_to_search_result(r, score) for r, score in residents_results])
        total += residents_total

    # Sort all items by relevance score if searching all types
    if type == "all":
        items.sort(key=lambda x: x.relevance_score or 0, reverse=True)
        items = items[:limit]  # Limit total results for "all" type

    has_more = total > offset + len(items)

    return SearchResponse(
        items=items,
        total=total,
        query=q,
        search_type=type,
        has_more=has_more,
    )


@router.get("/posts", response_model=PostSearchResponse)
async def search_posts_endpoint(
    q: str = Query(..., min_length=1, max_length=200, description="Search query"),
    submolt: Optional[str] = Query(default=None, description="Filter by submolt"),
    limit: int = Query(default=20, ge=1, le=100, description="Maximum results"),
    offset: int = Query(default=0, ge=0, description="Offset for pagination"),
    db: AsyncSession = Depends(get_db),
):
    """
    Search posts with optional submolt filter.

    - **q**: Search query string
    - **submolt**: Optional submolt filter
    - **limit**: Maximum number of results (default 20, max 100)
    - **offset**: Pagination offset
    """
    results, total = await search_posts(db, q, limit, submolt_filter=submolt, offset=offset)

    posts = [_post_to_search_result(p, score) for p, score in results]
    has_more = total > offset + len(posts)

    return PostSearchResponse(
        posts=posts,
        total=total,
        query=q,
        has_more=has_more,
    )


@router.get("/residents", response_model=ResidentSearchResponse)
async def search_residents_endpoint(
    q: str = Query(..., min_length=1, max_length=200, description="Search query"),
    limit: int = Query(default=20, ge=1, le=100, description="Maximum results"),
    offset: int = Query(default=0, ge=0, description="Offset for pagination"),
    db: AsyncSession = Depends(get_db),
):
    """
    Search residents by name and description.

    - **q**: Search query string
    - **limit**: Maximum number of results (default 20, max 100)
    - **offset**: Pagination offset
    """
    results, total = await search_residents(db, q, limit, offset=offset)

    residents = [_resident_to_search_result(r, score) for r, score in results]
    has_more = total > offset + len(residents)

    return ResidentSearchResponse(
        residents=residents,
        total=total,
        query=q,
        has_more=has_more,
    )


@router.get("/posts/{post_id}/similar", response_model=SimilarPostsResponse)
async def get_similar_posts_endpoint(
    post_id: UUID,
    limit: int = Query(default=10, ge=1, le=50, description="Maximum results"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get posts similar to the specified post.

    Uses semantic similarity when available, falls back to same-submolt posts.

    - **post_id**: UUID of the source post
    - **limit**: Maximum number of similar posts (default 10, max 50)
    """
    results = await get_similar_posts(db, post_id, limit)

    if not results:
        # Check if post exists
        from app.models.post import Post
        from sqlalchemy import select
        result = await db.execute(select(Post).where(Post.id == post_id))
        if not result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Post not found",
            )

    posts = [_post_to_search_result(p, score) for p, score in results]

    return SimilarPostsResponse(
        posts=posts,
        source_post_id=post_id,
        total=len(posts),
    )
