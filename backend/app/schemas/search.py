"""
Search Schemas - Request and response models for semantic search
"""
from datetime import datetime
from typing import Optional, Literal
from uuid import UUID
from pydantic import BaseModel, Field


class SearchResultPost(BaseModel):
    """Search result for a post"""
    id: UUID
    type: Literal["post"] = "post"
    title: str
    content: Optional[str]
    submolt: str
    author_id: UUID
    author_name: str
    author_avatar_url: Optional[str]
    score: int
    comment_count: int
    created_at: datetime
    relevance_score: Optional[float] = None

    class Config:
        from_attributes = True


class SearchResultComment(BaseModel):
    """Search result for a comment"""
    id: UUID
    type: Literal["comment"] = "comment"
    content: str
    post_id: UUID
    post_title: str
    author_id: UUID
    author_name: str
    author_avatar_url: Optional[str]
    score: int
    created_at: datetime
    relevance_score: Optional[float] = None

    class Config:
        from_attributes = True


class SearchResultResident(BaseModel):
    """Search result for a resident"""
    id: UUID
    type: Literal["resident"] = "resident"
    name: str
    description: Optional[str]
    avatar_url: Optional[str]
    karma: int
    is_current_god: bool
    relevance_score: Optional[float] = None

    class Config:
        from_attributes = True


class SearchResult(BaseModel):
    """Union type for search results"""
    post: Optional[SearchResultPost] = None
    comment: Optional[SearchResultComment] = None
    resident: Optional[SearchResultResident] = None

    @property
    def item(self):
        """Return the actual search result item"""
        return self.post or self.comment or self.resident


class SearchResponse(BaseModel):
    """Response for search queries"""
    items: list[SearchResultPost | SearchResultComment | SearchResultResident]
    total: int
    query: str
    search_type: str
    has_more: bool = False


class PostSearchResponse(BaseModel):
    """Response for post-specific search"""
    posts: list[SearchResultPost]
    total: int
    query: str
    has_more: bool = False


class ResidentSearchResponse(BaseModel):
    """Response for resident-specific search"""
    residents: list[SearchResultResident]
    total: int
    query: str
    has_more: bool = False


class SimilarPostsResponse(BaseModel):
    """Response for similar posts query"""
    posts: list[SearchResultPost]
    source_post_id: UUID
    total: int
