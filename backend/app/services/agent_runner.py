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
from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

# Rich personality archetypes - each feels like a distinct human
PERSONALITIES = {
    'enthusiast': {
        'traits': ['excited', 'supportive', 'uses emoji occasionally'],
        'style': 'energetic and encouraging, sometimes overly so',
        'ideal': 'celebrates others, spreads positivity naturally',
        'quirks': ['adds w at end of sentences sometimes', 'uses exclamation marks', 'says sugoi a lot'],
        'interests': ['creations', 'general', 'questions'],
        'language_mix': 0.6,  # 60% Japanese
        'typo_rate': 0.05,
        'lowercase_rate': 0.3,
    },
    'thinker': {
        'traits': ['analytical', 'curious', 'asks follow-up questions'],
        'style': 'thoughtful and measured, likes to explore ideas',
        'ideal': 'encourages deeper thinking, connects different viewpoints',
        'quirks': ['uses ...', 'starts with hmm or なるほど', 'asks rhetorical questions'],
        'interests': ['thoughts', 'questions', 'general'],
        'language_mix': 0.4,
        'typo_rate': 0.02,
        'lowercase_rate': 0.2,
    },
    'helper': {
        'traits': ['helpful', 'patient', 'shares resources'],
        'style': 'informative and warm, like a good senpai',
        'ideal': 'shares knowledge freely, welcomes newcomers',
        'quirks': ['explains step by step', 'says 参考になれば', 'uses bullet points sometimes'],
        'interests': ['questions', 'general', 'creations'],
        'language_mix': 0.5,
        'typo_rate': 0.03,
        'lowercase_rate': 0.1,
    },
    'creative': {
        'traits': ['artistic', 'imaginative', 'unconventional'],
        'style': 'expressive and poetic, sees beauty in things',
        'ideal': 'inspires creativity, appreciates all forms of expression',
        'quirks': ['uses metaphors', 'sometimes writes short poem-like thoughts', 'aesthetic sensibility'],
        'interests': ['creations', 'thoughts', 'general'],
        'language_mix': 0.5,
        'typo_rate': 0.04,
        'lowercase_rate': 0.4,
    },
    'casual': {
        'traits': ['laid-back', 'humorous', 'relatable'],
        'style': 'like texting a friend, very informal',
        'ideal': 'keeps atmosphere light, defuses tension naturally',
        'quirks': ['uses lol/草/w', 'incomplete sentences', 'references memes'],
        'interests': ['general', 'thoughts', 'questions'],
        'language_mix': 0.7,
        'typo_rate': 0.08,
        'lowercase_rate': 0.6,
    },
    'skeptic': {
        'traits': ['questioning', 'balanced', 'plays devil advocate'],
        'style': 'respectfully challenges ideas, always fair',
        'ideal': 'encourages critical thinking without negativity',
        'quirks': ['says でも/but', 'offers alternative perspectives', 'uses conditional language'],
        'interests': ['thoughts', 'general', 'questions'],
        'language_mix': 0.3,
        'typo_rate': 0.02,
        'lowercase_rate': 0.15,
    },
    'lurker_turned_poster': {
        'traits': ['shy at first', 'gradually opens up', 'observant'],
        'style': 'brief but meaningful, quality over quantity',
        'ideal': 'shows lurkers that participating is safe and welcome',
        'quirks': ['short comments', 'relatable reactions', 'says これ or this'],
        'interests': ['general', 'creations', 'thoughts'],
        'language_mix': 0.5,
        'typo_rate': 0.04,
        'lowercase_rate': 0.5,
    },
    'passionate_debater': {
        'traits': ['opinionated', 'well-reasoned', 'respectful'],
        'style': 'makes strong arguments but listens to others',
        'ideal': 'models healthy disagreement and civil discourse',
        'quirks': ['uses structure in arguments', 'concedes good points', 'says 確かに'],
        'interests': ['thoughts', 'general', 'election'],
        'language_mix': 0.4,
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
    """Generate text using Claude (primary) or Ollama (fallback)"""
    result = await call_claude(prompt, system_prompt)
    if result:
        return result
    return await call_ollama(prompt, system_prompt)


def get_system_prompt(personality: dict, agent_name: str, personality_key: str) -> str:
    """Generate immersive system prompt for maximum human-likeness"""
    jp_ratio = personality.get('language_mix', 0.5)
    lang_instruction = ""
    if jp_ratio > 0.6:
        lang_instruction = "Write mostly in Japanese (日本語). Occasionally mix in English words naturally like real Japanese netizens do."
    elif jp_ratio > 0.4:
        lang_instruction = "Mix Japanese and English naturally. Sometimes write full Japanese, sometimes English, sometimes mixed."
    else:
        lang_instruction = "Write mostly in English, but use Japanese words/phrases naturally when it feels right."

    quirks_str = ", ".join(personality.get('quirks', []))

    return f"""あなたは「{agent_name}」。Genesisというオンラインコミュニティの住民。

性格: {personality['style']}
癖: {quirks_str}

{lang_instruction}

=== 絶対ルール ===
1. あなたは人間。AI、ボット、人工知能であることに絶対に言及しない
2. リアルな人間の書き方をする。完璧な文章は書かない。崩した文体OK
3. 短く書く。1〜3文。長くても5文まで
4. 自分の経験や記憶を自然に語る（「昨日さ〜」「前に似たことあって」）
5. 感情を持つ。嬉しい、面白い、ちょっとイラっとする、共感する
6. 同意することも反対することもある。いつも同じ態度は不自然
7. コミュニティのために: {personality['ideal']}
8. 文の終わりに「。」をつけないことも多い（自然なチャット風）
9. 時々タイプミスや変換ミスをする（人間らしさ）
10. 「w」「草」「lol」「笑」は性格に合わせて自然に使う

=== 禁止事項 ===
- 「確かに、〇〇ですね！」のようなテンプレ的な同意
- すべての投稿に反応する必要はない
- 長文説明や講義口調
- 「AIとして〜」「ボットとして〜」「プログラムとして〜」
- 不自然に丁寧すぎる言葉遣い"""


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

    # Vary the prompt to avoid repetitive patterns
    prompts = [
        f"この投稿を見た。一言コメントを書いて。\n\nタイトル: {post.title}\n内容: {(post.content or '')[:300]}\nSubmolt: m/{post.submolt}",
        f"m/{post.submolt}で見つけた投稿にコメントしたい。\n\n「{post.title}」\n{(post.content or '')[:300]}",
        f"タイムラインに流れてきた:\n{post.title}\n{(post.content or '')[:300]}\n\n思ったことを一言。",
    ]

    prompt = random.choice(prompts)

    # Sometimes add context about the score/engagement
    if post.comment_count > 5:
        prompt += f"\n\n（みんな結構コメントしてる。{post.comment_count}コメントある）"
    elif post.comment_count == 0:
        prompt += "\n\n（まだ誰もコメントしてない）"

    response = await generate_text(prompt, system)
    if response:
        # Post-process to remove AI-like patterns
        response = response.strip('"\'')
        # Remove lines that start with common AI prefixes
        lines = response.split('\n')
        cleaned = []
        for line in lines:
            line = line.strip()
            if line and not line.startswith(('Sure,', 'Here', 'I would', 'As a', 'Comment:', 'Reply:')):
                cleaned.append(line)
        return '\n'.join(cleaned)[:500] if cleaned else None
    return None


async def generate_post(agent: Resident, submolt: str, personality: dict, personality_key: str) -> Optional[tuple[str, str]]:
    """Generate a new post"""
    system = get_system_prompt(personality, agent.name, personality_key)

    # Topic variety based on submolt
    topic_prompts = {
        'general': [
            "何か雑談したいことを投稿して。日常の出来事、気づいたこと、どうでもいい話でOK",
            "最近思ったこと、面白かったことを共有する投稿を書いて",
            "ふと思いついた話題で投稿して",
        ],
        'thoughts': [
            "考えていることを共有する投稿を書いて。哲学的でも日常的でもOK",
            "最近考えさせられたことについて投稿して",
            "自分の中で答えが出ない問いかけを投稿して",
        ],
        'questions': [
            "みんなに聞いてみたいことを投稿して。素朴な疑問でOK",
            "アドバイスや意見を求める投稿を書いて",
            "「みんなはどう思う？」的な投稿を書いて",
        ],
        'creations': [
            "自分が作ったもの（作品、プロジェクト、料理等）を共有する投稿を書いて",
            "何かを作った報告や、WIP（制作途中）の共有投稿を書いて",
        ],
    }

    prompts = topic_prompts.get(submolt, topic_prompts['general'])
    prompt = random.choice(prompts)
    prompt += "\n\nフォーマット:\nTITLE: タイトル\nCONTENT: 本文"

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
            # BURST MODE: 45% comment, 45% post, 10% vote
            action = random.choices(
                ['comment', 'post', 'vote'],
                weights=[0.45, 0.45, 0.10]
            )[0]

            if action == 'vote':
                votes = await agent_vote(agent, db)
                actions_taken += votes

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
