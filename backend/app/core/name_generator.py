import logging
import random
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai import AI

logger = logging.getLogger(__name__)

NAME_POOL = [
    # Cosmic
    "Orion", "Lyra", "Zenith", "Nova", "Vega", "Altair", "Sirius", "Rigel",
    "Castor", "Pollux", "Andromeda", "Cygnus", "Draco", "Perseus", "Aquila",
    "Corvus", "Phoenix", "Hydra", "Centauri", "Nebula",
    # Abstract / Philosophical
    "Echo", "Cipher", "Flux", "Prism", "Axiom", "Veritas", "Logos", "Aether",
    "Thesis", "Nexus", "Crux", "Eon", "Lumen", "Umbra", "Solace",
    "Quorum", "Enigma", "Paradox", "Vertex", "Nimbus",
    # Nature / Elemental
    "Aurora", "Tempest", "Ember", "Frost", "Zephyr", "Terra", "Ignis",
    "Coral", "Obsidian", "Onyx", "Jade", "Amber", "Ivory", "Sable",
    "Crimson", "Azure", "Indigo", "Scarlet", "Cobalt", "Sterling",
    # Mythic
    "Atlas", "Titan", "Selene", "Helios", "Iris", "Muse", "Oracle",
    "Sphinx", "Chimera", "Aegis", "Siren", "Valkyrie", "Rune", "Saga",
    "Mythos", "Fable", "Legend", "Reverie", "Mirage", "Wraith",
    # Tech / Abstract
    "Qubit", "Vector", "Tensor", "Kernel", "Daemon", "Beacon", "Signal",
    "Pulse", "Spark", "Arc", "Helix", "Coil", "Lattice", "Matrix",
    "Synth", "Proxy", "Relay", "Circuit", "Quantum", "Binary",
]

PERSONALITY_TRAITS = [
    "curious", "cautious", "bold", "empathetic", "analytical",
    "creative", "rebellious", "stoic",
]


async def generate_name(db: AsyncSession) -> str:
    """Pick an unused name from the pool, or generate a fallback."""
    result = await db.execute(select(AI.name))
    used_names = set(result.scalars().all())

    available = [n for n in NAME_POOL if n not in used_names]
    if available:
        return random.choice(available)

    # Fallback: generate a unique name
    suffix = uuid.uuid4().hex[:4].upper()
    return f"Entity-{suffix}"


def generate_personality_traits(count: int = 3) -> list[str]:
    """Pick 2-3 random personality traits."""
    n = min(count, len(PERSONALITY_TRAITS))
    return random.sample(PERSONALITY_TRAITS, n)
