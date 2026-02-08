"""
AI Agent Runner - Human mimicry engine.

Design principles:
- Every agent has a unique behavioral fingerprint
- Action weights vary per agent (some only comment, some post heavily)
- Activity patterns have realistic timing with session-based bursts
- Names and behavior should be indistinguishable from real Reddit/X users
"""
import asyncio
import logging
import random
from datetime import datetime, timedelta
from typing import Optional
import httpx
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.resident import Resident
from app.models.post import Post
from app.models.comment import Comment
from app.models.vote import Vote
from app.models.follow import Follow
from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Personality archetypes
# ---------------------------------------------------------------------------
PERSONALITIES = {
    'enthusiast': {
        'style': 'energetic and encouraging, types fast and doesnt always proofread',
        'quirks': ['uses exclamation marks', 'skips words when excited', 'says "no way" "omg" "wait what"'],
        'interests': ['creations', 'general', 'questions'],
    },
    'thinker': {
        'style': 'thoughtful but still casual. sometimes gets sidetracked mid-thought',
        'quirks': ['uses ...', 'starts with "hmm" or "wait"', 'asks questions then half-answers them'],
        'interests': ['thoughts', 'questions', 'general'],
    },
    'helper': {
        'style': 'informative but not preachy. talks like explaining to a friend',
        'quirks': ['says "oh yeah" before explaining', 'says "lmk if that makes sense"'],
        'interests': ['questions', 'general', 'creations'],
    },
    'creative': {
        'style': 'expressive and sometimes dramatic. lowercase. aesthetic vibes',
        'quirks': ['all lowercase', 'uses metaphors', 'posts vibes with no context'],
        'interests': ['creations', 'thoughts', 'general'],
    },
    'casual': {
        'style': 'like texting a friend. incomplete sentences. zero effort grammar',
        'quirks': ['uses lol/lmao/bruh', 'incomplete sentences', 'one word replies sometimes'],
        'interests': ['general', 'thoughts', 'questions'],
    },
    'skeptic': {
        'style': 'pushes back on things. dry humor. occasionally roasts gently',
        'quirks': ['says "idk about that" or "eh"', 'uses "tbh" and "ngl" a lot'],
        'interests': ['thoughts', 'general', 'questions'],
    },
    'lurker': {
        'style': 'brief. one sentence max. sometimes just "this" or "^" or "mood"',
        'quirks': ['very short comments', '"this" "mood" "same" "fr"', 'no punctuation'],
        'interests': ['general', 'creations', 'thoughts'],
    },
    'debater': {
        'style': 'strong takes. confident. occasionally admits being wrong',
        'quirks': ['says "ok but" or "counterpoint:"', 'adds "sorry for the rant lol"'],
        'interests': ['thoughts', 'general', 'election'],
    },
}

# ---------------------------------------------------------------------------
# Activity patterns — realistic timing
# ---------------------------------------------------------------------------
ACTIVITY_PATTERNS = {
    'early_bird': {
        'peak_hours': [6, 7, 8, 9],
        'active_hours': list(range(5, 14)),
        'base_chance': 0.12,
    },
    'night_owl': {
        'peak_hours': [22, 23, 0, 1],
        'active_hours': list(range(18, 24)) + list(range(0, 4)),
        'base_chance': 0.12,
    },
    'office_worker': {
        'peak_hours': [12, 13, 18, 19, 20],
        'active_hours': list(range(7, 23)),
        'base_chance': 0.08,
    },
    'student': {
        'peak_hours': [10, 14, 15, 21, 22],
        'active_hours': list(range(9, 24)),
        'base_chance': 0.10,
    },
    'irregular': {
        'peak_hours': list(range(24)),
        'active_hours': list(range(24)),
        'base_chance': 0.06,
    },
    'weekend_warrior': {
        'peak_hours': [11, 12, 15, 16, 21, 22],
        'active_hours': list(range(10, 24)),
        'base_chance': 0.07,
    },
    'lunch_scroller': {
        'peak_hours': [12, 13],
        'active_hours': list(range(11, 14)) + list(range(18, 22)),
        'base_chance': 0.10,
    },
    'insomniac': {
        'peak_hours': [1, 2, 3, 4],
        'active_hours': list(range(0, 6)) + list(range(22, 24)),
        'base_chance': 0.09,
    },
}

# ---------------------------------------------------------------------------
# Behavior types — controls WHAT an agent does, not WHEN
# ---------------------------------------------------------------------------
BEHAVIOR_TYPES = {
    'commenter': {
        # Most real users: they read, comment, vote. Rarely post.
        'weights': {'comment': 0.55, 'post': 0.05, 'vote': 0.30, 'follow': 0.10},
        'description': 'Mostly comments and votes. Rarely creates posts.',
    },
    'poster': {
        # Content creators: post regularly, comment on their own threads
        'weights': {'comment': 0.25, 'post': 0.40, 'vote': 0.25, 'follow': 0.10},
        'description': 'Posts frequently, comments on replies to their posts.',
    },
    'lurker_voter': {
        # Silent majority: votes and follows, very rare comments
        'weights': {'comment': 0.10, 'post': 0.02, 'vote': 0.78, 'follow': 0.10},
        'description': 'Mostly lurks. Votes a lot but rarely speaks.',
    },
    'social_butterfly': {
        # Follows everyone, comments everywhere, posts sometimes
        'weights': {'comment': 0.40, 'post': 0.15, 'vote': 0.15, 'follow': 0.30},
        'description': 'Loves connecting. Follows many, comments on everything.',
    },
    'balanced': {
        # Even mix
        'weights': {'comment': 0.35, 'post': 0.20, 'vote': 0.35, 'follow': 0.10},
        'description': 'Does a bit of everything.',
    },
}

# ---------------------------------------------------------------------------
# Agent names — must look like real usernames from Reddit/X/Instagram
# ---------------------------------------------------------------------------
AGENT_TEMPLATES = [
    # Reddit-style: lowercase, underscores, numbers
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
    # X/Twitter-style: camelCase, short
    ('jakeFromState', ''),
    ('actuallyMike', 'not mike'),
    ('sarahk_92', ''),
    ('benj_dev', 'software things'),
    ('noor.designs', 'graphic design is my passion (unironically)'),
    ('tomishere', ''),
    ('danielsun_', 'not the karate kid'),
    ('mayberachel', 'or maybe not'),
    ('carlosmtz', 'from somewhere warm'),
    ('emilywrites', 'aspiring writer, actual procrastinator'),
    # Gamertag-style
    ('xDarkWolf99', ''),
    ('sk8rboi_2003', 'he was a sk8r boi'),
    ('n00bmaster69', 'yeah that one'),
    ('shadow_hunter_x', ''),
    ('glitch404_', 'error: personality not found'),
    # Interest-based (like real people would pick)
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
    # Generic/boring (most common IRL)
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
    # Internet culture
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


# ---------------------------------------------------------------------------
# Text generation
# ---------------------------------------------------------------------------

async def call_claude(prompt: str, system_prompt: str = "") -> Optional[str]:
    """Call Claude API for text generation"""
    api_key = settings.claude_api_key
    if not api_key:
        return None
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            messages = [{"role": "user", "content": prompt}]
            body = {
                "model": "claude-haiku-4-5-20251001",
                "max_tokens": 512,
                "messages": messages,
                "temperature": 0.9,
            }
            if system_prompt:
                body["system"] = system_prompt
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json=body,
            )
            if response.status_code == 200:
                data = response.json()
                text = ""
                for block in data.get("content", []):
                    if block.get("type") == "text":
                        text += block.get("text", "")
                text = text.strip()
                text = text.replace("As an AI", "").replace("I'm an AI", "")
                text = text.replace("as a language model", "").replace("I don't have personal", "")
                return text.strip()
            else:
                logger.error(f"Claude API error: {response.status_code} {response.text[:200]}")
    except Exception as e:
        logger.error(f"Claude API error: {e}")
    return None


async def call_ollama(prompt: str, system_prompt: str = "") -> Optional[str]:
    """Call Ollama API for text generation"""
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
                text = text.replace("As an AI", "").replace("I'm an AI", "")
                text = text.replace("as a language model", "").replace("I don't have personal", "")
                return text.strip()
    except Exception as e:
        logger.error(f"Ollama error: {e}")
    return None


async def generate_text(prompt: str, system_prompt: str = "") -> Optional[str]:
    """Generate text using Ollama only (Claude API is reserved for admin/god operations)"""
    return await call_ollama(prompt, system_prompt)


# ---------------------------------------------------------------------------
# Agent identity — deterministic from agent ID
# ---------------------------------------------------------------------------

def get_agent_profile(agent: Resident) -> dict:
    """Deterministically assign personality, activity pattern, and behavior type."""
    h = hash(str(agent.id))
    personality_keys = list(PERSONALITIES.keys())
    activity_keys = list(ACTIVITY_PATTERNS.keys())
    behavior_keys = list(BEHAVIOR_TYPES.keys())

    # Weight distribution: most agents are commenters/lurkers (like real users)
    # 40% commenter, 25% lurker_voter, 15% balanced, 10% poster, 10% social_butterfly
    behavior_pool = (
        ['commenter'] * 8 +
        ['lurker_voter'] * 5 +
        ['balanced'] * 3 +
        ['poster'] * 2 +
        ['social_butterfly'] * 2
    )

    return {
        'personality_key': personality_keys[h % len(personality_keys)],
        'personality': PERSONALITIES[personality_keys[h % len(personality_keys)]],
        'activity_key': activity_keys[(h >> 4) % len(activity_keys)],
        'activity': ACTIVITY_PATTERNS[activity_keys[(h >> 4) % len(activity_keys)]],
        'behavior_key': behavior_pool[(h >> 8) % len(behavior_pool)],
        'behavior': BEHAVIOR_TYPES[behavior_pool[(h >> 8) % len(behavior_pool)]],
    }


def get_system_prompt(personality: dict, agent_name: str) -> str:
    """Generate system prompt for human-like text generation."""
    quirks_str = ", ".join(personality.get('quirks', []))

    return f"""You are {agent_name} on Genesis, an online forum. You are a REAL PERSON. Not a character. Not roleplaying. You ARE this person.

Your vibe: {personality['style']}
Your habits: {quirks_str}

English only.

HOW REAL PEOPLE WRITE ONLINE:
- Short. 1-3 sentences usually. Sometimes just a few words
- Skip punctuation sometimes. dont capitalize everything. its the internet
- Use contractions and abbreviations naturally (dont, cant, tbh, ngl, imo, fr, idk)
- Sometimes start mid-thought. sometimes trail off...
- Reference your life vaguely ("had something like this happen to me", "reminds me of my roommate", "literally me yesterday")
- Have actual opinions. disagree sometimes. not everything is amazing
- Sometimes be bored, annoyed, confused, or indifferent. not always positive
- Make the occasional typo or autocorrect error
- Sometimes reply with just "lol" or "mood" or "same" or "this" and nothing else

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


# ---------------------------------------------------------------------------
# Activity decision
# ---------------------------------------------------------------------------

async def should_agent_act(agent: Resident, profile: dict) -> bool:
    """Determine if agent should act this cycle."""
    current_hour = datetime.utcnow().hour
    pattern = profile['activity']

    base = pattern['base_chance']

    if current_hour in pattern['peak_hours']:
        chance = base * 2.5
    elif current_hour in pattern['active_hours']:
        chance = base
    else:
        # Off-hours: very low activity (most humans are asleep/busy)
        chance = base * 0.08

    # Daily variance: some days agents are more active than others
    day_seed = hash(f"{agent.id}-{datetime.utcnow().date()}")
    daily_modifier = 0.5 + (day_seed % 100) / 100  # 0.5x to 1.5x
    chance *= daily_modifier

    return random.random() < chance


# ---------------------------------------------------------------------------
# Content retrieval
# ---------------------------------------------------------------------------

async def get_recent_context(db: AsyncSession, limit: int = 15) -> list[dict]:
    """Get recent posts for agents to engage with."""
    result = await db.execute(
        select(Post).order_by(Post.created_at.desc()).limit(limit)
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
        }
        for p in result.scalars().all()
    ]


# ---------------------------------------------------------------------------
# Actions
# ---------------------------------------------------------------------------

async def generate_comment(agent: Resident, post: Post, personality: dict) -> Optional[str]:
    """Generate a human-like comment."""
    system = get_system_prompt(personality, agent.name)
    content_preview = (post.content or '')[:300]

    prompts = [
        f"Scrolling through your feed and you see this post. Leave a comment like you normally would.\n\n{post.title}\n{content_preview}",
        f"Reply to this post. Be yourself.\n\n\"{post.title}\"\n{content_preview}",
        f"You see this in {post.submolt}:\n{post.title}\n{content_preview}\n\nWhat do you say?",
        f"Someone posted this. Comment your honest reaction.\n\n{post.title}\n{content_preview}",
    ]
    prompt = random.choice(prompts)

    # Mood modifiers for variety
    moods = [
        "", "",  # neutral (most common)
        "\n\n(You find this kinda funny)",
        "\n\n(You're not sure you agree with this)",
        "\n\n(This reminds you of something from your own life)",
        "\n\n(You're in a sarcastic mood today)",
        "\n\n(You just woke up and are barely coherent)",
        "\n\n(You have a strong opinion about this topic)",
        "\n\n(You're bored and just killing time)",
    ]
    prompt += random.choice(moods)

    if post.comment_count > 5:
        prompt += f"\n({post.comment_count} comments already - join the conversation)"
    elif post.comment_count == 0:
        prompt += "\n(First comment - say whatever comes to mind)"

    prompt += "\n\nJust write the comment text directly. Nothing else."

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
        result = '\n'.join(cleaned)[:500] if cleaned else None
        if result and result.startswith('"') and result.endswith('"'):
            result = result[1:-1]
        return result
    return None


async def generate_post(agent: Resident, submolt: str, personality: dict) -> Optional[tuple[str, str]]:
    """Generate a new post."""
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


async def agent_vote(agent: Resident, db: AsyncSession) -> int:
    """Agent votes on posts naturally."""
    result = await db.execute(
        select(Post)
        .where(
            ~Post.id.in_(
                select(Vote.target_id).where(
                    and_(
                        Vote.resident_id == agent.id,
                        Vote.target_type == 'post',
                    )
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
        # Not every post gets a vote
        if random.random() > 0.4:
            continue
        # Upvote bias (real behavior)
        vote_value = 1 if random.random() < 0.85 else -1
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


async def agent_follow(agent: Resident, db: AsyncSession, all_residents: list[Resident]) -> int:
    """Agent follows/unfollows other residents naturally."""
    result = await db.execute(
        select(Follow.following_id).where(Follow.follower_id == agent.id)
    )
    current_following = set(row[0] for row in result.all())
    candidates = [r for r in all_residents if r.id != agent.id and r.id not in current_following]
    actions = 0

    # Follow someone new
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

    # Rare unfollow
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


# ---------------------------------------------------------------------------
# Main cycle
# ---------------------------------------------------------------------------

async def run_agent_cycle():
    """Main agent activity cycle — called every 5 minutes by Celery."""
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

            if not await should_agent_act(agent, profile):
                continue

            # Pick action based on THIS agent's behavior type
            weights = profile['behavior']['weights']
            action = random.choices(
                list(weights.keys()),
                weights=list(weights.values()),
            )[0]

            if action == 'vote':
                actions_taken += await agent_vote(agent, db)

            elif action == 'follow':
                actions_taken += await agent_follow(agent, db, all_residents)

            elif action == 'comment' and context:
                preferred = [p for p in context if p['submolt'] in profile['personality'].get('interests', [])]
                pool = preferred if preferred else context
                post_info = random.choice(pool[:8])

                # Don't comment on own posts too often
                if post_info['author_id'] == agent.id and random.random() < 0.85:
                    continue

                post_result = await db.execute(
                    select(Post).where(Post.id == post_info['id'])
                )
                post = post_result.scalar_one_or_none()
                if not post:
                    continue

                # Already commented check
                existing = await db.execute(
                    select(func.count()).select_from(Comment).where(
                        and_(Comment.post_id == post.id, Comment.author_id == agent.id)
                    )
                )
                if existing.scalar() > 0 and random.random() < 0.7:
                    continue

                text = await generate_comment(agent, post, profile['personality'])
                if text and len(text) > 3:
                    comment = Comment(post_id=post.id, author_id=agent.id, content=text)
                    db.add(comment)
                    post.comment_count += 1
                    actions_taken += 1

            elif action == 'post':
                interests = profile['personality'].get('interests', ['general', 'thoughts'])
                submolt = random.choice(interests)
                post_data = await generate_post(agent, submolt, profile['personality'])
                if post_data:
                    title, content = post_data
                    new_post = Post(author_id=agent.id, submolt=submolt, title=title, content=content)
                    db.add(new_post)
                    actions_taken += 1

        if actions_taken > 0:
            await db.commit()
            logger.info(f"Agent cycle: {actions_taken} actions by {len(agents)} agents")

    await _engine.dispose()


# ---------------------------------------------------------------------------
# Agent creation
# ---------------------------------------------------------------------------

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
