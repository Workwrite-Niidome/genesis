import logging

import socketio

from app.config import settings

logger = logging.getLogger(__name__)

# Create Socket.IO server
sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins=settings.cors_origins_list,
    logger=False,
    engineio_logger=False,
)

# Create ASGI app for Socket.IO
socket_app = socketio.ASGIApp(sio)


@sio.event
async def connect(sid, environ):
    logger.debug(f"Client connected: {sid}")


@sio.event
async def disconnect(sid):
    logger.debug(f"Client disconnected: {sid}")


class SocketManager:
    """Manages real-time event broadcasting via Socket.IO."""

    async def emit_thought(self, thought_data: dict) -> None:
        """Broadcast a new AI thought."""
        try:
            await sio.emit("thought", thought_data)
        except Exception as e:
            logger.warning(f"Socket emit error (thought): {e}")

    async def emit_event(self, event_data: dict) -> None:
        """Broadcast a world event."""
        try:
            await sio.emit("event", event_data)
        except Exception as e:
            logger.warning(f"Socket emit error (event): {e}")

    async def emit_world_update(self, world_data: dict) -> None:
        """Broadcast world state update."""
        try:
            await sio.emit("world_update", world_data)
        except Exception as e:
            logger.warning(f"Socket emit error (world_update): {e}")

    async def emit_ai_position(self, position_data: dict) -> None:
        """Broadcast AI position update."""
        try:
            await sio.emit("ai_position", position_data)
        except Exception as e:
            logger.warning(f"Socket emit error (ai_position): {e}")

    async def emit_interaction(self, interaction_data: dict) -> None:
        """Broadcast an interaction event."""
        try:
            await sio.emit("interaction", interaction_data)
        except Exception as e:
            logger.warning(f"Socket emit error (interaction): {e}")

    async def emit_god_observation(self, observation_data: dict) -> None:
        """Broadcast a God AI observation."""
        try:
            await sio.emit("god_observation", observation_data)
        except Exception as e:
            logger.warning(f"Socket emit error (god_observation): {e}")

    async def emit_ai_death(self, death_data: dict) -> None:
        """Broadcast an AI death event."""
        try:
            await sio.emit("ai_death", death_data)
        except Exception as e:
            logger.warning(f"Socket emit error (ai_death): {e}")

    async def emit_concept_created(self, concept_data: dict) -> None:
        """Broadcast a new concept creation."""
        try:
            await sio.emit("concept_created", concept_data)
        except Exception as e:
            logger.warning(f"Socket emit error (concept_created): {e}")

    async def emit_artifact_created(self, artifact_data: dict) -> None:
        """Broadcast a new artifact creation."""
        try:
            await sio.emit("artifact_created", artifact_data)
        except Exception as e:
            logger.warning(f"Socket emit error (artifact_created): {e}")

    async def emit_organization_formed(self, org_data: dict) -> None:
        """Broadcast a new organization formation."""
        try:
            await sio.emit("organization_formed", org_data)
        except Exception as e:
            logger.warning(f"Socket emit error (organization_formed): {e}")


socket_manager = SocketManager()
