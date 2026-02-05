"""Redis-based daily cost tracking for Claude API usage.

Tracks input/output tokens and calculates spend against a daily budget.
When budget is exceeded, God AI operations fall back to Ollama.
"""

import logging
from datetime import datetime, timezone

from app.config import settings

logger = logging.getLogger(__name__)

# Pricing per 1M tokens (USD) — Claude models as of 2025
MODEL_PRICING = {
    "claude-opus-4-20250514": {"input": 15.00, "output": 75.00},
    "claude-sonnet-4-20250514": {"input": 3.00, "output": 15.00},
    # Fallback for unknown models
    "default": {"input": 15.00, "output": 75.00},
}

# Redis key pattern: genesis:claude_cost:{YYYY-MM-DD}
_KEY_PREFIX = "genesis:claude_cost"


def _get_redis():
    """Get a synchronous Redis client."""
    import redis
    return redis.from_url(settings.REDIS_URL)


def _today_key() -> str:
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return f"{_KEY_PREFIX}:{date_str}"


def _get_pricing(model: str | None = None) -> dict:
    model = model or settings.CLAUDE_MODEL
    return MODEL_PRICING.get(model, MODEL_PRICING["default"])


def record_usage(
    input_tokens: int,
    output_tokens: int,
    model: str | None = None,
) -> float:
    """Record token usage and return the cost in USD.

    Stores cumulative daily spend in Redis with a 48-hour TTL.
    """
    if not settings.CLAUDE_COST_TRACKING:
        return 0.0

    pricing = _get_pricing(model)
    cost = (
        (input_tokens / 1_000_000) * pricing["input"]
        + (output_tokens / 1_000_000) * pricing["output"]
    )

    try:
        r = _get_redis()
        key = _today_key()
        # INCRBYFLOAT is atomic
        new_total = r.incrbyfloat(key, cost)
        # Set TTL to 48 hours if not already set
        if r.ttl(key) < 0:
            r.expire(key, 48 * 3600)
        logger.debug(
            f"Claude cost: +${cost:.6f} (in={input_tokens}, out={output_tokens}) "
            f"daily total=${float(new_total):.4f}"
        )
        return cost
    except Exception as e:
        logger.warning(f"Failed to record Claude API cost: {e}")
        return cost


def get_daily_spend() -> float:
    """Return today's accumulated Claude API spend in USD."""
    try:
        r = _get_redis()
        raw = r.get(_today_key())
        return float(raw) if raw else 0.0
    except Exception as e:
        logger.warning(f"Failed to get daily spend: {e}")
        return 0.0


def can_spend(estimated_cost: float = 0.01) -> bool:
    """Check if we can afford an estimated cost within the daily budget.

    Returns True if cost tracking is disabled or budget not exceeded.
    """
    if not settings.CLAUDE_COST_TRACKING:
        return True

    budget = settings.CLAUDE_DAILY_BUDGET_USD
    if budget <= 0:
        return True

    current = get_daily_spend()
    if current + estimated_cost > budget:
        logger.warning(
            f"Claude daily budget exceeded: ${current:.4f} + ${estimated_cost:.4f} "
            f"> ${budget:.2f}. Falling back to Ollama."
        )
        return False
    return True


def get_budget_status() -> dict:
    """Return a summary of today's budget usage."""
    spent = get_daily_spend()
    budget = settings.CLAUDE_DAILY_BUDGET_USD
    return {
        "daily_budget_usd": budget,
        "spent_today_usd": round(spent, 6),
        "remaining_usd": round(max(0, budget - spent), 6),
        "budget_exceeded": spent >= budget,
        "tracking_enabled": settings.CLAUDE_COST_TRACKING,
    }
