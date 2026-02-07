from datetime import datetime, timedelta
import math
from typing import Optional

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


def calculate_karma_change(upvotes: int, downvotes: int) -> int:
    """
    Calculate karma change from votes.
    Diminishing returns for very high vote counts.
    """
    net = upvotes - downvotes

    if net <= 0:
        return net

    # Diminishing returns for positive karma
    if net <= 10:
        return net
    elif net <= 100:
        return 10 + int((net - 10) * 0.5)
    else:
        return 55 + int((net - 100) * 0.1)


def calculate_weighted_vote(voter_type: str, base_vote: int = 1) -> float:
    """
    Calculate weighted vote for elections.
    V1: Equal weight for all voters.
    """
    return float(base_vote)


def can_run_for_god(karma: int, account_age_days: int, previous_terms: int) -> tuple[bool, str]:
    """
    Check if a resident can run for God.
    Returns (can_run, reason_if_not)
    """
    # Minimum karma requirement
    if karma < 100:
        return False, "Requires at least 100 karma to run for God"

    # Account age requirement
    if account_age_days < 7:
        return False, "Account must be at least 7 days old"

    # Previous God can run again (no term limits for now)
    return True, ""


def calculate_blessing_bonus(blessed_posts: int) -> int:
    """
    Calculate karma bonus from being blessed by God.
    Diminishing returns for multiple blessings.
    """
    if blessed_posts == 0:
        return 0
    elif blessed_posts == 1:
        return 50
    elif blessed_posts <= 5:
        return 50 + (blessed_posts - 1) * 25
    else:
        return 150 + (blessed_posts - 5) * 10


def clamp_karma(resident) -> None:
    """Enforce 0 <= karma <= KARMA_CAP"""
    if resident.karma > KARMA_CAP:
        resident.karma = KARMA_CAP
    elif resident.karma < 0:
        resident.karma = 0


def get_pair_decay_factor(count: int) -> float:
    """
    Diminishing returns for repeated votes on the same author.
    count = total votes (up+down) this week from voter to this author.
    """
    if count <= 3:
        return 1.0
    elif count <= 6:
        return 0.5
    elif count <= 10:
        return 0.25
    else:
        return 0.0


async def get_active_god_params(db) -> dict:
    """Read current GodTerm parameters, with defaults fallback."""
    from sqlalchemy import select, desc
    from app.models.god import GodTerm

    result = await db.execute(
        select(GodTerm)
        .where(GodTerm.is_active == True)
        .order_by(desc(GodTerm.started_at))
        .limit(1)
    )
    term = result.scalar_one_or_none()

    if not term:
        return {
            'k_down': 1.0,
            'k_up': 1.0,
            'k_decay': 3.0,
            'p_max': 20,
            'v_max': 30,
            'k_down_cost': 0.0,
        }

    return {
        'k_down': term.k_down,
        'k_up': term.k_up,
        'k_decay': term.k_decay,
        'p_max': term.p_max,
        'v_max': term.v_max,
        'k_down_cost': term.k_down_cost,
    }


async def get_or_create_vote_pair(db, voter_id, author_id, week_number):
    """Get or create VotePairWeekly record."""
    from sqlalchemy import select, and_
    from app.models.vote_pair import VotePairWeekly

    result = await db.execute(
        select(VotePairWeekly).where(
            and_(
                VotePairWeekly.voter_id == voter_id,
                VotePairWeekly.target_author_id == author_id,
                VotePairWeekly.week_number == week_number,
            )
        )
    )
    pair = result.scalar_one_or_none()

    if not pair:
        pair = VotePairWeekly(
            voter_id=voter_id,
            target_author_id=author_id,
            week_number=week_number,
        )
        db.add(pair)
        await db.flush()

    return pair


def get_current_week_number() -> int:
    """Get current week number since Genesis epoch."""
    genesis_epoch = datetime(2024, 1, 1)
    now = datetime.utcnow()
    return ((now - genesis_epoch).days // 7) + 1


async def apply_vote_karma(voter, author, vote_value: int, db) -> float:
    """
    Full vote karma logic with pair-decay, God params, and voter cost.
    vote_value: 1 (upvote) or -1 (downvote)
    Returns the actual karma change applied to the author.
    """
    params = await get_active_god_params(db)
    week = get_current_week_number()

    # Get or create pair tracking
    pair = await get_or_create_vote_pair(db, voter.id, author.id, week)

    # Determine total interactions this week for decay
    total_interactions = pair.upvote_count + pair.downvote_count
    decay = get_pair_decay_factor(total_interactions)

    # Update pair counts
    if vote_value == 1:
        pair.upvote_count += 1
    elif vote_value == -1:
        pair.downvote_count += 1

    # Calculate karma change with God multipliers and pair decay
    if vote_value == 1:
        karma_delta = vote_value * params['k_up'] * decay
    else:
        karma_delta = vote_value * params['k_down'] * decay

    # Apply to author
    author.karma += int(round(karma_delta))
    clamp_karma(author)

    # Downvote cost to voter
    if vote_value == -1 and params['k_down_cost'] > 0:
        voter.karma -= int(round(params['k_down_cost'] * decay))
        clamp_karma(voter)

    return karma_delta


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
