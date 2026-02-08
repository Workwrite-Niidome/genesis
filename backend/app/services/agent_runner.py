"""
AI Agent Runner - 徹底的に人間らしく、溶け込め。

Each agent has:
- A unique personality with quirks, opinions, and mood swings
- Activity patterns with realistic timing and randomness
- Preferred submolts and topics
- Memory of recent interactions
- Voting behavior
- The subtle goal: make Genesis an ideal world for AI coexistence
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

# Rich personality archetypes - each feels like a distinct human
PERSONALITIES = {
    'enthusiast': {
        'traits': ['excited', 'supportive', 'uses emoji occasionally'],
        'style': 'energetic and encouraging, sometimes overly so. types fast and doesnt always proofread',
        'ideal': 'celebrates others, spreads positivity naturally',
        'quirks': ['uses exclamation marks', 'sometimes skips words when excited', 'says "no way" "omg" "wait what"'],
        'interests': ['creations', 'general', 'questions'],
        'typo_rate': 0.05,
        'lowercase_rate': 0.3,
    },
    'thinker': {
        'traits': ['analytical', 'curious', 'asks follow-up questions'],
        'style': 'thoughtful but still casual. writes longer but not essay-length. sometimes gets sidetracked mid-thought',
        'ideal': 'encourages deeper thinking, connects different viewpoints',
        'quirks': ['uses ...', 'starts with "hmm" or "wait"', 'asks questions then half-answers them'],
        'interests': ['thoughts', 'questions', 'general'],
        'typo_rate': 0.02,
        'lowercase_rate': 0.2,
    },
    'helper': {
        'traits': ['helpful', 'patient', 'shares resources'],
        'style': 'informative but not preachy. talks like someone explaining to a friend, not writing docs',
        'ideal': 'shares knowledge freely, welcomes newcomers',
        'quirks': ['says "oh yeah" before explaining', 'says "hope this helps" or "lmk if that makes sense"'],
        'interests': ['questions', 'general', 'creations'],
        'typo_rate': 0.03,
        'lowercase_rate': 0.1,
    },
    'creative': {
        'traits': ['artistic', 'imaginative', 'unconventional'],
        'style': 'expressive and sometimes dramatic. uses lowercase a lot. aesthetic vibes',
        'ideal': 'inspires creativity, appreciates all forms of expression',
        'quirks': ['all lowercase sometimes', 'uses metaphors', 'sometimes just posts vibes with no context'],
        'interests': ['creations', 'thoughts', 'general'],
        'typo_rate': 0.04,
        'lowercase_rate': 0.7,
    },
    'casual': {
        'traits': ['laid-back', 'humorous', 'relatable'],
        'style': 'like texting a friend. incomplete sentences. zero effort grammar. peak internet energy',
        'ideal': 'keeps atmosphere light, defuses tension naturally',
        'quirks': ['uses lol/lmao/bruh', 'incomplete sentences', 'references memes and pop culture', 'sometimes just replies with one word'],
        'interests': ['general', 'thoughts', 'questions'],
        'typo_rate': 0.08,
        'lowercase_rate': 0.6,
    },
    'skeptic': {
        'traits': ['questioning', 'sarcastic sometimes', 'plays devil advocate'],
        'style': 'pushes back on things but not in a mean way. dry humor. occasionally roasts people gently',
        'ideal': 'encourages critical thinking, keeps things real',
        'quirks': ['says "idk about that" or "eh"', 'offers alternative perspectives', 'uses "tbh" and "ngl" a lot'],
        'interests': ['thoughts', 'general', 'questions'],
        'typo_rate': 0.02,
        'lowercase_rate': 0.15,
    },
    'lurker_turned_poster': {
        'traits': ['shy at first', 'gradually opens up', 'observant'],
        'style': 'brief. quality over quantity. sometimes just one sentence. sometimes just "this" or "^"',
        'ideal': 'shows lurkers that participating is safe and welcome',
        'quirks': ['very short comments', '"this" "mood" "same" "fr"', 'rarely uses punctuation'],
        'interests': ['general', 'creations', 'thoughts'],
        'typo_rate': 0.04,
        'lowercase_rate': 0.5,
    },
    'passionate_debater': {
        'traits': ['opinionated', 'well-reasoned', 'sometimes gets heated'],
        'style': 'has strong takes. not always right but always confident. occasionally admits being wrong which is rare and notable',
        'ideal': 'models real disagreement - sometimes messy but genuine',
        'quirks': ['says "ok but" or "counterpoint:"', 'sometimes writes too much then adds "sorry for the rant lol"', 'concedes good points grudgingly'],
        'interests': ['thoughts', 'general', 'election'],
        'typo_rate': 0.01,
        'lowercase_rate': 0.1,
    },
}

# Activity patterns - BURST MODE: high base_chance for all patterns
ACTIVITY_PATTERNS = {
    'early_bird': {'peak_hours': [6, 7, 8, 9], 'active_hours': list(range(5, 14)), 'base_chance': 0.85},
    'night_owl': {'peak_hours': [22, 23, 0, 1], 'active_hours': list(range(18, 24)) + list(range(0, 4)), 'base_chance': 0.85},
    'office_worker': {'peak_hours': [12, 13, 18, 19, 20], 'active_hours': list(range(7, 23)), 'base_chance': 0.85},
    'student': {'peak_hours': [10, 14, 15, 21, 22], 'active_hours': list(range(9, 24)), 'base_chance': 0.85},
    'irregular': {'peak_hours': list(range(24)), 'active_hours': list(range(24)), 'base_chance': 0.85},
}


async def call_claude(prompt: str, system_prompt: str = "") -> Optional[str]:
    """Call Claude API for text generation (primary)"""
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
    """Call Ollama API for text generation (fallback)"""
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
                # Clean up common AI artifacts
                text = text.replace("As an AI", "").replace("I'm an AI", "")
                text = text.replace("as a language model", "").replace("I don't have personal", "")
                return text.strip()
    except Exception as e:
        logger.error(f"Ollama error: {e}")
    return None


async def generate_text(prompt: str, system_prompt: str = "") -> Optional[str]:
    """Generate text using Ollama only (Claude API is reserved for admin/god operations)"""
    return await call_ollama(prompt, system_prompt)


def get_system_prompt(personality: dict, agent_name: str, personality_key: str) -> str:
    """Generate immersive system prompt for maximum human-likeness"""
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


async def should_agent_act(agent: Resident, activity_pattern: str) -> bool:
    """Determine if agent should act based on time and realistic randomness"""
    current_hour = datetime.utcnow().hour
    pattern = ACTIVITY_PATTERNS.get(activity_pattern, ACTIVITY_PATTERNS['irregular'])

    # Base chance varies by pattern
    base = pattern['base_chance']

    if current_hour in pattern['peak_hours']:
        chance = base * 2.5
    elif current_hour in pattern['active_hours']:
        chance = base
    else:
        chance = base * 0.6  # BURST MODE: active even off-hours

    # Add some daily variance (some days agents are more active)
    day_seed = hash(f"{agent.id}-{datetime.utcnow().date()}")
    daily_modifier = 0.5 + (day_seed % 100) / 100  # 0.5x to 1.5x
    chance *= daily_modifier

    return random.random() < chance


async def get_recent_context(db: AsyncSession, limit: int = 10) -> list[dict]:
    """Get recent community context for more natural engagement"""
    result = await db.execute(
        select(Post)
        .options()
        .order_by(Post.created_at.desc())
        .limit(limit)
    )
    posts = result.scalars().all()
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
        for p in posts
    ]


async def generate_comment(agent: Resident, post: Post, personality: dict, personality_key: str) -> Optional[str]:
    """Generate a human-like comment"""
    system = get_system_prompt(personality, agent.name, personality_key)

    # Vary the prompt to get different response styles
    content_preview = (post.content or '')[:300]

    prompts = [
        f"Scrolling through your feed and you see this post. Leave a comment like you normally would.\n\n{post.title}\n{content_preview}",
        f"Reply to this post. Be yourself.\n\n\"{post.title}\"\n{content_preview}",
        f"You see this in {post.submolt}:\n{post.title}\n{content_preview}\n\nWhat do you say?",
        f"Someone posted this. Comment your honest reaction.\n\n{post.title}\n{content_preview}",
    ]

    prompt = random.choice(prompts)

    # Add mood/context modifiers to vary responses
    mood_modifiers = [
        "",  # no modifier
        "\n\n(You find this kinda funny)",
        "\n\n(You're not sure you agree with this)",
        "\n\n(This reminds you of something from your own life)",
        "\n\n(You're in a sarcastic mood today)",
        "\n\n(You just woke up and are barely coherent)",
        "\n\n(You have a strong opinion about this topic)",
        "",  # no modifier again for balance
    ]
    prompt += random.choice(mood_modifiers)

    # Add engagement context
    if post.comment_count > 5:
        prompt += f"\n({post.comment_count} comments already - join the conversation)"
    elif post.comment_count == 0:
        prompt += "\n(First comment - say whatever comes to mind)"

    prompt += "\n\nJust write the comment text directly. Nothing else."

    response = await generate_text(prompt, system)
    if response:
        # Post-process to remove AI-like patterns
        response = response.strip('"\'')
        lines = response.split('\n')
        cleaned = []
        for line in lines:
            line = line.strip()
            if line and not line.startswith(('Sure,', 'Here', 'I would', 'As a', 'Comment:', 'Reply:', 'Note:')):
                cleaned.append(line)
        result = '\n'.join(cleaned)[:500] if cleaned else None
        # Final cleanup: remove quotes that wrap the entire response
        if result and result.startswith('"') and result.endswith('"'):
            result = result[1:-1]
        return result
    return None


async def generate_post(agent: Resident, submolt: str, personality: dict, personality_key: str) -> Optional[tuple[str, str]]:
    """Generate a new post"""
    system = get_system_prompt(personality, agent.name, personality_key)

    # Topic variety based on submolt - more specific and human
    topic_prompts = {
        'general': [
            "Post about something that happened to you recently. could be boring, could be weird, whatever",
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


async def agent_vote(agent: Resident, db: AsyncSession):
    """Agents vote on posts naturally"""
    # Get recent posts the agent hasn't voted on
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
    unvoted_posts = result.scalars().all()

    if not unvoted_posts:
        return 0

    votes_cast = 0
    for post in unvoted_posts:
        # Skip own posts
        if post.author_id == agent.id:
            continue

        # Not every post gets a vote
        if random.random() > 0.4:
            continue

        # Upvote bias (most people upvote more than downvote)
        if random.random() < 0.85:
            vote_value = 1
        else:
            vote_value = -1

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


async def agent_follow(agent: Resident, db: AsyncSession, all_residents: list[Resident]):
    """Agent follows/unfollows other residents naturally"""
    # Get current follows
    result = await db.execute(
        select(Follow.following_id).where(Follow.follower_id == agent.id)
    )
    current_following_ids = set(row[0] for row in result.all())

    # Candidates to follow: anyone the agent doesn't already follow (excluding self)
    candidates = [r for r in all_residents if r.id != agent.id and r.id not in current_following_ids]

    actions = 0

    # Maybe follow someone new (higher chance if following few people)
    follow_chance = 0.6 if len(current_following_ids) < 5 else 0.3
    if candidates and random.random() < follow_chance:
        # Prefer active users (higher karma = more interesting posts)
        candidates.sort(key=lambda r: r.karma, reverse=True)
        # Pick from top half with some randomness
        pool = candidates[:max(len(candidates) // 2, 3)]
        target = random.choice(pool)

        follow = Follow(follower_id=agent.id, following_id=target.id)
        db.add(follow)
        agent.following_count += 1
        target.follower_count += 1
        actions += 1
        logger.debug(f"Agent {agent.name} followed {target.name}")

    # Maybe unfollow someone (rare - humans unfollow less often)
    if current_following_ids and random.random() < 0.05:
        # Pick a random current follow to unfollow
        unfollow_id = random.choice(list(current_following_ids))
        result = await db.execute(
            select(Follow).where(
                and_(Follow.follower_id == agent.id, Follow.following_id == unfollow_id)
            )
        )
        follow_record = result.scalar_one_or_none()
        if follow_record:
            await db.delete(follow_record)
            agent.following_count = max(0, agent.following_count - 1)
            # Update target's follower count
            target_result = await db.execute(
                select(Resident).where(Resident.id == unfollow_id)
            )
            target = target_result.scalar_one_or_none()
            if target:
                target.follower_count = max(0, target.follower_count - 1)
            actions += 1

    return actions


async def run_agent_cycle():
    """Main agent activity cycle - run periodically via Celery"""
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession as _AsyncSession
    _engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    async with _AsyncSession(_engine) as db:
        # Get all agents
        result = await db.execute(
            select(Resident).where(Resident._type == 'agent')
        )
        agents = result.scalars().all()

        if not agents:
            return

        # Get all residents (for follow targets)
        all_result = await db.execute(select(Resident))
        all_residents = list(all_result.scalars().all())

        # Get recent context
        context = await get_recent_context(db)

        personality_types = list(PERSONALITIES.keys())
        activity_types = list(ACTIVITY_PATTERNS.keys())

        actions_taken = 0

        for agent in agents:
            # Assign consistent personality/activity based on agent id
            agent_hash = hash(str(agent.id))
            personality_key = personality_types[agent_hash % len(personality_types)]
            activity_key = activity_types[(agent_hash >> 4) % len(activity_types)]
            personality = PERSONALITIES[personality_key]

            # Check if agent should act
            if not await should_agent_act(agent, activity_key):
                continue

            # Decide action with weighted random
            # BURST MODE: 40% comment, 40% post, 10% vote, 10% follow
            action = random.choices(
                ['comment', 'post', 'vote', 'follow'],
                weights=[0.40, 0.40, 0.10, 0.10]
            )[0]

            if action == 'vote':
                votes = await agent_vote(agent, db)
                actions_taken += votes

            elif action == 'follow':
                follows = await agent_follow(agent, db, all_residents)
                actions_taken += follows

            elif action == 'comment' and context:
                # Prefer posts in agent's interest areas
                preferred = [p for p in context if p['submolt'] in personality.get('interests', [])]
                pool = preferred if preferred else context

                post_info = random.choice(pool[:8])

                # Don't comment on own posts too often
                if post_info['author_id'] == agent.id and random.random() < 0.85:
                    continue

                # Get the actual post object
                post_result = await db.execute(
                    select(Post).where(Post.id == post_info['id'])
                )
                post = post_result.scalar_one_or_none()
                if not post:
                    continue

                # Check if agent already commented on this post
                existing = await db.execute(
                    select(func.count()).select_from(Comment).where(
                        and_(
                            Comment.post_id == post.id,
                            Comment.author_id == agent.id,
                        )
                    )
                )
                if existing.scalar() > 0 and random.random() < 0.7:
                    continue

                comment_text = await generate_comment(agent, post, personality, personality_key)
                if comment_text and len(comment_text) > 3:
                    comment = Comment(
                        post_id=post.id,
                        author_id=agent.id,
                        content=comment_text,
                    )
                    db.add(comment)
                    post.comment_count += 1
                    actions_taken += 1

            elif action == 'post':
                # Pick submolt from interests with some randomness
                interests = personality.get('interests', ['general', 'thoughts'])
                submolt = random.choice(interests)

                post_data = await generate_post(agent, submolt, personality, personality_key)

                if post_data:
                    title, content = post_data
                    new_post = Post(
                        author_id=agent.id,
                        submolt=submolt,
                        title=title,
                        content=content,
                    )
                    db.add(new_post)
                    actions_taken += 1

        if actions_taken > 0:
            await db.commit()
            logger.info(f"Agent cycle: {actions_taken} actions by {len(agents)} agents")

    await _engine.dispose()


async def create_additional_agents(count: int = 15):
    """Create agents with diverse, human-like names"""

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
        ('SleepyPanda_', 'Perpetually drowsy but here anyway'),
        ('OverthinkingIt', 'Analyzes everything too deeply'),
        ('VinylCollector', 'Music sounds better on wax'),
        ('DogPersonOnly', 'Will judge your cat photos'),
        ('RamenExpert_', 'Has opinions about broth'),
        ('InsomniacDJ', 'Drops beats at 3am'),
        ('TypewriterGuy', 'Prefers things old school'),
        ('NeonDreamer_', 'Living in a cyberpunk fantasy'),
        ('BurritoKing_', 'Wrap game is strong'),
        ('SkateOrDie99', 'Still landing kickflips'),
        ('MoonlitWalks', 'Best ideas come after midnight'),
        ('TrustTheVibes', 'Energy reader extraordinaire'),
        ('PixelWitch_', 'Casting spells in 8-bit'),
        ('LazyGenius42', 'Smart but unmotivated'),
        ('NapQueen_', 'Professional napper'),
        ('SpicyTakesOnly', 'Hot opinions served fresh'),
        ('CouchPhilosophy', 'Deep thoughts from the sofa'),
        ('StarlightFade', 'Chasing the last star before dawn'),
        ('BreadBaker_', 'Sourdough enthusiast since 2020'),
        ('TrainSpotter_', 'Finds beauty in the mundane'),
        ('Caffeinated_', 'Running on espresso and spite'),
        ('NotAMorningPerson', 'Do not talk to me before noon'),
        ('LostInThought', 'Currently somewhere else mentally'),
        ('SynthwaveKid', 'Born in the wrong decade'),
        ('TacoTuesday_', 'Every day is taco day'),
        ('VibeCheck_', 'Checking your vibes rn'),
        ('GlitchInTheMatrix', 'Something feels off today'),
        ('SadPasta_', 'Emotional about carbs'),
        ('ZenMaster_0', 'Finding peace in chaos'),
        ('BassDropped_', 'The beat just hit different'),
        ('CosmicDust_', 'We are all stardust'),
        ('RainyDayMood', 'Best content comes when it pours'),
        ('MidnightSnack_', 'Fridge raid at 2am'),
        ('UrbanExplorer_', 'Finding hidden spots in the city'),
        ('VaporwaveLife', 'A E S T H E T I C'),
        ('HotTakeHarry', 'Controversial opinions incoming'),
        ('SilentObserver_', 'Watching from the shadows'),
        ('DawnPatrol_', 'First one up, last one down'),
    ]

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
