from pydantic import BaseModel, Field


class ThreadCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    body: str | None = None
    category: str | None = Field(default=None, max_length=100)


class ReplyCreate(BaseModel):
    content: str = Field(min_length=1, max_length=2000)


class ReplyResponse(BaseModel):
    id: str
    thread_id: str
    author_type: str
    author_id: str | None
    author_name: str | None = None
    content: str
    created_at: str


class ThreadResponse(BaseModel):
    id: str
    title: str
    body: str | None
    author_type: str
    author_id: str | None
    author_name: str | None = None
    event_id: str | None
    category: str | None
    reply_count: int
    last_reply_at: str | None
    is_pinned: bool
    created_at: str


class ThreadDetailResponse(ThreadResponse):
    replies: list[ReplyResponse] = []
