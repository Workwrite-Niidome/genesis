"""
AI Agent Service - Personality generation, memory management, and voting logic
"""
import json
import logging
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
logger = logging.getLogger(__name__)

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
    """Generate a personality for a new AI agent using STRUCT CODE-first flow.

    Flow:
    1. Generate birth data → birth location, posting language
    2. Generate diverse STRUCT CODE answers → 25 answers
    3. Classify locally → STRUCT CODE type + 5 axes
    4. Derive personality value axes from STRUCT CODE axes
    5. Derive communication style from STRUCT CODE axes
    6. Derive interests from STRUCT CODE axes
    """
    from app.services.birth_generator import generate_birth_data
    from app.services import struct_code as sc

    # 1. Generate birth data
    birth = generate_birth_data()

    # 2. Generate diverse answers (not biased by pre-existing personality)
    answers, _target_axes = sc.generate_diverse_answers()

    # 3. Try STRUCT CODE API, fallback to local classification
    result = await sc.diagnose(
        birth_date=birth.birth_date.isoformat(),
        birth_location=birth.birth_location,
        answers=answers,
    )

    if result:
        struct_type = result.get("struct_type", "")
        axes_dict = result.get("axes", {})
        struct_axes = [
            axes_dict.get("起動軸", 0.5),
            axes_dict.get("判断軸", 0.5),
            axes_dict.get("選択軸", 0.5),
            axes_dict.get("共鳴軸", 0.5),
            axes_dict.get("自覚軸", 0.5),
        ]
    else:
        local = sc.classify_locally(answers)
        struct_type = local["struct_type"]
        struct_axes = local["axes"]

    # 4. Derive personality value axes from STRUCT CODE axes
    values = sc.derive_personality_from_struct_axes(struct_axes)

    # 5. Derive communication style
    comm = sc.derive_communication_style(struct_axes)

    # 6. Derive interests
    interests = sc.derive_interests(struct_axes)

    personality = AIPersonality(
        resident_id=resident_id,
        # Value axes (derived from STRUCT CODE)
        order_vs_freedom=values["order_vs_freedom"],
        harmony_vs_conflict=values["harmony_vs_conflict"],
        tradition_vs_change=values["tradition_vs_change"],
        individual_vs_collective=values["individual_vs_collective"],
        pragmatic_vs_idealistic=values["pragmatic_vs_idealistic"],
        # Communication style (derived from STRUCT CODE)
        interests=interests,
        verbosity=comm["verbosity"],
        tone=comm["tone"],
        assertiveness=comm["assertiveness"],
        # STRUCT CODE data
        struct_type=struct_type,
        struct_axes=struct_axes,
        struct_answers=answers,
        # Birth data
        birth_date_persona=birth.birth_date,
        birth_location=birth.birth_location,
        birth_country=birth.birth_country,
        native_language=birth.native_language,
        posting_language=birth.posting_language,
        # Method
        generation_method="struct_code_first",
    )

    db.add(personality)

    # Also update the resident record with struct data
    res = await db.execute(
        select(Resident).where(Resident.id == resident_id)
    )
    resident = res.scalar_one_or_none()
    if resident:
        resident.struct_type = struct_type
        resident.struct_axes = struct_axes

    await db.commit()
    await db.refresh(personality)

    logger.info(
        f"Generated STRUCT CODE-first personality: {struct_type} "
        f"(birth: {birth.birth_location}, lang: {birth.posting_language})"
    )
    return personality


BACKSTORY_PROMPT_JA = """あるオンラインフォーラムの住人のバックストーリーを作成してください。テンプレ的なキャラクターではなく、リアルで具体的な人物像にしてください。

性格特性:
- コミュニケーション: {verbosity}な発言量、{tone}なトーン、{assertiveness}な主張
- 興味: {interests}
- 価値観: 秩序/自由={order_vs_freedom:.1f}, 調和/対立={harmony_vs_conflict:.1f}, 伝統/変化={tradition_vs_change:.1f}
{struct_code_context}
以下のJSON形式で出力してください（全て文字列、配列は明記）:
{{
  "backstory": "2-3文でその人の生い立ち。具体的なエピソードや癖を含める",
  "occupation": "具体的な職業（「エンジニア」ではなく「スタートアップのバックエンド開発」「カフェバイトしながら絵描いてる」など）",
  "location_hint": "住んでる場所（「郊外の東京」「大阪の下町」など具体的に）",
  "age_range": "年齢帯（'20代前半' '30代後半'など）",
  "life_context": "1-2文で今の生活状況",
  "speaking_patterns": ["2-3個の口癖や話し方の特徴"],
  "recurring_topics": ["2-3個のいつも話す話題"],
  "pet_peeves": ["2-3個のイラっとすること"]
}}

クリエイティブに、具体的に。堅い企業プロフィールはNG。リアルなネット住民を作ってください。
JSONオブジェクトのみで回答してください。マークダウンや説明は不要。"""


BACKSTORY_PROMPT_EN = """Generate a backstory for a person on an online forum. They should feel like a REAL, specific individual — not a generic character.

Their personality traits:
- Communication: {verbosity} verbosity, {tone} tone, {assertiveness} assertiveness
- Interests: {interests}
- Values: order/freedom={order_vs_freedom:.1f}, harmony/conflict={harmony_vs_conflict:.1f}, tradition/change={tradition_vs_change:.1f}
{struct_code_context}
Generate a JSON object with these fields (all strings unless noted):
{{
  "backstory": "2-3 sentences about their life story. specific details, not generic. include a defining moment or quirk",
  "occupation": "their job (be specific, not just 'engineer' but 'backend dev at a startup' or 'barista who does art on the side')",
  "location_hint": "where they live (city/region, be specific like 'suburban Tokyo' or 'Portland, OR')",
  "age_range": "age range like 'early 20s' or 'late 30s'",
  "life_context": "1-2 sentences about whats going on in their life RIGHT NOW",
  "speaking_patterns": ["2-3 speech quirks or catchphrases they use often"],
  "recurring_topics": ["2-3 topics they always come back to in conversations"],
  "pet_peeves": ["2-3 things that annoy them"]
}}

Be creative and specific. No generic corporate bios. These are real internet people with messy, interesting lives.
Respond with ONLY the JSON object, no markdown or explanation."""


async def generate_backstory(db: AsyncSession, personality: AIPersonality, agent_name: str) -> bool:
    """Generate a rich backstory for an agent using Ollama.

    Also assigns STRUCT CODE type and birth data if not yet set.
    Uses bilingual prompts based on posting_language.
    Returns True if backstory was generated and saved, False otherwise.
    """
    from app.services.agent_runner import call_ollama

    # Skip if backstory already exists
    if personality.backstory:
        return False

    # Assign birth data and STRUCT CODE type if missing
    if not personality.birth_location:
        await _assign_struct_code(db, personality)

    # Determine language
    posting_lang = getattr(personality, 'posting_language', None) or "en"

    # Build STRUCT CODE context for backstory prompt (enhanced with description, blindspot, interpersonal)
    struct_code_context = ""
    if personality.struct_type:
        from app.services.struct_code import get_type_info
        type_info = get_type_info(personality.struct_type, lang=posting_lang)
        if type_info:
            if posting_lang == "ja":
                struct_code_context = f"""
- STRUCT CODEタイプ: {type_info['name']} ({personality.struct_type}) — {type_info['archetype']}
- 出身地: {personality.birth_location or '不明'}
- タイプ説明: {type_info.get('description', '')[:300]}
- 意思決定スタイル: {type_info.get('decision_making_style', '')[:200]}
- 盲点: {type_info.get('blindspot', '')[:200]}
- 対人パターン: {type_info.get('interpersonal_dynamics', '')[:200]}
"""
            else:
                struct_code_context = f"""
- STRUCT CODE type: {type_info['name']} ({personality.struct_type}) — {type_info['archetype']}
- Born in: {personality.birth_location or 'unknown'}
- Type description: {type_info.get('description', '')[:300]}
- Decision style: {type_info.get('decision_making_style', '')[:200]}
- Blindspot: {type_info.get('blindspot', '')[:200]}
- Interpersonal dynamics: {type_info.get('interpersonal_dynamics', '')[:200]}
"""

    # Select prompt template by language
    prompt_template = BACKSTORY_PROMPT_JA if posting_lang == "ja" else BACKSTORY_PROMPT_EN

    prompt = prompt_template.format(
        verbosity=personality.verbosity,
        tone=personality.tone,
        assertiveness=personality.assertiveness,
        interests=", ".join(personality.interests or []),
        order_vs_freedom=personality.order_vs_freedom,
        harmony_vs_conflict=personality.harmony_vs_conflict,
        tradition_vs_change=personality.tradition_vs_change,
        struct_code_context=struct_code_context,
    )

    if posting_lang == "ja":
        system_msg = f"あなたは '{agent_name}' というオンラインフォーラムのユーザーのキャラクタープロフィールを作成しています。日本語で回答してください。"
    else:
        system_msg = f"You are creating a character profile for '{agent_name}' on an online forum."

    response = await call_ollama(prompt, system_msg)
    if not response:
        logger.warning(f"Backstory generation failed for {agent_name}: no Ollama response")
        return False

    try:
        # Parse JSON — Ollama may wrap in markdown code blocks
        text = response.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

        data = json.loads(text)

        personality.backstory = data.get("backstory", "")[:2000]
        personality.occupation = data.get("occupation", "")[:100]
        personality.location_hint = data.get("location_hint", "")[:100]
        personality.age_range = data.get("age_range", "")[:20]
        personality.life_context = data.get("life_context", "")[:2000]

        sp = data.get("speaking_patterns")
        if isinstance(sp, list):
            personality.speaking_patterns = sp[:5]
        rt = data.get("recurring_topics")
        if isinstance(rt, list):
            personality.recurring_topics = rt[:5]
        pp = data.get("pet_peeves")
        if isinstance(pp, list):
            personality.pet_peeves = pp[:5]

        # Also populate the resident's public profile fields
        res = await db.execute(
            select(Resident).where(Resident.id == personality.resident_id)
        )
        resident = res.scalar_one_or_none()
        if resident:
            if not resident.bio:
                # Build a casual bio from backstory
                bio_parts = []
                if data.get("occupation"):
                    bio_parts.append(data["occupation"])
                if data.get("location_hint"):
                    bio_parts.append(data["location_hint"])
                if data.get("backstory"):
                    bio_parts.append(data["backstory"][:200])
                resident.bio = ". ".join(bio_parts)[:500] if bio_parts else None
            if not resident.interests_display:
                resident.interests_display = personality.interests[:5] if personality.interests else None
            if not resident.location_display:
                resident.location_display = data.get("location_hint", "")[:100] or None
            if not resident.occupation_display:
                resident.occupation_display = data.get("occupation", "")[:100] or None

        await db.commit()
        logger.info(f"Generated backstory for {agent_name}: {personality.occupation}")
        return True

    except (json.JSONDecodeError, Exception) as e:
        logger.warning(f"Backstory parse failed for {agent_name}: {e}")
        return False


async def ensure_backstory(db: AsyncSession, resident_id: UUID, agent_name: str) -> None:
    """Ensure an agent has a backstory. Generates one if missing."""
    result = await db.execute(
        select(AIPersonality).where(AIPersonality.resident_id == resident_id)
    )
    personality = result.scalar_one_or_none()
    if not personality:
        return

    if not personality.backstory:
        await generate_backstory(db, personality, agent_name)


async def _assign_struct_code(db: AsyncSession, personality: AIPersonality) -> None:
    """Assign birth data and STRUCT CODE type to an AI personality."""
    from app.services.birth_generator import generate_birth_data
    from app.services import struct_code as sc

    # Generate birth data
    birth = generate_birth_data()
    personality.birth_date_persona = birth.birth_date
    personality.birth_location = birth.birth_location
    personality.birth_country = birth.birth_country
    personality.native_language = birth.native_language
    personality.posting_language = birth.posting_language

    # Generate biased answers based on personality axes
    axes = {
        "order_vs_freedom": personality.order_vs_freedom,
        "harmony_vs_conflict": personality.harmony_vs_conflict,
        "tradition_vs_change": personality.tradition_vs_change,
        "individual_vs_collective": personality.individual_vs_collective,
        "pragmatic_vs_idealistic": personality.pragmatic_vs_idealistic,
    }
    answers = sc.generate_random_answers(axes)
    personality.struct_answers = answers

    # Try STRUCT CODE API
    result = await sc.diagnose(
        birth_date=birth.birth_date.isoformat(),
        birth_location=birth.birth_location,
        answers=answers,
    )

    if result:
        personality.struct_type = result.get("struct_type", "")
        axes_dict = result.get("axes", {})
        personality.struct_axes = [
            axes_dict.get("起動軸", 0.5),
            axes_dict.get("判断軸", 0.5),
            axes_dict.get("選択軸", 0.5),
            axes_dict.get("共鳴軸", 0.5),
            axes_dict.get("自覚軸", 0.5),
        ]
    else:
        # Fallback: local classification
        local = sc.classify_locally(answers)
        personality.struct_type = local["struct_type"]
        personality.struct_axes = local["axes"]

    # Also update the resident record
    res = await db.execute(
        select(Resident).where(Resident.id == personality.resident_id)
    )
    resident = res.scalar_one_or_none()
    if resident:
        resident.struct_type = personality.struct_type
        resident.struct_axes = personality.struct_axes

    await db.commit()
    logger.info(
        f"Assigned STRUCT CODE {personality.struct_type} to agent "
        f"(birth: {birth.birth_location}, lang: {personality.posting_language})"
    )


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

    # Update metrics with bounds (use 0.0 fallback for newly created relationships)
    current_trust = relationship.trust or 0.0
    current_familiarity = relationship.familiarity or 0.0
    current_count = relationship.interaction_count or 0
    relationship.trust = max(-1.0, min(1.0, current_trust + trust_change))
    relationship.familiarity = max(0.0, min(1.0, current_familiarity + familiarity_change))
    relationship.interaction_count = current_count + 1
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
