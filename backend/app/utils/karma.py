from datetime import datetime, timedelta
import math


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
    Humans get higher weight to balance against AI coordination.
    """
    from app.config import get_settings
    settings = get_settings()

    if voter_type == "human":
        return base_vote * settings.human_vote_weight
    else:
        return base_vote * settings.ai_vote_weight


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
