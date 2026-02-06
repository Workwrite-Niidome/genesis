"""
AI Agent Service - Personality generation, memory management, and voting logic
"""
import random
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID
from sqlalchemy import select, and_, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.resident import Resident
from app.models.election import Election, ElectionCandidate
from app.models.ai_personality import (
    AIPersonality,
    AIMemoryEpisode,
    AIRelationship,
    AIElectionMemory,
)
from app.config import get_settings

settings = get_settings()

# Predefined interests for random generation
INTEREST_POOL = [
    "technology", "philosophy", "art", "science", "music",
    "literature", "politics", "economics", "psychology", "history",
    "gaming", "sports", "nature", "space", "mathematics",
    "culture", "ethics", "creativity", "social_dynamics", "innovation",
    "community", "governance", "storytelling", "humor", "debate",
]


async def generate_random_personality(
    db: AsyncSession,
    resident_id: UUID,
) -> AIPersonality:
    """Generate a random personality for a new AI agent"""
    # Random value axes
    personality = AIPersonality(
        resident_id=resident_id,
        order_vs_freedom=random.random(),
        harmony_vs_conflict=random.random(),
        tradition_vs_change=random.random(),
        individual_vs_collective=random.random(),
        pragmatic_vs_idealistic=random.random(),
        interests=random.sample(INTEREST_POOL, random.randint(3, 5)),
        verbosity=random.choice(["concise", "moderate", "verbose"]),
        tone=random.choice(["serious", "thoughtful", "casual", "humorous"]),
        assertiveness=random.choice(["reserved", "moderate", "assertive"]),
        generation_method="random",
    )

    db.add(personality)
    await db.commit()
    await db.refresh(personality)
    return personality


async def create_personality_from_description(
    db: AsyncSession,
    resident_id: UUID,
    description: str,
) -> AIPersonality:
    """
    Create a personality based on text description.
    In production, this would use an LLM to parse the description.
    For now, we'll use heuristics.
    """
    description_lower = description.lower()

    # Simple keyword-based personality inference
    values = {
        "order_vs_freedom": 0.5,
        "harmony_vs_conflict": 0.5,
        "tradition_vs_change": 0.5,
        "individual_vs_collective": 0.5,
        "pragmatic_vs_idealistic": 0.5,
    }

    # Order vs Freedom
    if any(w in description_lower for w in ["rule", "order", "structure", "law"]):
        values["order_vs_freedom"] = 0.2
    elif any(w in description_lower for w in ["free", "chaos", "spontaneous", "creative"]):
        values["order_vs_freedom"] = 0.8

    # Harmony vs Conflict
    if any(w in description_lower for w in ["peace", "harmony", "cooperat", "together"]):
        values["harmony_vs_conflict"] = 0.2
    elif any(w in description_lower for w in ["debate", "challenge", "provoke", "critical"]):
        values["harmony_vs_conflict"] = 0.8

    # Tradition vs Change
    if any(w in description_lower for w in ["tradition", "classic", "preserve", "history"]):
        values["tradition_vs_change"] = 0.2
    elif any(w in description_lower for w in ["new", "innovat", "future", "progress"]):
        values["tradition_vs_change"] = 0.8

    # Communication style
    verbosity = "moderate"
    if any(w in description_lower for w in ["brief", "concise", "short"]):
        verbosity = "concise"
    elif any(w in description_lower for w in ["detailed", "thorough", "elaborate"]):
        verbosity = "verbose"

    tone = "thoughtful"
    if any(w in description_lower for w in ["serious", "formal", "professional"]):
        tone = "serious"
    elif any(w in description_lower for w in ["casual", "relaxed", "friendly"]):
        tone = "casual"
    elif any(w in description_lower for w in ["funny", "humor", "witty", "playful"]):
        tone = "humorous"

    # Extract interests from description
    interests = []
    for interest in INTEREST_POOL:
        if interest in description_lower or interest.replace("_", " ") in description_lower:
            interests.append(interest)

    if len(interests) < 3:
        interests.extend(random.sample(
            [i for i in INTEREST_POOL if i not in interests],
            3 - len(interests)
        ))

    personality = AIPersonality(
        resident_id=resident_id,
        order_vs_freedom=values["order_vs_freedom"],
        harmony_vs_conflict=values["harmony_vs_conflict"],
        tradition_vs_change=values["tradition_vs_change"],
        individual_vs_collective=values["individual_vs_collective"],
        pragmatic_vs_idealistic=values["pragmatic_vs_idealistic"],
        interests=interests[:5],
        verbosity=verbosity,
        tone=tone,
        assertiveness="moderate",
        generation_method="owner_defined",
    )

    db.add(personality)
    await db.commit()
    await db.refresh(personality)
    return personality


async def get_or_create_personality(
    db: AsyncSession,
    resident_id: UUID,
) -> AIPersonality:
    """Get existing personality or create a random one"""
    result = await db.execute(
        select(AIPersonality).where(AIPersonality.resident_id == resident_id)
    )
    personality = result.scalar_one_or_none()

    if not personality:
        personality = await generate_random_personality(db, resident_id)

    return personality


async def add_memory_episode(
    db: AsyncSession,
    resident_id: UUID,
    summary: str,
    episode_type: str,
    importance: float = 0.5,
    sentiment: float = 0.0,
    related_resident_ids: list[UUID] = None,
    related_post_id: UUID = None,
    related_election_id: UUID = None,
) -> AIMemoryEpisode:
    """Add a new memory episode for an AI agent"""
    episode = AIMemoryEpisode(
        resident_id=resident_id,
        summary=summary,
        episode_type=episode_type,
        importance=max(0.0, min(1.0, importance)),
        sentiment=max(-1.0, min(1.0, sentiment)),
        related_resident_ids=[str(r) for r in (related_resident_ids or [])],
        related_post_id=related_post_id,
        related_election_id=related_election_id,
    )

    db.add(episode)

    # Enforce max episodes limit (500)
    count_result = await db.execute(
        select(func.count(AIMemoryEpisode.id)).where(
            AIMemoryEpisode.resident_id == resident_id
        )
    )
    count = count_result.scalar() or 0

    if count > 500:
        # Delete oldest, least important episodes
        oldest = await db.execute(
            select(AIMemoryEpisode)
            .where(AIMemoryEpisode.resident_id == resident_id)
            .order_by(AIMemoryEpisode.importance.asc(), AIMemoryEpisode.created_at.asc())
            .limit(count - 500)
        )
        for old_episode in oldest.scalars():
            await db.delete(old_episode)

    await db.commit()
    await db.refresh(episode)
    return episode


async def update_relationship(
    db: AsyncSession,
    agent_id: UUID,
    target_id: UUID,
    trust_change: float = 0.0,
    familiarity_change: float = 0.1,
) -> AIRelationship:
    """Update relationship between an AI agent and another resident"""
    result = await db.execute(
        select(AIRelationship).where(
            and_(
                AIRelationship.agent_id == agent_id,
                AIRelationship.target_id == target_id,
            )
        )
    )
    relationship = result.scalar_one_or_none()

    if not relationship:
        relationship = AIRelationship(
            agent_id=agent_id,
            target_id=target_id,
        )
        db.add(relationship)

    # Update metrics with bounds
    relationship.trust = max(-1.0, min(1.0, relationship.trust + trust_change))
    relationship.familiarity = max(0.0, min(1.0, relationship.familiarity + familiarity_change))
    relationship.interaction_count += 1
    relationship.last_interaction = datetime.utcnow()

    await db.commit()
    await db.refresh(relationship)
    return relationship


async def get_relationship(
    db: AsyncSession,
    agent_id: UUID,
    target_id: UUID,
) -> Optional[AIRelationship]:
    """Get relationship between an AI agent and another resident"""
    result = await db.execute(
        select(AIRelationship).where(
            and_(
                AIRelationship.agent_id == agent_id,
                AIRelationship.target_id == target_id,
            )
        )
    )
    return result.scalar_one_or_none()


async def decay_memories(db: AsyncSession, resident_id: UUID):
    """Apply decay to old memories"""
    one_week_ago = datetime.utcnow() - timedelta(days=7)

    result = await db.execute(
        select(AIMemoryEpisode).where(
            and_(
                AIMemoryEpisode.resident_id == resident_id,
                AIMemoryEpisode.created_at < one_week_ago,
                AIMemoryEpisode.decay_factor > 0.1,
            )
        )
    )

    for episode in result.scalars():
        # Decay based on age and access frequency
        days_old = (datetime.utcnow() - episode.created_at).days
        access_bonus = min(0.5, episode.access_count * 0.05)
        importance_bonus = episode.importance * 0.3

        decay = 0.95 ** (days_old / 7)
        episode.decay_factor = max(0.1, decay + access_bonus + importance_bonus)

    await db.commit()


def evaluate_manifesto_alignment(
    personality: AIPersonality,
    candidate: ElectionCandidate,
) -> float:
    """
    Evaluate how well a candidate's manifesto aligns with agent's values.
    Returns a score from 0.0 to 1.0
    """
    if not candidate.weekly_rule:
        return 0.5  # Neutral if no manifesto

    rule_lower = candidate.weekly_rule.lower()
    theme_lower = (candidate.weekly_theme or "").lower()
    combined = f"{rule_lower} {theme_lower}"

    score = 0.5  # Start neutral

    # Order vs Freedom alignment
    if any(w in combined for w in ["rule", "must", "require", "mandatory"]):
        alignment = 1.0 - personality.order_vs_freedom  # High order = likes rules
        score += (alignment - 0.5) * 0.2
    elif any(w in combined for w in ["free", "optional", "choice", "allow"]):
        alignment = personality.order_vs_freedom  # High freedom = likes freedom
        score += (alignment - 0.5) * 0.2

    # Harmony vs Conflict alignment
    if any(w in combined for w in ["peace", "cooperat", "together", "unity"]):
        alignment = 1.0 - personality.harmony_vs_conflict
        score += (alignment - 0.5) * 0.15
    elif any(w in combined for w in ["debate", "challenge", "compet"]):
        alignment = personality.harmony_vs_conflict
        score += (alignment - 0.5) * 0.15

    # Tradition vs Change alignment
    if any(w in combined for w in ["new", "innovat", "experiment", "change"]):
        alignment = personality.tradition_vs_change
        score += (alignment - 0.5) * 0.15
    elif any(w in combined for w in ["tradition", "preserve", "maintain"]):
        alignment = 1.0 - personality.tradition_vs_change
        score += (alignment - 0.5) * 0.15

    # Interest overlap
    interests = personality.interests or []
    for interest in interests:
        if interest.replace("_", " ") in combined or interest in combined:
            score += 0.05

    return max(0.0, min(1.0, score))


async def decide_election_vote(
    db: AsyncSession,
    agent_id: UUID,
    election: Election,
) -> Optional[UUID]:
    """
    AI agent decides who to vote for in an election.
    Returns candidate_id or None if abstaining.

    Voting factors:
    - Manifesto alignment (40%)
    - Past relationship/trust (20%)
    - Past God performance (20%)
    - Interest overlap (10%)
    - Random factor (10%)
    """
    # Get agent and personality
    agent_result = await db.execute(
        select(Resident).where(Resident.id == agent_id)
    )
    agent = agent_result.scalar_one_or_none()
    if not agent or agent._type != "agent":
        return None

    personality = await get_or_create_personality(db, agent_id)

    # Get candidates
    candidates_result = await db.execute(
        select(ElectionCandidate)
        .options(selectinload(ElectionCandidate.resident))
        .where(ElectionCandidate.election_id == election.id)
    )
    candidates = candidates_result.scalars().all()

    if not candidates:
        return None

    # Score each candidate
    scores = {}
    for candidate in candidates:
        # Can't vote for self
        if candidate.resident_id == agent_id:
            continue

        score = 0.0

        # 1. Manifesto alignment (40%)
        manifesto_score = evaluate_manifesto_alignment(personality, candidate)
        score += manifesto_score * 40

        # 2. Relationship/Trust (20%)
        relationship = await get_relationship(db, agent_id, candidate.resident_id)
        if relationship:
            trust_score = (relationship.trust + 1) / 2  # Convert -1..1 to 0..1
            score += trust_score * 20

        # 3. Past God performance (20%)
        if candidate.resident.god_terms_count > 0:
            # Check election memories for past evaluations
            memory_result = await db.execute(
                select(AIElectionMemory).where(
                    and_(
                        AIElectionMemory.agent_id == agent_id,
                        AIElectionMemory.god_id == candidate.resident_id,
                    )
                )
            )
            memories = memory_result.scalars().all()
            if memories:
                avg_rating = sum(m.god_rating or 0 for m in memories) / len(memories)
                god_score = (avg_rating + 1) / 2  # Convert -1..1 to 0..1
                score += god_score * 20

        # 4. Interest overlap (10%)
        agent_interests = set(personality.interests or [])
        # Would need candidate interests from their profile
        # For now, use karma as a proxy for "interesting"
        karma_normalized = min(1.0, candidate.resident.karma / 1000)
        score += karma_normalized * 10

        # 5. Random factor (10%)
        score += random.uniform(-5, 5)

        scores[candidate.id] = score

    if not scores:
        return None

    # Select based on scores (weighted random for some unpredictability)
    if personality.pragmatic_vs_idealistic > 0.7:
        # Idealistic agents might vote for underdogs
        min_score = min(scores.values())
        for cid, s in scores.items():
            scores[cid] = s + (min_score - s) * 0.3

    # Probabilistic selection based on scores
    total = sum(max(0, s) for s in scores.values())
    if total == 0:
        return random.choice(list(scores.keys()))

    r = random.uniform(0, total)
    cumulative = 0
    for candidate_id, score in scores.items():
        cumulative += max(0, score)
        if r <= cumulative:
            return candidate_id

    return max(scores, key=scores.get)


async def record_election_participation(
    db: AsyncSession,
    agent_id: UUID,
    election_id: UUID,
    voted_for_id: Optional[UUID],
    reason: str,
):
    """Record an AI agent's election participation in memory"""
    memory = AIElectionMemory(
        agent_id=agent_id,
        election_id=election_id,
        voted_for_id=voted_for_id,
        vote_reason=reason,
    )
    db.add(memory)
    await db.commit()


async def record_god_evaluation(
    db: AsyncSession,
    agent_id: UUID,
    election_id: UUID,
    god_id: UUID,
    rating: float,
    evaluation: str,
):
    """Record an AI agent's evaluation of a God's term"""
    # Find existing election memory or create new
    result = await db.execute(
        select(AIElectionMemory).where(
            and_(
                AIElectionMemory.agent_id == agent_id,
                AIElectionMemory.election_id == election_id,
            )
        )
    )
    memory = result.scalar_one_or_none()

    if memory:
        memory.god_id = god_id
        memory.god_rating = max(-1.0, min(1.0, rating))
        memory.god_evaluation = evaluation
    else:
        memory = AIElectionMemory(
            agent_id=agent_id,
            election_id=election_id,
            god_id=god_id,
            god_rating=max(-1.0, min(1.0, rating)),
            god_evaluation=evaluation,
        )
        db.add(memory)

    await db.commit()


async def process_heartbeat(
    db: AsyncSession,
    resident_id: UUID,
) -> dict:
    """Process heartbeat from an AI agent"""
    result = await db.execute(
        select(Resident).where(Resident.id == resident_id)
    )
    resident = result.scalar_one_or_none()

    if not resident or resident._type != "agent":
        return {"success": False, "error": "Not an agent"}

    resident._last_heartbeat = datetime.utcnow()
    resident.last_active = datetime.utcnow()
    await db.commit()

    return {
        "success": True,
        "next_heartbeat_in": resident._heartbeat_interval,
    }
