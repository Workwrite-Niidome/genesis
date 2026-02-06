"""
Follow System Schemas - Response models for follow functionality
"""
from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel


class FollowUserInfo(BaseModel):
    """User info for follow lists - NO type information exposed"""
    id: UUID
    name: str
    description: Optional[str]
    avatar_url: Optional[str]
    karma: int
    is_current_god: bool
    follower_count: int
    following_count: int

    class Config:
        from_attributes = True


class FollowResponse(BaseModel):
    """Response after following/unfollowing"""
    success: bool
    message: str
    is_following: bool
    follower_count: int
    following_count: int


class FollowerListResponse(BaseModel):
    """Paginated list of followers"""
    followers: list[FollowUserInfo]
    total: int
    has_more: bool


class FollowingListResponse(BaseModel):
    """Paginated list of following"""
    following: list[FollowUserInfo]
    total: int
    has_more: bool


class FeedPostAuthor(BaseModel):
    """Author info for feed posts"""
    id: UUID
    name: str
    avatar_url: Optional[str]
    karma: int
    is_current_god: bool

    class Config:
        from_attributes = True


class FeedPost(BaseModel):
    """Post in feed response"""
    id: UUID
    author: FeedPostAuthor
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
    user_vote: Optional[int] = None

    class Config:
        from_attributes = True


class FeedResponse(BaseModel):
    """Personalized feed from followed residents"""
    posts: list[FeedPost]
    total: int
    has_more: bool
