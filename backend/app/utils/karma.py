from datetime import datetime
import math


KARMA_CAP = 500
KARMA_START = 50


def calculate_hot_score(upvotes: int, downvotes: int, created_at: datetime) -> float:
    """
    Calculate hot score for post ranking.
    Based on Reddit's hot algorithm with Genesis modifications.
    """
    score = upvotes - downvotes
    order = math.log10(max(abs(score), 1))

    if score > 0:
        sign = 1
    elif score < 0:
        sign = -1
    else:
        sign = 0

    # Seconds since epoch (using a Genesis-specific epoch)
    genesis_epoch = datetime(2024, 1, 1)
    seconds = (created_at - genesis_epoch).total_seconds()

    return round(sign * order + seconds / 45000, 7)


def get_default_limits() -> dict:
    """Return default post/vote limits (no God system)."""
    return {
        'p_max': 20,
        'v_max': 50,
    }


async def get_daily_vote_count(db, resident_id) -> int:
    """Count votes cast today by a resident."""
    from sqlalchemy import select, func, and_
    from app.models.vote import Vote

    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    result = await db.execute(
        select(func.count(Vote.id)).where(
            and_(
                Vote.resident_id == resident_id,
                Vote.created_at >= today_start,
            )
        )
    )
    return result.scalar() or 0


async def get_daily_post_count(db, resident_id) -> int:
    """Count posts created today by a resident."""
    from sqlalchemy import select, func, and_
    from app.models.post import Post

    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    result = await db.execute(
        select(func.count(Post.id)).where(
            and_(
                Post.author_id == resident_id,
                Post.created_at >= today_start,
            )
        )
    )
    return result.scalar() or 0
