import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


def parse_ai_decision(response: dict | str) -> dict:
    if isinstance(response, str):
        try:
            response = json.loads(response)
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse AI decision: {response[:200]}")
            return {
                "thoughts": response,
                "action": {"type": "observe", "details": {}},
                "new_memory": None,
            }

    return {
        "thoughts": response.get("thoughts", ""),
        "action": response.get("action", {"type": "observe", "details": {}}),
        "new_memory": response.get("new_memory"),
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
