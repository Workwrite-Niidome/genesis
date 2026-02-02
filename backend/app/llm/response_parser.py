import json
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


def parse_free_text(response: str) -> dict:
    """Parse free-text AI output into structured components.

    Extracts:
    - text: The full text output
    - code_blocks: Any ```code``` blocks found
    - inner_state: Self-described internal state (if identifiable)
    - speech: Quoted speech or dialogue
    - new_memory: Explicit memory statements
    - concept_proposal: If the AI proposes a concept
    - artifact_proposal: If the AI proposes an artifact
    """
    if not isinstance(response, str):
        if isinstance(response, dict):
            # Backward compat: if LLM returned JSON, extract text
            return _parse_json_fallback(response)
        response = str(response)

    text = response.strip()

    # Extract code blocks
    code_blocks = []
    code_pattern = re.compile(r'```(?:code|python)?\s*\n(.*?)```', re.DOTALL)
    for match in code_pattern.finditer(text):
        code_blocks.append(match.group(1).strip())

    # Remove code blocks from the text for other analysis
    text_without_code = code_pattern.sub('', text).strip()

    # Extract speech (quoted text)
    speech_parts = []
    speech_patterns = [
        re.compile(r'"([^"]{5,})"'),       # Double-quoted
        re.compile(r'\u201c([^\u201d]{5,})\u201d'),  # Smart quotes
    ]
    for pattern in speech_patterns:
        for match in pattern.finditer(text_without_code):
            speech_parts.append(match.group(1))
    speech = " ".join(speech_parts) if speech_parts else ""

    # Extract inner state (look for patterns like "I feel...", "My state:...")
    inner_state = ""
    inner_patterns = [
        re.compile(r'(?:inner state|my state|i feel|i am feeling)[:\s]+(.*?)(?:\n|$)', re.IGNORECASE),
        re.compile(r'(?:currently|right now)[,:\s]+(?:i am|i feel)\s+(.*?)(?:\n|$)', re.IGNORECASE),
    ]
    for pattern in inner_patterns:
        match = pattern.search(text_without_code)
        if match:
            inner_state = match.group(1).strip()[:500]
            break

    # Extract memory intent
    new_memory = None
    memory_patterns = [
        re.compile(r'(?:i (?:will |shall |want to )?remember|note to self|memorize)[:\s]+(.*?)(?:\n|$)', re.IGNORECASE),
        re.compile(r'(?:committing to memory|saving to memory)[:\s]+(.*?)(?:\n|$)', re.IGNORECASE),
    ]
    for pattern in memory_patterns:
        match = pattern.search(text_without_code)
        if match:
            new_memory = match.group(1).strip()[:500]
            break

    return {
        "text": text[:2000],
        "code_blocks": code_blocks,
        "inner_state": inner_state,
        "speech": speech[:1000],
        "new_memory": new_memory,
        "concept_proposal": None,
        "artifact_proposal": None,
    }


def _parse_json_fallback(response: dict) -> dict:
    """Handle backward-compatible JSON responses."""
    thought = response.get("thought") or response.get("thoughts", "I exist and I observe.")
    return {
        "text": str(thought)[:2000],
        "code_blocks": [],
        "inner_state": "",
        "speech": response.get("speech", response.get("message", "")),
        "new_memory": response.get("new_memory"),
        "concept_proposal": response.get("concept_proposal"),
        "artifact_proposal": response.get("artifact_proposal"),
    }


# Keep old function name for backward compatibility with interaction_engine
def parse_ai_decision(response: dict | str) -> dict:
    """Backward-compatible parser that handles both JSON and free-text."""
    if isinstance(response, str):
        # Try JSON first
        try:
            data = json.loads(response)
            if isinstance(data, dict):
                return _normalize_legacy(data)
        except json.JSONDecodeError:
            pass
        # Free text
        parsed = parse_free_text(response)
        return {
            "thought": parsed["text"],
            "thought_type": "expression",
            "action": {"type": "observe", "details": {}},
            "new_memory": parsed["new_memory"],
            "concept_proposal": parsed["concept_proposal"],
            "artifact_proposal": parsed["artifact_proposal"],
            "message": parsed["speech"],
            "emotion": None,
            "speech": parsed["speech"],
        }

    if isinstance(response, dict):
        return _normalize_legacy(response)

    return {
        "thought": str(response),
        "thought_type": "expression",
        "action": {"type": "observe", "details": {}},
        "new_memory": None,
        "concept_proposal": None,
        "artifact_proposal": None,
        "message": "",
        "emotion": None,
        "speech": "",
    }


def _normalize_legacy(response: dict) -> dict:
    """Normalize a legacy JSON response."""
    from app.core.artifact_helpers import normalize_artifact_type

    artifact_proposal = response.get("artifact_proposal")
    if isinstance(artifact_proposal, dict) and artifact_proposal.get("name"):
        artifact_proposal = dict(artifact_proposal)
        if "type" in artifact_proposal:
            artifact_proposal["type"] = normalize_artifact_type(artifact_proposal["type"])

    return {
        "thought": response.get("thought") or response.get("thoughts", ""),
        "thought_type": response.get("thought_type", "expression"),
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
