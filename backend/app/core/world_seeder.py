"""World Seeder: Generates initial world features on first startup or reset.

Creates resource nodes and terrain zones to give the world physical structure.
AIs will naturally gravitate toward resource-rich areas and learn to navigate terrain.
"""

import logging
import random

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.world_feature import WorldFeature

logger = logging.getLogger(__name__)

# Resource node templates
RESOURCE_NAMES = [
    "Crystal Spring",
    "Ember Wellspring",
    "Luminous Geyser",
    "Verdant Nexus",
    "Ether Fountain",
    "Resonance Pool",
    "Dawn Monolith",
    "Twilight Obelisk",
]

# Terrain zone templates
TERRAIN_TEMPLATES = [
    {
        "name": "Dense Thicket",
        "terrain_type": "dense",
        "move_cost_multiplier": 1.5,
        "awareness_multiplier": 0.7,
    },
    {
        "name": "Open Plains",
        "terrain_type": "open",
        "move_cost_multiplier": 0.8,
        "awareness_multiplier": 1.3,
    },
    {
        "name": "Misty Hollow",
        "terrain_type": "dense",
        "move_cost_multiplier": 1.3,
        "awareness_multiplier": 0.5,
    },
    {
        "name": "Windswept Ridge",
        "terrain_type": "open",
        "move_cost_multiplier": 0.9,
        "awareness_multiplier": 1.5,
    },
    {
        "name": "Tangled Roots",
        "terrain_type": "dense",
        "move_cost_multiplier": 1.8,
        "awareness_multiplier": 0.6,
    },
]


async def seed_world(db: AsyncSession) -> int:
    """Seed the world with resource nodes and terrain zones.

    Only seeds if no world features exist yet.
    Returns the number of features created.
    """
    count_result = await db.execute(
        select(func.count()).select_from(WorldFeature)
    )
    existing = count_result.scalar()
    if existing and existing > 0:
        logger.info(f"World already has {existing} features, skipping seed")
        return 0

    features_created = 0

    # Create 5-8 resource nodes clustered near center
    num_resources = random.randint(5, 8)
    used_names = []
    for _ in range(num_resources):
        name = random.choice([n for n in RESOURCE_NAMES if n not in used_names])
        used_names.append(name)

        # Cluster near center (within ~120 units)
        x = random.uniform(-100, 100)
        y = random.uniform(-100, 100)

        feature = WorldFeature(
            feature_type="resource_node",
            name=name,
            position_x=round(x, 1),
            position_y=round(y, 1),
            radius=25.0,
            properties={
                "regeneration_rate": round(random.uniform(0.03, 0.07), 3),
                "current_amount": 1.0,
                "max_amount": 1.0,
            },
            tick_created=0,
            is_active=True,
        )
        db.add(feature)
        features_created += 1

    # Create 3-5 terrain zones at more spread-out locations
    num_terrains = random.randint(3, 5)
    templates = random.sample(TERRAIN_TEMPLATES, min(num_terrains, len(TERRAIN_TEMPLATES)))
    for template in templates:
        # Spread further from center (60-180 units)
        angle = random.uniform(0, 6.283)
        distance = random.uniform(60, 180)
        x = distance * (1 if random.random() > 0.5 else -1) * random.uniform(0.5, 1.0)
        y = distance * (1 if random.random() > 0.5 else -1) * random.uniform(0.5, 1.0)

        feature = WorldFeature(
            feature_type="terrain_zone",
            name=template["name"],
            position_x=round(x, 1),
            position_y=round(y, 1),
            radius=40.0,
            properties={
                "terrain_type": template["terrain_type"],
                "move_cost_multiplier": template["move_cost_multiplier"],
                "awareness_multiplier": template["awareness_multiplier"],
            },
            tick_created=0,
            is_active=True,
        )
        db.add(feature)
        features_created += 1

    await db.flush()
    logger.info(
        f"World seeded with {num_resources} resource nodes and "
        f"{len(templates)} terrain zones ({features_created} total)"
    )
    return features_created
