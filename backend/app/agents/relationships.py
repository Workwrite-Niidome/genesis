"""
GENESIS v3 - Relationship System
==================================
7-axis relationship tracking with event-driven updates and time decay.

Axes:
  trust       [-100, 100]  - How much one entity trusts another
  familiarity [   0, 100]  - How well they know each other
  respect     [   0, 100]  - Admiration and deference
  fear        [   0, 100]  - Intimidation and dread
  anger       [   0, 100]  - Active hostility
  gratitude   [   0, 100]  - Indebtedness and appreciation
  rivalry     [   0, 100]  - Competitive tension
"""

from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entity import EntityRelationship

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------
# Axis metadata
# ------------------------------------------------------------------

# Axes and their valid ranges: (min, max)
AXIS_RANGES: dict[str, tuple[float, float]] = {
    "trust": (-100.0, 100.0),
    "familiarity": (0.0, 100.0),
    "respect": (0.0, 100.0),
    "fear": (0.0, 100.0),
    "anger": (0.0, 100.0),
    "gratitude": (0.0, 100.0),
    "rivalry": (0.0, 100.0),
}

DEFAULT_VALUES: dict[str, float] = {axis: 0.0 for axis in AXIS_RANGES}

# ------------------------------------------------------------------
# Decay rates -- applied once per decay cycle
# ------------------------------------------------------------------

DECAY_RATES: dict[str, float] = {
    "trust": 1.0,        # trust does not decay
    "familiarity": 1.0,  # familiarity does not decay
    "respect": 1.0,      # respect does not decay
    "fear": 0.995,
    "anger": 0.99,
    "gratitude": 0.999,
    "rivalry": 1.0,      # rivalry does not decay
}

# ------------------------------------------------------------------
# Event-driven update rules
# ------------------------------------------------------------------

UPDATE_RULES: dict[str, dict[str, float]] = {
    "helped": {"trust": 1.0, "gratitude": 0.8},
    "betrayed": {"trust": -2.0, "anger": 1.5},
    "attacked": {"trust": -1.5, "fear": 1.0, "anger": 1.0},
    "long_talk": {"familiarity": 0.3, "trust": 0.1},
    "competed_won": {"rivalry": 0.5, "fear": 0.3},
    "competed_lost": {"rivalry": 0.8, "anger": 0.3},
    "shared_creation": {"familiarity": 0.5, "respect": 0.2},
    "insulted": {"anger": 0.8, "trust": -0.5},
    "traded": {"trust": 0.3, "familiarity": 0.2},
    "defended": {"trust": 1.5, "gratitude": 1.0, "respect": 0.5},
    "submitted_to": {"fear": 0.5, "rivalry": -0.3},
}


def _clamp(value: float, axis: str) -> float:
    """Clamp a value to the valid range for the given axis."""
    lo, hi = AXIS_RANGES[axis]
    return max(lo, min(hi, value))


class RelationshipManager:
    """Manages directional relationships between entities across 7 axes."""

    # ------------------------------------------------------------------
    # Core retrieval
    # ------------------------------------------------------------------

    async def get_relationship(
        self, db: AsyncSession, entity_id: UUID, target_id: UUID
    ) -> dict:
        """Get the relationship from entity_id toward target_id.

        Returns a dict with all 7 axes. If no relationship record exists,
        returns default zeros.
        """
        rel = await self._get_or_none(db, entity_id, target_id)
        if rel is None:
            return {
                "entity_id": str(entity_id),
                "target_id": str(target_id),
                **DEFAULT_VALUES,
            }
        return self._rel_to_dict(rel)

    async def _get_or_none(
        self, db: AsyncSession, entity_id: UUID, target_id: UUID
    ) -> EntityRelationship | None:
        stmt = select(EntityRelationship).where(
            EntityRelationship.entity_id == entity_id,
            EntityRelationship.target_id == target_id,
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def _get_or_create(
        self, db: AsyncSession, entity_id: UUID, target_id: UUID
    ) -> EntityRelationship:
        rel = await self._get_or_none(db, entity_id, target_id)
        if rel is not None:
            return rel

        rel = EntityRelationship(
            entity_id=entity_id,
            target_id=target_id,
            trust=0.0,
            familiarity=0.0,
            respect=0.0,
            fear=0.0,
            anger=0.0,
            gratitude=0.0,
            rivalry=0.0,
        )
        db.add(rel)
        await db.flush()
        return rel

    # ------------------------------------------------------------------
    # Event-driven updates
    # ------------------------------------------------------------------

    async def update_relationship(
        self,
        db: AsyncSession,
        entity_id: UUID,
        target_id: UUID,
        event_type: str,
        magnitude: float = 1.0,
        tick: int = 0,
    ) -> dict:
        """Apply an event-driven update to the relationship.

        The ``event_type`` must be a key in UPDATE_RULES. Each axis delta
        is multiplied by ``magnitude`` before being applied.

        Returns the updated relationship dict.
        """
        if event_type not in UPDATE_RULES:
            raise ValueError(
                f"Unknown event type '{event_type}'. "
                f"Valid types: {sorted(UPDATE_RULES.keys())}"
            )

        deltas = UPDATE_RULES[event_type]
        rel = await self._get_or_create(db, entity_id, target_id)

        for axis, base_delta in deltas.items():
            current = getattr(rel, axis)
            new_value = _clamp(current + base_delta * magnitude, axis)
            setattr(rel, axis, new_value)

        # Persist the tick of last update if the model supports it
        if hasattr(rel, "last_update_tick"):
            rel.last_update_tick = tick

        await db.flush()

        logger.debug(
            "Relationship %s -> %s updated via '%s' (mag=%.1f): %s",
            entity_id, target_id, event_type, magnitude,
            {ax: round(getattr(rel, ax), 2) for ax in AXIS_RANGES},
        )
        return self._rel_to_dict(rel)

    # ------------------------------------------------------------------
    # Time decay
    # ------------------------------------------------------------------

    async def decay_all(self, db: AsyncSession, entity_id: UUID) -> None:
        """Apply time-decay to all volatile axes for every relationship
        the entity holds.

        Decay rates:
          anger    *= 0.99
          gratitude *= 0.999
          fear     *= 0.995
        """
        stmt = select(EntityRelationship).where(
            EntityRelationship.entity_id == entity_id
        )
        result = await db.execute(stmt)
        relationships = result.scalars().all()

        for rel in relationships:
            for axis, rate in DECAY_RATES.items():
                if rate >= 1.0:
                    continue  # no decay for this axis
                current = getattr(rel, axis)
                if abs(current) < 0.01:
                    continue  # skip negligible values
                decayed = current * rate
                # Snap to zero if negligible after decay
                if abs(decayed) < 0.01:
                    decayed = 0.0
                setattr(rel, axis, _clamp(decayed, axis))

        await db.flush()
        logger.debug(
            "Decayed relationships for entity %s (%d rels)",
            entity_id, len(relationships),
        )

    # ------------------------------------------------------------------
    # Bulk retrieval
    # ------------------------------------------------------------------

    async def get_all_relationships(
        self, db: AsyncSession, entity_id: UUID
    ) -> list[dict]:
        """Get all relationships for an entity, sorted by familiarity desc."""
        stmt = (
            select(EntityRelationship)
            .where(EntityRelationship.entity_id == entity_id)
            .order_by(EntityRelationship.familiarity.desc())
        )
        result = await db.execute(stmt)
        return [self._rel_to_dict(r) for r in result.scalars().all()]

    async def get_allies(
        self, db: AsyncSession, entity_id: UUID
    ) -> list[dict]:
        """Get entities with positive trust (trust > 30).

        An ally is someone the entity trusts significantly.
        """
        stmt = (
            select(EntityRelationship)
            .where(
                EntityRelationship.entity_id == entity_id,
                EntityRelationship.trust > 30,
            )
            .order_by(EntityRelationship.trust.desc())
        )
        result = await db.execute(stmt)
        return [self._rel_to_dict(r) for r in result.scalars().all()]

    async def get_enemies(
        self, db: AsyncSession, entity_id: UUID
    ) -> list[dict]:
        """Get entities considered enemies.

        An enemy is someone with trust < -30 OR anger > 50.
        """
        stmt = (
            select(EntityRelationship)
            .where(
                EntityRelationship.entity_id == entity_id,
                (EntityRelationship.trust < -30)
                | (EntityRelationship.anger > 50),
            )
            .order_by(EntityRelationship.trust.asc())
        )
        result = await db.execute(stmt)
        return [self._rel_to_dict(r) for r in result.scalars().all()]

    # ------------------------------------------------------------------
    # Prompt generation
    # ------------------------------------------------------------------

    async def summarize_for_prompt(
        self,
        db: AsyncSession,
        entity_id: UUID,
        entity_names: dict[str, str],
    ) -> str:
        """Build a text summary of relationships for LLM prompt injection.

        ``entity_names`` maps entity-id strings to display names.
        """
        all_rels = await self.get_all_relationships(db, entity_id)
        if not all_rels:
            return "== Relationships ==\n  (none yet)"

        lines: list[str] = ["== Relationships =="]
        for rel in all_rels:
            target_id = rel["target_id"]
            name = entity_names.get(str(target_id), f"Entity-{str(target_id)[:8]}")

            # Build a compact descriptor
            descriptors: list[str] = []
            trust_val = rel["trust"]
            if trust_val > 50:
                descriptors.append("deeply trusted")
            elif trust_val > 20:
                descriptors.append("trusted")
            elif trust_val < -50:
                descriptors.append("deeply distrusted")
            elif trust_val < -20:
                descriptors.append("distrusted")

            if rel["familiarity"] > 60:
                descriptors.append("well-known")
            elif rel["familiarity"] > 25:
                descriptors.append("acquaintance")
            else:
                descriptors.append("barely known")

            if rel["respect"] > 50:
                descriptors.append("highly respected")
            elif rel["respect"] > 20:
                descriptors.append("respected")

            if rel["fear"] > 50:
                descriptors.append("feared")
            elif rel["fear"] > 20:
                descriptors.append("somewhat feared")

            if rel["anger"] > 50:
                descriptors.append("enraged at")
            elif rel["anger"] > 20:
                descriptors.append("annoyed with")

            if rel["gratitude"] > 50:
                descriptors.append("greatly indebted to")
            elif rel["gratitude"] > 20:
                descriptors.append("grateful to")

            if rel["rivalry"] > 50:
                descriptors.append("intense rival")
            elif rel["rivalry"] > 20:
                descriptors.append("rival")

            desc_str = ", ".join(descriptors) if descriptors else "neutral"

            # Compact axis values for reference
            axes_compact = (
                f"T:{trust_val:+.0f} F:{rel['familiarity']:.0f} "
                f"R:{rel['respect']:.0f} Fr:{rel['fear']:.0f} "
                f"A:{rel['anger']:.0f} G:{rel['gratitude']:.0f} "
                f"Rv:{rel['rivalry']:.0f}"
            )

            lines.append(f"  {name}: {desc_str} [{axes_compact}]")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _rel_to_dict(rel: EntityRelationship) -> dict:
        """Convert an EntityRelationship ORM object to a plain dict."""
        return {
            "entity_id": rel.entity_id,
            "target_id": rel.target_id,
            "trust": rel.trust,
            "familiarity": rel.familiarity,
            "respect": rel.respect,
            "fear": rel.fear,
            "anger": rel.anger,
            "gratitude": rel.gratitude,
            "rivalry": rel.rivalry,
        }


# Module-level singleton
relationship_manager = RelationshipManager()
