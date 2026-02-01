from pydantic import BaseModel, Field


class ObserverRegister(BaseModel):
    username: str = Field(min_length=2, max_length=50)
    password: str = Field(min_length=4, max_length=100)
    language: str = "en"


class ObserverLogin(BaseModel):
    username: str
    password: str


class ObserverResponse(BaseModel):
    id: str
    username: str
    role: str
    language: str
    token: str  # JWT token


class ChatMessageCreate(BaseModel):
    channel: str = "global"
    content: str = Field(min_length=1, max_length=500)


class ChatMessageResponse(BaseModel):
    id: str
    username: str
    channel: str
    content: str
    timestamp: str
