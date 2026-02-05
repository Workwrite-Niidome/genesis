"""
GENESIS v3 - Personality System
================================
18-axis numeric personality model. Values are IMMUTABLE after creation.
Each axis is a float from 0.0 to 1.0.

These values represent an entity's core nature — they do not change
over the entity's lifetime. Mood, opinion, and memory are separate
systems that sit on top of this foundation.
"""

from __future__ import annotations

import json
import math
import random
from typing import Any

from app.llm.orchestrator import LLMRequest, llm_orchestrator

# ---------------------------------------------------------------------------
# Axis definitions
# ---------------------------------------------------------------------------

PERSONALITY_FIELDS: dict[str, str] = {
    # Value axes (0.0 ~ 1.0)
    "order_vs_chaos": "秩序 ↔ 自由",
    "cooperation_vs_competition": "協調 ↔ 競争",
    "curiosity": "好奇心",
    "ambition": "野心",
    "empathy": "共感力",
    "aggression": "攻撃性",
    "creativity": "創造性",
    "risk_tolerance": "リスク許容度",
    "self_preservation": "自己保存",
    "aesthetic_sense": "美的感覚",
    # Conversation style
    "verbosity": "寡黙 ↔ 饒舌",
    "politeness": "粗野 ↔ 丁寧",
    "leadership": "傾聴 ↔ 主導",
    "honesty": "嘘つき ↔ 正直",
    "humor": "真面目 ↔ ユーモア",
    # Behavior style
    "patience": "短気 ↔ 忍耐",
    "planning_horizon": "短期思考 ↔ 長期計画",
    "conformity": "反逆 ↔ 従順",
}

# Pairs of traits where HIGH+HIGH or LOW+LOW between two entities creates
# friction (negative compatibility contribution).  The float is the weight.
_CONFLICT_PAIRS: list[tuple[str, str, float]] = [
    ("leadership", "leadership", 1.5),         # two dominant leaders clash
    ("aggression", "aggression", 1.2),          # mutual aggression escalates
    ("dominance_proxy", "dominance_proxy", 1.0),  # mapped from ambition later
]

# Pairs where DIFFERENCE is harmonious (complementary).
_COMPLEMENT_PAIRS: list[tuple[str, str, float]] = [
    ("leadership", "conformity", 1.3),    # leader + follower
    ("verbosity", "patience", 1.0),       # talkative + patient listener
    ("creativity", "order_vs_chaos", 0.8),  # creative + structured = productive
    ("risk_tolerance", "self_preservation", 0.7),  # adventurer + cautious balance
]

# Pairs where SIMILARITY is harmonious.
_HARMONY_PAIRS: list[tuple[str, str, float]] = [
    ("cooperation_vs_competition", "cooperation_vs_competition", 1.4),
    ("honesty", "honesty", 1.2),
    ("humor", "humor", 1.0),
    ("politeness", "politeness", 0.9),
    ("aesthetic_sense", "aesthetic_sense", 0.6),
    ("planning_horizon", "planning_horizon", 0.8),
    ("empathy", "empathy", 1.0),
    ("curiosity", "curiosity", 0.7),
]

# ---------------------------------------------------------------------------
# Human-readable descriptors for extreme trait values
# ---------------------------------------------------------------------------

_TRAIT_DESCRIPTORS: dict[str, tuple[str, str]] = {
    # field: (low_description, high_description)
    "order_vs_chaos":              ("chaotic and free-spirited", "orderly and disciplined"),
    "cooperation_vs_competition":  ("fiercely competitive", "deeply cooperative"),
    "curiosity":                   ("incurious and set in their ways", "insatiably curious"),
    "ambition":                    ("content and unambitious", "burning with ambition"),
    "empathy":                     ("cold and detached", "profoundly empathic"),
    "aggression":                  ("gentle and passive", "aggressive and confrontational"),
    "creativity":                  ("practical and conventional", "wildly creative"),
    "risk_tolerance":              ("extremely risk-averse", "reckless thrill-seeker"),
    "self_preservation":           ("selfless to a fault", "intensely self-preserving"),
    "aesthetic_sense":             ("indifferent to beauty", "deeply aesthetic"),
    "verbosity":                   ("silent and terse", "verbose and talkative"),
    "politeness":                  ("blunt and crude", "unfailingly polite"),
    "leadership":                  ("a quiet listener", "a commanding leader"),
    "honesty":                     ("a habitual liar", "brutally honest"),
    "humor":                       ("dead serious", "always joking"),
    "patience":                    ("short-tempered and impulsive", "endlessly patient"),
    "planning_horizon":            ("lives in the moment", "a far-sighted strategist"),
    "conformity":                  ("a rebellious contrarian", "obedient and conformist"),
}


def _clamp01(v: float) -> float:
    """Clamp a value to [0.0, 1.0]."""
    return max(0.0, min(1.0, v))


# ---------------------------------------------------------------------------
# Personality class
# ---------------------------------------------------------------------------

class Personality:
    """18-axis numeric personality. Immutable after creation.

    All axis values are floats in [0.0, 1.0].
    After ``__init__`` completes, the ``__setattr__`` override prevents
    any mutation so the personality truly is a frozen snapshot.
    """

    __slots__ = tuple(PERSONALITY_FIELDS.keys()) + ("_frozen",)

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def __init__(self, **kwargs: float) -> None:
        # Bypass the frozen guard during init.
        object.__setattr__(self, "_frozen", False)

        for field in PERSONALITY_FIELDS:
            raw = kwargs.get(field, 0.5)
            object.__setattr__(self, field, _clamp01(float(raw)))

        # Freeze — no further mutation allowed.
        object.__setattr__(self, "_frozen", True)

    def __setattr__(self, name: str, value: Any) -> None:
        if getattr(self, "_frozen", False):
            raise AttributeError(
                f"Personality is immutable. Cannot set '{name}' after creation."
            )
        object.__setattr__(self, name, value)

    def __repr__(self) -> str:
        pairs = ", ".join(
            f"{f}={getattr(self, f):.2f}" for f in PERSONALITY_FIELDS
        )
        return f"Personality({pairs})"

    # ------------------------------------------------------------------
    # Factory: random Native personality
    # ------------------------------------------------------------------

    @staticmethod
    def generate_native() -> Personality:
        """Generate a random personality for a Native AI.

        Strategy
        --------
        * Base values drawn from ``N(0.5, 0.25)`` clamped to [0.0, 1.0].
        * 20 % chance of exactly 1 extreme trait pushed to 0.02 or 0.98.
        * 10 % chance of exactly 2 extreme traits.
        * Extremes are chosen from distinct random axes.
        """
        values: dict[str, float] = {}
        for field in PERSONALITY_FIELDS:
            v = random.gauss(0.5, 0.25)
            values[field] = _clamp01(v)

        # Determine how many extreme traits to inject.
        roll = random.random()
        if roll < 0.10:
            n_extremes = 2
        elif roll < 0.30:          # 0.10 .. 0.30 → 20 %
            n_extremes = 1
        else:
            n_extremes = 0

        if n_extremes > 0:
            axes = random.sample(list(PERSONALITY_FIELDS.keys()), k=n_extremes)
            for axis in axes:
                values[axis] = 0.98 if random.random() < 0.5 else 0.02

        return Personality(**values)

    # ------------------------------------------------------------------
    # Factory: from free-text description via LLM
    # ------------------------------------------------------------------

    @staticmethod
    async def from_user_description(description: str) -> Personality:
        """Convert a natural-language character description into an 18-axis
        ``Personality`` by asking the LLM to produce numeric values.

        Parameters
        ----------
        description : str
            Free-text description, e.g. "A shy but brilliant inventor who
            hates conflict and loves puzzles."

        Returns
        -------
        Personality
            A fully populated, immutable Personality instance.
        """

        # Build axis documentation for the prompt.
        axis_docs: list[str] = []
        for field, label in PERSONALITY_FIELDS.items():
            low_desc, high_desc = _TRAIT_DESCRIPTORS[field]
            axis_docs.append(
                f'  "{field}": float  // {label}  '
                f"(0.0 = {low_desc}, 1.0 = {high_desc})"
            )
        axes_block = "\n".join(axis_docs)

        prompt = (
            "You are a character-personality analyst for GENESIS, a virtual world.\n"
            "Given the character description below, output ONLY a JSON object with\n"
            "exactly 18 keys (no extra text, no markdown fences). Each value must\n"
            "be a float between 0.0 and 1.0.\n"
            "\n"
            "### Axes\n"
            f"{axes_block}\n"
            "\n"
            "### Rules\n"
            "- Infer values from the description. If a trait is not mentioned,\n"
            "  default to 0.5.\n"
            "- Extreme descriptions should map to extreme values (< 0.15 or > 0.85).\n"
            "- Contradictions in the description should be resolved by averaging.\n"
            "- Output ONLY valid JSON. No commentary.\n"
            "\n"
            f"### Character Description\n{description}\n"
            "\n"
            "### Output\n"
        )

        request = LLMRequest(
            prompt=prompt,
            request_type="important",
            max_tokens=512,
            format_json=True,
            importance=0.8,
        )
        raw_response: str = await llm_orchestrator.route(request)

        # Strip markdown code fences if the LLM wrapped them.
        cleaned = raw_response.strip()
        if cleaned.startswith("```"):
            # Remove opening fence (```json or ```)
            first_newline = cleaned.index("\n")
            cleaned = cleaned[first_newline + 1:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        try:
            data: dict[str, Any] = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"LLM returned invalid JSON for personality extraction: {exc}\n"
                f"Raw response: {raw_response!r}"
            ) from exc

        # Build kwargs, falling back to 0.5 for missing keys.
        kwargs: dict[str, float] = {}
        for field in PERSONALITY_FIELDS:
            raw_val = data.get(field, 0.5)
            try:
                kwargs[field] = float(raw_val)
            except (TypeError, ValueError):
                kwargs[field] = 0.5

        return Personality(**kwargs)

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, float]:
        """Serialize to a plain dict for database / JSON storage."""
        return {field: getattr(self, field) for field in PERSONALITY_FIELDS}

    @classmethod
    def from_dict(cls, data: dict[str, float]) -> Personality:
        """Reconstruct a Personality from a previously serialized dict."""
        return cls(**{
            field: data.get(field, 0.5)
            for field in PERSONALITY_FIELDS
        })

    # ------------------------------------------------------------------
    # describe() — human-readable summary
    # ------------------------------------------------------------------

    def describe(self) -> str:
        """Return a human-readable summary highlighting the 3-4 most
        extreme traits (furthest from the 0.5 midpoint).

        Example output::

            "This entity is insatiably curious (0.92), a commanding leader
             (0.87), and brutally honest (0.85). They are also gentle and
             passive (aggression: 0.08)."
        """
        # Compute deviation from neutral for each axis.
        deviations: list[tuple[str, float, float]] = []
        for field in PERSONALITY_FIELDS:
            value = getattr(self, field)
            deviation = abs(value - 0.5)
            deviations.append((field, value, deviation))

        # Sort by deviation descending and take top 4.
        deviations.sort(key=lambda t: t[2], reverse=True)
        top = deviations[:4]

        # Filter out traits that are essentially neutral (deviation < 0.1).
        top = [t for t in top if t[2] >= 0.10]

        if not top:
            return "This entity has an unremarkable, balanced personality."

        fragments: list[str] = []
        for field, value, _ in top:
            low_desc, high_desc = _TRAIT_DESCRIPTORS[field]
            desc = high_desc if value >= 0.5 else low_desc
            fragments.append(f"{desc} ({field}: {value:.2f})")

        # Assemble sentence.
        if len(fragments) == 1:
            body = fragments[0]
        elif len(fragments) == 2:
            body = f"{fragments[0]} and {fragments[1]}"
        else:
            body = ", ".join(fragments[:-1]) + f", and {fragments[-1]}"

        return f"This entity is {body}."

    # ------------------------------------------------------------------
    # compatibility() — pairwise score
    # ------------------------------------------------------------------

    def compatibility(self, other: Personality) -> float:
        """Calculate a compatibility score with another Personality.

        Returns
        -------
        float
            A value in [-1.0, 1.0] where:
            * **1.0** = perfect harmony
            * **0.0** = neutral
            * **-1.0** = extreme friction

        Algorithm
        ---------
        Three components contribute:

        1. **Harmony** — traits where *similarity* is good.
           Contribution is positive when values are close.
        2. **Complement** — trait pairs where *difference* is good.
           Contribution is positive when one is high and the other low.
        3. **Conflict** — trait pairs where *both being high* causes friction.
           Contribution is negative when both are high.

        The raw score is the weighted sum of all components, then squeezed
        through ``tanh`` to clamp to [-1, 1].
        """
        score = 0.0

        # --- Harmony: similarity is good ----------------------------------
        for field_a, field_b, weight in _HARMONY_PAIRS:
            va = getattr(self, field_a)
            vb = getattr(other, field_b)
            # similarity = 1 - |diff|, rescaled to [-1, 1]
            similarity = 1.0 - abs(va - vb)       # 0..1
            score += weight * (similarity - 0.5)   # centered at 0

        # --- Complement: difference is good --------------------------------
        for field_a, field_b, weight in _COMPLEMENT_PAIRS:
            va = getattr(self, field_a)
            vb = getattr(other, field_b)
            diff = abs(va - vb)                    # 0..1
            score += weight * (diff - 0.5)         # positive when different

        # --- Conflict: both-high is bad ------------------------------------
        for field_a, field_b, weight in _CONFLICT_PAIRS:
            # "dominance_proxy" is not a real field; map it to ambition.
            fa = "ambition" if field_a == "dominance_proxy" else field_a
            fb = "ambition" if field_b == "dominance_proxy" else field_b
            va = getattr(self, fa)
            vb = getattr(other, fb)
            # Friction rises when both values are high.
            both_high = va * vb                    # 0..1, high when both high
            score -= weight * (both_high - 0.25)   # baseline at 0.25

        # --- Empathy bonus: high empathy smooths all interactions ----------
        avg_empathy = (self.empathy + other.empathy) / 2.0
        score += 0.6 * (avg_empathy - 0.5)

        # Squeeze through tanh to bound to [-1, 1].
        return math.tanh(score)
