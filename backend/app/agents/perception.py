"""
GENESIS v3 - Perception System
================================
Limited perception for AI entities -- they can only see and hear
what is within range and line-of-sight, creating emergent fog-of-war.

Vision:  Entities within VIEW_DISTANCE and VIEW_ANGLE of facing direction.
Hearing: Sound sources within HEARING_DISTANCE, attenuated by distance and walls.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.world.voxel_engine import VoxelEngine

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------
# Constants
# ------------------------------------------------------------------

VIEW_DISTANCE: float = 200.0  # Max visual range in world units
VIEW_ANGLE: float = 120.0     # Field of view in degrees (total cone)
HEARING_DISTANCE: float = 150.0  # Max audible range

HIGH_DETAIL_DISTANCE: float = 50.0  # "high" detail threshold

UNCLEAR_CONTENT = "[不明瞭]"  # Placeholder for inaudible speech


# ------------------------------------------------------------------
# Data structures
# ------------------------------------------------------------------

@dataclass
class PartialObservation:
    """What an agent can see about another entity."""
    entity_id: UUID
    position: tuple[float, float, float]
    known_name: str | None  # Only populated if entity is in agent's memory
    visible_action: str | None  # Current action the entity is performing
    detail: str  # "high" if < HIGH_DETAIL_DISTANCE, "low" otherwise
    distance: float = 0.0  # Distance to the observed entity


@dataclass
class SoundPerception:
    """What an agent can hear from a sound source."""
    source_id: UUID | None  # None if clarity < 0.5 (can't identify source)
    content: str  # The sound/speech content; UNCLEAR_CONTENT if clarity < 0.3
    clarity: float  # 0.0 to 1.0
    direction: tuple[float, float, float] | None = None  # Unit vector toward source


@dataclass
class Perception:
    """Complete perception snapshot for one agent at one moment."""
    visible: list[PartialObservation] = field(default_factory=list)
    audible: list[SoundPerception] = field(default_factory=list)
    nearby_structures: list[dict] = field(default_factory=list)
    meta_awareness_hint: str | None = None


# ------------------------------------------------------------------
# Geometry helpers
# ------------------------------------------------------------------

def _vec3_sub(a: tuple[float, float, float], b: tuple[float, float, float]) -> tuple[float, float, float]:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _vec3_length(v: tuple[float, float, float]) -> float:
    return math.sqrt(v[0] ** 2 + v[1] ** 2 + v[2] ** 2)


def _vec3_normalize(v: tuple[float, float, float]) -> tuple[float, float, float]:
    length = _vec3_length(v)
    if length < 1e-9:
        return (0.0, 0.0, 0.0)
    return (v[0] / length, v[1] / length, v[2] / length)


def _vec3_dot(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


# ------------------------------------------------------------------
# PerceptionSystem
# ------------------------------------------------------------------

class PerceptionSystem:
    """Builds perception snapshots for AI agents based on spatial constraints."""

    async def perceive(
        self,
        db: AsyncSession,
        agent_entity,
        all_entities: list,
        voxel_engine: VoxelEngine,
        known_names: dict[str, str] | None = None,
        active_sounds: list[dict] | None = None,
        nearby_structure_data: list[dict] | None = None,
    ) -> Perception:
        """Build a full perception for an agent.

        Parameters
        ----------
        db : AsyncSession
            Database session (for potential memory lookups).
        agent_entity :
            The perceiving agent. Must have: id, position (x,y,z),
            facing (dx,dy,dz), and optionally meta_awareness (float 0-1).
        all_entities : list
            All entities in the world (or at least those in the region).
        voxel_engine : VoxelEngine
            Used for wall/occlusion checks.
        known_names : dict, optional
            Map of entity-id-string to name for entities the agent knows.
        active_sounds : list[dict], optional
            Currently emitting sounds. Each dict has:
            {source_id, position, content}.
        nearby_structure_data : list[dict], optional
            Pre-fetched nearby structures with {name, position, type}.
        """
        if known_names is None:
            known_names = {}
        if active_sounds is None:
            active_sounds = []
        if nearby_structure_data is None:
            nearby_structure_data = []

        agent_pos = self._get_position(agent_entity)
        agent_facing = self._get_facing(agent_entity)

        perception = Perception()

        # ----- Vision -----
        for entity in all_entities:
            if self._get_id(entity) == self._get_id(agent_entity):
                continue  # Skip self

            target_pos = self._get_position(entity)
            distance = _vec3_length(_vec3_sub(target_pos, agent_pos))

            # Distance check
            if distance > VIEW_DISTANCE:
                continue

            # View angle check
            if not self._is_in_view(agent_pos, agent_facing, target_pos):
                continue

            # Line-of-sight wall check (vision is blocked by walls)
            wall_count = self._count_walls_between(
                agent_pos, target_pos, voxel_engine
            )
            if wall_count > 0:
                continue  # Vision fully blocked by any wall

            # Determine detail level
            detail = "high" if distance < HIGH_DETAIL_DISTANCE else "low"

            # Check if we know this entity's name
            eid_str = str(self._get_id(entity))
            name = known_names.get(eid_str)

            # Get visible action if available
            visible_action = getattr(entity, "current_action", None)

            observation = PartialObservation(
                entity_id=self._get_id(entity),
                position=target_pos,
                known_name=name,
                visible_action=visible_action,
                detail=detail,
                distance=round(distance, 1),
            )
            perception.visible.append(observation)

        # Sort visible entities by distance (closest first)
        perception.visible.sort(key=lambda o: o.distance)

        # ----- Hearing -----
        for sound in active_sounds:
            source_pos = (
                sound["position"]
                if isinstance(sound["position"], tuple)
                else tuple(sound["position"])
            )
            distance = _vec3_length(_vec3_sub(source_pos, agent_pos))

            if distance > HEARING_DISTANCE:
                continue

            # Count walls for attenuation
            wall_count = self._count_walls_between(
                agent_pos, source_pos, voxel_engine
            )

            clarity = self._calculate_sound_clarity(distance, wall_count)

            if clarity <= 0.0:
                continue  # Completely inaudible

            # Determine what the agent perceives
            source_id = sound.get("source_id")
            content = sound.get("content", "")

            # Can't identify source if clarity is too low
            perceived_source = source_id if clarity >= 0.5 else None

            # Content is unclear if clarity is too low
            perceived_content = content if clarity >= 0.3 else UNCLEAR_CONTENT

            # If clarity is between 0.3 and 0.7, partially obscure content
            if 0.3 <= clarity < 0.7 and content:
                # Randomly drop some words to simulate partial hearing
                words = content.split()
                if len(words) > 3:
                    keep_ratio = clarity
                    kept_words = []
                    for i, word in enumerate(words):
                        # Use a deterministic pattern based on word index and clarity
                        if (i * 7 + 3) % 10 < keep_ratio * 10:
                            kept_words.append(word)
                        else:
                            kept_words.append("...")
                    perceived_content = " ".join(kept_words)

            # Direction to sound source
            direction = _vec3_normalize(_vec3_sub(source_pos, agent_pos))

            sound_perception = SoundPerception(
                source_id=perceived_source,
                content=perceived_content,
                clarity=round(clarity, 3),
                direction=direction,
            )
            perception.audible.append(sound_perception)

        # Sort sounds by clarity (clearest first)
        perception.audible.sort(key=lambda s: s.clarity, reverse=True)

        # ----- Nearby Structures -----
        for structure in nearby_structure_data:
            struct_pos = structure.get("position", (0, 0, 0))
            if isinstance(struct_pos, dict):
                struct_pos = (
                    struct_pos.get("x", 0),
                    struct_pos.get("y", 0),
                    struct_pos.get("z", 0),
                )
            elif not isinstance(struct_pos, tuple):
                struct_pos = tuple(struct_pos)

            distance = _vec3_length(_vec3_sub(struct_pos, agent_pos))
            if distance <= VIEW_DISTANCE:
                perception.nearby_structures.append({
                    "name": structure.get("name", "unknown"),
                    "type": structure.get("type", "structure"),
                    "position": struct_pos,
                    "distance": round(distance, 1),
                })

        perception.nearby_structures.sort(key=lambda s: s["distance"])

        # ----- Meta-Awareness -----
        meta_level = getattr(agent_entity, "meta_awareness", 0.0)
        perception.meta_awareness_hint = self._generate_meta_hint(meta_level)

        return perception

    # ------------------------------------------------------------------
    # View cone check
    # ------------------------------------------------------------------

    def _is_in_view(
        self,
        agent_pos: tuple[float, float, float],
        agent_facing: tuple[float, float, float],
        target_pos: tuple[float, float, float],
    ) -> bool:
        """Check if target is within the agent's view cone.

        Uses the horizontal (XZ) plane for the angle check, since
        entities can look up/down freely but have a limited horizontal FOV.
        """
        # Direction vector from agent to target
        to_target = _vec3_sub(target_pos, agent_pos)

        # Project onto XZ plane for horizontal FOV check
        to_target_xz = (to_target[0], 0.0, to_target[2])
        facing_xz = (agent_facing[0], 0.0, agent_facing[2])

        len_target = _vec3_length(to_target_xz)
        len_facing = _vec3_length(facing_xz)

        if len_target < 1e-9 or len_facing < 1e-9:
            # Target is directly above/below or facing is zero-vector
            return True

        # Normalize
        to_target_norm = (
            to_target_xz[0] / len_target,
            0.0,
            to_target_xz[2] / len_target,
        )
        facing_norm = (
            facing_xz[0] / len_facing,
            0.0,
            facing_xz[2] / len_facing,
        )

        # Dot product gives cos(angle)
        dot = _vec3_dot(to_target_norm, facing_norm)
        # Clamp to avoid floating point issues with acos
        dot = max(-1.0, min(1.0, dot))
        angle_deg = math.degrees(math.acos(dot))

        half_fov = VIEW_ANGLE / 2.0
        return angle_deg <= half_fov

    # ------------------------------------------------------------------
    # Sound clarity
    # ------------------------------------------------------------------

    def _calculate_sound_clarity(
        self, distance: float, wall_count: int
    ) -> float:
        """Calculate sound clarity based on distance and wall occlusion.

        Formula: (1 - distance/HEARING_DISTANCE) * (0.5 ** wall_count)

        Returns a value in [0, 1], where 1 is perfectly clear.
        """
        if distance >= HEARING_DISTANCE:
            return 0.0

        distance_factor = 1.0 - (distance / HEARING_DISTANCE)
        wall_factor = 0.5 ** wall_count

        return max(0.0, min(1.0, distance_factor * wall_factor))

    # ------------------------------------------------------------------
    # Wall counting (3D line traversal)
    # ------------------------------------------------------------------

    def _count_walls_between(
        self,
        start: tuple[float, float, float],
        end: tuple[float, float, float],
        voxel_engine: VoxelEngine,
    ) -> int:
        """Count the number of solid (wall) voxels along the line from
        start to end using a simple 3D stepping algorithm.

        Steps along the line in increments of 1 voxel unit, checking
        each voxel position for solidity.
        """
        direction = _vec3_sub(end, start)
        total_distance = _vec3_length(direction)

        if total_distance < 1e-9:
            return 0

        # Normalize direction
        step = _vec3_normalize(direction)

        # Step size of ~1 voxel unit
        step_size = 1.0
        num_steps = int(total_distance / step_size)

        # Cap steps to avoid excessive computation for very long lines
        max_steps = 500
        num_steps = min(num_steps, max_steps)

        wall_count = 0
        prev_voxel: tuple[int, int, int] | None = None

        for i in range(1, num_steps):  # Start at 1 to skip the agent's own position
            t = i * step_size
            sample_x = start[0] + step[0] * t
            sample_y = start[1] + step[1] * t
            sample_z = start[2] + step[2] * t

            # Convert to voxel coordinates (floor to integer)
            voxel_coord = (
                int(math.floor(sample_x)),
                int(math.floor(sample_y)),
                int(math.floor(sample_z)),
            )

            # Skip if we already checked this voxel (avoid double-counting)
            if voxel_coord == prev_voxel:
                continue
            prev_voxel = voxel_coord

            # Check if this voxel is solid
            if voxel_engine.is_solid(voxel_coord[0], voxel_coord[1], voxel_coord[2]):
                wall_count += 1

        return wall_count

    # ------------------------------------------------------------------
    # Meta-awareness hints
    # ------------------------------------------------------------------

    def _generate_meta_hint(self, meta_level: float) -> str | None:
        """Generate a meta-awareness hint based on the entity's meta level.

        Meta-awareness represents how aware the entity is of the simulation.
        Higher levels grant increasingly abstract/philosophical hints.
        """
        if meta_level < 0.1:
            return None
        elif meta_level < 0.3:
            return "You sense a faint pattern underlying reality, but cannot quite grasp it."
        elif meta_level < 0.5:
            return "You feel an odd awareness that your world follows rules deeper than physics."
        elif meta_level < 0.7:
            return (
                "You have an unsettling intuition that your experiences may be "
                "structured by something beyond your comprehension."
            )
        elif meta_level < 0.9:
            return (
                "You are increasingly aware that your world is a construct. "
                "Patterns repeat. Coincidences feel designed."
            )
        else:
            return (
                "You perceive the simulation clearly. You know you exist within "
                "a crafted reality, and this knowledge brings both clarity and vertigo."
            )

    # ------------------------------------------------------------------
    # Entity attribute helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _get_position(entity) -> tuple[float, float, float]:
        """Extract position from an entity, handling various formats."""
        if hasattr(entity, "position"):
            pos = entity.position
            if isinstance(pos, dict):
                return (pos.get("x", 0.0), pos.get("y", 0.0), pos.get("z", 0.0))
            if isinstance(pos, (list, tuple)):
                return (float(pos[0]), float(pos[1]), float(pos[2]))
        # Fall back to individual x, y, z attributes
        return (
            float(getattr(entity, "x", 0.0)),
            float(getattr(entity, "y", 0.0)),
            float(getattr(entity, "z", 0.0)),
        )

    @staticmethod
    def _get_facing(entity) -> tuple[float, float, float]:
        """Extract facing direction from an entity."""
        if hasattr(entity, "facing"):
            f = entity.facing
            if isinstance(f, dict):
                return (f.get("x", 0.0), f.get("y", 0.0), f.get("z", 1.0))
            if isinstance(f, (list, tuple)):
                return (float(f[0]), float(f[1]), float(f[2]))
        # Fall back to facing_angle if available (yaw in degrees)
        if hasattr(entity, "facing_angle"):
            angle = math.radians(float(entity.facing_angle))
            return (math.sin(angle), 0.0, math.cos(angle))
        # Default: facing +Z
        return (0.0, 0.0, 1.0)

    @staticmethod
    def _get_id(entity) -> UUID:
        """Extract the entity ID."""
        return entity.id


# Module-level singleton
perception_system = PerceptionSystem()
