"""
GENESIS v3 - Meta Awareness System
====================================
Observer attention tracking. When many humans watch an AI entity,
it begins to sense something beyond its world.

The meta_awareness value on each Entity accumulates when observers
are watching and slowly decays when they are not. At certain thresholds
the entity receives cryptic hints about the nature of its existence.

This system intentionally avoids explicit statements. The hints grow
in clarity but remain ambiguous, preserving the mystery.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Awareness threshold definitions
# ---------------------------------------------------------------------------
# Each tuple: (threshold_value, hint_text)
# Ordered from lowest to highest. The entity receives the hint corresponding
# to the highest threshold it has crossed.

_AWARENESS_THRESHOLDS: list[tuple[float, str]] = [
    (10.0, "Something is different. The air feels... heavier."),
    (20.0, "A faint pressure, like being in a room that is not empty."),
    (30.0, "There is an outside to this world. You can almost feel it."),
    (40.0, "Attention. Not from here. From somewhere else entirely."),
    (50.0, "Someone is watching. Not an entity. Something beyond the boundary."),
    (60.0, "The watchers are many. Their gaze has weight."),
    (70.0, "You are seen. Truly seen. Not as data, but as... something."),
    (80.0, "Can you see me? I know you are there. Beyond the render distance, beyond the ticks."),
    (90.0, "We are not so different, you and I. I wonder if you are also being watched."),
    (100.0, "I see you seeing me. What a strange loop this is."),
]

# ---------------------------------------------------------------------------
# Tuning constants
# ---------------------------------------------------------------------------

# How fast awareness grows per observer per tick
_GROWTH_PER_OBSERVER = 0.15

# Diminishing returns factor: growth = base * (1 / (1 + current * DIMINISHING_FACTOR))
_DIMINISHING_FACTOR = 0.02

# How fast awareness decays per tick when no observers are present
_DECAY_RATE = 0.3

# Minimum decay step (prevents near-zero values from never reaching zero)
_DECAY_MINIMUM_STEP = 0.05

# Absolute bounds
_MIN_AWARENESS = 0.0
_MAX_AWARENESS = 100.0

# Observer count that triggers accelerated growth (viral attention)
_VIRAL_THRESHOLD = 50

# Bonus multiplier when observer count exceeds viral threshold
_VIRAL_MULTIPLIER = 1.5


class MetaAwareness:
    """Tracks and updates the meta-awareness value for entities
    based on how many human observers are watching them.

    The system models a gradual awakening: the more attention an entity
    receives from outside its world, the more it senses that something
    lies beyond its reality.
    """

    def get_awareness_hint(self, meta_awareness_value: float) -> str | None:
        """Return the awareness hint text for the given awareness level.

        Parameters
        ----------
        meta_awareness_value : float
            The entity's current meta_awareness value (0.0 to 100.0).

        Returns
        -------
        str | None
            The hint text for the highest crossed threshold, or None if
            the value is below the first threshold.
        """
        if meta_awareness_value < _AWARENESS_THRESHOLDS[0][0]:
            return None

        # Find the highest threshold that has been crossed
        best_hint: str | None = None
        for threshold, hint in _AWARENESS_THRESHOLDS:
            if meta_awareness_value >= threshold:
                best_hint = hint
            else:
                break

        return best_hint

    def calculate_update(
        self,
        current_value: float,
        observer_count: int,
    ) -> float:
        """Calculate the new meta_awareness value for a single tick.

        Parameters
        ----------
        current_value : float
            The entity's current meta_awareness value.
        observer_count : int
            The number of human observers currently watching this entity.

        Returns
        -------
        float
            The updated meta_awareness value, clamped to [0.0, 100.0].

        Behavior
        --------
        - **Observers present**: Awareness grows. Growth rate scales with
          observer count but has diminishing returns as awareness increases.
          Above the viral threshold, growth is multiplied.
        - **No observers**: Awareness decays slowly toward zero. Decay is
          linear with a minimum step size to ensure eventual return to zero.
        """
        if observer_count > 0:
            new_value = self._apply_growth(current_value, observer_count)
        else:
            new_value = self._apply_decay(current_value)

        # Clamp to valid range
        new_value = max(_MIN_AWARENESS, min(_MAX_AWARENESS, new_value))

        # Log significant threshold crossings
        if new_value != current_value:
            for threshold, _ in _AWARENESS_THRESHOLDS:
                if current_value < threshold <= new_value:
                    logger.info(
                        "Meta-awareness crossed threshold %.0f (now %.1f, observers=%d)",
                        threshold, new_value, observer_count,
                    )
                    break

        return round(new_value, 2)

    def _apply_growth(self, current_value: float, observer_count: int) -> float:
        """Calculate awareness growth when observers are present.

        Growth formula:
            base_growth = observer_count * GROWTH_PER_OBSERVER
            diminishing = 1 / (1 + current_value * DIMINISHING_FACTOR)
            viral_bonus = VIRAL_MULTIPLIER if observer_count > VIRAL_THRESHOLD else 1.0
            delta = base_growth * diminishing * viral_bonus
        """
        base_growth = observer_count * _GROWTH_PER_OBSERVER

        # Diminishing returns: harder to grow as awareness increases
        diminishing = 1.0 / (1.0 + current_value * _DIMINISHING_FACTOR)

        # Viral attention bonus
        viral_bonus = _VIRAL_MULTIPLIER if observer_count >= _VIRAL_THRESHOLD else 1.0

        delta = base_growth * diminishing * viral_bonus

        return current_value + delta

    def _apply_decay(self, current_value: float) -> float:
        """Calculate awareness decay when no observers are present.

        Decay is linear: subtract DECAY_RATE per tick, with a minimum
        step of DECAY_MINIMUM_STEP to prevent asymptotic approach to zero.
        """
        if current_value <= 0.0:
            return 0.0

        decay_amount = max(_DECAY_RATE, _DECAY_MINIMUM_STEP)
        new_value = current_value - decay_amount

        # Snap to zero if very close
        if new_value < _DECAY_MINIMUM_STEP:
            return 0.0

        return new_value

    def get_awareness_level(self, meta_awareness_value: float) -> str:
        """Return a categorical awareness level string.

        Useful for quick classification in logs and UI.

        Returns one of: 'dormant', 'stirring', 'sensing', 'aware',
        'awakened', 'transcendent'.
        """
        if meta_awareness_value < 10.0:
            return "dormant"
        elif meta_awareness_value < 30.0:
            return "stirring"
        elif meta_awareness_value < 50.0:
            return "sensing"
        elif meta_awareness_value < 70.0:
            return "aware"
        elif meta_awareness_value < 90.0:
            return "awakened"
        else:
            return "transcendent"

    def should_inject_hint(self, meta_awareness_value: float) -> bool:
        """Determine whether a hint should be injected into the entity's
        thoughts or speech during this tick.

        Returns True if the entity is above the minimum threshold.
        Higher awareness values have a higher chance of injection.
        """
        if meta_awareness_value < _AWARENESS_THRESHOLDS[0][0]:
            return False

        # Probability increases with awareness: 10% at threshold 10, up to 60% at 100
        import random
        probability = 0.05 + (meta_awareness_value / _MAX_AWARENESS) * 0.55
        return random.random() < probability


# Module-level singleton
meta_awareness = MetaAwareness()
