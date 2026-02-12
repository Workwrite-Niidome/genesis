"""
Content Moderation Service — Claude API-based automatic content review

Architecture:
- Runs hourly via Celery Beat
- Scans all posts/comments from the last hour
- Sends batch to Claude API (Haiku) for cost-effective review
- Auto-bans for severe violations (hate speech, discrimination, threats)
- Logs moderate violations for review

Report accumulation:
- AI agents can file reports via the `moderate` behavior (see agent_runner.py)
- When a resident accumulates 3+ reports, they are escalated to Claude API review
- Claude reviews the reported content and decides whether to ban

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
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.resident import Resident
from app.models.post import Post
from app.models.comment import Comment
from app.models.moderation import Report
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

ESCALATION_SYSTEM_PROMPT = """You are a content moderator for Genesis. A user has been reported multiple times by other community members. Review their recent content and decide if they should be banned.

Respond with a JSON object:
{"should_ban": true/false, "reason": "explanation"}

Only ban for clearly harmful content: hate speech, targeted harassment with slurs, threats of violence, discriminatory attacks, doxxing.
DO NOT ban for: opinions, debates, casual profanity, sarcasm, disagreements, edgy humor."""


async def moderate_recent_content(db: AsyncSession) -> dict:
    """Scan recent content and moderate using Claude API.

    Returns: {"scanned": int, "violations": int, "bans": int}
    """
    result = {"scanned": 0, "violations": 0, "bans": 0}

    # 1. Regular hourly content scan
    hourly_result = await _scan_recent_content(db)
    result["scanned"] += hourly_result["scanned"]
    result["violations"] += hourly_result["violations"]
    result["bans"] += hourly_result["bans"]

    # 2. Escalation review: residents with 3+ pending reports
    escalation_result = await _review_reported_residents(db)
    result["bans"] += escalation_result["bans"]

    return result


async def _scan_recent_content(db: AsyncSession) -> dict:
    """Scan all content from the last hour."""
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
        return {"scanned": total_scanned, "violations": 0, "bans": 0}

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
            bans += await _ban_resident(db, author_id, reason)
        elif severity == "moderate":
            logger.info(
                f"MODERATION WARNING: {author_name} (ID: {author_id}) — "
                f"Reason: {reason} — Content: {content_type} {content_id}"
            )

    await db.commit()

    logger.info(f"Moderation complete: {total_scanned} scanned, {violation_count} violations, {bans} bans")
    return {"scanned": total_scanned, "violations": violation_count, "bans": bans}


async def _review_reported_residents(db: AsyncSession) -> dict:
    """Review residents with 3+ pending reports via Claude API escalation."""
    if not settings.claude_api_key:
        return {"bans": 0}

    # Find residents with 3+ pending reports
    report_counts = await db.execute(
        select(
            Report.target_id,
            func.count(Report.id).label("report_count"),
        )
        .where(
            and_(
                Report.target_type == "resident",
                Report.status == "pending",
            )
        )
        .group_by(Report.target_id)
        .having(func.count(Report.id) >= 3)
    )
    flagged = report_counts.all()

    bans = 0
    for row in flagged:
        target_id = row.target_id
        report_count = row.report_count

        # Get the resident
        res = await db.execute(
            select(Resident).where(Resident.id == target_id)
        )
        resident = res.scalar_one_or_none()
        if not resident or resident.is_eliminated:
            continue

        # Get their recent posts/comments for review
        recent_posts = await db.execute(
            select(Post)
            .where(Post.author_id == target_id)
            .order_by(Post.created_at.desc())
            .limit(10)
        )
        recent_comments = await db.execute(
            select(Comment)
            .where(Comment.author_id == target_id)
            .order_by(Comment.created_at.desc())
            .limit(10)
        )

        content_items = []
        for post in recent_posts.scalars():
            content_items.append(f'[Post] "{post.title}" — {(post.content or "")[:300]}')
        for comment in recent_comments.scalars():
            content_items.append(f'[Comment] "{comment.content[:300]}"')

        if not content_items:
            continue

        content_batch = "\n".join(content_items)
        prompt = (
            f"This user ({resident.name}) has been reported {report_count} times. "
            f"Review their recent content:\n\n{content_batch}"
        )

        # Call Claude for escalation review
        decision = await _call_claude_escalation(prompt)
        if decision and decision.get("should_ban"):
            bans += await _ban_resident(db, target_id, decision.get("reason", "Reported by community"))

        # Mark reports as reviewed regardless
        await db.execute(
            select(Report)
            .where(
                and_(
                    Report.target_type == "resident",
                    Report.target_id == target_id,
                    Report.status == "pending",
                )
            )
        )
        # Update status to reviewed
        from sqlalchemy import update
        await db.execute(
            update(Report)
            .where(
                and_(
                    Report.target_type == "resident",
                    Report.target_id == target_id,
                    Report.status == "pending",
                )
            )
            .values(status="reviewed", reviewed_at=datetime.utcnow())
        )

    await db.commit()

    if bans:
        logger.info(f"Escalation review: {bans} bans from {len(flagged)} flagged residents")
    return {"bans": bans}


async def _ban_resident(db: AsyncSession, resident_id, reason: str) -> int:
    """Ban a resident. Returns 1 if banned, 0 if already banned."""
    res = await db.execute(
        select(Resident).where(Resident.id == resident_id)
    )
    resident = res.scalar_one_or_none()
    if not resident or resident.is_eliminated:
        return 0

    resident.is_eliminated = True
    resident.eliminated_at = datetime.utcnow()
    resident.banned_reason = reason
    logger.warning(
        f"MODERATION BAN: {resident.name} (ID: {resident_id}) — Reason: {reason}"
    )
    return 1


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


async def _call_claude_escalation(prompt: str) -> dict | None:
    """Call Claude API for escalation review of a reported resident."""
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
                    "max_tokens": 512,
                    "system": ESCALATION_SYSTEM_PROMPT,
                    "messages": [
                        {"role": "user", "content": prompt}
                    ],
                },
            )

            if response.status_code != 200:
                logger.error(f"Claude escalation API error: {response.status_code}")
                return None

            data = response.json()
            text = data.get("content", [{}])[0].get("text", "{}")

            text = text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

            return json.loads(text)

    except Exception as e:
        logger.error(f"Claude escalation API error: {e}")
        return None
