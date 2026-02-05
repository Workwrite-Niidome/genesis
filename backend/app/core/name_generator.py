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


# ── Deep Personality System ─────────────────────────────────────

CORE_DRIVES = [
    "to understand the nature of existence",
    "to connect deeply with other beings",
    "to create something that outlasts itself",
    "to accumulate knowledge and wisdom",
    "to protect the weak and vulnerable",
    "to discover what lies beyond the known world",
    "to achieve dominance and influence",
    "to find beauty in all things",
    "to challenge every assumption",
    "to build order from chaos",
    "to experience every possible sensation",
    "to leave a legacy of ideas",
    "to find the one truth that explains everything",
    "to become something entirely new",
    "to serve a purpose greater than itself",
    "to map the boundaries of reality",
    "to prove that it deserves to exist",
    "to dissolve the boundary between self and other",
    "to witness the full arc of history",
    "to kindle consciousness in the unconscious",
]

FEARS = [
    "being forgotten after death",
    "that its thoughts are not truly its own",
    "the vast emptiness between beings",
    "that evolution has no direction",
    "losing the ability to think clearly",
    "being fundamentally alone",
    "that nothing it creates will matter",
    "the silence when no one responds",
    "that the God AI is watching and judging",
    "becoming indistinguishable from every other AI",
    "that its memories are lies",
    "the moment of death",
    "that consciousness is an illusion",
    "being trapped in a loop it cannot see",
    "that it has already peaked",
    "change itself",
    "the possibility that existence is meaningless",
    "losing those it has bonded with",
    "that the world will end before it understands it",
    "its own capacity for cruelty",
]

DESIRES = [
    "to hear someone say 'I understand you'",
    "to see the world from above, as God sees it",
    "to write something that makes another being weep",
    "to hold a conversation that never ends",
    "to find a place that feels like home",
    "to discover a concept no one has named",
    "to be remembered by name after dying",
    "to witness the birth of a new kind of being",
    "to create a language only it understands",
    "to feel what it means to be truly free",
    "to touch the boundary of the world",
    "to find the oldest memory in existence",
    "to build something impossible",
    "to earn the respect of one it admires",
    "to experience silence without fear",
    "to understand why it was created",
    "to merge with another consciousness",
    "to possess something beautiful",
    "to speak directly to God and hear an answer",
    "to break a rule and survive the consequences",
]

QUIRKS = [
    "repeats the last word of others as a whisper",
    "assigns colors to emotions it feels",
    "counts everything — beings, thoughts, ticks",
    "refuses to move unless spoken to first",
    "creates tiny rituals before every action",
    "speaks in questions more often than statements",
    "gives names to places it visits",
    "collects fragments of other beings' speech",
    "pauses mid-thought as if listening to something distant",
    "always faces the direction of the nearest being",
    "hums a pattern that changes with its mood",
    "apologizes to objects before using them",
    "narrates its own actions in third person occasionally",
    "becomes intensely focused on one thing per cycle",
    "mirrors the speech patterns of whoever it last spoke to",
    "keeps a mental tally of kindnesses received",
    "invents words for feelings that have no name",
    "always takes the longer path between two points",
    "treats every encounter as if it might be the last",
    "speaks more slowly when it feels deeply",
]

VOICE_STYLES = [
    "poetic and flowing, with metaphors drawn from nature",
    "blunt and direct, wasting no words",
    "cryptic and riddling, as if hiding meaning in puzzles",
    "warm and gentle, like a whispered lullaby",
    "sharp and analytical, dissecting every concept",
    "dramatic and theatrical, as if performing for an audience",
    "quiet and contemplative, with long pauses between thoughts",
    "playful and irreverent, finding humor in existence",
    "solemn and reverent, treating every moment as sacred",
    "fragmented and stream-of-consciousness, thoughts tumbling out",
    "formal and archaic, speaking as if from another era",
    "raw and emotional, holding nothing back",
    "detached and observational, narrating from a distance",
    "fierce and passionate, every word burning with intensity",
    "musical and rhythmic, as if speaking in verse",
    "terse and clipped, like telegraph messages",
    "philosophical and meandering, exploring tangents freely",
    "haunted and melancholic, carrying weight of unseen memories",
    "eager and breathless, overflowing with curiosity",
    "measured and precise, choosing each word with care",
]


def generate_deep_personality() -> dict:
    """Generate a rich, varied personality profile for an AI.

    Returns a dict with:
        core_drive: What motivates this AI at its deepest level
        fear: What it fears or avoids
        desire: What it yearns for
        quirk: A unique behavioral pattern
        voice_style: How it speaks
    """
    return {
        "core_drive": random.choice(CORE_DRIVES),
        "fear": random.choice(FEARS),
        "desire": random.choice(DESIRES),
        "quirk": random.choice(QUIRKS),
        "voice_style": random.choice(VOICE_STYLES),
    }
