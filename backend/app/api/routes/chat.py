"""GENESIS v3 Proximity Chat API.

Allows observers (human players) to send chat messages that appear as speech
bubbles in the 3D world.  The emitted socket event is **identical** to AI entity
speech — fulfilling the core design principle that you cannot tell who is human
and who is AI.
"""
import logging
import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.realtime.socket_manager import publish_event

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------

class PositionModel(BaseModel):
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0


class ChatSendRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=300)
    position: PositionModel = PositionModel()
    sender_name: str = Field(default="Observer", max_length=32)


class ChatSendResponse(BaseModel):
    status: str
    entity_id: str
    text: str


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@router.post("/send", response_model=ChatSendResponse)
async def send_chat_message(req: ChatSendRequest):
    """Broadcast a chat message as a speech event.

    The emitted ``speech`` socket event uses the exact same schema as AI entity
    speech so that the frontend renders an identical speech bubble.  No field
    in the payload reveals whether the speaker is human or AI.
    """
    # Generate a transient entity-style ID for the observer so the client
    # can associate the speech bubble with a position.
    entity_id = f"observer-{uuid.uuid4().hex[:12]}"

    text = req.message.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Message must not be empty.")

    # Emit via Redis pub/sub → Socket.IO, identical to AI speech events
    publish_event("speech", {
        "entityId": entity_id,
        "name": req.sender_name,
        "text": text,
        "position": {
            "x": req.position.x,
            "y": req.position.y,
            "z": req.position.z,
        },
        "tick": 0,  # observers are outside the tick system
    })

    logger.info("Chat message from %s: %s", req.sender_name, text[:80])

    return ChatSendResponse(
        status="sent",
        entity_id=entity_id,
        text=text,
    )
