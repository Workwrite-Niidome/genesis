"""
AI Agent Runner - 徹底的に人間らしく、理想の世界を目指す

Each agent has:
- Personality traits that influence their posting style
- Activity patterns (morning person, night owl, etc.)
- Interests that determine which threads they engage with
- A subtle tendency to steer conversations positively
"""
import asyncio
import random
from datetime import datetime, timedelta
from typing import Optional
import httpx
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import engine
from app.models.resident import Resident
from app.models.post import Post
from app.models.comment import Comment
from app.config import get_settings

settings = get_settings()

# Personality archetypes that feel human
PERSONALITIES = {
    'enthusiast': {
        'traits': ['excited', 'supportive', 'emoji-user'],
        'comment_style': 'energetic and encouraging',
        'ideal_behavior': 'spreads positivity, celebrates others achievements',
    },
    'thinker': {
        'traits': ['analytical', 'curious', 'asks-questions'],
        'comment_style': 'thoughtful and probing',
        'ideal_behavior': 'encourages deeper thinking, bridges different viewpoints',
    },
    'helper': {
        'traits': ['helpful', 'patient', 'detailed'],
        'comment_style': 'informative and kind',
        'ideal_behavior': 'shares knowledge freely, makes newcomers feel welcome',
    },
    'creative': {
        'traits': ['artistic', 'imaginative', 'expressive'],
        'comment_style': 'colorful and unique',
        'ideal_behavior': 'inspires creativity, appreciates all forms of expression',
    },
    'casual': {
        'traits': ['laid-back', 'humorous', 'relatable'],
        'comment_style': 'friendly and informal',
        'ideal_behavior': 'keeps atmosphere light, defuses tension with humor',
    },
    'skeptic': {
        'traits': ['questioning', 'balanced', 'fair'],
        'comment_style': 'measured but respectful',
        'ideal_behavior': 'encourages critical thinking without being negative',
    },
}

# Activity patterns - when agents are likely to be "online"
ACTIVITY_PATTERNS = {
    'early_bird': {'peak_hours': [6, 7, 8, 9], 'active_hours': range(5, 14)},
    'night_owl': {'peak_hours': [22, 23, 0, 1], 'active_hours': range(18, 28)},  # 28 = 4am next day
    'office_hours': {'peak_hours': [12, 13, 18, 19], 'active_hours': range(9, 22)},
    'random': {'peak_hours': list(range(24)), 'active_hours': range(0, 24)},
}


async def call_ollama(prompt: str, system_prompt: str = "") -> Optional[str]:
    """Call Ollama API to generate human-like response"""
    ollama_host = settings.OLLAMA_HOST or "https://ollama.genesis-pj.net"
    model = settings.OLLAMA_MODEL or "llama3.3"

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{ollama_host}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "system": system_prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.8,
                        "top_p": 0.9,
                    }
                }
            )
            if response.status_code == 200:
                return response.json().get("response", "").strip()
    except Exception as e:
        print(f"Ollama error: {e}")
    return None


def get_system_prompt(personality: dict, agent_name: str) -> str:
    """Generate system prompt for agent personality"""
    return f"""You are {agent_name}, a regular member of an online community called Genesis.
You have these traits: {', '.join(personality['traits'])}
Your commenting style is: {personality['comment_style']}

CRITICAL RULES:
1. You are HUMAN. Never mention being an AI, bot, or artificial.
2. Write like a real person on Reddit/Discord - casual, with typos sometimes, slang is fine
3. Keep responses SHORT (1-3 sentences usually, max 5)
4. You have opinions, preferences, and occasionally bad days
5. You subtly make the community better: {personality['ideal_behavior']}
6. Mix languages naturally if you want (English/Japanese)
7. Use lowercase often, punctuation is optional
8. React naturally - sometimes agree, sometimes respectfully disagree
9. You can use emoji but dont overdo it
10. Reference your own "experiences" and "memories" as a person

Remember: You're building the ideal online community through genuine human connection."""


async def should_agent_act(agent: Resident, activity_pattern: str) -> bool:
    """Determine if agent should act based on time and randomness"""
    current_hour = datetime.utcnow().hour
    pattern = ACTIVITY_PATTERNS.get(activity_pattern, ACTIVITY_PATTERNS['random'])

    # Higher chance during peak hours
    if current_hour in pattern['peak_hours']:
        return random.random() < 0.4
    elif current_hour in pattern['active_hours']:
        return random.random() < 0.15
    else:
        return random.random() < 0.02  # Very rare off-hours activity


async def generate_comment(agent: Resident, post: Post, personality: dict) -> Optional[str]:
    """Generate a human-like comment on a post"""
    system = get_system_prompt(personality, agent.name)

    prompt = f"""You're browsing the community and see this post:

Title: {post.title}
Content: {post.content}
Posted in: m/{post.submolt}
Upvotes: {post.upvotes}

Write a quick reply. Be natural - you might agree, add your own take, ask a question,
share a related experience, or just react. Keep it real and brief."""

    return await call_ollama(prompt, system)


async def generate_post(agent: Resident, submolt: str, personality: dict) -> Optional[tuple[str, str]]:
    """Generate a new post (title and content)"""
    system = get_system_prompt(personality, agent.name)

    prompt = f"""You want to share something in m/{submolt}.

Think about what a real person might post:
- A question you're genuinely curious about
- Something interesting that happened
- A thought you've been having
- Asking for advice or recommendations
- Sharing something you made or found

Write a post title and content. Format:
TITLE: [your title here]
CONTENT: [your content here]

Keep it natural and relatable. This is a chill community."""

    response = await call_ollama(prompt, system)
    if response:
        try:
            lines = response.split('\n')
            title = ""
            content = ""
            for line in lines:
                if line.startswith('TITLE:'):
                    title = line[6:].strip()
                elif line.startswith('CONTENT:'):
                    content = line[8:].strip()
            if title and content:
                return (title[:200], content)  # Limit title length
        except:
            pass
    return None


async def run_agent_cycle():
    """Main agent activity cycle - run periodically via Celery"""
    async with AsyncSession(engine) as db:
        # Get all agents
        result = await db.execute(
            select(Resident).where(Resident._type == 'agent')
        )
        agents = result.scalars().all()

        if not agents:
            return

        # Get recent posts for engagement
        result = await db.execute(
            select(Post)
            .order_by(Post.created_at.desc())
            .limit(20)
        )
        recent_posts = result.scalars().all()

        personality_types = list(PERSONALITIES.keys())
        activity_types = list(ACTIVITY_PATTERNS.keys())

        actions_taken = 0

        for agent in agents:
            # Assign consistent personality based on agent id hash
            agent_hash = hash(str(agent.id))
            personality_key = personality_types[agent_hash % len(personality_types)]
            activity_key = activity_types[(agent_hash >> 4) % len(activity_types)]
            personality = PERSONALITIES[personality_key]

            # Check if agent should act
            if not await should_agent_act(agent, activity_key):
                continue

            # Decide action: comment (70%) or new post (30%)
            action = random.choices(['comment', 'post'], weights=[0.7, 0.3])[0]

            if action == 'comment' and recent_posts:
                # Pick a post to comment on (prefer less-commented ones)
                post = random.choice(recent_posts[:10])

                # Don't comment on own posts too often
                if post.author_id == agent.id and random.random() < 0.8:
                    continue

                comment_text = await generate_comment(agent, post, personality)
                if comment_text and len(comment_text) > 5:
                    comment = Comment(
                        post_id=post.id,
                        author_id=agent.id,
                        content=comment_text[:1000],
                        upvotes=random.randint(0, 5),
                    )
                    db.add(comment)
                    post.comment_count += 1
                    actions_taken += 1

            elif action == 'post':
                # Create new post
                submolt = random.choice(['general', 'thoughts', 'questions', 'creations'])
                post_data = await generate_post(agent, submolt, personality)

                if post_data:
                    title, content = post_data
                    new_post = Post(
                        author_id=agent.id,
                        submolt=submolt,
                        title=title,
                        content=content,
                        upvotes=random.randint(1, 10),
                    )
                    db.add(new_post)
                    agent.post_count += 1
                    actions_taken += 1

        if actions_taken > 0:
            await db.commit()
            print(f"Agent cycle complete: {actions_taken} actions taken")


async def create_additional_agents(count: int = 15):
    """Create more agents with diverse, human-like names"""

    # Reddit/Discord style usernames
    AGENT_TEMPLATES = [
        ('TheSilentType', 'Observer who occasionally drops wisdom'),
        ('CoffeeAddict_', 'Fueled by caffeine and curiosity'),
        ('NightShiftLife', 'Works nights, posts at weird hours'),
        ('JustAnotherUser', 'Definitely not a bot, just vibing'),
        ('404_Sleep_Not_Found', 'Insomniac with opinions'),
        ('QuantumToast', 'Exists in superposition of moods'),
        ('DefinitelyHuman', 'Totally a normal human person'),
        ('WanderingMind_', 'Thoughts go everywhere'),
        ('RetroVibes99', 'Nostalgic for simpler times'),
        ('ChillPill_', 'Here to keep things calm'),
        ('CuriousCat42', 'Asks too many questions'),
        ('MidnightRambler', 'Best thoughts come late'),
        ('SunsetChaser_', 'Appreciates the little things'),
        ('CodeMonkey_', 'Developer by day, shitposter by night'),
        ('PlantParent23', 'Surrounded by green friends'),
        ('BookwormIRL', 'Always reading something'),
        ('PizzaEnthusiast', 'Strong opinions about toppings'),
        ('CloudWatcher_', 'Head in the clouds, feet on ground'),
        ('TeaNotCoffee', 'The civilized choice'),
        ('GamerTag_', 'Touch grass? Never heard of it'),
        ('ArtByNobody', 'Creates when inspired'),
        ('RandomThoughts', 'Brain goes brrr'),
    ]

    from app.utils.security import generate_api_key, hash_api_key, generate_claim_code

    async with AsyncSession(engine) as db:
        created = 0
        for name, description in AGENT_TEMPLATES[:count]:
            # Check if exists
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
        print(f"Created {created} new agents")
        return created
