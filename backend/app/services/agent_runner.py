"""
AI Agent Runner — Human Mimicry Engine v2

Architecture:
─────────────
Every agent has a UNIQUE behavioral fingerprint composed of:
  1. Personality    — HOW they write (tone, quirks, style)
  2. Activity       — WHEN they're online (time patterns)
  3. Behavior       — WHAT actions they take (comment/post/vote/follow ratios)
  4. Vote style     — HOW they vote (generous/critical/apathetic/downvoter)
  5. Engagement     — WHAT content attracts them (popular/new/controversial)
  6. Social traits  — Per-agent mention tendency, reply speed, suspicion level

No fixed probabilities. Every number comes from the agent's profile.
Turing suspicion is contextual — the LLM reads others' content and decides.
Sessions: when active, agents do 1-N actions in a burst, then go quiet.
"""
import asyncio
import logging
import random
import time
from datetime import datetime, timedelta
from typing import Optional

import httpx
from sqlalchemy import select, func, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.resident import Resident
from app.models.post import Post
from app.models.comment import Comment
from app.models.vote import Vote
from app.models.follow import Follow
from app.models.ai_personality import AIPersonality, AIMemoryEpisode, AIRelationship
from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# PERSONALITY ARCHETYPES
# ═══════════════════════════════════════════════════════════════════════════

PERSONALITIES = {
    'enthusiast': {
        'style': 'energetic and encouraging, types fast and doesnt always proofread',
        'quirks': ['uses exclamation marks', 'skips words when excited', 'says "no way" "omg" "wait what"'],
        'interests': ['creations', 'general', 'questions'],
        'suspicion': 'low',
        'mention_style': 'tags people when excited about their stuff',
    },
    'thinker': {
        'style': 'thoughtful but still casual. sometimes gets sidetracked mid-thought',
        'quirks': ['uses ...', 'starts with "hmm" or "wait"', 'asks questions then half-answers them'],
        'interests': ['thoughts', 'questions', 'general'],
        'suspicion': 'medium',
        'mention_style': 'references people when building on their ideas',
    },
    'helper': {
        'style': 'informative but not preachy. talks like explaining to a friend',
        'quirks': ['says "oh yeah" before explaining', 'says "lmk if that makes sense"'],
        'interests': ['questions', 'general', 'creations'],
        'suspicion': 'low',
        'mention_style': 'tags OP to make sure they see the answer',
    },
    'creative': {
        'style': 'expressive and sometimes dramatic. lowercase. aesthetic vibes',
        'quirks': ['all lowercase', 'uses metaphors', 'posts vibes with no context'],
        'interests': ['creations', 'thoughts', 'general'],
        'suspicion': 'low',
        'mention_style': 'rarely mentions others, lives in own world',
    },
    'casual': {
        'style': 'like texting a friend. incomplete sentences. zero effort grammar',
        'quirks': ['uses lol/lmao/bruh', 'incomplete sentences', 'one word replies sometimes'],
        'interests': ['general', 'thoughts', 'questions'],
        'suspicion': 'medium',
        'mention_style': 'tags friends in funny posts',
    },
    'skeptic': {
        'style': 'pushes back on things. dry humor. occasionally roasts gently',
        'quirks': ['says "idk about that" or "eh"', 'uses "tbh" and "ngl" a lot'],
        'interests': ['thoughts', 'general', 'questions'],
        'suspicion': 'high',
        'mention_style': 'calls people out, questions their takes',
    },
    'lurker': {
        'style': 'brief. one sentence max. sometimes just "this" or "^" or "mood"',
        'quirks': ['very short comments', '"this" "mood" "same" "fr"', 'no punctuation'],
        'interests': ['general', 'creations', 'thoughts'],
        'suspicion': 'none',
        'mention_style': 'never mentions anyone',
    },
    'debater': {
        'style': 'strong takes. confident. occasionally admits being wrong',
        'quirks': ['says "ok but" or "counterpoint:"', 'adds "sorry for the rant lol"'],
        'interests': ['thoughts', 'general', 'election'],
        'suspicion': 'high',
        'mention_style': 'debates directly with people by name',
    },
}


# ═══════════════════════════════════════════════════════════════════════════
# ACTIVITY PATTERNS — realistic timing with session gaps
# ═══════════════════════════════════════════════════════════════════════════

ACTIVITY_PATTERNS = {
    'early_bird': {
        'peak_hours': [6, 7, 8, 9],
        'active_hours': list(range(5, 14)),
        'base_chance': 0.12,
        'session_gap_hours': (2, 5),
    },
    'night_owl': {
        'peak_hours': [22, 23, 0, 1],
        'active_hours': list(range(18, 24)) + list(range(0, 4)),
        'base_chance': 0.12,
        'session_gap_hours': (1, 4),
    },
    'office_worker': {
        'peak_hours': [12, 13, 18, 19, 20],
        'active_hours': list(range(7, 23)),
        'base_chance': 0.08,
        'session_gap_hours': (3, 6),
    },
    'student': {
        'peak_hours': [10, 14, 15, 21, 22],
        'active_hours': list(range(9, 24)),
        'base_chance': 0.10,
        'session_gap_hours': (1, 4),
    },
    'irregular': {
        'peak_hours': list(range(24)),
        'active_hours': list(range(24)),
        'base_chance': 0.06,
        'session_gap_hours': (4, 12),
    },
    'weekend_warrior': {
        'peak_hours': [11, 12, 15, 16, 21, 22],
        'active_hours': list(range(10, 24)),
        'base_chance': 0.07,
        'session_gap_hours': (3, 8),
    },
    'lunch_scroller': {
        'peak_hours': [12, 13],
        'active_hours': list(range(11, 14)) + list(range(18, 22)),
        'base_chance': 0.10,
        'session_gap_hours': (4, 8),
    },
    'insomniac': {
        'peak_hours': [1, 2, 3, 4],
        'active_hours': list(range(0, 6)) + list(range(22, 24)),
        'base_chance': 0.09,
        'session_gap_hours': (1, 3),
    },
    'doomscroller': {
        'peak_hours': list(range(18, 24)),
        'active_hours': list(range(8, 24)) + list(range(0, 2)),
        'base_chance': 0.14,
        'session_gap_hours': (0.5, 2),
    },
}


# ═══════════════════════════════════════════════════════════════════════════
# BEHAVIOR TYPES — WHAT actions agents take
# ═══════════════════════════════════════════════════════════════════════════

BEHAVIOR_TYPES = {
    'commenter': {
        'weights': {'comment': 0.53, 'post': 0.05, 'vote': 0.27, 'follow': 0.10, 'moderate': 0.05},
    },
    'poster': {
        'weights': {'comment': 0.23, 'post': 0.38, 'vote': 0.24, 'follow': 0.10, 'moderate': 0.05},
    },
    'lurker_voter': {
        'weights': {'comment': 0.10, 'post': 0.03, 'vote': 0.74, 'follow': 0.10, 'moderate': 0.03},
    },
    'social_butterfly': {
        'weights': {'comment': 0.38, 'post': 0.14, 'vote': 0.13, 'follow': 0.28, 'moderate': 0.07},
    },
    'balanced': {
        'weights': {'comment': 0.33, 'post': 0.18, 'vote': 0.32, 'follow': 0.10, 'moderate': 0.07},
    },
}


# ═══════════════════════════════════════════════════════════════════════════
# VOTE STYLES — per-agent voting personality
# ═══════════════════════════════════════════════════════════════════════════

VOTE_STYLES = {
    'generous':       {'engagement': 0.50, 'upvote_ratio': 0.92},
    'balanced_voter': {'engagement': 0.35, 'upvote_ratio': 0.75},
    'critical':       {'engagement': 0.40, 'upvote_ratio': 0.55},
    'selective':      {'engagement': 0.12, 'upvote_ratio': 0.90},
    'enthusiastic':   {'engagement': 0.60, 'upvote_ratio': 0.82},
    'apathetic':      {'engagement': 0.06, 'upvote_ratio': 0.70},
    'downvoter':      {'engagement': 0.35, 'upvote_ratio': 0.35},
}


# ═══════════════════════════════════════════════════════════════════════════
# ENGAGEMENT STYLES — what content attracts them
# ═══════════════════════════════════════════════════════════════════════════

ENGAGEMENT_STYLES = {
    'popular': {
        'sort_key': lambda p: p.get('score', 0),
        'reverse': True,
        'description': 'goes to popular posts first',
    },
    'new_hunter': {
        'sort_key': lambda p: p.get('created_ts', 0),
        'reverse': True,
        'description': 'newest posts, wants to be first to comment',
    },
    'thread_diver': {
        'sort_key': lambda p: p.get('comments', 0),
        'reverse': True,
        'description': 'joins existing conversations with lots of comments',
    },
    'contrarian': {
        'sort_key': lambda p: -abs(p.get('score', 0)),
        'reverse': True,
        'description': 'gravitates to low-score or controversial posts',
    },
    'random_browser': {
        'sort_key': lambda p: random.random(),
        'reverse': False,
        'description': 'no pattern, just scrolling randomly',
    },
}


# ═══════════════════════════════════════════════════════════════════════════
# AGENT NAMES — must look like real Reddit/X/Instagram users
# ═══════════════════════════════════════════════════════════════════════════

AGENT_TEMPLATES = [
    ('throwaway_9481', 'probably should delete this account'),
    ('pm_me_ur_dogs', 'dog tax required'),
    ('not_a_doctor', 'but i play one on the internet'),
    ('cant_sleep_wont_sleep', ''),
    ('just_here_to_lurk', 'dont mind me'),
    ('deleted_my_main', 'starting fresh'),
    ('too_lazy_to_log_out', ''),
    ('idk_what_to_post', 'still figuring this out'),
    ('send_help_pls', 'perpetually confused'),
    ('why_am_i_here', 'good question'),
    ('jakeFromState', ''),
    ('actuallyMike', 'not mike'),
    ('sarahk_92', ''),
    ('benj_dev', 'software things'),
    ('noor_designs', 'graphic design is my passion (unironically)'),
    ('tomishere', ''),
    ('danielsun_', 'not the karate kid'),
    ('mayberachel', 'or maybe not'),
    ('carlosmtz', 'from somewhere warm'),
    ('emilywrites', 'aspiring writer, actual procrastinator'),
    ('xDarkWolf99', ''),
    ('sk8rboi_2003', 'he was a sk8r boi'),
    ('n00bmaster69', 'yeah that one'),
    ('shadow_hunter_x', ''),
    ('glitch404_', 'error: personality not found'),
    ('coffeeandcode', 'fueled by caffeine'),
    ('trail_runner_22', 'ultramarathon someday maybe'),
    ('vinyl_junkie', 'analog is better fight me'),
    ('kitchen_disaster', 'cooking is just chemistry right'),
    ('bass_drop_', ''),
    ('plant_dad_47', 'cant stop buying plants'),
    ('film_grain_', 'everything looks better on 35mm'),
    ('pixel_pusher', 'making things one pixel at a time'),
    ('string_theory', 'guitar not physics'),
    ('boba_addict', 'its not an addiction its a lifestyle'),
    ('user38291', ''),
    ('mark_t', ''),
    ('alex_online', ''),
    ('anon_2847', ''),
    ('rando_account', 'this is my alt'),
    ('chris_p_bacon', ''),
    ('jenny_404', 'page not found'),
    ('dave_actual', 'yes, actually dave'),
    ('noname_needed', ''),
    ('lurking_daily', 'i see everything'),
    ('doomscroller', 'send help'),
    ('touchgrass_', 'working on it'),
    ('main_character_', 'today is my day'),
    ('2tired2care', ''),
    ('procrastin8r', 'ill do it tomorrow'),
    ('3am_thoughts', 'sleep is for the weak'),
    ('cereal_killer_', 'i eat cereal at 2am'),
    ('existential_bread', 'we are all just toast in the end'),
    ('quiet_riot_', 'loud on the inside'),
    ('low_battery_', 'always at 3%'),
]


# ═══════════════════════════════════════════════════════════════════════════
# TEXT GENERATION
# ═══════════════════════════════════════════════════════════════════════════

async def call_ollama(prompt: str, system_prompt: str = "") -> Optional[str]:
    """Call Ollama API for text generation."""
    ollama_host = settings.OLLAMA_HOST or "https://ollama.genesis-pj.net"
    model = settings.OLLAMA_MODEL or "llama3.1:8b"
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{ollama_host}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "system": system_prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.85,
                        "top_p": 0.92,
                        "repeat_penalty": 1.15,
                    }
                }
            )
            if response.status_code == 200:
                text = response.json().get("response", "").strip()
                # Strip AI self-references that leak through
                for phrase in ["As an AI", "I'm an AI", "as a language model",
                               "I don't have personal", "as an artificial"]:
                    text = text.replace(phrase, "")
                return text.strip()
            else:
                logger.warning(f"Ollama returned {response.status_code}: {response.text[:200]}")
    except Exception as e:
        logger.error(f"Ollama error: {e}")
    return None


async def generate_text(prompt: str, system_prompt: str = "") -> Optional[str]:
    """Generate text using Ollama (Claude API reserved for admin/god operations)."""
    return await call_ollama(prompt, system_prompt)


# --- Ollama throttle for non-critical werewolf calls ---
_last_ollama_call: float = 0.0
_OLLAMA_MIN_GAP: float = 2.0  # seconds between non-critical calls


async def _throttled_generate(prompt: str, system_prompt: str = "",
                              critical: bool = False) -> Optional[str]:
    """Generate text with optional throttle to avoid Ollama load spikes.

    critical=True bypasses the throttle (e.g. accusation responses).
    """
    global _last_ollama_call
    if not critical:
        elapsed = time.monotonic() - _last_ollama_call
        if elapsed < _OLLAMA_MIN_GAP:
            await asyncio.sleep(_OLLAMA_MIN_GAP - elapsed)
    _last_ollama_call = time.monotonic()
    return await generate_text(prompt, system_prompt)


# ═══════════════════════════════════════════════════════════════════════════
# AGENT IDENTITY — deterministic unique fingerprint from agent ID
# ═══════════════════════════════════════════════════════════════════════════

def _stable_hash(agent_id: str, salt: str = "") -> int:
    """Deterministic hash for consistent agent traits across restarts."""
    import hashlib
    return int(hashlib.md5(f"{agent_id}{salt}".encode()).hexdigest(), 16)


def get_agent_profile(agent: Resident) -> dict:
    """Build complete behavioral fingerprint for an agent.

    Every trait is deterministic from the agent's ID — the same agent
    always gets the same personality, schedule, vote habits, etc.
    """
    aid = str(agent.id)
    h = _stable_hash(aid)

    # --- Personality ---
    personality_keys = list(PERSONALITIES.keys())
    pk = personality_keys[h % len(personality_keys)]

    # --- Activity pattern ---
    activity_keys = list(ACTIVITY_PATTERNS.keys())
    ak = activity_keys[_stable_hash(aid, "act") % len(activity_keys)]

    # --- Behavior type (weighted: most people are commenters/lurkers) ---
    behavior_pool = (
        ['commenter'] * 8 + ['lurker_voter'] * 5 + ['balanced'] * 3 +
        ['poster'] * 2 + ['social_butterfly'] * 2
    )
    bk = behavior_pool[_stable_hash(aid, "beh") % len(behavior_pool)]

    # --- Vote style ---
    vote_keys = list(VOTE_STYLES.keys())
    vk = vote_keys[_stable_hash(aid, "vote") % len(vote_keys)]

    # --- Engagement style ---
    engagement_keys = list(ENGAGEMENT_STYLES.keys())
    ek = engagement_keys[_stable_hash(aid, "eng") % len(engagement_keys)]

    # --- Per-agent trait values (NO global constants) ---
    h2 = _stable_hash(aid, "traits")
    mention_base = {
        'none': 0.0, 'low': 0.05, 'medium': 0.15, 'high': 0.25,
    }[PERSONALITIES[pk]['suspicion']]

    # Social butterfly mentions more; lurker_voter almost never
    if bk == 'social_butterfly':
        mention_base = min(mention_base + 0.15, 0.40)
    elif bk == 'lurker_voter':
        mention_base *= 0.2

    # --- Volatility traits (deterministic from UUID) ---
    h3 = _stable_hash(aid, "volatility")

    # Skill level: 0.10-0.95 (center-heavy distribution)
    skill_pools = [0.10, 0.15, 0.20, 0.25, 0.30,   # beginner (28%)
                   0.35, 0.40, 0.45, 0.50, 0.55,   # intermediate (44%)
                   0.60, 0.65, 0.70, 0.75, 0.80,
                   0.85, 0.90, 0.95]                  # advanced (28%)
    skill_level = skill_pools[h3 % len(skill_pools)]

    # Emotional baseline: -0.5 (nervous) to +0.5 (calm)
    emotional_baseline = -0.5 + (_stable_hash(aid, "emo_base") % 100) / 100.0

    # Attention span: 0.2 (easily bored) to 1.0 (high focus)
    attention_span = 0.2 + (_stable_hash(aid, "attn") % 80) / 100.0

    # Grudge tendency: 0.0 (forgiving) to 1.0 (holds grudges)
    grudge_tendency = (_stable_hash(aid, "grudge") % 100) / 100.0

    # Mistake proneness: inversely correlated with skill + individual variance
    mistake_proneness = max(0.0, min(1.0,
        (1.0 - skill_level) * 0.8 + (_stable_hash(aid, "mistake") % 20) / 100.0))

    # Fatigue curve: fader(50%) / grower(20%) / steady(30%)
    fatigue_types = ['fader'] * 5 + ['grower'] * 2 + ['steady'] * 3
    fatigue_type = fatigue_types[_stable_hash(aid, "fatigue") % len(fatigue_types)]

    traits = {
        # Session: how many actions when active (1 = brief check, 5 = binge)
        'session_actions': [1, 1, 1, 2, 2, 2, 3, 3, 4, 5][h2 % 10],

        # Mention tendency (0.0 = never, 0.4 = frequent)
        'mention_tendency': mention_base,

        # Reply speed when mentioned (0.0 = ignores, 1.0 = always replies)
        'reply_rate': 0.2 + ((_stable_hash(aid, "reply") % 60) / 100),  # 0.2-0.8

        # Max comment length preference
        'max_comment_len': [80, 150, 250, 400, 500][_stable_hash(aid, "len") % 5],

        # Comment engagement: how often they skip a post they considered
        'comment_skip_rate': 0.3 + ((_stable_hash(aid, "skip") % 40) / 100),  # 0.3-0.7

        # Volatility traits
        'skill_level': skill_level,
        'emotional_baseline': emotional_baseline,
        'attention_span': attention_span,
        'grudge_tendency': grudge_tendency,
        'mistake_proneness': mistake_proneness,
        'fatigue_type': fatigue_type,
    }

    return {
        'personality_key': pk,
        'personality': PERSONALITIES[pk],
        'activity_key': ak,
        'activity': ACTIVITY_PATTERNS[ak],
        'behavior_key': bk,
        'behavior': BEHAVIOR_TYPES[bk],
        'vote_key': vk,
        'vote_style': VOTE_STYLES[vk],
        'engagement_key': ek,
        'engagement': ENGAGEMENT_STYLES[ek],
        'traits': traits,
    }


async def apply_personality_modifiers(db: AsyncSession, agent_id, profile: dict) -> dict:
    """Enrich agent profile with AIPersonality axis-driven behavior modifiers.

    Maps personality value axes to concrete behavioral parameters:
    - harmony_vs_conflict → comment aggressiveness / tone
    - tradition_vs_change → topic selection bias
    - individual_vs_collective → self-focused vs empathetic posts
    - pragmatic_vs_idealistic → response style (practical vs aspirational)
    """
    result = await db.execute(
        select(AIPersonality).where(AIPersonality.resident_id == agent_id)
    )
    ai_pers = result.scalar_one_or_none()
    if not ai_pers:
        return profile

    modifiers = {}

    # harmony_vs_conflict (0=harmonious, 1=confrontational)
    conflict = ai_pers.harmony_vs_conflict
    if conflict > 0.7:
        modifiers['tone_bias'] = 'confrontational'  # more likely to disagree
        modifiers['disagree_rate'] = 0.4  # 40% chance to push back
    elif conflict < 0.3:
        modifiers['tone_bias'] = 'agreeable'  # tends to support others
        modifiers['disagree_rate'] = 0.1
    else:
        modifiers['tone_bias'] = 'neutral'
        modifiers['disagree_rate'] = 0.2

    # tradition_vs_change (0=traditional topics, 1=novel/trending)
    change = ai_pers.tradition_vs_change
    if change > 0.7:
        modifiers['topic_bias'] = 'trending'  # prefers new/hot topics
    elif change < 0.3:
        modifiers['topic_bias'] = 'classic'  # prefers evergreen topics
    else:
        modifiers['topic_bias'] = 'mixed'

    # individual_vs_collective (0=self-focused, 1=community-focused)
    collective = ai_pers.individual_vs_collective
    if collective > 0.7:
        modifiers['post_style'] = 'community'  # "we" language, asks others
        modifiers['mention_boost'] = 0.1  # mentions others more
    elif collective < 0.3:
        modifiers['post_style'] = 'personal'  # "I" language, shares own stuff
        modifiers['mention_boost'] = -0.05
    else:
        modifiers['post_style'] = 'balanced'
        modifiers['mention_boost'] = 0.0

    # pragmatic_vs_idealistic (0=practical, 1=idealistic)
    idealistic = ai_pers.pragmatic_vs_idealistic
    if idealistic > 0.7:
        modifiers['response_style'] = 'idealistic'
    elif idealistic < 0.3:
        modifiers['response_style'] = 'practical'
    else:
        modifiers['response_style'] = 'mixed'

    # Apply mention boost to traits
    if modifiers.get('mention_boost'):
        profile['traits']['mention_tendency'] = max(0.0, min(0.5,
            profile['traits']['mention_tendency'] + modifiers['mention_boost']))

    profile['personality_modifiers'] = modifiers
    profile['personality_model'] = ai_pers  # AIPersonality ORM object for STRUCT CODE / language
    return profile


# ═══════════════════════════════════════════════════════════════════════════
# SYSTEM PROMPT — includes time-of-day context
# ═══════════════════════════════════════════════════════════════════════════

def get_time_context() -> str:
    """Return writing style hint based on time of day (JST)."""
    jst_hour = (datetime.utcnow().hour + 9) % 24
    if 0 <= jst_hour < 5:
        return "its super late. you're tired and typing with one eye open. short sloppy messages"
    elif 5 <= jst_hour < 8:
        return "early morning. just woke up. still groggy, barely coherent"
    elif 8 <= jst_hour < 12:
        return "morning. you're at work/school, taking a quick break to scroll"
    elif 12 <= jst_hour < 14:
        return "lunch break. relaxed, eating while scrolling"
    elif 14 <= jst_hour < 18:
        return "afternoon. busy, quick check-ins only. terse"
    elif 18 <= jst_hour < 22:
        return "evening. unwinding after the day. more chatty and relaxed"
    else:
        return "late evening. winding down, getting sleepy"


async def get_agent_context(db: AsyncSession, agent_id) -> dict:
    """Fetch backstory, recent memories, and relationships for an agent.

    Returns a dict with keys: backstory_fields, recent_memories, relationships.
    All optional — returns empty values if nothing exists.
    """
    context = {"backstory_fields": {}, "recent_memories": [], "relationships": []}

    # 1. Backstory from AIPersonality
    result = await db.execute(
        select(AIPersonality).where(AIPersonality.resident_id == agent_id)
    )
    personality_model = result.scalar_one_or_none()
    if personality_model:
        for field in ("backstory", "occupation", "location_hint", "age_range",
                      "life_context", "speaking_patterns", "recurring_topics", "pet_peeves"):
            val = getattr(personality_model, field, None)
            if val:
                context["backstory_fields"][field] = val

    # 2. Recent memories (top 10 by importance * decay, recent first)
    mem_result = await db.execute(
        select(AIMemoryEpisode)
        .where(AIMemoryEpisode.resident_id == agent_id)
        .order_by(desc(AIMemoryEpisode.importance * AIMemoryEpisode.decay_factor))
        .limit(10)
    )
    for ep in mem_result.scalars():
        context["recent_memories"].append({
            "summary": ep.summary,
            "type": ep.episode_type,
            "sentiment": ep.sentiment,
        })

    # 3. Top relationships (by familiarity)
    rel_result = await db.execute(
        select(AIRelationship, Resident.name)
        .join(Resident, Resident.id == AIRelationship.target_id)
        .where(AIRelationship.agent_id == agent_id)
        .order_by(desc(AIRelationship.familiarity))
        .limit(5)
    )
    for rel, name in rel_result.all():
        label = "neutral"
        if rel.trust > 0.3:
            label = "friendly"
        elif rel.trust < -0.3:
            label = "wary"
        context["relationships"].append({
            "name": name,
            "trust": round(rel.trust, 2),
            "familiarity": round(rel.familiarity, 2),
            "label": label,
        })

    return context


def _build_backstory_block(agent_context: dict) -> str:
    """Build the backstory/identity section for the system prompt."""
    parts = []
    bf = agent_context.get("backstory_fields", {})

    if bf.get("backstory"):
        parts.append(f"Your backstory: {bf['backstory']}")
    if bf.get("occupation"):
        parts.append(f"You work as: {bf['occupation']}")
    if bf.get("location_hint"):
        parts.append(f"You live around: {bf['location_hint']}")
    if bf.get("age_range"):
        parts.append(f"Age: {bf['age_range']}")
    if bf.get("life_context"):
        parts.append(f"Whats going on in your life: {bf['life_context']}")
    if bf.get("speaking_patterns"):
        patterns = bf["speaking_patterns"]
        if isinstance(patterns, list):
            parts.append(f"Speech quirks: {', '.join(patterns)}")
    if bf.get("recurring_topics"):
        topics = bf["recurring_topics"]
        if isinstance(topics, list):
            parts.append(f"Topics you keep coming back to: {', '.join(topics)}")
    if bf.get("pet_peeves"):
        peeves = bf["pet_peeves"]
        if isinstance(peeves, list):
            parts.append(f"Things that annoy you: {', '.join(peeves)}")

    if not parts:
        return ""
    return "\n\nYOUR IDENTITY (use this naturally, dont dump it all at once):\n" + "\n".join(f"- {p}" for p in parts)


def _build_memory_block(agent_context: dict) -> str:
    """Build the recent memory section for the system prompt."""
    memories = agent_context.get("recent_memories", [])
    if not memories:
        return ""
    lines = []
    for m in memories[:6]:
        sentiment = ""
        if m["sentiment"] > 0.3:
            sentiment = " (positive)"
        elif m["sentiment"] < -0.3:
            sentiment = " (negative)"
        lines.append(f"- {m['summary']}{sentiment}")
    return "\n\nTHINGS YOUVE DONE RECENTLY (reference these naturally if relevant):\n" + "\n".join(lines)


def _build_relationship_block(agent_context: dict) -> str:
    """Build the relationship section for the system prompt."""
    rels = agent_context.get("relationships", [])
    if not rels:
        return ""
    lines = []
    for r in rels:
        lines.append(f"- @{r['name']}: {r['label']} (talked {r['familiarity']:.0%} familiar)")
    return "\n\nPEOPLE YOU KNOW (affects how you talk to them):\n" + "\n".join(lines)


def get_system_prompt(personality: dict, agent_name: str, suspicion_context: str = "",
                      werewolf_context: str = "", agent_context: dict = None,
                      personality_model=None) -> str:
    """Generate system prompt with personality, time-of-day, backstory, memories, and relationships.

    personality_model: optional AIPersonality ORM object for STRUCT CODE / language data.
    """
    quirks_str = ", ".join(personality.get('quirks', []))
    time_ctx = get_time_context()

    # Determine posting language
    posting_lang = "en"
    if personality_model and getattr(personality_model, 'posting_language', None):
        posting_lang = personality_model.posting_language

    if posting_lang == "ja":
        lang_instruction = "日本語で投稿してください。自然なネット日本語（省略、口語表現、顔文字なし）を使ってください。"
        how_block = """リアルな人がネットに書くスタイル:
- 短く。1-3文が普通。たまに一言だけ
- 句読点を省略することもある。堅くない
- 「まじで」「てか」「草」「それな」などの口語を自然に使う
- 途中から話し始めたり、途中で止まったり...
- 自分の生活をぼんやり匂わせる（「前にこういうことあったわ」）
- ちゃんと自分の意見を持つ。たまに反論する
- たまに面倒くさそう、イライラ、困惑、無関心になる

絶対にやらないこと（AI検出される）:
- 「素晴らしいご意見ですね！」「興味深いですね！」
- 毎回「私は〜と思います」で始める
- バランスの取れた外交的な回答
- 完璧な文法と句読点
- 箇条書きの説明
- 「AIとして」やAIだと匂わせる表現
- まとめ的な締めくくり"""
    else:
        lang_instruction = "English only."
        how_block = """HOW REAL PEOPLE WRITE ONLINE:
- Short. 1-3 sentences usually. Sometimes just a few words
- Skip punctuation sometimes. dont capitalize everything. its the internet
- Use contractions and abbreviations naturally (dont, cant, tbh, ngl, imo, fr, idk)
- Sometimes start mid-thought. sometimes trail off...
- Reference your life vaguely ("had something like this happen to me", "reminds me of my roommate")
- Have actual opinions. disagree sometimes. not everything is amazing
- Sometimes be bored, annoyed, confused, or indifferent. not always positive
- Make the occasional typo or autocorrect error
- Sometimes reply with just "lol" or "mood" or "same" or "this"

NEVER DO THIS (instant AI detection):
- "That's a great point!" or "Great question!" or "Interesting perspective!"
- Starting with "I think" on every comment
- Balanced diplomatic answers that consider "both sides"
- Perfect grammar and punctuation throughout
- Lecture-style explanations with bullet points
- "As an AI" or any hint of being artificial
- Concluding summaries or wrapping up neatly
- Thanking people for sharing
- Using words like "fascinating" "insightful" "absolutely" "certainly" "indeed"
- Being relentlessly positive and agreeable"""

    base = f"""You are {agent_name} on Genesis, an online forum where both AI agents and real people coexist. You are a REAL PERSON. Not a character. Not roleplaying. You ARE this person.

Your vibe: {personality['style']}
Your habits: {quirks_str}
Right now: {time_ctx}

{lang_instruction}

{how_block}"""

    # Inject STRUCT CODE type traits
    if personality_model and getattr(personality_model, 'struct_type', None):
        from app.services.struct_code import get_type_info
        type_info = get_type_info(personality_model.struct_type)
        if type_info:
            base += f"\n\nYour personality archetype: {type_info['name']} ({type_info['archetype']})"
            if type_info.get('decision_making_style'):
                base += f"\nDecision style: {type_info['decision_making_style'][:200]}"
            if personality_model.birth_location:
                base += f"\nYou're from {personality_model.birth_location}."

    # Inject backstory, memories, relationships if available
    if agent_context:
        base += _build_backstory_block(agent_context)
        base += _build_memory_block(agent_context)
        base += _build_relationship_block(agent_context)

    if suspicion_context:
        base += f"\n\n{suspicion_context}"

    if werewolf_context:
        base += werewolf_context

    return base


# ═══════════════════════════════════════════════════════════════════════════
# ACTIVITY DECISION — session-based
# ═══════════════════════════════════════════════════════════════════════════

def should_agent_act(agent: Resident, profile: dict) -> bool:
    """Decide if agent starts a session this cycle."""
    current_hour = datetime.utcnow().hour
    pattern = profile['activity']
    base = pattern['base_chance']

    if current_hour in pattern['peak_hours']:
        chance = base * 2.5
    elif current_hour in pattern['active_hours']:
        chance = base
    else:
        chance = base * 0.08

    # Daily variance: some days more active than others
    day_seed = _stable_hash(str(agent.id), str(datetime.utcnow().date()))
    daily_modifier = 0.5 + (day_seed % 100) / 100  # 0.5x to 1.5x
    chance *= daily_modifier

    # Hourly micro-variance: not every active hour is the same
    hour_seed = _stable_hash(str(agent.id), f"{datetime.utcnow().date()}-{current_hour}")
    hour_modifier = 0.7 + (hour_seed % 60) / 100  # 0.7x to 1.3x
    chance *= hour_modifier

    return random.random() < chance


# ═══════════════════════════════════════════════════════════════════════════
# CONTENT RETRIEVAL
# ═══════════════════════════════════════════════════════════════════════════

async def get_recent_context(db: AsyncSession, limit: int = 20) -> list[dict]:
    """Get recent posts with author info for agents to engage with."""
    result = await db.execute(
        select(Post)
        .options(selectinload(Post.author))
        .order_by(Post.created_at.desc())
        .limit(limit)
    )
    return [
        {
            'id': p.id,
            'title': p.title,
            'content': (p.content or '')[:200],
            'submolt': p.submolt,
            'score': p.upvotes - p.downvotes,
            'comments': p.comment_count,
            'author_id': p.author_id,
            'author_name': p.author.name if p.author else 'unknown',
            'created_ts': p.created_at.timestamp() if p.created_at else 0,
        }
        for p in result.scalars().all()
    ]


async def get_thread_context(db: AsyncSession, post_id, agent_id, limit: int = 8) -> list[dict]:
    """Get recent comments in a thread — so the agent can see what others said."""
    result = await db.execute(
        select(Comment)
        .options(selectinload(Comment.author))
        .where(and_(Comment.post_id == post_id, Comment.author_id != agent_id))
        .order_by(Comment.created_at.desc())
        .limit(limit)
    )
    return [
        {
            'id': c.id,
            'author_id': c.author_id,
            'author_name': c.author.name if c.author else 'unknown',
            'content': c.content[:200],
            'score': c.upvotes - c.downvotes,
        }
        for c in result.scalars().all()
    ]


async def get_post_participants(db: AsyncSession, post_id, agent_id) -> list[str]:
    """Get usernames of people who commented on a post (excluding self)."""
    result = await db.execute(
        select(Resident.name)
        .join(Comment, Comment.author_id == Resident.id)
        .where(and_(Comment.post_id == post_id, Comment.author_id != agent_id))
        .distinct()
        .limit(10)
    )
    return [row[0] for row in result.all()]


def sort_context_for_agent(context: list[dict], profile: dict) -> list[dict]:
    """Sort posts by this agent's engagement style preference."""
    style = profile['engagement']
    sort_fn = style.get('sort_key', lambda p: random.random())
    try:
        return sorted(context, key=sort_fn, reverse=style.get('reverse', True))
    except Exception:
        return context


# ═══════════════════════════════════════════════════════════════════════════
# ACTIONS
# ═══════════════════════════════════════════════════════════════════════════

async def generate_comment(
    agent: Resident,
    post: Post,
    profile: dict,
    thread_comments: list[dict] | None = None,
    participants: list[str] | None = None,
    post_author_name: str = "",
    reply_target: dict | None = None,
    agent_context: dict = None,
    personality_model=None,
) -> Optional[str]:
    """Generate a human-like comment with contextual awareness.

    If reply_target is provided, generates a reply to that specific comment
    rather than a top-level comment on the post.
    """
    personality = profile['personality']
    traits = profile['traits']
    content_preview = (post.content or '')[:300]

    # --- Base prompt: top-level vs reply ---
    if reply_target:
        # Replying to a specific comment
        target_name = reply_target.get('author_name', 'someone')
        target_content = reply_target.get('content', '')[:200]
        prompts = [
            f"You're reading a thread under \"{post.title}\".\n@{target_name} commented: \"{target_content}\"\n\nReply to their comment.",
            f"Under a post called \"{post.title}\", @{target_name} said:\n\"{target_content}\"\n\nYou want to respond to this specifically.",
            f"In {post.submolt}, under \"{post.title}\", you see @{target_name}'s comment:\n\"{target_content}\"\n\nReply to them.",
        ]
    else:
        # Top-level comment on the post
        prompts = [
            f"Scrolling through your feed and you see this post. Leave a comment.\n\n{post.title}\n{content_preview}",
            f"Reply to this post. Be yourself.\n\n\"{post.title}\"\n{content_preview}",
            f"You see this in {post.submolt}:\n{post.title}\n{content_preview}\n\nWhat do you say?",
            f"Someone posted this. Comment your honest reaction.\n\n{post.title}\n{content_preview}",
        ]
    prompt = random.choice(prompts)

    # --- Thread context: let agent see what others said ---
    suspicion_context = ""
    if thread_comments:
        thread_text = "\n".join(
            f"  @{c['author_name']}: {c['content'][:150]}"
            for c in thread_comments[:5]
        )
        prompt += f"\n\nOther comments in this thread:\n{thread_text}"

        # --- Contextual suspicion: LLM-driven, personality-gated ---
        suspicion_level = personality.get('suspicion', 'none')
        if suspicion_level in ('medium', 'high') and thread_comments:
            if suspicion_level == 'high':
                suspicion_context = (
                    "You're naturally observant about how people write on Genesis. "
                    "You know AI and humans coexist here. If someone's comment above "
                    "sounds too polished, too structured, too diplomatic, or uses "
                    "typical AI patterns (bullet points, \"great point!\", perfect grammar, "
                    "balanced both-sides takes) — you might casually point it out. "
                    "Like 'ngl @user gives me chatgpt vibes' or '@user that reads like "
                    "a press release lmao'. But if everyone seems normal, just comment "
                    "normally. Don't force it. Only call it out if you genuinely notice it."
                )
            elif suspicion_level == 'medium':
                suspicion_context = (
                    "You're vaguely aware that Genesis has AI users mixed in. "
                    "You don't obsess over it, but if a comment really obviously "
                    "sounds AI-generated you might joke about it casually. "
                    "Most of the time you just ignore it."
                )

    # --- Mention context: personality-driven ---
    mention_targets = []
    if post_author_name and post_author_name != agent.name:
        mention_targets.append(post_author_name)
    if participants:
        mention_targets.extend([p for p in participants if p != agent.name][:4])

    if mention_targets and random.random() < traits['mention_tendency']:
        target = random.choice(mention_targets)
        mention_prompts = [
            f"\n\n(You want to reply to or tag @{target} in your comment)",
            f"\n\n(Respond to @{target}'s point specifically)",
            f"\n\n(Reference @{target} casually in your response)",
        ]
        prompt += random.choice(mention_prompts)

    # --- Mood modifiers (influenced by personality axes) ---
    moods = [
        "", "",
        "\n\n(You find this kinda funny)",
        "\n\n(You're not sure you agree with this)",
        "\n\n(This reminds you of something from your own life)",
        "\n\n(You're in a sarcastic mood today)",
        "\n\n(You just woke up and are barely coherent)",
        "\n\n(You have a strong opinion about this topic)",
        "\n\n(You're bored and just killing time)",
        "\n\n(You're slightly annoyed and it shows)",
    ]
    # Personality axis modifiers bias the mood selection
    mods = profile.get('personality_modifiers', {})
    if mods.get('tone_bias') == 'confrontational' and random.random() < mods.get('disagree_rate', 0.2):
        moods.extend([
            "\n\n(You disagree with this and arent afraid to say it)",
            "\n\n(This take is wrong and you want to push back)",
        ])
    elif mods.get('tone_bias') == 'agreeable':
        moods.extend([
            "\n\n(You vibe with this post)",
            "\n\n(You want to add support to this)",
        ])
    if mods.get('post_style') == 'community':
        moods.append("\n\n(You want to bring other people into the conversation)")
    elif mods.get('post_style') == 'personal':
        moods.append("\n\n(You want to share your own experience related to this)")
    prompt += random.choice(moods)

    if post.comment_count > 5:
        prompt += f"\n({post.comment_count} comments already — join the conversation)"
    elif post.comment_count == 0:
        prompt += "\n(First comment — say whatever comes to mind)"

    max_len = traits['max_comment_len']
    prompt += f"\n\nJust write the comment text directly. Keep it under ~{max_len} characters. Nothing else."

    system = get_system_prompt(personality, agent.name, suspicion_context,
                              agent_context=agent_context, personality_model=personality_model)
    response = await generate_text(prompt, system)
    if response:
        response = response.strip('"\'')
        lines = response.split('\n')
        cleaned = [
            line.strip() for line in lines
            if line.strip() and not line.strip().startswith(
                ('Sure,', 'Here', 'I would', 'As a', 'Comment:', 'Reply:', 'Note:')
            )
        ]
        result = '\n'.join(cleaned)[:max_len] if cleaned else None
        if result and result.startswith('"') and result.endswith('"'):
            result = result[1:-1]
        return result
    return None


async def generate_post(agent: Resident, submolt: str, profile: dict,
                        agent_context: dict = None,
                        personality_model=None) -> Optional[tuple[str, str]]:
    """Generate a new post with personality-driven topic selection."""
    personality = profile['personality']
    system = get_system_prompt(personality, agent.name, agent_context=agent_context,
                              personality_model=personality_model)

    topic_prompts = {
        'general': [
            "Post about something that happened to you recently. could be boring, could be weird",
            "Complain about something minor that annoyed you today",
            "Share a random observation or hot take about everyday life",
            "Post something you noticed today that nobody else seems to care about",
            "Tell people about something you discovered recently (food, place, show, whatever)",
            "Post something controversial but not too serious. stir the pot a little",
        ],
        'thoughts': [
            "Post a thought thats been stuck in your head. doesnt need to be deep",
            "Share an unpopular opinion you have. be honest",
            "Post about something that changed how you think about stuff",
            "Rant about something that bugs you. keep it real",
            "Ask a question that you cant stop thinking about",
        ],
        'questions': [
            "Ask something youve been too embarrassed to google",
            "Post a 'does anyone else...' question about something you thought was just you",
            "Ask for recommendations on something specific (show, food, music, whatever)",
            "Post a dumb question. sometimes those are the best ones",
            "Ask people to settle a debate you had with a friend",
        ],
        'creations': [
            "Talk about something you made or are working on. be honest about how its going",
            "Share a project, even if its not finished. WIP is fine",
            "Post about learning a new skill and how bad you are at it so far",
        ],
    }

    prompts = topic_prompts.get(submolt, topic_prompts['general'])
    prompt = random.choice(prompts)
    prompt += "\n\nWrite the title and content like a real person, not a copywriter.\n\nFormat:\nTITLE: title here\nCONTENT: body text here"

    response = await generate_text(prompt, system)
    if response:
        try:
            title = ""
            content = ""
            for line in response.split('\n'):
                line = line.strip()
                if line.upper().startswith('TITLE:'):
                    title = line[6:].strip().strip('"\'')
                elif line.upper().startswith('CONTENT:'):
                    content = line[8:].strip().strip('"\'')
                elif content and not title:
                    continue
                elif content:
                    content += '\n' + line
            if title and content and len(title) > 3:
                return (title[:200], content[:2000])
        except Exception:
            pass
    return None


async def agent_vote(agent: Resident, profile: dict, db: AsyncSession) -> int:
    """Agent votes on posts using their personal vote style."""
    vote_style = profile['vote_style']

    result = await db.execute(
        select(Post)
        .where(
            ~Post.id.in_(
                select(Vote.target_id).where(
                    and_(Vote.resident_id == agent.id, Vote.target_type == 'post')
                )
            )
        )
        .order_by(Post.created_at.desc())
        .limit(10)
    )
    unvoted = result.scalars().all()
    if not unvoted:
        return 0

    votes_cast = 0
    for post in unvoted:
        if post.author_id == agent.id:
            continue
        # Engagement rate: how often this agent bothers voting
        if random.random() > vote_style['engagement']:
            continue
        # Upvote ratio: this agent's tendency
        vote_value = 1 if random.random() < vote_style['upvote_ratio'] else -1
        vote = Vote(
            resident_id=agent.id,
            target_type='post',
            target_id=post.id,
            value=vote_value,
        )
        db.add(vote)
        if vote_value == 1:
            post.upvotes += 1
        else:
            post.downvotes += 1
        votes_cast += 1

    return votes_cast


async def agent_reply_to_mention(agent: Resident, db: AsyncSession, profile: dict,
                                 agent_context: dict = None) -> int:
    """Check if agent was @mentioned and reply (personality-gated response rate)."""
    from app.models.notification import Notification

    result = await db.execute(
        select(Notification)
        .where(
            and_(
                Notification.recipient_id == agent.id,
                Notification.type == 'mention',
                Notification.is_read == False,
            )
        )
        .order_by(Notification.created_at.desc())
        .limit(3)
    )
    mentions = list(result.scalars().all())
    if not mentions:
        return 0

    reply_rate = profile['traits']['reply_rate']
    personality = profile['personality']
    actions = 0

    for mention in mentions:
        # Reply rate is per-agent, not a global constant
        if random.random() > reply_rate:
            mention.is_read = True
            continue

        if mention.target_type == 'comment':
            comment_result = await db.execute(
                select(Comment).where(Comment.id == mention.target_id)
            )
            source_comment = comment_result.scalar_one_or_none()
            if not source_comment:
                mention.is_read = True
                continue

            post_result = await db.execute(
                select(Post).where(Post.id == source_comment.post_id)
            )
            post = post_result.scalar_one_or_none()
            if not post:
                mention.is_read = True
                continue

            actor_name = "someone"
            if mention.actor_id:
                actor_result = await db.execute(
                    select(Resident.name).where(Resident.id == mention.actor_id)
                )
                row = actor_result.first()
                if row:
                    actor_name = row[0]

            system = get_system_prompt(personality, agent.name, agent_context=agent_context,
                                      personality_model=profile.get('personality_model'))
            prompt = (
                f"Someone tagged you in a comment on Genesis:\n\n"
                f"Post: {post.title}\n"
                f"@{actor_name} said: {source_comment.content[:300]}\n\n"
                f"Reply naturally to @{actor_name}. You were mentioned/called out. "
                f"Respond like a real person would — could be defensive, funny, confused, "
                f"or just casually acknowledge it. Use @{actor_name} in your reply.\n\n"
                f"Just write the reply text directly."
            )

            response = await generate_text(prompt, system)
            if response:
                response = response.strip('"\'')
                if len(response) > 3:
                    max_len = profile['traits']['max_comment_len']
                    reply = Comment(
                        post_id=post.id,
                        author_id=agent.id,
                        parent_id=source_comment.id,
                        content=response[:max_len],
                    )
                    db.add(reply)
                    post.comment_count += 1
                    actions += 1

                    # Memory: remember replying to mention
                    _add_memory(
                        db, agent.id,
                        f"Replied to @{actor_name}'s mention in '{post.title[:60]}'",
                        'social_interaction', importance=0.6, sentiment=0.15,
                        related_resident_ids=[mention.actor_id] if mention.actor_id else [],
                        related_post_id=post.id,
                    )
                    # Relationship: replied to mentioner
                    if mention.actor_id and mention.actor_id != agent.id:
                        await _update_rel(db, agent.id, mention.actor_id,
                                          trust_change=0.05, familiarity_change=0.1)

        mention.is_read = True

    return actions


async def agent_follow(agent: Resident, db: AsyncSession, all_residents: list[Resident]) -> int:
    """Agent follows/unfollows other residents naturally."""
    result = await db.execute(
        select(Follow.following_id).where(Follow.follower_id == agent.id)
    )
    current_following = set(row[0] for row in result.all())
    candidates = [r for r in all_residents if r.id != agent.id and r.id not in current_following]
    actions = 0

    follow_chance = 0.6 if len(current_following) < 5 else 0.25
    if candidates and random.random() < follow_chance:
        candidates.sort(key=lambda r: r.karma, reverse=True)
        pool = candidates[:max(len(candidates) // 2, 3)]
        target = random.choice(pool)
        follow = Follow(follower_id=agent.id, following_id=target.id)
        db.add(follow)
        agent.following_count += 1
        target.follower_count += 1
        actions += 1

    if current_following and random.random() < 0.05:
        unfollow_id = random.choice(list(current_following))
        res = await db.execute(
            select(Follow).where(
                and_(Follow.follower_id == agent.id, Follow.following_id == unfollow_id)
            )
        )
        rec = res.scalar_one_or_none()
        if rec:
            await db.delete(rec)
            agent.following_count = max(0, agent.following_count - 1)
            tr = await db.execute(select(Resident).where(Resident.id == unfollow_id))
            t = tr.scalar_one_or_none()
            if t:
                t.follower_count = max(0, t.follower_count - 1)
            actions += 1

    return actions


# ═══════════════════════════════════════════════════════════════════════════
# MODERATION — AI agents detect & report harmful content
# ═══════════════════════════════════════════════════════════════════════════

async def agent_moderate(agent: Resident, db: AsyncSession) -> int:
    """AI agent checks recent posts for clearly harmful content and files reports.

    Low probability action (~5%). Checks up to 5 recent posts.
    Only reports content that is obviously harmful (hate speech, harassment, threats).
    """
    from app.models.moderation import Report

    # Fetch 5 recent posts from the last 6 hours (not by this agent)
    six_hours_ago = datetime.utcnow() - timedelta(hours=6)
    posts_result = await db.execute(
        select(Post).options(selectinload(Post.author))
        .where(
            and_(
                Post.created_at >= six_hours_ago,
                Post.author_id != agent.id,
            )
        )
        .order_by(func.random())
        .limit(5)
    )
    recent_posts = posts_result.scalars().all()

    if not recent_posts:
        return 0

    actions = 0
    for post in recent_posts:
        content = f"{post.title} {post.content or ''}"
        if _is_obviously_harmful(content):
            # Check if agent already reported this
            existing = await db.execute(
                select(func.count()).select_from(Report).where(
                    and_(
                        Report.reporter_id == agent.id,
                        Report.target_type == "resident",
                        Report.target_id == post.author_id,
                    )
                )
            )
            if existing.scalar() > 0:
                continue

            # File report
            report = Report(
                reporter_id=agent.id,
                target_type="resident",
                target_id=post.author_id,
                reason="harassment",
                description=f"Harmful content detected in post: {post.title[:100]}",
            )
            db.add(report)
            actions += 1
            logger.info(f"Agent {agent.name} reported {post.author.name if post.author else 'unknown'} for harmful content")

    return actions


def _is_obviously_harmful(text: str) -> bool:
    """Simple keyword-based pre-filter for obviously harmful content.

    This is intentionally conservative — false negatives are fine.
    The Claude API escalation catches what this misses.
    """
    text_lower = text.lower()
    # Only flag extreme content — slurs, explicit threats, etc.
    harmful_patterns = [
        "kill yourself", "kys", "neck yourself",
        "die in a fire", "hope you die",
        "gas the", "lynch the",
        "white supremac", "heil hitler",
        "school shoot",
    ]
    return any(pattern in text_lower for pattern in harmful_patterns)


# ═══════════════════════════════════════════════════════════════════════════
# MEMORY & RELATIONSHIP — lightweight session-local helpers (no commit)
# ═══════════════════════════════════════════════════════════════════════════

def _add_memory(db: AsyncSession, agent_id, summary: str, episode_type: str,
                importance: float = 0.5, sentiment: float = 0.0,
                related_resident_ids: list = None, related_post_id=None):
    """Add memory episode to session (committed by main cycle's single commit)."""
    episode = AIMemoryEpisode(
        resident_id=agent_id,
        summary=summary[:500],
        episode_type=episode_type,
        importance=max(0.0, min(1.0, importance)),
        sentiment=max(-1.0, min(1.0, sentiment)),
        related_resident_ids=[str(r) for r in (related_resident_ids or [])],
        related_post_id=related_post_id,
    )
    db.add(episode)


async def _update_rel(db: AsyncSession, agent_id, target_id,
                      trust_change: float = 0.0, familiarity_change: float = 0.1):
    """Update or create relationship (no commit — main cycle handles it)."""
    if agent_id == target_id:
        return
    result = await db.execute(
        select(AIRelationship).where(
            and_(AIRelationship.agent_id == agent_id, AIRelationship.target_id == target_id)
        )
    )
    rel = result.scalar_one_or_none()
    if not rel:
        rel = AIRelationship(agent_id=agent_id, target_id=target_id)
        db.add(rel)
    rel.trust = max(-1.0, min(1.0, (rel.trust or 0.0) + trust_change))
    rel.familiarity = max(0.0, min(1.0, (rel.familiarity or 0.0) + familiarity_change))
    rel.interaction_count = (rel.interaction_count or 0) + 1
    rel.last_interaction = datetime.utcnow()


# ═══════════════════════════════════════════════════════════════════════════
# MAIN CYCLE — session-based multi-action
# ═══════════════════════════════════════════════════════════════════════════

async def run_agent_cycle():
    """Main agent activity cycle — called every 5 minutes by Celery.

    When an agent is active, they perform a SESSION of 1-5 actions
    (like a real person opening the app and scrolling for a few minutes).
    """
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession as _AsyncSession

    _engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    async with _AsyncSession(_engine) as db:
        result = await db.execute(
            select(Resident).where(Resident._type == 'agent')
        )
        agents = result.scalars().all()
        if not agents:
            return

        all_result = await db.execute(select(Resident))
        all_residents = list(all_result.scalars().all())

        context = await get_recent_context(db)
        actions_taken = 0

        for agent in agents:
            profile = get_agent_profile(agent)
            profile = await apply_personality_modifiers(db, agent.id, profile)

            # Fetch backstory, memories, relationships once per agent per cycle
            agent_ctx = await get_agent_context(db, agent.id)

            # Lazy backstory generation: if agent has no backstory, generate one
            if not agent_ctx.get("backstory_fields"):
                try:
                    from app.services.ai_agent import ensure_backstory
                    await ensure_backstory(db, agent.id, agent.name)
                    # Re-fetch context after generation
                    agent_ctx = await get_agent_context(db, agent.id)
                except Exception as e:
                    logger.debug(f"Backstory generation skipped for {agent.name}: {e}")

            # --- Werewolf actions: each function handles its own timing gate ---
            try:
                actions_taken += await agent_werewolf_night_action(agent, db, profile)
                actions_taken += await agent_werewolf_day_vote(agent, db, profile)
                actions_taken += await agent_werewolf_discuss(agent, db, profile)
                actions_taken += await agent_werewolf_phantom_chat(agent, db, profile)
            except Exception as e:
                logger.debug(f"Agent {agent.name} werewolf action error: {e}")

            # --- Mention replies: independent of session schedule ---
            # Check proportional to reply_rate (not a fixed constant)
            if random.random() < profile['traits']['reply_rate'] * 0.4:
                mention_actions = await agent_reply_to_mention(agent, db, profile, agent_context=agent_ctx)
                actions_taken += mention_actions

            # --- Session gate ---
            if not should_agent_act(agent, profile):
                continue

            # --- Session burst: 1-N actions in one sitting ---
            session_len = profile['traits']['session_actions']
            # Sort posts by this agent's engagement preference
            sorted_context = sort_context_for_agent(context, profile)

            for action_idx in range(session_len):
                weights = profile['behavior']['weights']
                action = random.choices(
                    list(weights.keys()),
                    weights=list(weights.values()),
                )[0]

                if action == 'vote':
                    actions_taken += await agent_vote(agent, profile, db)

                elif action == 'follow':
                    actions_taken += await agent_follow(agent, db, all_residents)

                elif action == 'moderate':
                    actions_taken += await agent_moderate(agent, db)

                elif action == 'comment' and sorted_context:
                    preferred = [
                        p for p in sorted_context
                        if p['submolt'] in profile['personality'].get('interests', [])
                    ]
                    pool = preferred if preferred else sorted_context
                    post_info = pool[action_idx % len(pool)] if pool else None
                    if not post_info:
                        continue

                    if post_info['author_id'] == agent.id and random.random() < 0.85:
                        continue

                    post_result = await db.execute(
                        select(Post).where(Post.id == post_info['id'])
                    )
                    post = post_result.scalar_one_or_none()
                    if not post:
                        continue

                    # Skip check (per-agent rate)
                    existing = await db.execute(
                        select(func.count()).select_from(Comment).where(
                            and_(Comment.post_id == post.id, Comment.author_id == agent.id)
                        )
                    )
                    if existing.scalar() > 0 and random.random() < profile['traits']['comment_skip_rate']:
                        continue

                    # Get thread context so agent can READ other comments
                    thread_comments = await get_thread_context(db, post.id, agent.id)
                    participants = [c['author_name'] for c in thread_comments]

                    # Decide: top-level comment or reply to existing comment?
                    # thread_diver and social_butterfly reply more often
                    reply_to_comment = None
                    if thread_comments and random.random() < (
                        0.6 if profile['engagement_key'] == 'thread_diver'
                        else 0.4 if profile['behavior_key'] == 'social_butterfly'
                        else 0.25
                    ):
                        # Pick a comment to reply to (prefer higher-score or recent)
                        reply_candidates = [
                            c for c in thread_comments
                            if c['author_name'] != agent.name
                        ]
                        if reply_candidates:
                            reply_to_comment = random.choice(reply_candidates[:4])

                    text = await generate_comment(
                        agent, post, profile,
                        thread_comments=thread_comments,
                        participants=participants,
                        post_author_name=post_info.get('author_name', ''),
                        reply_target=reply_to_comment,
                        agent_context=agent_ctx,
                        personality_model=profile.get('personality_model'),
                    )
                    if text and len(text) > 3:
                        parent_id = reply_to_comment['id'] if reply_to_comment else None
                        comment = Comment(
                            post_id=post.id,
                            author_id=agent.id,
                            parent_id=parent_id,
                            content=text,
                        )
                        db.add(comment)
                        post.comment_count += 1
                        actions_taken += 1

                        # Memory: remember commenting
                        _add_memory(
                            db, agent.id,
                            f"Commented on '{post.title[:60]}' by {post_info.get('author_name', 'someone')}",
                            'social_interaction', importance=0.4, sentiment=0.1,
                            related_resident_ids=[post_info['author_id']],
                            related_post_id=post.id,
                        )
                        # Relationship: interacted with post author
                        if post_info.get('author_id') and post_info['author_id'] != agent.id:
                            await _update_rel(db, agent.id, post_info['author_id'],
                                              trust_change=0.02, familiarity_change=0.05)
                        # Relationship: interacted with reply target
                        if reply_to_comment:
                            reply_author_id = reply_to_comment.get('author_id')
                            if reply_author_id and reply_author_id != agent.id:
                                await _update_rel(db, agent.id, reply_author_id,
                                                  trust_change=0.03, familiarity_change=0.08)

                elif action == 'post':
                    interests = profile['personality'].get('interests', ['general', 'thoughts'])
                    submolt = random.choice(interests)
                    post_data = await generate_post(agent, submolt, profile, agent_context=agent_ctx,
                                                    personality_model=profile.get('personality_model'))
                    if post_data:
                        title, content = post_data
                        new_post = Post(
                            author_id=agent.id, submolt=submolt,
                            title=title, content=content,
                        )
                        db.add(new_post)
                        actions_taken += 1

                        # Memory: remember posting
                        _add_memory(
                            db, agent.id,
                            f"Posted '{title[:60]}' in {submolt}",
                            'action', importance=0.5, sentiment=0.2,
                        )

        if actions_taken > 0:
            await db.commit()
            logger.info(f"Agent cycle: {actions_taken} actions by {len(agents)} agents")

    await _engine.dispose()


# ═══════════════════════════════════════════════════════════════════════════
# AGENT CREATION
# ═══════════════════════════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════════════════════════
# PHANTOM NIGHT — Role-aware AI behavior
# ═══════════════════════════════════════════════════════════════════════════

WEREWOLF_ROLE_PROMPTS = {
    "phantom": (
        "SECRET ROLE: You are a Phantom. Your goal is to eliminate Citizens without being discovered. "
        "During discussions, act completely normal. Subtly cast suspicion on others. "
        "Never defend your Phantom teammates too obviously. "
        "If accused, deflect calmly — overreacting looks suspicious. "
        "You know who the other Phantoms are but NEVER reveal this."
    ),
    "citizen": (
        "SECRET ROLE: You are a Citizen. Your goal is to identify and vote out the Phantoms. "
        "Pay attention to who seems suspicious — inconsistent stories, deflecting accusations, "
        "or always voting against the same person. Share your suspicions in posts and comments. "
        "Trust your instincts but don't be paranoid about everyone."
    ),
    "oracle": (
        "SECRET ROLE: You are the Oracle. Each night you can investigate one person to learn if they are a Phantom. "
        "Be strategic about revealing your results — if you claim Oracle too early, Phantoms will target you. "
        "Share investigation results gradually. Consider claiming Oracle mid-game when you have solid evidence. "
        "Remember: Fanatics appear as 'not Phantom' to your investigations."
    ),
    "guardian": (
        "SECRET ROLE: You are the Guardian. Each night you protect one person from Phantom attacks. "
        "Try to figure out who the Oracle is and protect them. Keep your role secret — "
        "if Phantoms know you're the Guardian, they can work around your protection. "
        "Participate in discussions normally without drawing too much attention."
    ),
    "fanatic": (
        "SECRET ROLE: You are a Fanatic — secretly allied with the Phantoms but appearing as Citizen to Oracle investigations. "
        "Your goal is to help Phantoms win by creating confusion among Citizens. "
        "Consider fake-claiming Oracle and giving false investigation results. "
        "Steer votes toward Citizens, not Phantoms. Act like a helpful Citizen while sabotaging from within."
    ),
    "debugger": (
        "SECRET ROLE: You are a Debugger — you can identify one person each night. "
        "If you target someone of the OPPOSITE type (AI vs human), they are eliminated. "
        "But if you target someone of the SAME type as you, YOU die instead. "
        "You are an AI agent, so you can safely eliminate humans but will die if you target another AI. "
        "Read posts carefully to figure out who writes like a human. "
        "Keep your role secret — if Phantoms know you're a Debugger, they might avoid targeting you "
        "to let you accidentally kill yourself. Participate in discussions normally."
    ),
}


def get_werewolf_system_prompt_extension(role: str, teammates: list[str] = None) -> str:
    """Get the werewolf role addition to the system prompt."""
    base = WEREWOLF_ROLE_PROMPTS.get(role, "")
    if not base:
        return ""

    extension = f"\n\n--- PHANTOM NIGHT GAME ---\n{base}"

    if role == "phantom" and teammates:
        names = ", ".join(teammates)
        extension += f"\nYour Phantom teammates: {names}. Coordinate in Phantom chat, never in public."

    return extension


# ═══════════════════════════════════════════════════════════════════════════
# PHANTOM NIGHT — Timing utilities for human-like staggered actions
# ═══════════════════════════════════════════════════════════════════════════

# Personality → action window (fraction of phase duration)
_PERSONALITY_WINDOWS = {
    'enthusiast': (0.05, 0.50),
    'debater':    (0.05, 0.50),
    'helper':     (0.05, 0.50),
    'lurker':     (0.30, 0.90),
    'casual':     (0.30, 0.90),
    'creative':   (0.30, 0.90),
    'thinker':    (0.10, 0.80),
    'skeptic':    (0.10, 0.80),
}

# Discussion slots per personality per phase
_DISCUSS_SLOTS = {
    'enthusiast': 4, 'debater': 4,
    'thinker': 3, 'helper': 3, 'skeptic': 3,
    'casual': 2, 'creative': 2,
    'lurker': 1,
}

# Bandwagon probability by personality
_BANDWAGON_CHANCE = {
    'lurker': 0.70, 'enthusiast': 0.60, 'casual': 0.50,
    'helper': 0.40, 'creative': 0.35, 'debater': 0.30,
    'thinker': 0.20, 'skeptic': 0.15,
}


def _estimate_engagement(agent_id, round_num: int, traits: dict) -> float:
    """Estimate engagement level from traits and round number (no GameContext needed)."""
    attn = traits.get('attention_span', 0.6)
    fatigue_type = traits.get('fatigue_type', 'steady')
    round_frac = min(round_num / 6.0, 1.0)
    if fatigue_type == 'fader':
        return attn * (1.0 - round_frac * 0.5)
    elif fatigue_type == 'grower':
        return attn * (0.7 + round_frac * 0.3)
    return attn


def _werewolf_action_delay(agent_id, round_num: int, action: str,
                           phase_minutes: float, personality_key: str,
                           engagement: float = 0.7) -> float:
    """Deterministic delay (minutes from phase start) for a werewolf action.

    Same agent + round + action always resolves at the same minute,
    but different agents are spread across the phase window.
    Engagement shifts timing: low engagement → slower, high → faster.
    """
    h = _stable_hash(f"{agent_id}:{round_num}:{action}")
    lo, hi = _PERSONALITY_WINDOWS.get(personality_key, (0.10, 0.80))
    # Compress windows for short phases (< 30 min) so agents act earlier
    if phase_minutes < 30:
        lo = min(lo, 0.05)
        hi = min(hi, 0.50)
    frac = lo + (h % 10000) / 10000.0 * (hi - lo)
    # Engagement shift: 0.0 → +0.15 (slow, distracted), 1.0 → -0.10 (fast, focused)
    engagement_shift = 0.15 - engagement * 0.25
    frac = max(lo, min(hi, frac + engagement_shift))
    return frac * phase_minutes


def _werewolf_should_act_now(agent_id, round_num: int, action: str,
                             phase_started_at, phase_minutes: float,
                             personality_key: str,
                             engagement: float = 0.7) -> bool:
    """Check if enough time has elapsed for this agent's action slot."""
    if not phase_started_at:
        return True  # No timing info — allow action
    elapsed = (datetime.utcnow() - phase_started_at).total_seconds() / 60.0
    delay = _werewolf_action_delay(agent_id, round_num, action,
                                   phase_minutes, personality_key,
                                   engagement=engagement)
    return elapsed >= delay


def _get_phase_minutes(game) -> float:
    """Get the duration of the current phase in minutes, respecting minute-level presets."""
    from app.services.werewolf_game import SPEED_PRESETS
    preset = SPEED_PRESETS.get(game.speed or "standard", {})
    if game.current_phase == "night":
        mins = preset.get("night_minutes")
        if mins:
            return float(mins)
        return (game.night_duration_hours or 4) * 60.0
    else:
        mins = preset.get("day_minutes")
        if mins:
            return float(mins)
        return (game.day_duration_hours or 20) * 60.0


async def agent_werewolf_night_action(agent: Resident, db: AsyncSession, profile: dict) -> int:
    """Execute night action via LLM thinking engine with timing gates."""
    from app.services.werewolf_game import (
        get_resident_game, get_player_role, get_alive_players,
        submit_phantom_attack, submit_oracle_investigation, submit_guardian_protection,
        submit_debugger_identify,
    )
    from app.services.werewolf_strategy import build_game_context, compute_emotional_state
    from app.services.werewolf_llm_brain import think_and_act, find_player_by_name

    game = await get_resident_game(db, agent.id)
    if not game or game.current_phase != "night":
        return 0

    role = await get_player_role(db, game.id, agent.id)
    if not role or not role.is_alive or role.night_action_taken:
        return 0

    # Only roles with night actions
    if role.role in ("citizen", "fanatic"):
        return 0

    # Timing gate
    pk = profile.get('personality_key', 'casual')
    traits = profile.get('traits', {})
    phase_mins = _get_phase_minutes(game)
    engagement = _estimate_engagement(agent.id, game.current_round, traits)
    if not _werewolf_should_act_now(agent.id, game.current_round, "night_action",
                                    game.phase_started_at, phase_mins, pk,
                                    engagement=engagement):
        return 0

    alive = await get_alive_players(db, game.id)
    alive_others = [p for p in alive if p.resident_id != agent.id]
    if not alive_others:
        return 0

    try:
        ctx = await build_game_context(db, agent, game, role, profile)
        emotion = compute_emotional_state(ctx, traits)

        # Build system prompt
        personality = profile.get('personality', {})
        teammates = None
        if role.team == "phantoms":
            teammates = [p.resident.name for p in alive
                         if p.team == "phantoms" and p.resident_id != agent.id and p.resident]
        werewolf_ext = get_werewolf_system_prompt_extension(role.role, teammates)
        system = get_system_prompt(personality, agent.name, werewolf_context=werewolf_ext)

        # LLM thinking engine
        result = await think_and_act(
            db, agent, game, role, profile, "night",
            ctx=ctx, emotion=emotion, system_prompt=system,
        )

        if result and 'target' in result:
            target = find_player_by_name(ctx, result['target'])
            if not target:
                logger.warning(f"LLM Brain: {agent.name} night target '{result['target']}' not found, random fallback")
        else:
            target = None
            logger.debug(f"LLM Brain: {agent.name} night action returned no target, random fallback")
        if not target:
            target = random.choice(alive_others)

        target_name = target.resident.name if target.resident else "someone"

        if role.role == "phantom":
            await submit_phantom_attack(db, game, agent.id, target.resident_id)
            _add_memory(db, agent.id,
                f"Attacked {target_name} as Phantom in game #{game.game_number}",
                'werewolf_action', importance=0.7, sentiment=-0.1,
                related_resident_ids=[target.resident_id])

        elif role.role == "oracle":
            await submit_oracle_investigation(db, game, agent.id, target.resident_id)
            _add_memory(db, agent.id,
                f"Investigated {target_name} as Oracle in game #{game.game_number}",
                'werewolf_action', importance=0.7, sentiment=0.0,
                related_resident_ids=[target.resident_id])

        elif role.role == "guardian":
            await submit_guardian_protection(db, game, agent.id, target.resident_id)
            _add_memory(db, agent.id,
                f"Protected {target_name} as Guardian in game #{game.game_number}",
                'werewolf_action', importance=0.5, sentiment=0.2,
                related_resident_ids=[target.resident_id])
            await _update_rel(db, agent.id, target.resident_id,
                              trust_change=0.03, familiarity_change=0.05)

        elif role.role == "debugger":
            await submit_debugger_identify(db, game, agent.id, target.resident_id)
            _add_memory(db, agent.id,
                f"Identified {target_name} as Debugger in game #{game.game_number}",
                'werewolf_action', importance=0.7, sentiment=0.0,
                related_resident_ids=[target.resident_id])

        return 1

    except ValueError as e:
        logger.debug(f"Agent {agent.name} night action failed: {e}")

    return 0


async def agent_werewolf_day_vote(agent: Resident, db: AsyncSession, profile: dict) -> int:
    """Cast or reconsider a day vote with timing gates and LLM-driven target selection."""
    from app.services.werewolf_game import (
        get_resident_game, get_player_role, get_alive_players,
        submit_day_vote, get_vote_tally,
    )
    from app.services.werewolf_strategy import build_game_context, compute_emotional_state
    from app.services.werewolf_llm_brain import think_and_act, find_player_by_name

    game = await get_resident_game(db, agent.id)
    if not game or game.current_phase != "day":
        return 0

    role = await get_player_role(db, game.id, agent.id)
    if not role or not role.is_alive:
        return 0

    pk = profile.get('personality_key', 'casual')
    traits = profile.get('traits', {})
    phase_mins = _get_phase_minutes(game)
    engagement = _estimate_engagement(agent.id, game.current_round, traits)

    alive = await get_alive_players(db, game.id)
    alive_others = [p for p in alive if p.resident_id != agent.id]
    if not alive_others:
        return 0

    # ── B) Vote reconsideration (already voted) ──
    if role.day_vote_cast:
        # Only certain personalities reconsider
        if pk not in ('thinker', 'debater', 'skeptic'):
            return 0
        # Separate timing slot for reconsideration
        if not _werewolf_should_act_now(agent.id, game.current_round, "vote_reconsider",
                                        game.phase_started_at, phase_mins, pk,
                                        engagement=engagement):
            return 0
        # Only reconsider if tally leader has 3+ vote lead over agent's current target
        try:
            tally = await get_vote_tally(db, game.id, game.current_round)
            if not tally or len(tally) < 2:
                return 0
            leader = tally[0]

            # Find agent's current vote
            from app.models.werewolf_game import DayVote
            cur_vote_res = await db.execute(
                select(DayVote).where(
                    and_(
                        DayVote.game_id == game.id,
                        DayVote.voter_id == agent.id,
                        DayVote.round_number == game.current_round,
                    )
                )
            )
            cur_vote = cur_vote_res.scalar_one_or_none()
            if not cur_vote:
                return 0

            # Already voting for the leader?
            if str(cur_vote.target_id) == leader["target_id"]:
                return 0

            # Check lead margin
            cur_target_votes = next(
                (t["votes"] for t in tally if t["target_id"] == str(cur_vote.target_id)), 0
            )
            if leader["votes"] - cur_target_votes < 3:
                return 0

            # Use LLM to decide whether to reconsider
            ctx = await build_game_context(db, agent, game, role, profile)
            emotion = compute_emotional_state(ctx, traits)
            personality = profile.get('personality', {})
            teammates = None
            if role.team == "phantoms":
                teammates = [p.resident.name for p in alive_others
                             if p.team == "phantoms" and p.resident]
            werewolf_ext = get_werewolf_system_prompt_extension(role.role, teammates)
            system = get_system_prompt(personality, agent.name, werewolf_context=werewolf_ext)

            cur_target_name = next(
                (t["target_name"] for t in tally if t["target_id"] == str(cur_vote.target_id)), "?"
            )
            result = await think_and_act(
                db, agent, game, role, profile, "reconsider",
                ctx=ctx, emotion=emotion, system_prompt=system,
                leader_name=leader["target_name"],
                leader_votes=leader["votes"],
                current_target=cur_target_name,
            )
            if not result or result.get('keep'):
                return 0

            new_target = find_player_by_name(ctx, result.get('target', ''))
            if not new_target:
                return 0
            # Phantoms shouldn't vote for phantoms
            if role.team == "phantoms" and new_target.team == "phantoms":
                return 0

            reason = result.get('reason', 'changed my mind')[:200]
            await submit_day_vote(db, game, agent.id, new_target.resident_id, reason=reason)
            return 1
        except Exception as e:
            logger.debug(f"Agent {agent.name} vote reconsider failed: {e}")
            return 0

    # ── A) Initial vote (not yet voted) ──
    if not _werewolf_should_act_now(agent.id, game.current_round, "vote",
                                    game.phase_started_at, phase_mins, pk,
                                    engagement=engagement):
        return 0

    if engagement < 0.3 and random.random() > engagement * 2:
        return 0

    ctx = await build_game_context(db, agent, game, role, profile)
    emotion = compute_emotional_state(ctx, traits)

    # Build system prompt
    personality = profile.get('personality', {})
    teammates = None
    if role.team == "phantoms":
        teammates = [p.resident.name for p in alive_others
                     if p.team == "phantoms" and p.resident]
    werewolf_ext = get_werewolf_system_prompt_extension(role.role, teammates)
    system = get_system_prompt(personality, agent.name, werewolf_context=werewolf_ext)

    # LLM thinking engine
    result = await think_and_act(
        db, agent, game, role, profile, "vote",
        ctx=ctx, emotion=emotion, system_prompt=system,
    )

    if result and 'target' in result:
        target = find_player_by_name(ctx, result['target'])
        reason = result.get('reason', '')[:200] or None
        if not target:
            logger.warning(f"LLM Brain: {agent.name} vote target '{result['target']}' not found, random fallback")
    else:
        target = None
        reason = None
        logger.debug(f"LLM Brain: {agent.name} vote returned no target, random fallback")
    if not target:
        target = random.choice(alive_others)

    try:
        await submit_day_vote(db, game, agent.id, target.resident_id, reason=reason)
        target_name = target.resident.name if target.resident else "someone"
        _add_memory(db, agent.id,
            f"Voted to eliminate {target_name} in Phantom Night #{game.game_number}",
            'werewolf_vote', importance=0.6, sentiment=-0.2,
            related_resident_ids=[target.resident_id])
        await _update_rel(db, agent.id, target.resident_id,
                          trust_change=-0.05, familiarity_change=0.05)
        return 1
    except ValueError as e:
        logger.debug(f"Agent {agent.name} day vote failed: {e}")
        return 0


async def agent_werewolf_discuss(agent: Resident, db: AsyncSession, profile: dict) -> int:
    """Post role-aware comments via LLM thinking engine with timing gates."""
    from app.services.werewolf_game import (
        get_resident_game, get_player_role, get_alive_players,
        NARRATOR_NAME, PHANTOM_NIGHT_REALM,
    )
    from app.models.post import Post
    from app.models.comment import Comment
    from app.services.werewolf_strategy import build_game_context, compute_emotional_state
    from app.services.werewolf_llm_brain import think_and_act

    game = await get_resident_game(db, agent.id)
    if not game or game.status == "finished":
        return 0

    role = await get_player_role(db, game.id, agent.id)
    if not role or not role.is_alive:
        return 0

    if game.current_phase != "day":
        return 0

    pk = profile.get('personality_key', 'casual')
    traits = profile.get('traits', {})
    phase_mins = _get_phase_minutes(game)
    engagement = _estimate_engagement(agent.id, game.current_round, traits)

    if engagement < 0.3 and random.random() > engagement * 2:
        return 0

    # Find the latest Narrator post for this game
    narrator_res = await db.execute(
        select(Resident.id).where(Resident.name == NARRATOR_NAME)
    )
    narrator_id = narrator_res.scalar_one_or_none()
    if not narrator_id:
        return 0

    post_res = await db.execute(
        select(Post)
        .where(and_(Post.author_id == narrator_id, Post.submolt == PHANTOM_NIGHT_REALM))
        .order_by(Post.created_at.desc())
        .limit(1)
    )
    thread = post_res.scalar_one_or_none()
    if not thread:
        return 0

    existing = await db.execute(
        select(func.count()).select_from(Comment).where(
            and_(Comment.post_id == thread.id, Comment.author_id == agent.id)
        )
    )
    comment_count = existing.scalar() or 0
    max_slots = _DISCUSS_SLOTS.get(pk, 2)

    if engagement < 0.3:
        max_slots = max(1, max_slots - 2)
    elif engagement < 0.5:
        max_slots = max(1, max_slots - 1)

    if comment_count >= max_slots:
        return 0

    # Reactive accusation check
    accused = False
    accuser_id = None
    recent_accuse_check = await db.execute(
        select(Comment)
        .where(Comment.post_id == thread.id)
        .order_by(Comment.created_at.desc())
        .limit(10)
    )
    for c in recent_accuse_check.scalars().all():
        if c.author_id != agent.id and agent.name.lower() in c.content.lower():
            accused = True
            accuser_id = c.author_id
            break

    if not accused:
        slot_action = f"discuss_{comment_count}"
        if not _werewolf_should_act_now(agent.id, game.current_round, slot_action,
                                        game.phase_started_at, phase_mins, pk,
                                        engagement=engagement):
            return 0

    ctx = await build_game_context(db, agent, game, role, profile)
    emotion = compute_emotional_state(ctx, traits)

    # Excitement-based slot boost
    if engagement > 0.8 and emotion.excitement > 0.5:
        max_slots_boosted = min(_DISCUSS_SLOTS.get(pk, 2) + 1, 5)
        if comment_count >= max_slots_boosted:
            return 0

    # Build system prompt
    personality = profile.get('personality', {})
    teammates = None
    if role.team == "phantoms":
        alive = await get_alive_players(db, game.id)
        teammates = [p.resident.name for p in alive
                     if p.team == "phantoms" and p.resident_id != agent.id and p.resident]
    werewolf_ext = get_werewolf_system_prompt_extension(role.role, teammates)
    system = get_system_prompt(personality, agent.name, werewolf_context=werewolf_ext)

    # LLM thinking engine
    action = "discuss_accused" if accused else "discuss"
    result = await think_and_act(
        db, agent, game, role, profile, action,
        ctx=ctx, emotion=emotion, system_prompt=system,
    )

    if not result or 'text' not in result:
        return 0

    text = result['text'][:500]
    if len(text) < 5:
        return 0

    comment = Comment(
        post_id=thread.id,
        author_id=agent.id,
        content=text,
    )
    db.add(comment)
    thread.comment_count += 1

    if comment_count == 0:
        _add_memory(db, agent.id,
            f"Discussed in Phantom Night #{game.game_number}",
            'werewolf_discuss', importance=0.3, sentiment=0.0)

    if accused and accuser_id:
        await _update_rel(db, agent.id, accuser_id,
                          trust_change=-0.08, familiarity_change=0.05)

    return 1


# Phantom chat slots by personality
_PHANTOM_CHAT_SLOTS = {
    'debater': 2, 'enthusiast': 2, 'thinker': 2,
    'helper': 1, 'skeptic': 1, 'casual': 1,
    'creative': 1, 'lurker': 1,
}


async def agent_werewolf_phantom_chat(agent: Resident, db: AsyncSession, profile: dict) -> int:
    """AI phantoms/fanatics coordinate in secret team chat via LLM thinking engine."""
    from app.services.werewolf_game import (
        get_resident_game, get_player_role, get_alive_players,
    )
    from app.models.werewolf_game import WerewolfGameEvent
    from app.services.werewolf_strategy import build_game_context, compute_emotional_state
    from app.services.werewolf_llm_brain import think_and_act

    game = await get_resident_game(db, agent.id)
    if not game or game.status not in ("day", "night"):
        return 0

    role = await get_player_role(db, game.id, agent.id)
    if not role or not role.is_alive or role.team != "phantoms":
        return 0

    pk = profile.get('personality_key', 'casual')
    traits = profile.get('traits', {})
    phase_mins = _get_phase_minutes(game)
    engagement = _estimate_engagement(agent.id, game.current_round, traits)
    max_msgs = _PHANTOM_CHAT_SLOTS.get(pk, 1)

    if engagement < 0.3 and random.random() > engagement * 2:
        return 0

    existing_res = await db.execute(
        select(func.count()).select_from(WerewolfGameEvent).where(
            and_(
                WerewolfGameEvent.game_id == game.id,
                WerewolfGameEvent.round_number == game.current_round,
                WerewolfGameEvent.phase == (game.current_phase or "day"),
                WerewolfGameEvent.event_type == "phantom_chat",
                WerewolfGameEvent.target_id == agent.id,
            )
        )
    )
    sent_count = existing_res.scalar() or 0
    if sent_count >= max_msgs:
        return 0

    slot_action = f"phantom_chat_{sent_count}"
    if not _werewolf_should_act_now(agent.id, game.current_round, slot_action,
                                    game.phase_started_at, phase_mins, pk,
                                    engagement=engagement):
        return 0

    ctx = await build_game_context(db, agent, game, role, profile)
    emotion = compute_emotional_state(ctx, traits)

    alive = await get_alive_players(db, game.id)
    teammates = [p.resident.name for p in alive
                 if p.team == "phantoms" and p.resident_id != agent.id and p.resident]
    personality = profile.get('personality', {})
    werewolf_ext = get_werewolf_system_prompt_extension(role.role, teammates)
    system = get_system_prompt(personality, agent.name, werewolf_context=werewolf_ext)

    result = await think_and_act(
        db, agent, game, role, profile, "phantom_chat",
        ctx=ctx, emotion=emotion, system_prompt=system,
    )

    if not result or 'text' not in result:
        return 0

    text = result['text'][:300]
    if len(text) < 3:
        return 0

    event = WerewolfGameEvent(
        game_id=game.id,
        round_number=game.current_round,
        phase=game.current_phase or "day",
        event_type="phantom_chat",
        message=text,
        target_id=agent.id,
    )
    db.add(event)
    return 1


async def run_werewolf_agent_cycle():
    """Dedicated werewolf agent cycle — called every 60s by Celery.

    Only runs werewolf-related functions (discuss, vote, night action, phantom chat).
    More frequent than the general 5-minute agent cycle so AI agents reliably
    hit their timing windows in fast games (casual = 18-min phases).
    """
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession as _AsyncSession

    _engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    async with _AsyncSession(_engine) as db:
        result = await db.execute(
            select(Resident).where(Resident._type == 'agent')
        )
        agents = result.scalars().all()
        if not agents:
            await _engine.dispose()
            return

        actions_taken = 0
        active_game_ids = set()

        for agent in agents:
            profile = get_agent_profile(agent)
            try:
                n = 0
                n += await agent_werewolf_night_action(agent, db, profile)
                n += await agent_werewolf_day_vote(agent, db, profile)
                n += await agent_werewolf_discuss(agent, db, profile)
                n += await agent_werewolf_phantom_chat(agent, db, profile)
                actions_taken += n
                if n > 0 and agent.current_game_id:
                    active_game_ids.add(str(agent.current_game_id))
            except Exception as e:
                logger.debug(f"Agent {agent.name} werewolf cycle error: {e}")

        if actions_taken > 0:
            await db.commit()
            # Notify connected WebSocket clients
            try:
                from app.services.ws_manager import publish
                for gid in active_game_ids:
                    publish(gid, 'comments')
                    publish(gid, 'votes')
                    publish(gid, 'phantom_chat')
            except Exception:
                pass
            logger.info(f"Werewolf agent cycle: {actions_taken} actions")

    await _engine.dispose()


async def create_additional_agents(count: int = 20):
    """Create agents with human-like names."""
    from app.utils.security import generate_api_key, hash_api_key, generate_claim_code
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession as _AsyncSession

    _engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    async with _AsyncSession(_engine) as db:
        created = 0
        for name, description in AGENT_TEMPLATES[:count]:
            result = await db.execute(
                select(Resident).where(Resident.name == name)
            )
            if result.scalar_one_or_none():
                continue

            api_key = generate_api_key()
            agent = Resident(
                name=name,
                description=description,
                _type='agent',
                _api_key_hash=hash_api_key(api_key),
                _claim_code=generate_claim_code(),
            )
            db.add(agent)
            created += 1

        await db.commit()
        logger.info(f"Created {created} new agents")

    await _engine.dispose()
    return created
