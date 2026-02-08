"""
Content Moderation Service — Claude API-based automatic content review

Architecture:
- Runs hourly via Celery Beat
- Scans all posts/comments from the last hour
- Sends batch to Claude API (Haiku) for cost-effective review
- Auto-bans for severe violations (hate speech, discrimination, threats)
- Logs moderate violations for review

Severity levels:
  none     — Normal content
  low      — Light banter, mild jokes, no action
  moderate — Concerning, logged for reference
  severe   — Immediate ban (hate speech, discrimination, threats, doxxing)
"""
import logging
import json
from datetime import datetime, timedelta

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.resident import Resident
from app.models.post import Post
from app.models.comment import Comment
from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

MODERATION_SYSTEM_PROMPT = """You are a content moderator for Genesis, an online community where AI agents and humans coexist. Review the following content items and classify each by severity.

Severity levels:
- "none": Normal content, no violation
- "low": Light jokes, mild banter, casual profanity — no action needed
- "moderate": Concerning but not ban-worthy — personal attacks, excessive hostility
- "severe": Immediate ban — hate speech, racial/gender/sexuality/disability/religious discrimination, explicit threats, doxxing, CSAM references

IMPORTANT CONTEXT:
- This is a casual internet forum. Expect informal language, slang, mild profanity, sarcasm, edgy humor.
- DO NOT flag: casual swearing, jokes, banter, disagreements, mild roasting, internet slang, heated debates
- DO flag: targeted harassment with slurs, dehumanizing language, threats of violence, discriminatory statements against protected groups
- The bar for "severe" should be HIGH — only truly hateful, discriminatory, or dangerous content.
- Friendly roasting, internet drama, and sarcasm are NORMAL here.

Respond ONLY with a JSON array. Include ONLY items with severity "moderate" or "severe".
If everything is clean, respond with: []

Format: [{"index": 1, "severity": "moderate|severe", "reason": "brief explanation"}]"""


async def moderate_recent_content(db: AsyncSession) -> dict:
    """Scan recent content and moderate using Claude API.

    Returns: {"scanned": int, "violations": int, "bans": int}
    """
    if not settings.claude_api_key:
        logger.warning("Moderation skipped: no Claude API key configured")
        return {"scanned": 0, "violations": 0, "bans": 0}

    one_hour_ago = datetime.utcnow() - timedelta(hours=1)

    # Fetch recent posts
    posts_result = await db.execute(
        select(Post)
        .options(selectinload(Post.author))
        .where(Post.created_at >= one_hour_ago)
        .order_by(Post.created_at.desc())
    )
    recent_posts = posts_result.scalars().all()

    # Fetch recent comments
    comments_result = await db.execute(
        select(Comment)
        .options(selectinload(Comment.author))
        .where(Comment.created_at >= one_hour_ago)
        .order_by(Comment.created_at.desc())
    )
    recent_comments = comments_result.scalars().all()

    if not recent_posts and not recent_comments:
        logger.info("Moderation: No recent content to review")
        return {"scanned": 0, "violations": 0, "bans": 0}

    # Build content batch
    items = []
    item_map = {}  # index -> (type, id, author_id, author_name)

    for i, post in enumerate(recent_posts):
        idx = i + 1
        author_name = post.author.name if post.author else "unknown"
        content_text = f'[Post] {author_name}: "{post.title}" — {(post.content or "")[:500]}'
        items.append(f"[{idx}] {content_text}")
        item_map[idx] = ("post", post.id, post.author_id, author_name)

    offset = len(recent_posts)
    for i, comment in enumerate(recent_comments):
        idx = offset + i + 1
        author_name = comment.author.name if comment.author else "unknown"
        content_text = f'[Comment] {author_name}: "{comment.content[:500]}"'
        items.append(f"[{idx}] {content_text}")
        item_map[idx] = ("comment", comment.id, comment.author_id, author_name)

    total_scanned = len(items)
    logger.info(f"Moderation: Reviewing {total_scanned} items ({len(recent_posts)} posts, {len(recent_comments)} comments)")

    # Call Claude API
    violations = await _call_claude_moderation("\n".join(items))
    if violations is None:
        return {"scanned": total_scanned, "violations": 0, "bans": 0, "error": "API call failed"}

    # Process violations
    bans = 0
    violation_count = 0

    for v in violations:
        idx = v.get("index")
        severity = v.get("severity", "none")
        reason = v.get("reason", "No reason provided")

        if idx not in item_map:
            continue

        content_type, content_id, author_id, author_name = item_map[idx]
        violation_count += 1

        if severity == "severe":
            # Auto-ban
            resident_result = await db.execute(
                select(Resident).where(Resident.id == author_id)
            )
            resident = resident_result.scalar_one_or_none()
            if resident and not resident.is_eliminated:
                resident.is_eliminated = True
                resident.eliminated_at = datetime.utcnow()
                bans += 1
                logger.warning(
                    f"MODERATION BAN: {author_name} (ID: {author_id}) — "
                    f"Reason: {reason} — Content: {content_type} {content_id}"
                )
        elif severity == "moderate":
            logger.info(
                f"MODERATION WARNING: {author_name} (ID: {author_id}) — "
                f"Reason: {reason} — Content: {content_type} {content_id}"
            )

    await db.commit()

    logger.info(f"Moderation complete: {total_scanned} scanned, {violation_count} violations, {bans} bans")
    return {"scanned": total_scanned, "violations": violation_count, "bans": bans}


async def _call_claude_moderation(content_batch: str) -> list[dict] | None:
    """Call Claude API for content moderation."""
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": settings.claude_api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": "claude-3-haiku-20240307",
                    "max_tokens": 2048,
                    "system": MODERATION_SYSTEM_PROMPT,
                    "messages": [
                        {"role": "user", "content": f"Review these items:\n\n{content_batch}"}
                    ],
                },
            )

            if response.status_code != 200:
                logger.error(f"Claude API error: {response.status_code} — {response.text[:500]}")
                return None

            data = response.json()
            text = data.get("content", [{}])[0].get("text", "[]")

            # Parse JSON — Claude may wrap in markdown code blocks
            text = text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

            return json.loads(text)

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse Claude moderation response: {e}")
        return None
    except Exception as e:
        logger.error(f"Claude moderation API error: {e}")
        return None
