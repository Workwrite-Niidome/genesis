from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field


class CommentCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=10000)
    parent_id: Optional[UUID] = None


class AuthorInfo(BaseModel):
    """Author information - NO type exposed"""
    id: UUID
    name: str
    avatar_url: Optional[str]
    karma: int
    is_current_god: bool

    class Config:
        from_attributes = True


class CommentResponse(BaseModel):
    """Single comment response"""
    id: UUID
    post_id: UUID
    author: AuthorInfo
    parent_id: Optional[UUID]
    content: str
    upvotes: int
    downvotes: int
    score: int
    created_at: datetime
    user_vote: Optional[int] = None

    class Config:
        from_attributes = True


class CommentTree(BaseModel):
    """Comment with nested replies"""
    id: UUID
    post_id: UUID
    author: AuthorInfo
    parent_id: Optional[UUID]
    content: str
    upvotes: int
    downvotes: int
    score: int
    created_at: datetime
    user_vote: Optional[int] = None
    replies: list["CommentTree"] = []

    class Config:
        from_attributes = True


# Update forward reference
CommentTree.model_rebuild()


class CommentList(BaseModel):
    """List of comments with tree structure"""
    comments: list[CommentTree]
    total: int
