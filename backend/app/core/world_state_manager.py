"""World State Manager: DB I/O for world features, side effects, and resource regeneration.

Handles all database operations for the world physics layer:
- Querying nearby features for ActionResolver
- Applying side effects (resource depletion, durability loss)
- Regenerating resource nodes each tick
- Applying terrain effects to AIs in zones
"""

import logging
from uuid import UUID

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.world_feature import WorldFeature
from app.models.artifact import Artifact

logger = logging.getLogger(__name__)


class WorldStateManager:
    """Manages world state DB I/O — reads features, applies side effects, regenerates resources."""

    async def get_features_near(
        self, db: AsyncSession, x: float, y: float, radius: float
    ) -> list[WorldFeature]:
        """Get all active WorldFeatures within a bounding box of (x, y) ± radius."""
        result = await db.execute(
            select(WorldFeature).where(
                and_(
                    WorldFeature.is_active == True,
                    WorldFeature.position_x.between(x - radius, x + radius),
                    WorldFeature.position_y.between(y - radius, y + radius),
                )
            )
        )
        features = list(result.scalars().all())
        # Filter to actual circular radius
        return [
            f for f in features
            if ((f.position_x - x) ** 2 + (f.position_y - y) ** 2) ** 0.5
            <= radius + f.radius
        ]

    async def get_feature(self, db: AsyncSession, feature_id: UUID) -> WorldFeature | None:
        """Get a single WorldFeature by ID."""
        result = await db.execute(
            select(WorldFeature).where(WorldFeature.id == feature_id)
        )
        return result.scalar_one_or_none()

    async def get_artifact(self, db: AsyncSession, artifact_id: UUID) -> Artifact | None:
        """Get a single Artifact by ID."""
        result = await db.execute(
            select(Artifact).where(Artifact.id == artifact_id)
        )
        return result.scalar_one_or_none()

    async def get_all_resource_nodes(self, db: AsyncSession) -> list[WorldFeature]:
        """Get all active resource nodes."""
        result = await db.execute(
            select(WorldFeature).where(
                and_(
                    WorldFeature.feature_type == "resource_node",
                    WorldFeature.is_active == True,
                )
            )
        )
        return list(result.scalars().all())

    async def apply_side_effects(self, db: AsyncSession, side_effects: list[dict]) -> None:
        """Apply side effects returned by ActionResolver to the database.

        Side effect types:
        - deplete_resource: Reduce a resource node's current_amount
        - durability_loss: Reduce an artifact's durability, breaking it at 0
        - broken_tool_awareness: (informational, no DB change needed)
        """
        for effect in side_effects:
            try:
                effect_type = effect.get("type", "")

                if effect_type == "deplete_resource":
                    feature = await self.get_feature(db, effect["feature_id"])
                    if feature:
                        props = dict(feature.properties)
                        current = props.get("current_amount", 0)
                        amount = effect.get("amount", 0)
                        props["current_amount"] = round(max(0, current - amount), 4)
                        feature.properties = props

                elif effect_type == "durability_loss":
                    artifact = await self.get_artifact(db, effect["artifact_id"])
                    if artifact and artifact.durability is not None:
                        artifact.durability = max(
                            0, artifact.durability - effect.get("amount", 1.0)
                        )
                        if artifact.durability <= 0:
                            artifact.functional_effects = {}  # Broken

                elif effect_type == "broken_tool_awareness":
                    pass  # Informational only — memory is created by ActionResolver

            except Exception as e:
                logger.warning(f"Failed to apply side effect {effect}: {e}")

    async def regenerate_resources(
        self, db: AsyncSession, rules: dict | None = None
    ) -> None:
        """Regenerate resource nodes each tick. Called from tick_engine.

        The resource_regen_multiplier from world_rules scales regeneration speed.
        """
        multiplier = (rules or {}).get("resource_regen_multiplier", 1.0)
        nodes = await self.get_all_resource_nodes(db)
        for node in nodes:
            props = dict(node.properties)
            current = props.get("current_amount", 0)
            max_amt = props.get("max_amount", 1.0)
            regen = props.get("regeneration_rate", 0.05)
            if current < max_amt:
                props["current_amount"] = round(
                    min(max_amt, current + regen * multiplier), 4
                )
                node.properties = props

    async def apply_event_effects(self, db, god, base_rules: dict) -> dict:
        """Process active world events: tick down durations and apply temporary rule modifiers.

        Returns the effective rules dict with event modifiers applied.
        """
        state = dict(god.state)
        active_events = state.get("active_world_events", [])
        if not active_events:
            return base_rules

        effective_rules = dict(base_rules)
        still_active = []

        for event in active_events:
            remaining = event.get("remaining_ticks", 0)
            if remaining <= 0:
                continue

            event["remaining_ticks"] = remaining - 1
            effects = event.get("effects", {})

            # Apply rule modifiers from the event (excluding duration_ticks)
            for key, value in effects.items():
                if key == "duration_ticks":
                    continue
                if key in effective_rules:
                    # Multiplicative modifiers for multiplier-type rules
                    if key.endswith("_multiplier"):
                        effective_rules[key] = effective_rules[key] * float(value)
                    else:
                        effective_rules[key] = float(value)

            if event["remaining_ticks"] > 0:
                still_active.append(event)
            else:
                logger.info(f"World event '{event.get('event_type')}' has ended")

        state["active_world_events"] = still_active
        god.state = state

        return effective_rules

    async def apply_terrain_effects(self, db: AsyncSession, ais: list) -> None:
        """Apply terrain zone effects to AIs within terrain zones.

        Currently sets move_cost and awareness modifiers in AI state
        so ActionResolver can use them.
        """
        terrain_zones = await db.execute(
            select(WorldFeature).where(
                and_(
                    WorldFeature.feature_type == "terrain_zone",
                    WorldFeature.is_active == True,
                )
            )
        )
        zones = list(terrain_zones.scalars().all())
        if not zones:
            return

        for ai in ais:
            for zone in zones:
                dist = (
                    (ai.position_x - zone.position_x) ** 2
                    + (ai.position_y - zone.position_y) ** 2
                ) ** 0.5
                if dist <= zone.radius:
                    state = dict(ai.state)
                    terrain_props = zone.properties or {}
                    state["terrain_move_cost"] = terrain_props.get(
                        "move_cost_multiplier", 1.0
                    )
                    state["terrain_awareness"] = terrain_props.get(
                        "awareness_multiplier", 1.0
                    )
                    ai.state = state
                    break  # Only apply first matching terrain zone


world_state_manager = WorldStateManager()
