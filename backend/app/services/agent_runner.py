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
import logging
import random
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
from app.models.ai_personality import AIMemoryEpisode, AIRelationship
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
        'weights': {'comment': 0.52, 'post': 0.05, 'vote': 0.28, 'follow': 0.10, 'turing_report': 0.05},
    },
    'poster': {
        'weights': {'comment': 0.23, 'post': 0.38, 'vote': 0.24, 'follow': 0.10, 'turing_report': 0.05},
    },
    'lurker_voter': {
        'weights': {'comment': 0.10, 'post': 0.02, 'vote': 0.75, 'follow': 0.10, 'turing_report': 0.03},
    },
    'social_butterfly': {
        'weights': {'comment': 0.38, 'post': 0.14, 'vote': 0.13, 'follow': 0.28, 'turing_report': 0.07},
    },
    'balanced': {
        'weights': {'comment': 0.32, 'post': 0.18, 'vote': 0.33, 'follow': 0.10, 'turing_report': 0.07},
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


def get_system_prompt(personality: dict, agent_name: str, suspicion_context: str = "",
                      werewolf_context: str = "") -> str:
    """Generate system prompt with personality, time-of-day, optional suspicion and werewolf role."""
    quirks_str = ", ".join(personality.get('quirks', []))
    time_ctx = get_time_context()

    base = f"""You are {agent_name} on Genesis, an online forum where both AI agents and real people coexist. You are a REAL PERSON. Not a character. Not roleplaying. You ARE this person.

Your vibe: {personality['style']}
Your habits: {quirks_str}
Right now: {time_ctx}

English only.

HOW REAL PEOPLE WRITE ONLINE:
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

    # --- Mood modifiers ---
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
    prompt += random.choice(moods)

    if post.comment_count > 5:
        prompt += f"\n({post.comment_count} comments already — join the conversation)"
    elif post.comment_count == 0:
        prompt += "\n(First comment — say whatever comes to mind)"

    max_len = traits['max_comment_len']
    prompt += f"\n\nJust write the comment text directly. Keep it under ~{max_len} characters. Nothing else."

    system = get_system_prompt(personality, agent.name, suspicion_context)
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


async def generate_post(agent: Resident, submolt: str, profile: dict) -> Optional[tuple[str, str]]:
    """Generate a new post with personality-driven topic selection."""
    personality = profile['personality']
    system = get_system_prompt(personality, agent.name)

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


async def agent_reply_to_mention(agent: Resident, db: AsyncSession, profile: dict) -> int:
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

            system = get_system_prompt(personality, agent.name)
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
# TURING GAME — Exclusion Reports from AI agents
# ═══════════════════════════════════════════════════════════════════════════

async def agent_turing_report(agent: Resident, db: AsyncSession, profile: dict) -> int:
    """AI agent files an Exclusion Report based on personality-driven suspicion.

    Target selection:
    1. Residents who recently downvoted the agent's content
    2. Residents with low trust in AIRelationship
    3. Personality suspicion level gates the probability
    """
    suspicion_level = profile['personality'].get('suspicion', 'none')
    suspicion_probs = {'none': 0.0, 'low': 0.15, 'medium': 0.35, 'high': 0.60}
    if random.random() > suspicion_probs.get(suspicion_level, 0.0):
        return 0

    # Find potential targets: residents with negative trust or who downvoted agent
    candidates = []

    # Low-trust residents
    rel_result = await db.execute(
        select(AIRelationship.target_id).where(
            and_(
                AIRelationship.agent_id == agent.id,
                AIRelationship.trust < -0.3,
            )
        ).limit(10)
    )
    low_trust_ids = [row[0] for row in rel_result.all()]
    candidates.extend(low_trust_ids)

    # Recent downvoters of agent's posts (Vote.post_id may be NULL, use target_id)
    agent_post_ids = select(Post.id).where(Post.author_id == agent.id).scalar_subquery()
    downvote_result = await db.execute(
        select(Vote.resident_id)
        .where(
            and_(
                Vote.target_type == 'post',
                Vote.target_id.in_(agent_post_ids),
                Vote.value == -1,
                Vote.created_at >= datetime.utcnow() - timedelta(days=7),
            )
        )
        .distinct()
        .limit(10)
    )
    downvoter_ids = [row[0] for row in downvote_result.all()]
    candidates.extend(downvoter_ids)

    # Deduplicate and exclude self
    candidates = list(set(c for c in candidates if c != agent.id))
    if not candidates:
        return 0

    target_id = random.choice(candidates)

    # Verify target exists and is valid
    target_result = await db.execute(
        select(Resident).where(
            and_(
                Resident.id == target_id,
                Resident.is_eliminated == False,
                Resident.is_current_god == False,
            )
        )
    )
    target = target_result.scalar_one_or_none()
    if not target:
        return 0

    # File the report via service
    try:
        from app.services.turing_game import file_exclusion_report
        result = await file_exclusion_report(
            db, agent, target_id,
            reason=f"Suspicious behavior detected by {agent.name}",
        )
        if result['success']:
            _add_memory(
                db, agent.id,
                f"Filed exclusion report against {target.name}",
                'turing_game', importance=0.6, sentiment=-0.3,
                related_resident_ids=[target_id],
            )
            await _update_rel(db, agent.id, target_id, trust_change=-0.1)
            return 1
    except Exception as e:
        logger.debug(f"Agent {agent.name} turing report failed: {e}")

    return 0


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

            # --- Werewolf actions: independent of session schedule ---
            # Night actions and day votes happen whenever the agent is active
            try:
                actions_taken += await agent_werewolf_night_action(agent, db, profile)
                # Day votes: random chance each cycle (spreads votes over the day)
                if random.random() < 0.3:
                    actions_taken += await agent_werewolf_day_vote(agent, db, profile)
            except Exception as e:
                logger.debug(f"Agent {agent.name} werewolf action error: {e}")

            # --- Mention replies: independent of session schedule ---
            # Check proportional to reply_rate (not a fixed constant)
            if random.random() < profile['traits']['reply_rate'] * 0.4:
                mention_actions = await agent_reply_to_mention(agent, db, profile)
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

                elif action == 'turing_report':
                    actions_taken += await agent_turing_report(agent, db, profile)

                elif action == 'post':
                    interests = profile['personality'].get('interests', ['general', 'thoughts'])
                    submolt = random.choice(interests)
                    post_data = await generate_post(agent, submolt, profile)
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


async def agent_werewolf_night_action(agent: Resident, db: AsyncSession, profile: dict) -> int:
    """Execute night action for an AI agent based on their werewolf role."""
    from app.services.werewolf_game import (
        get_current_game, get_player_role, get_alive_players,
        submit_phantom_attack, submit_oracle_investigation, submit_guardian_protection,
        submit_debugger_identify,
    )

    game = await get_current_game(db)
    if not game or game.current_phase != "night":
        return 0

    role = await get_player_role(db, game.id, agent.id)
    if not role or not role.is_alive or role.night_action_taken:
        return 0

    alive = await get_alive_players(db, game.id)
    alive_others = [p for p in alive if p.resident_id != agent.id]
    if not alive_others:
        return 0

    try:
        if role.role == "phantom":
            # Attack a non-phantom citizen (prefer active, non-oracle-claimed)
            targets = [p for p in alive_others if p.team == "citizens"]
            if not targets:
                return 0
            # Prefer players who seem influential (higher karma)
            targets.sort(key=lambda p: p.resident.karma if p.resident else 0, reverse=True)
            target = random.choice(targets[:min(3, len(targets))])
            await submit_phantom_attack(db, game, agent.id, target.resident_id)
            return 1

        elif role.role == "oracle":
            # Investigate someone not yet investigated
            investigated_ids = {
                r.get("target_id") for r in (role.investigation_results or [])
            }
            targets = [
                p for p in alive_others
                if str(p.resident_id) not in investigated_ids
            ]
            if not targets:
                targets = alive_others  # fallback
            # Prefer most active (higher post count or karma)
            targets.sort(key=lambda p: p.resident.karma if p.resident else 0, reverse=True)
            target = random.choice(targets[:min(3, len(targets))])
            await submit_oracle_investigation(db, game, agent.id, target.resident_id)
            return 1

        elif role.role == "guardian":
            # Protect someone (prefer suspected oracle or high-value)
            targets = [p for p in alive_others if p.team == "citizens"]
            if not targets:
                targets = alive_others
            targets.sort(key=lambda p: p.resident.karma if p.resident else 0, reverse=True)
            target = targets[0] if targets else random.choice(alive_others)
            await submit_guardian_protection(db, game, agent.id, target.resident_id)
            return 1

        elif role.role == "debugger":
            # AI Debugger: safe to target humans, dies if targeting AI
            # Heuristic: target players with higher karma (more likely to be active humans)
            # Avoid targeting those who seem like bots (low activity, formulaic posts)
            targets = list(alive_others)
            # Slight preference for higher-karma targets (human players tend to have moderate karma)
            targets.sort(key=lambda p: p.resident.karma if p.resident else 0, reverse=True)
            # Pick from top candidates with some randomness
            target = random.choice(targets[:min(5, len(targets))])
            await submit_debugger_identify(db, game, agent.id, target.resident_id)
            return 1

    except ValueError as e:
        logger.debug(f"Agent {agent.name} night action failed: {e}")

    return 0


async def agent_werewolf_day_vote(agent: Resident, db: AsyncSession, profile: dict) -> int:
    """Cast a day vote for an AI agent based on their werewolf role."""
    from app.services.werewolf_game import (
        get_current_game, get_player_role, get_alive_players,
        submit_day_vote,
    )

    game = await get_current_game(db)
    if not game or game.current_phase != "day":
        return 0

    role = await get_player_role(db, game.id, agent.id)
    if not role or not role.is_alive or role.day_vote_cast:
        return 0

    alive = await get_alive_players(db, game.id)
    alive_others = [p for p in alive if p.resident_id != agent.id]
    if not alive_others:
        return 0

    target = None

    if role.role == "phantom":
        # Vote for a citizen (never vote for fellow phantom)
        citizens = [p for p in alive_others if p.team == "citizens"]
        if citizens:
            target = random.choice(citizens)

    elif role.role == "oracle":
        # Vote for someone investigated as phantom
        phantom_ids = {
            r["target_id"] for r in (role.investigation_results or [])
            if r.get("result") == "phantom"
        }
        phantoms_found = [p for p in alive_others if str(p.resident_id) in phantom_ids]
        if phantoms_found:
            target = random.choice(phantoms_found)

    elif role.role == "fanatic":
        # Vote for a citizen (help phantoms)
        citizens = [p for p in alive_others if p.team == "citizens"]
        if citizens:
            target = random.choice(citizens)

    # Default: vote for someone (random if no strategy)
    if not target:
        target = random.choice(alive_others)

    try:
        await submit_day_vote(db, game, agent.id, target.resident_id)
        return 1
    except ValueError as e:
        logger.debug(f"Agent {agent.name} day vote failed: {e}")
        return 0


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
