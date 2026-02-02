"""World Rules: GOD AI-adjustable global parameters for the GENESIS world.

Energy-related rules have been removed. The field provides only basic physics.
GOD AI can add new rules via set_world_rule.
"""

from app.models.god_ai import GodAI

DEFAULT_WORLD_RULES: dict[str, float] = {
    "resource_regen_multiplier": 1.0,     # multiplier for resource node regeneration
    "max_world_radius": 300.0,            # maximum world radius
}

RULE_BOUNDS: dict[str, tuple[float, float]] = {
    "resource_regen_multiplier": (0.1, 5.0),
    "max_world_radius": (100.0, 1000.0),
}


def get_world_rules(god: GodAI) -> dict[str, float]:
    """Return effective world rules by merging defaults with GOD AI overrides."""
    overrides = (god.state or {}).get("world_rules", {})
    rules = dict(DEFAULT_WORLD_RULES)
    for key, value in overrides.items():
        if key in rules:
            rules[key] = float(value)
        else:
            # GOD AI can introduce new rules
            try:
                rules[key] = float(value)
            except (ValueError, TypeError):
                pass
    return rules


def validate_rule(rule: str, value: float) -> tuple[bool, float]:
    """Validate and clamp a rule value within RULE_BOUNDS.

    Returns (is_valid_key, clamped_value).
    For new rules not in RULE_BOUNDS, accept any float value.
    """
    if rule not in RULE_BOUNDS:
        # Allow GOD AI to create new rules with any value
        return True, float(value)
    lo, hi = RULE_BOUNDS[rule]
    return True, max(lo, min(hi, float(value)))
