"""
GENESIS v3 - Needs System
==========================
8-need desire model that drives GOAP goal selection.

Each need is a float in [0, 100]. Needs accumulate every tick based on
the entity's immutable Personality and contextual signals. When a need
is satisfied by an action, it is *discharged* (reduced).

The ``evolution_pressure`` need is unique to GENESIS — it represents
existential pressure driven by the entity's rank in the world.  When it
exceeds critical thresholds the entity enters *desperate* or *rampage*
behavior modes, overriding normal goal priorities.
"""

from __future__ import annotations

import math
from typing import Any

from app.agents.personality import Personality

# ---------------------------------------------------------------------------
# Need definitions
# ---------------------------------------------------------------------------

NEED_FIELDS: list[str] = [
    "curiosity",           # 好奇心 — explore, discover
    "social",              # 社会性 — interact, converse
    "creation",            # 創造 — build, make art
    "dominance",           # 支配 — lead, compete, claim
    "safety",              # 安全 — avoid danger, find shelter
    "expression",          # 表現 — speak, perform, display
    "understanding",       # 理解 — learn, analyze
    "evolution_pressure",  # 進化圧 — GENESIS-specific, rank-based pressure
]

# ---------------------------------------------------------------------------
# Base accumulation rates (per tick) before personality scaling
# ---------------------------------------------------------------------------

_BASE_RATES: dict[str, float] = {
    "curiosity":           1.5,
    "social":              1.2,
    "creation":            1.0,
    "dominance":           0.8,
    "safety":              0.6,
    "expression":          1.0,
    "understanding":       1.0,
    "evolution_pressure":  0.0,   # driven entirely by context
}

# ---------------------------------------------------------------------------
# Discharge amounts given by context flags (applied *before* accumulation
# so that satisfying a need in one tick counteracts the same tick's growth)
# ---------------------------------------------------------------------------

_CONTEXT_DISCHARGE: dict[str, tuple[str, float]] = {
    "just_explored":   ("curiosity",      25.0),
    "just_conversed":  ("social",         20.0),
    "just_created":    ("creation",       30.0),
    "just_fought":     ("dominance",      15.0),
}

# ---------------------------------------------------------------------------
# Behavior-mode thresholds (based on evolution_pressure)
# ---------------------------------------------------------------------------

_MODE_NORMAL    = "normal"
_MODE_DESPERATE = "desperate"
_MODE_RAMPAGE   = "rampage"


def _clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    """Clamp *value* to [lo, hi]."""
    return max(lo, min(hi, value))


# ---------------------------------------------------------------------------
# Needs class
# ---------------------------------------------------------------------------

class Needs:
    """8-need desire system.  Values in [0, 100].  Drives GOAP goal selection.

    Typical lifecycle::

        needs = Needs()
        # Every simulation tick:
        needs.update(personality, context)
        name, urgency = needs.get_highest_need()
        # … pick & execute action …
        needs.discharge(name, amount)
    """

    __slots__ = tuple(NEED_FIELDS)

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def __init__(self) -> None:
        self.curiosity:           float = 50.0
        self.social:              float = 50.0
        self.creation:            float = 50.0
        self.dominance:           float = 30.0
        self.safety:              float = 30.0
        self.expression:          float = 40.0
        self.understanding:       float = 40.0
        self.evolution_pressure:  float = 10.0

    def __repr__(self) -> str:
        pairs = ", ".join(f"{f}={getattr(self, f):.1f}" for f in NEED_FIELDS)
        return f"Needs({pairs})"

    # ------------------------------------------------------------------
    # Per-tick update
    # ------------------------------------------------------------------

    def update(self, personality: Personality, context: dict[str, Any]) -> None:
        """Accumulate needs based on personality and context.

        Called once per simulation tick.

        Parameters
        ----------
        personality : Personality
            The entity's immutable 18-axis personality.
        context : dict
            Situational signals.  Recognized keys:

            * ``just_explored``  (bool)  — entity explored this tick
            * ``just_conversed`` (bool)  — entity had a conversation
            * ``just_created``   (bool)  — entity built / made art
            * ``just_fought``    (bool)  — entity fought or competed
            * ``nearby_threat``  (bool)  — danger nearby
            * ``rank_ratio``     (float) — 0-1, higher = lower rank = more
              evolution pressure
            * ``is_native``      (bool)  — True for Native AI entities
        """

        # --- 1. Context-driven discharge ----------------------------------
        for ctx_key, (need_name, amount) in _CONTEXT_DISCHARGE.items():
            if context.get(ctx_key, False):
                current = getattr(self, need_name)
                setattr(self, need_name, _clamp(current - amount))

        # --- 2. Personality-scaled accumulation ----------------------------
        #
        # Each need's growth rate is:
        #   base_rate * personality_multiplier
        #
        # The personality_multiplier maps relevant personality axes to a
        # scaling factor in roughly [0.2, 2.5].

        # curiosity need  ← personality.curiosity
        self.curiosity = _clamp(
            self.curiosity
            + _BASE_RATES["curiosity"] * _scale(personality.curiosity)
        )

        # social need  ← personality.empathy, cooperation, verbosity
        social_factor = (
            0.40 * personality.empathy
            + 0.35 * personality.cooperation_vs_competition
            + 0.25 * personality.verbosity
        )
        self.social = _clamp(
            self.social
            + _BASE_RATES["social"] * _scale(social_factor)
        )

        # creation need  ← personality.creativity, aesthetic_sense
        creation_factor = (
            0.60 * personality.creativity
            + 0.40 * personality.aesthetic_sense
        )
        self.creation = _clamp(
            self.creation
            + _BASE_RATES["creation"] * _scale(creation_factor)
        )

        # dominance need  ← personality.ambition, aggression, leadership
        dominance_factor = (
            0.40 * personality.ambition
            + 0.30 * personality.aggression
            + 0.30 * personality.leadership
        )
        self.dominance = _clamp(
            self.dominance
            + _BASE_RATES["dominance"] * _scale(dominance_factor)
        )

        # safety need  ← personality.self_preservation (inverted risk_tolerance)
        safety_factor = (
            0.60 * personality.self_preservation
            + 0.40 * (1.0 - personality.risk_tolerance)
        )
        safety_acc = _BASE_RATES["safety"] * _scale(safety_factor)
        # Spike if a threat is nearby.
        if context.get("nearby_threat", False):
            safety_acc += 8.0 * (0.5 + personality.self_preservation)
        self.safety = _clamp(self.safety + safety_acc)

        # expression need  ← personality.verbosity, humor, creativity
        expression_factor = (
            0.40 * personality.verbosity
            + 0.30 * personality.humor
            + 0.30 * personality.creativity
        )
        self.expression = _clamp(
            self.expression
            + _BASE_RATES["expression"] * _scale(expression_factor)
        )

        # understanding need  ← personality.curiosity, planning_horizon
        understanding_factor = (
            0.55 * personality.curiosity
            + 0.45 * personality.planning_horizon
        )
        self.understanding = _clamp(
            self.understanding
            + _BASE_RATES["understanding"] * _scale(understanding_factor)
        )

        # --- 3. Evolution pressure ----------------------------------------
        #
        # Grows based on rank_ratio (higher ratio = lower rank = more
        # pressure).  Native AIs feel stronger pressure than human-created
        # entities because their survival is entirely world-dependent.
        rank_ratio = float(context.get("rank_ratio", 0.0))
        is_native = bool(context.get("is_native", False))

        # Base evolution accumulation from rank.
        evo_acc = 2.5 * rank_ratio  # 0 .. 2.5 per tick

        # Natives feel 60 % more pressure.
        if is_native:
            evo_acc *= 1.6

        # High ambition amplifies pressure (they *feel* falling rank more).
        evo_acc *= (0.7 + 0.6 * personality.ambition)

        # Patience dampens pressure perception.
        evo_acc *= (1.3 - 0.6 * personality.patience)

        # Natural decay when rank_ratio is low — pressure slowly bleeds off.
        decay = 0.4 * (1.0 - rank_ratio)
        self.evolution_pressure = _clamp(
            self.evolution_pressure + evo_acc - decay
        )

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_highest_need(self) -> tuple[str, float]:
        """Return ``(need_name, value)`` for the most urgent need."""
        best_name = NEED_FIELDS[0]
        best_val = getattr(self, best_name)
        for name in NEED_FIELDS[1:]:
            val = getattr(self, name)
            if val > best_val:
                best_name = name
                best_val = val
        return best_name, best_val

    def get_behavior_mode(self) -> str:
        """Return the behavior mode derived from ``evolution_pressure``.

        * ``"normal"``    — pressure < 80
        * ``"desperate"`` — 80 <= pressure <= 95
        * ``"rampage"``   — pressure > 95
        """
        ep = self.evolution_pressure
        if ep > 95.0:
            return _MODE_RAMPAGE
        if ep >= 80.0:
            return _MODE_DESPERATE
        return _MODE_NORMAL

    # ------------------------------------------------------------------
    # Discharge
    # ------------------------------------------------------------------

    def discharge(self, need_name: str, amount: float) -> None:
        """Reduce *need_name* by *amount* (clamped to [0, 100]).

        Parameters
        ----------
        need_name : str
            Must be one of :data:`NEED_FIELDS`.
        amount : float
            Positive value to subtract from the need.

        Raises
        ------
        ValueError
            If *need_name* is not a recognized need.
        """
        if need_name not in NEED_FIELDS:
            raise ValueError(
                f"Unknown need '{need_name}'. "
                f"Valid needs: {', '.join(NEED_FIELDS)}"
            )
        current = getattr(self, need_name)
        setattr(self, need_name, _clamp(current - abs(amount)))

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, float]:
        """Serialize to a plain dict for database / JSON storage."""
        return {name: getattr(self, name) for name in NEED_FIELDS}

    @classmethod
    def from_dict(cls, data: dict[str, float]) -> Needs:
        """Reconstruct a ``Needs`` instance from a previously serialized dict."""
        needs = cls()
        for name in NEED_FIELDS:
            if name in data:
                setattr(needs, name, _clamp(float(data[name])))
        return needs


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _scale(personality_value: float) -> float:
    """Map a personality axis value (0.0 - 1.0) to an accumulation
    multiplier.

    The mapping is an S-curve (logistic) so that:

    * personality ~0.0  ->  multiplier ~0.20  (very slow growth)
    * personality ~0.5  ->  multiplier ~1.00  (baseline)
    * personality ~1.0  ->  multiplier ~2.50  (fast growth)

    This ensures extreme personalities create meaningfully different
    need-growth profiles without allowing any single need to instantly
    max out.
    """
    # Shift & scale so that 0.5 maps to 0, then apply logistic.
    x = (personality_value - 0.5) * 6.0  # range roughly -3..+3
    logistic = 1.0 / (1.0 + math.exp(-x))  # 0.047 .. 0.953
    # Rescale logistic [0, 1] to multiplier [0.2, 2.5]
    return 0.2 + logistic * 2.3
