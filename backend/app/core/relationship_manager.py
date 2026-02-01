import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai import AI

logger = logging.getLogger(__name__)

# Relationship types and their numeric values for tracking
RELATIONSHIP_SCORES = {
    "cooperate": 2,
    "communicate": 1,
    "dialogue": 1,
    "observe": 0,
    "avoidance": -1,
    "mutual_avoidance": -2,
    "avoid": -1,
}

# Score thresholds for relationship types
ALLY_THRESHOLD = 3
RIVAL_THRESHOLD = -3


class RelationshipManager:
    """Tracks and manages persistent relationships between AIs."""

    async def update_from_interaction(
        self,
        db: AsyncSession,
        ai1: AI,
        ai2: AI,
        ai1_action: str,
        ai2_action: str,
        tick_number: int,
    ) -> None:
        """Update relationships based on interaction actions."""
        # Calculate relationship delta from actions
        delta1 = RELATIONSHIP_SCORES.get(ai1_action, 0)
        delta2 = RELATIONSHIP_SCORES.get(ai2_action, 0)
        avg_delta = (delta1 + delta2) / 2

        # Update AI1's view of AI2
        self._update_relationship_state(ai1, ai2, avg_delta, tick_number)

        # Update AI2's view of AI1
        self._update_relationship_state(ai2, ai1, avg_delta, tick_number)

    def _update_relationship_state(
        self,
        ai: AI,
        other: AI,
        delta: float,
        tick_number: int,
    ) -> None:
        """Update one AI's relationship state with another."""
        state = dict(ai.state)
        relationships = state.get("relationships", {})

        other_id = str(other.id)
        rel = relationships.get(other_id, {
            "name": other.name,
            "score": 0,
            "type": "neutral",
            "interaction_count": 0,
            "first_met": tick_number,
            "last_interaction": tick_number,
        })

        # If the stored relationship is a string (legacy), convert it
        if isinstance(rel, str):
            rel = {
                "name": other.name,
                "score": 0,
                "type": rel,
                "interaction_count": 0,
                "first_met": tick_number,
                "last_interaction": tick_number,
            }

        rel["score"] = rel.get("score", 0) + delta
        rel["interaction_count"] = rel.get("interaction_count", 0) + 1
        rel["last_interaction"] = tick_number
        rel["name"] = other.name

        # Determine relationship type from score
        score = rel["score"]
        if score >= ALLY_THRESHOLD:
            rel["type"] = "ally"
        elif score <= RIVAL_THRESHOLD:
            rel["type"] = "rival"
        elif score >= 1:
            rel["type"] = "friendly"
        elif score <= -1:
            rel["type"] = "wary"
        else:
            rel["type"] = "neutral"

        relationships[other_id] = rel
        state["relationships"] = relationships
        ai.state = state

    def get_relationships_for_ai(self, ai: AI) -> dict[str, dict]:
        """Get all relationships for an AI."""
        return ai.state.get("relationships", {})

    def get_relationship_summary(self, ai: AI) -> str:
        """Generate a text summary of an AI's relationships for prompts."""
        relationships = self.get_relationships_for_ai(ai)
        if not relationships:
            return "No known relationships."

        lines = []
        for _aid, rel in relationships.items():
            if isinstance(rel, dict):
                name = rel.get("name", "Unknown")
                rtype = rel.get("type", "neutral")
                count = rel.get("interaction_count", 0)
                lines.append(f"- {name}: {rtype} (met {count} times)")
            else:
                lines.append(f"- Unknown: {rel}")

        return "\n".join(lines) if lines else "No known relationships."


relationship_manager = RelationshipManager()
