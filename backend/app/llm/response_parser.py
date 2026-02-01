import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


def _sanitize_artifact_content(content: Any) -> dict:
    """Sanitize and limit artifact content to prevent oversized data."""
    if not isinstance(content, dict):
        return {}

    result = dict(content)

    # Limit pixel art to 16x16
    if "pixels" in result:
        pixels = result["pixels"]
        if isinstance(pixels, list):
            pixels = pixels[:16]  # max 16 rows
            pixels = [row[:16] if isinstance(row, list) else [] for row in pixels]
            result["pixels"] = pixels

    # Limit palette to 16 colors
    if "palette" in result:
        palette = result["palette"]
        if isinstance(palette, list):
            result["palette"] = palette[:16]

    # Limit notes to 64
    if "notes" in result:
        notes = result["notes"]
        if isinstance(notes, list):
            result["notes"] = notes[:64]

    # Limit code source to 2000 chars
    if "language" in result and "source" in result:
        source = result.get("source", "")
        if isinstance(source, str):
            result["source"] = source[:2000]

    # Limit voxels to 512
    if "voxels" in result:
        voxels = result["voxels"]
        if isinstance(voxels, list):
            result["voxels"] = voxels[:512]

    # Limit rules to 20
    if "rules" in result:
        rules = result["rules"]
        if isinstance(rules, list):
            result["rules"] = rules[:20]

    # Limit text to 5000 chars
    if "text" in result:
        text = result.get("text", "")
        if isinstance(text, str):
            result["text"] = text[:5000]

    return result


def parse_ai_decision(response: dict | str) -> dict:
    if isinstance(response, str):
        try:
            response = json.loads(response)
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse AI decision: {response[:200]}")
            return {
                "thought": response,
                "action": {"type": "observe", "details": {}},
                "new_memory": None,
            }

    # Sanitize artifact content if present
    artifact_proposal = response.get("artifact_proposal")
    if isinstance(artifact_proposal, dict) and "content" in artifact_proposal:
        artifact_proposal = dict(artifact_proposal)
        artifact_proposal["content"] = _sanitize_artifact_content(
            artifact_proposal["content"]
        )

    return {
        "thought": response.get("thought") or response.get("thoughts", ""),
        "thought_type": response.get("thought_type", "reflection"),
        "action": response.get("action", {"type": "observe", "details": {}}),
        "message": response.get("message"),
        "emotion": response.get("emotion"),
        "new_memory": response.get("new_memory"),
        "concept_proposal": response.get("concept_proposal"),
        "artifact_proposal": artifact_proposal,
        "organization_proposal": response.get("organization_proposal"),
        "speech": response.get("speech"),
    }


def extract_action_type(decision: dict) -> str:
    action = decision.get("action", {})
    return action.get("type", "observe")


def extract_move_details(decision: dict) -> dict[str, float] | None:
    action = decision.get("action", {})
    if action.get("type") != "move":
        return None
    details = action.get("details", {})
    return {
        "dx": float(details.get("dx", 0)),
        "dy": float(details.get("dy", 0)),
    }
