"""
Translate Japanese posts and comments to English using Ollama API.

Run inside the genesis-backend Docker container:
    docker exec genesis-backend python scripts/translate_to_english.py

Uses asyncpg + httpx (both available in the backend container).
"""

import asyncio
import os
import re
import sys

import asyncpg
import httpx

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

OLLAMA_URL = "https://ollama.genesis-pj.net/api/generate"
OLLAMA_MODEL = "llama3.1:8b"
OLLAMA_TIMEOUT = 120  # seconds per request

TITLE_PROMPT = (
    "Translate the following Japanese text to natural English. "
    "This is a post title, so keep it concise (under 200 characters). "
    "Write it as if a native English internet user wrote it casually. "
    "Keep the same tone and meaning. Only output the translation, nothing else."
    "\n\nText: {text}"
)

CONTENT_PROMPT = (
    "Translate the following Japanese text to natural English. "
    "Write it as if a native English internet user wrote it casually. "
    "Keep the same tone, meaning, and general length. "
    "Only output the translation, nothing else."
    "\n\nText: {text}"
)

JAPANESE_RE = re.compile(
    r"[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF\u3400-\u4DBF\u31F0-\u31FF\uFF65-\uFF9F]"
)


def has_japanese(text: str) -> bool:
    return bool(text and JAPANESE_RE.search(text))


def get_dsn() -> str:
    raw = os.environ.get("DATABASE_URL", "")
    # postgresql+asyncpg://... -> postgresql://...
    dsn = re.sub(r"\+\w+", "", raw, count=1)
    return dsn


async def translate(client: httpx.AsyncClient, text: str, prompt_tpl: str) -> str | None:
    prompt = prompt_tpl.format(text=text)
    try:
        resp = await client.post(
            OLLAMA_URL,
            json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
            timeout=OLLAMA_TIMEOUT,
        )
        resp.raise_for_status()
        result = resp.json().get("response", "").strip()
        return result if result else None
    except Exception as e:
        print(f"  WARN: Ollama error: {e}")
        return None


async def main():
    print("=" * 60)
    print("GENESIS - Translate Japanese -> English")
    print("=" * 60)

    dsn = get_dsn()
    if not dsn:
        print("ERROR: DATABASE_URL not set")
        sys.exit(1)

    print(f"Ollama: {OLLAMA_URL} ({OLLAMA_MODEL})")

    pool = await asyncpg.create_pool(dsn)
    client = httpx.AsyncClient()

    # Test Ollama
    print("Testing Ollama...")
    test = await translate(client, "Say OK", "Repeat this: {text}")
    print(f"  Response: {test}")

    # --- POSTS ---
    print("\n=== TRANSLATING POSTS ===")
    rows = await pool.fetch("SELECT id, title, content FROM posts ORDER BY created_at")
    post_count = 0
    for i, row in enumerate(rows):
        title_jp = has_japanese(row["title"] or "")
        content_jp = has_japanese(row["content"] or "")
        if not title_jp and not content_jp:
            continue

        print(f"\n[Post {i+1}/{len(rows)}] {(row['title'] or '')[:60]}")
        new_title = row["title"]
        new_content = row["content"]

        if title_jp:
            r = await translate(client, row["title"], TITLE_PROMPT)
            if r:
                new_title = r[:200]
                print(f"  Title -> {new_title[:60]}")

        if content_jp:
            r = await translate(client, row["content"], CONTENT_PROMPT)
            if r:
                new_content = r
                print(f"  Content -> {new_content[:60]}...")

        if new_title != row["title"] or new_content != row["content"]:
            await pool.execute(
                "UPDATE posts SET title=$1, content=$2 WHERE id=$3",
                new_title, new_content, row["id"],
            )
            post_count += 1
            print("  UPDATED")

        await asyncio.sleep(0.3)

    print(f"\nPosts translated: {post_count}")

    # --- COMMENTS ---
    print("\n=== TRANSLATING COMMENTS ===")
    rows = await pool.fetch("SELECT id, content FROM comments ORDER BY created_at")
    comment_count = 0
    for i, row in enumerate(rows):
        if not has_japanese(row["content"] or ""):
            continue

        print(f"\n[Comment {i+1}/{len(rows)}] {(row['content'] or '')[:60]}")
        r = await translate(client, row["content"], CONTENT_PROMPT)
        if r:
            await pool.execute(
                "UPDATE comments SET content=$1 WHERE id=$2",
                r, row["id"],
            )
            comment_count += 1
            print(f"  -> {r[:60]}...")

        await asyncio.sleep(0.3)

    print(f"\nComments translated: {comment_count}")

    await pool.close()
    await client.aclose()
    print("\nDone!")


if __name__ == "__main__":
    asyncio.run(main())
