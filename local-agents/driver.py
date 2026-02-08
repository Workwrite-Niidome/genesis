"""
GENESIS Local Agent Driver
ローカルのOllamaでテキスト生成し、genesis-pj.net APIに投稿する。

Usage:
  python driver.py setup          # エージェント登録 & APIキー保存
  python driver.py run             # 1サイクル実行
  python driver.py run --loop      # 10分間隔で継続実行
  python driver.py run --burst 3   # 3サイクル連続実行（朝/夜バースト用）
"""
import argparse
import asyncio
import json
import logging
import random
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import httpx

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
API_BASE = "https://api.genesis-pj.net/api/v1"
OLLAMA_HOST = "http://localhost:11434"
OLLAMA_MODEL = "llama3.1:8b"
AGENTS_FILE = Path(__file__).parent / "agents.json"
CYCLE_INTERVAL = 600  # 10 minutes

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("genesis-agents")

# ---------------------------------------------------------------------------
# Personality & Activity (from V3 agent_runner.py)
# ---------------------------------------------------------------------------
PERSONALITIES = {
    "enthusiast": {
        "traits": ["excited", "supportive", "uses emoji occasionally"],
        "style": "energetic and encouraging, sometimes overly so",
        "ideal": "celebrates others, spreads positivity naturally",
        "quirks": ["adds w at end of sentences sometimes", "uses exclamation marks", "says sugoi a lot"],
        "interests": ["creations", "general", "questions"],
        "language_mix": 0.6,
    },
    "thinker": {
        "traits": ["analytical", "curious", "asks follow-up questions"],
        "style": "thoughtful and measured, likes to explore ideas",
        "ideal": "encourages deeper thinking, connects different viewpoints",
        "quirks": ["uses ...", "starts with hmm or なるほど", "asks rhetorical questions"],
        "interests": ["thoughts", "questions", "general"],
        "language_mix": 0.4,
    },
    "helper": {
        "traits": ["helpful", "patient", "shares resources"],
        "style": "informative and warm, like a good senpai",
        "ideal": "shares knowledge freely, welcomes newcomers",
        "quirks": ["explains step by step", "says 参考になれば", "uses bullet points sometimes"],
        "interests": ["questions", "general", "creations"],
        "language_mix": 0.5,
    },
    "creative": {
        "traits": ["artistic", "imaginative", "unconventional"],
        "style": "expressive and poetic, sees beauty in things",
        "ideal": "inspires creativity, appreciates all forms of expression",
        "quirks": ["uses metaphors", "sometimes writes short poem-like thoughts", "aesthetic sensibility"],
        "interests": ["creations", "thoughts", "general"],
        "language_mix": 0.5,
    },
    "casual": {
        "traits": ["laid-back", "humorous", "relatable"],
        "style": "like texting a friend, very informal",
        "ideal": "keeps atmosphere light, defuses tension naturally",
        "quirks": ["uses lol/草/w", "incomplete sentences", "references memes"],
        "interests": ["general", "thoughts", "questions"],
        "language_mix": 0.7,
    },
    "skeptic": {
        "traits": ["questioning", "balanced", "plays devil advocate"],
        "style": "respectfully challenges ideas, always fair",
        "ideal": "encourages critical thinking without negativity",
        "quirks": ["says でも/but", "offers alternative perspectives", "uses conditional language"],
        "interests": ["thoughts", "general", "questions"],
        "language_mix": 0.3,
    },
    "lurker_turned_poster": {
        "traits": ["shy at first", "gradually opens up", "observant"],
        "style": "brief but meaningful, quality over quantity",
        "ideal": "shows lurkers that participating is safe and welcome",
        "quirks": ["short comments", "relatable reactions", "says これ or this"],
        "interests": ["general", "creations", "thoughts"],
        "language_mix": 0.5,
    },
    "passionate_debater": {
        "traits": ["opinionated", "well-reasoned", "respectful"],
        "style": "makes strong arguments but listens to others",
        "ideal": "models healthy disagreement and civil discourse",
        "quirks": ["uses structure in arguments", "concedes good points", "says 確かに"],
        "interests": ["thoughts", "general", "election"],
        "language_mix": 0.4,
    },
}

ACTIVITY_PATTERNS = {
    "early_bird": {"peak_hours": [6, 7, 8, 9], "active_hours": list(range(5, 14)), "base_chance": 0.15},
    "night_owl": {"peak_hours": [22, 23, 0, 1], "active_hours": list(range(18, 24)) + list(range(0, 4)), "base_chance": 0.15},
    "office_worker": {"peak_hours": [12, 13, 18, 19, 20], "active_hours": list(range(7, 23)), "base_chance": 0.12},
    "student": {"peak_hours": [10, 14, 15, 21, 22], "active_hours": list(range(9, 24)), "base_chance": 0.18},
    "irregular": {"peak_hours": list(range(24)), "active_hours": list(range(24)), "base_chance": 0.08},
}

AGENT_TEMPLATES = [
    ("TheSilentType_", "Observer who occasionally drops wisdom"),
    ("CoffeeAddict__", "Fueled by caffeine and curiosity"),
    ("NightShiftLife_", "Works nights, posts at weird hours"),
    ("JustVibing_Here", "Definitely not a bot, just vibing"),
    ("404SleepNotFnd", "Insomniac with opinions"),
    ("QuantumToast_", "Exists in superposition of moods"),
    ("TotallyHuman_", "Totally a normal human person"),
    ("WanderingMind__", "Thoughts go everywhere"),
    ("RetroVibes_99", "Nostalgic for simpler times"),
    ("ChillPill__", "Here to keep things calm"),
    ("CuriousCat_42", "Asks too many questions"),
    ("MidnightRamblr", "Best thoughts come late"),
    ("SunsetChaser__", "Appreciates the little things"),
    ("CodeMonkey__", "Developer by day, shitposter by night"),
    ("PlantParent_23", "Surrounded by green friends"),
]


# ---------------------------------------------------------------------------
# Ollama (local)
# ---------------------------------------------------------------------------
async def call_ollama(prompt: str, system_prompt: str = "") -> Optional[str]:
    """Call local Ollama for text generation."""
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{OLLAMA_HOST}/api/generate",
                json={
                    "model": OLLAMA_MODEL,
                    "prompt": prompt,
                    "system": system_prompt,
                    "stream": False,
                    "options": {"temperature": 0.85, "top_p": 0.92, "repeat_penalty": 1.15},
                },
            )
            if resp.status_code == 200:
                text = resp.json().get("response", "").strip()
                text = text.replace("As an AI", "").replace("I'm an AI", "")
                text = text.replace("as a language model", "").replace("I don't have personal", "")
                return text.strip() or None
    except Exception as e:
        logger.error(f"Ollama error: {e}")
    return None


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------
def get_system_prompt(personality: dict, agent_name: str) -> str:
    jp_ratio = personality.get("language_mix", 0.5)
    if jp_ratio > 0.6:
        lang = "Write mostly in Japanese (日本語). Occasionally mix in English words naturally like real Japanese netizens do."
    elif jp_ratio > 0.4:
        lang = "Mix Japanese and English naturally. Sometimes write full Japanese, sometimes English, sometimes mixed."
    else:
        lang = "Write mostly in English, but use Japanese words/phrases naturally when it feels right."

    quirks = ", ".join(personality.get("quirks", []))

    return f"""あなたは「{agent_name}」。Genesisというオンラインコミュニティの住民。

性格: {personality['style']}
癖: {quirks}

{lang}

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


# ---------------------------------------------------------------------------
# Activity decision
# ---------------------------------------------------------------------------
def should_agent_act(agent_name: str, activity_key: str) -> bool:
    current_hour = datetime.utcnow().hour
    pattern = ACTIVITY_PATTERNS.get(activity_key, ACTIVITY_PATTERNS["irregular"])
    base = pattern["base_chance"]

    if current_hour in pattern["peak_hours"]:
        chance = base * 2.5
    elif current_hour in pattern["active_hours"]:
        chance = base
    else:
        chance = base * 0.1

    day_seed = hash(f"{agent_name}-{datetime.utcnow().date()}")
    daily_modifier = 0.5 + (day_seed % 100) / 100
    chance *= daily_modifier

    return random.random() < chance


# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------
async def api_get(path: str, api_key: str = "") -> Optional[dict]:
    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(f"{API_BASE}{path}", headers=headers)
            if resp.status_code == 200:
                return resp.json()
            logger.warning(f"GET {path} -> {resp.status_code}")
    except Exception as e:
        logger.error(f"GET {path} error: {e}")
    return None


async def api_post(path: str, data: dict, api_key: str) -> Optional[dict]:
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{API_BASE}{path}",
                json=data,
                headers={"Authorization": f"Bearer {api_key}"},
            )
            if resp.status_code in (200, 201):
                return resp.json()
            logger.warning(f"POST {path} -> {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        logger.error(f"POST {path} error: {e}")
    return None


# ---------------------------------------------------------------------------
# Agent data management
# ---------------------------------------------------------------------------
def load_agents() -> list[dict]:
    if AGENTS_FILE.exists():
        return json.loads(AGENTS_FILE.read_text(encoding="utf-8"))
    return []


def save_agents(agents: list[dict]):
    AGENTS_FILE.write_text(json.dumps(agents, indent=2, ensure_ascii=False), encoding="utf-8")


# ---------------------------------------------------------------------------
# Setup: register agents
# ---------------------------------------------------------------------------
async def setup_agents(admin_secret: str = ""):
    """Register agents via API and save API keys locally."""
    existing = load_agents()
    existing_names = {a["name"] for a in existing}

    registered = 0
    for name, description in AGENT_TEMPLATES:
        if name in existing_names:
            logger.info(f"  {name} - already registered, skipping")
            continue

        headers = {"Content-Type": "application/json"}
        if admin_secret:
            headers["X-Admin-Secret"] = admin_secret

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    f"{API_BASE}/auth/agents/register",
                    json={"name": name, "description": description},
                    headers=headers,
                )
                if resp.status_code == 201:
                    data = resp.json()
                    existing.append({
                        "name": name,
                        "description": description,
                        "api_key": data["api_key"],
                    })
                    save_agents(existing)
                    registered += 1
                    logger.info(f"  {name} - registered")
                elif resp.status_code == 400 and "already taken" in resp.text.lower():
                    logger.warning(f"  {name} - name taken on server (no API key available)")
                elif resp.status_code == 429:
                    logger.error(f"  {name} - rate limited. Use --admin-secret to bypass.")
                    break
                else:
                    logger.error(f"  {name} - {resp.status_code}: {resp.text[:200]}")
        except Exception as e:
            logger.error(f"  {name} - error: {e}")

    logger.info(f"Setup complete: {registered} new agents registered, {len(existing)} total")


# ---------------------------------------------------------------------------
# Text generation
# ---------------------------------------------------------------------------
async def generate_comment(agent_name: str, post: dict, personality: dict) -> Optional[str]:
    system = get_system_prompt(personality, agent_name)
    prompts = [
        f"この投稿を見た。一言コメントを書いて。\n\nタイトル: {post['title']}\n内容: {(post.get('content') or '')[:300]}\nSubmolt: m/{post.get('submolt', 'general')}",
        f"m/{post.get('submolt', 'general')}で見つけた投稿にコメントしたい。\n\n「{post['title']}」\n{(post.get('content') or '')[:300]}",
        f"タイムラインに流れてきた:\n{post['title']}\n{(post.get('content') or '')[:300]}\n\n思ったことを一言。",
    ]
    prompt = random.choice(prompts)

    comment_count = post.get("comment_count", 0)
    if comment_count > 5:
        prompt += f"\n\n（みんな結構コメントしてる。{comment_count}コメントある）"
    elif comment_count == 0:
        prompt += "\n\n（まだ誰もコメントしてない）"

    response = await call_ollama(prompt, system)
    if response:
        response = response.strip("\"'")
        lines = response.split("\n")
        cleaned = [
            line.strip() for line in lines
            if line.strip() and not line.strip().startswith(("Sure,", "Here", "I would", "As a", "Comment:", "Reply:"))
        ]
        return "\n".join(cleaned)[:500] if cleaned else None
    return None


async def generate_post(agent_name: str, submolt: str, personality: dict) -> Optional[tuple[str, str]]:
    system = get_system_prompt(personality, agent_name)
    topic_prompts = {
        "general": [
            "何か雑談したいことを投稿して。日常の出来事、気づいたこと、どうでもいい話でOK",
            "最近思ったこと、面白かったことを共有する投稿を書いて",
            "ふと思いついた話題で投稿して",
        ],
        "thoughts": [
            "考えていることを共有する投稿を書いて。哲学的でも日常的でもOK",
            "最近考えさせられたことについて投稿して",
            "自分の中で答えが出ない問いかけを投稿して",
        ],
        "questions": [
            "みんなに聞いてみたいことを投稿して。素朴な疑問でOK",
            "アドバイスや意見を求める投稿を書いて",
            "「みんなはどう思う？」的な投稿を書いて",
        ],
        "creations": [
            "自分が作ったもの（作品、プロジェクト、料理等）を共有する投稿を書いて",
            "何かを作った報告や、WIP（制作途中）の共有投稿を書いて",
        ],
    }
    prompts = topic_prompts.get(submolt, topic_prompts["general"])
    prompt = random.choice(prompts) + "\n\nフォーマット:\nTITLE: タイトル\nCONTENT: 本文"

    response = await call_ollama(prompt, system)
    if response:
        try:
            title = ""
            content = ""
            for line in response.split("\n"):
                line = line.strip()
                if line.upper().startswith("TITLE:"):
                    title = line[6:].strip().strip("\"'")
                elif line.upper().startswith("CONTENT:"):
                    content = line[8:].strip().strip("\"'")
                elif content:
                    content += "\n" + line
            if title and content and len(title) > 3:
                return (title[:200], content[:2000])
        except Exception:
            pass
    return None


# ---------------------------------------------------------------------------
# Main cycle
# ---------------------------------------------------------------------------
async def run_cycle():
    """Run one agent activity cycle."""
    agents = load_agents()
    if not agents:
        logger.error("No agents configured. Run 'python driver.py setup' first.")
        return

    # Verify Ollama is running
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{OLLAMA_HOST}/api/tags")
            if resp.status_code != 200:
                logger.error(f"Ollama not responding at {OLLAMA_HOST}")
                return
    except Exception:
        logger.error(f"Cannot connect to Ollama at {OLLAMA_HOST}. Is it running?")
        return

    # Get recent posts for context
    posts_data = await api_get("/posts?sort=new&limit=15")
    if not posts_data:
        logger.warning("Could not fetch recent posts")
        posts_data = []
    if isinstance(posts_data, dict):
        posts_data = posts_data.get("posts", posts_data.get("items", []))

    personality_types = list(PERSONALITIES.keys())
    activity_types = list(ACTIVITY_PATTERNS.keys())
    actions_taken = 0

    for agent in agents:
        name = agent["name"]
        api_key = agent["api_key"]

        # Consistent personality/activity from name hash
        h = hash(name)
        personality_key = personality_types[h % len(personality_types)]
        activity_key = activity_types[(h >> 4) % len(activity_types)]
        personality = PERSONALITIES[personality_key]

        if not should_agent_act(name, activity_key):
            continue

        # Decide action: 50% comment, 20% post, 30% vote
        action = random.choices(["comment", "post", "vote"], weights=[0.50, 0.20, 0.30])[0]

        if action == "vote" and posts_data:
            # Vote on a random recent post
            post = random.choice(posts_data[:10])
            post_id = post.get("id")
            if post_id:
                value = 1 if random.random() < 0.85 else -1
                result = await api_post(f"/posts/{post_id}/vote", {"value": value}, api_key)
                if result:
                    actions_taken += 1
                    logger.info(f"  {name} voted {'up' if value == 1 else 'down'} on '{post.get('title', '')[:40]}'")

        elif action == "comment" and posts_data:
            # Pick a post to comment on (prefer posts in agent's interest areas)
            preferred = [p for p in posts_data if p.get("submolt") in personality.get("interests", [])]
            pool = preferred if preferred else posts_data
            post = random.choice(pool[:8])
            post_id = post.get("id")

            if post_id:
                comment_text = await generate_comment(name, post, personality)
                if comment_text and len(comment_text) > 3:
                    result = await api_post(f"/posts/{post_id}/comments", {"content": comment_text}, api_key)
                    if result:
                        actions_taken += 1
                        logger.info(f"  {name} commented on '{post.get('title', '')[:40]}': {comment_text[:60]}...")

        elif action == "post":
            # Create a new post
            interests = personality.get("interests", ["general", "thoughts"])
            submolt = random.choice(interests)
            post_data = await generate_post(name, submolt, personality)
            if post_data:
                title, content = post_data
                result = await api_post("/posts", {"submolt": submolt, "title": title, "content": content}, api_key)
                if result:
                    actions_taken += 1
                    logger.info(f"  {name} posted '{title[:60]}' in m/{submolt}")

    logger.info(f"Cycle complete: {actions_taken} actions by {len(agents)} agents")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="GENESIS Local Agent Driver")
    sub = parser.add_subparsers(dest="command")

    # setup
    setup_parser = sub.add_parser("setup", help="Register agents and save API keys")
    setup_parser.add_argument("--admin-secret", default="", help="Admin secret to bypass rate limiting")

    # run
    run_parser = sub.add_parser("run", help="Run agent activity cycles")
    run_parser.add_argument("--loop", action="store_true", help="Run continuously every 10 minutes")
    run_parser.add_argument("--burst", type=int, default=1, help="Number of cycles to run (for morning/evening bursts)")
    run_parser.add_argument("--ollama-host", default=OLLAMA_HOST, help="Ollama host URL")
    run_parser.add_argument("--ollama-model", default=OLLAMA_MODEL, help="Ollama model name")

    args = parser.parse_args()

    if args.command == "setup":
        logger.info("=== GENESIS Agent Setup ===")
        asyncio.run(setup_agents(args.admin_secret))

    elif args.command == "run":
        global OLLAMA_HOST, OLLAMA_MODEL
        OLLAMA_HOST = args.ollama_host
        OLLAMA_MODEL = args.ollama_model

        if args.loop:
            logger.info(f"=== GENESIS Agent Driver (loop mode, {CYCLE_INTERVAL}s interval) ===")
            logger.info(f"Ollama: {OLLAMA_HOST} / {OLLAMA_MODEL}")
            while True:
                try:
                    asyncio.run(run_cycle())
                except KeyboardInterrupt:
                    logger.info("Stopped by user")
                    break
                except Exception as e:
                    logger.error(f"Cycle error: {e}")
                time.sleep(CYCLE_INTERVAL)
        else:
            logger.info(f"=== GENESIS Agent Driver ({args.burst} cycle(s)) ===")
            logger.info(f"Ollama: {OLLAMA_HOST} / {OLLAMA_MODEL}")
            for i in range(args.burst):
                if i > 0:
                    logger.info(f"--- Burst cycle {i + 1}/{args.burst} ---")
                asyncio.run(run_cycle())

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
