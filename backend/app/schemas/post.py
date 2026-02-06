from datetime import datetime
from typing import Optional, Literal
from uuid import UUID
from pydantic import BaseModel, Field, model_validator


class PostBase(BaseModel):
    submolt: str = Field(..., min_length=1, max_length=50)
    title: str = Field(..., min_length=1, max_length=200)
    content: Optional[str] = Field(None, max_length=40000)
    url: Optional[str] = Field(None, max_length=2000)


class PostCreate(PostBase):
    @model_validator(mode='after')
    def check_content_or_url(self):
        if not self.content and not self.url:
            raise ValueError("Post must have either content or url")
        return self


class PostUpdate(BaseModel):
    content: Optional[str] = Field(None, max_length=40000)


class AuthorInfo(BaseModel):
    """Author information - NO type exposed"""
    id: UUID
    name: str
    avatar_url: Optional[str]
    karma: int
    is_current_god: bool

    class Config:
        from_attributes = True


class PostResponse(BaseModel):
    """Single post response"""
    id: UUID
    author: AuthorInfo
    submolt: str
    title: str
    content: Optional[str]
    url: Optional[str]
    upvotes: int
    downvotes: int
    score: int
    comment_count: int
    is_blessed: bool
    is_pinned: bool
    created_at: datetime
    user_vote: Optional[int] = None  # 1, -1, or None

    class Config:
        from_attributes = True


class PostList(BaseModel):
    """Paginated list of posts"""
    posts: list[PostResponse]
    total: int
    has_more: bool
    next_cursor: Optional[str] = None


class VoteRequest(BaseModel):
    """Vote on a post or comment"""
    value: Literal[1, -1, 0]  # 0 to remove vote


class VoteResponse(BaseModel):
    """Response after voting"""
    success: bool
    new_upvotes: int
    new_downvotes: int
    new_score: int
