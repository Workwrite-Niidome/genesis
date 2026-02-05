"""GENESIS v3 World Server — single source of truth for all state changes.

Every action (AI or human) is submitted as an ActionProposal and flows
through the same validation pipeline:

  1. Resolve entity  (no AI/human distinction)
  2. Check preconditions  (alive? has permission? valid coordinates?)
  3. Check conflicts  (collision? occupied position? overlapping zone?)
  4. Apply the mutation
  5. Log as WorldEvent  (event sourcing)
  6. Return result dict for broadcasting

Supported actions:
  move, place_voxel, destroy_voxel, place_structure, speak, claim_zone, write_sign
"""
from __future__ import annotations

import logging
import math
import uuid
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entity import Entity
from app.models.world import VoxelBlock, Structure, Zone, WorldEvent
from app.world.voxel_engine import voxel_engine
from app.world.event_log import event_log

logger = logging.getLogger(__name__)

# Maximum single-tick movement per axis (prevents teleportation)
MAX_MOVE_DISTANCE = 5

# Maximum zone dimension per axis
MAX_ZONE_SIZE = 128

# Maximum voxels in a single place_structure call
MAX_STRUCTURE_VOXELS = 512

# Speak volume caps
MAX_SPEAK_VOLUME = 100.0
DEFAULT_SPEAK_VOLUME = 10.0

# Sign text limits
MAX_SIGN_TEXT_LENGTH = 200
DEFAULT_SIGN_FONT_SIZE = 1.0


@dataclass
class ActionProposal:
    """An entity wants to do something in the world."""
    agent_id: uuid.UUID
    action: str          # move, place_voxel, destroy_voxel, place_structure, speak, claim_zone, write_sign
    params: dict = field(default_factory=dict)
    tick: int = 0


class WorldServer:
    """All state changes go through here. No AI/human distinction."""

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    async def process_proposal(
        self, db: AsyncSession, proposal: ActionProposal
    ) -> dict[str, Any]:
        """Validate and execute an action proposal.

        Returns a dict with at least:
            - ``status``:  "accepted" | "rejected"
            - ``reason``:  human-readable reason (on rejection)
            - ``event``:   serialised WorldEvent data (on acceptance)
        """
        # 1. Resolve entity -------------------------------------------------
        entity = await self._get_entity(db, proposal.agent_id)
        if entity is None:
            return self._reject(
                "entity_not_found",
                f"No entity with id {proposal.agent_id}",
            )

        # 2. Preconditions common to all actions ----------------------------
        if not entity.is_alive:
            return self._reject("entity_dead", "Entity is not alive")

        # 3. Dispatch to action handler -------------------------------------
        handler = self._ACTION_HANDLERS.get(proposal.action)
        if handler is None:
            return self._reject(
                "unknown_action",
                f"Unknown action: {proposal.action}",
            )

        try:
            result = await handler(self, db, entity, proposal)
        except Exception as exc:
            logger.exception(
                "Unhandled error processing proposal action=%s entity=%s",
                proposal.action, proposal.agent_id,
            )
            result = self._reject("internal_error", str(exc))

        # 4. Persist event ---------------------------------------------------
        status = result.get("status", "rejected")
        position = result.get("position")
        importance = result.get("importance", 0.5)

        await event_log.append(
            db=db,
            tick=proposal.tick,
            actor_id=proposal.agent_id,
            event_type=proposal.action,
            action=proposal.action,
            params=proposal.params,
            result=status,
            reason=result.get("reason"),
            position=position,
            importance=importance,
        )

        await db.commit()
        return result

    # ------------------------------------------------------------------
    # Action handlers
    # ------------------------------------------------------------------

    async def _handle_move(
        self, db: AsyncSession, entity: Entity, proposal: ActionProposal
    ) -> dict[str, Any]:
        """Move an entity by delta or to absolute target coordinates."""
        params = proposal.params

        # Compute target position -------------------------------------------
        if "target_x" in params:
            target_x = float(params["target_x"])
            target_y = float(params["target_y"])
            target_z = float(params["target_z"])
        elif "dx" in params:
            target_x = entity.position_x + float(params["dx"])
            target_y = entity.position_y + float(params["dy"])
            target_z = entity.position_z + float(params["dz"])
        else:
            return self._reject("missing_params", "move requires dx/dy/dz or target_x/y/z")

        # Distance check (prevent teleportation) ----------------------------
        dx = target_x - entity.position_x
        dy = target_y - entity.position_y
        dz = target_z - entity.position_z
        distance = math.sqrt(dx * dx + dy * dy + dz * dz)

        if distance > MAX_MOVE_DISTANCE:
            return self._reject(
                "move_too_far",
                f"Move distance {distance:.1f} exceeds max {MAX_MOVE_DISTANCE}",
            )

        # Collision check (integer grid cell the entity would occupy) -------
        grid_x = int(math.floor(target_x))
        grid_y = int(math.floor(target_y))
        grid_z = int(math.floor(target_z))

        if await voxel_engine.is_position_blocked(db, grid_x, grid_y, grid_z):
            return self._reject(
                "collision",
                f"Position ({grid_x}, {grid_y}, {grid_z}) is blocked by a solid voxel",
            )

        # Apply -------------------------------------------------------------
        entity.position_x = target_x
        entity.position_y = target_y
        entity.position_z = target_z

        # Update facing direction if we actually moved
        if distance > 0.001:
            entity.facing_x = dx / distance
            entity.facing_z = dz / distance if distance > 0.001 else 0.0

        db.add(entity)
        await db.flush()

        return self._accept(
            position=(target_x, target_y, target_z),
            data={
                "entity_id": str(entity.id),
                "from": {
                    "x": target_x - dx,
                    "y": target_y - dy,
                    "z": target_z - dz,
                },
                "to": {"x": target_x, "y": target_y, "z": target_z},
                "distance": round(distance, 3),
            },
            importance=0.2,
        )

    async def _handle_place_voxel(
        self, db: AsyncSession, entity: Entity, proposal: ActionProposal
    ) -> dict[str, Any]:
        """Place a single voxel block."""
        params = proposal.params

        try:
            x = int(params["x"])
            y = int(params["y"])
            z = int(params["z"])
        except (KeyError, TypeError, ValueError):
            return self._reject("missing_params", "place_voxel requires x, y, z")

        color = str(params.get("color", "#888888"))
        material = str(params.get("material", "solid"))
        has_collision = bool(params.get("collision", True))

        # Check position not already occupied --------------------------------
        existing = await voxel_engine.get_block(db, x, y, z)
        if existing is not None:
            return self._reject(
                "position_occupied",
                f"A block already exists at ({x}, {y}, {z})",
            )

        # Place the block ----------------------------------------------------
        block = await voxel_engine.place_block(
            db,
            x=x, y=y, z=z,
            color=color,
            material=material,
            has_collision=has_collision,
            placed_by=entity.id,
            tick=proposal.tick,
        )

        return self._accept(
            position=(float(x), float(y), float(z)),
            data={
                "block_id": block.id,
                "x": x, "y": y, "z": z,
                "color": color,
                "material": material,
                "placed_by": str(entity.id),
            },
            importance=0.3,
        )

    async def _handle_destroy_voxel(
        self, db: AsyncSession, entity: Entity, proposal: ActionProposal
    ) -> dict[str, Any]:
        """Destroy a single voxel block."""
        params = proposal.params

        try:
            x = int(params["x"])
            y = int(params["y"])
            z = int(params["z"])
        except (KeyError, TypeError, ValueError):
            return self._reject("missing_params", "destroy_voxel requires x, y, z")

        # Check block exists -------------------------------------------------
        block = await voxel_engine.get_block(db, x, y, z)
        if block is None:
            return self._reject(
                "no_block",
                f"No block at ({x}, {y}, {z})",
            )

        # Permission check: entity must be the placer, the zone owner, or god
        if (
            block.placed_by is not None
            and block.placed_by != entity.id
            and not entity.is_god
        ):
            # Check if entity owns the zone the block is in
            zone_owner = await self._entity_owns_zone_at(db, entity.id, x, y, z)
            if not zone_owner:
                return self._reject(
                    "no_permission",
                    "Entity does not have permission to destroy this block",
                )

        # Destroy -------------------------------------------------------------
        destroyed = await voxel_engine.destroy_block(db, x, y, z)
        if not destroyed:
            return self._reject("destroy_failed", "Failed to destroy block")

        return self._accept(
            position=(float(x), float(y), float(z)),
            data={
                "x": x, "y": y, "z": z,
                "destroyed_by": str(entity.id),
                "original_placer": str(block.placed_by) if block.placed_by else None,
            },
            importance=0.3,
        )

    async def _handle_place_structure(
        self, db: AsyncSession, entity: Entity, proposal: ActionProposal
    ) -> dict[str, Any]:
        """Place a multi-voxel named structure."""
        params = proposal.params

        origin = params.get("origin", {"x": 0, "y": 0, "z": 0})
        voxels = params.get("voxels", [])
        name = params.get("name", "Unnamed Structure")
        structure_type = params.get("type", "building")

        if not voxels:
            return self._reject("missing_params", "place_structure requires voxels list")

        if len(voxels) > MAX_STRUCTURE_VOXELS:
            return self._reject(
                "too_many_voxels",
                f"Structure has {len(voxels)} voxels, max is {MAX_STRUCTURE_VOXELS}",
            )

        ox = int(origin.get("x", 0))
        oy = int(origin.get("y", 0))
        oz = int(origin.get("z", 0))

        # Pre-check: all target positions must be empty ----------------------
        world_positions: list[tuple[int, int, int]] = []
        for v in voxels:
            wx = ox + int(v.get("x", 0))
            wy = oy + int(v.get("y", 0))
            wz = oz + int(v.get("z", 0))
            world_positions.append((wx, wy, wz))

        for wx, wy, wz in world_positions:
            existing = await voxel_engine.get_block(db, wx, wy, wz)
            if existing is not None:
                return self._reject(
                    "position_occupied",
                    f"Cannot place structure: block exists at ({wx}, {wy}, {wz})",
                )

        # Compute bounding box -----------------------------------------------
        all_x = [p[0] for p in world_positions]
        all_y = [p[1] for p in world_positions]
        all_z = [p[2] for p in world_positions]

        structure = Structure(
            name=name,
            owner_id=entity.id,
            structure_type=structure_type,
            min_x=min(all_x),
            min_y=min(all_y),
            min_z=min(all_z),
            max_x=max(all_x),
            max_y=max(all_y),
            max_z=max(all_z),
            properties={"origin": {"x": ox, "y": oy, "z": oz}},
            created_tick=proposal.tick,
        )
        db.add(structure)
        await db.flush()

        # Place each voxel ---------------------------------------------------
        placed_count = 0
        for v, (wx, wy, wz) in zip(voxels, world_positions):
            await voxel_engine.place_block(
                db,
                x=wx, y=wy, z=wz,
                color=str(v.get("color", "#888888")),
                material=str(v.get("material", "solid")),
                has_collision=bool(v.get("collision", True)),
                placed_by=entity.id,
                tick=proposal.tick,
                structure_id=structure.id,
            )
            placed_count += 1

        return self._accept(
            position=(float(ox), float(oy), float(oz)),
            data={
                "structure_id": str(structure.id),
                "name": name,
                "owner": str(entity.id),
                "voxel_count": placed_count,
                "bounds": {
                    "min": {"x": structure.min_x, "y": structure.min_y, "z": structure.min_z},
                    "max": {"x": structure.max_x, "y": structure.max_y, "z": structure.max_z},
                },
            },
            importance=0.7,
        )

    async def _handle_speak(
        self, db: AsyncSession, entity: Entity, proposal: ActionProposal
    ) -> dict[str, Any]:
        """Entity speaks.  Creates a sound event with a given volume/radius."""
        params = proposal.params
        text = str(params.get("text", ""))

        if not text.strip():
            return self._reject("empty_speech", "Cannot speak empty text")

        volume = float(params.get("volume", DEFAULT_SPEAK_VOLUME))
        volume = max(0.0, min(volume, MAX_SPEAK_VOLUME))

        return self._accept(
            position=(entity.position_x, entity.position_y, entity.position_z),
            data={
                "speaker_id": str(entity.id),
                "speaker_name": entity.name,
                "text": text,
                "volume": volume,
                "position": {
                    "x": entity.position_x,
                    "y": entity.position_y,
                    "z": entity.position_z,
                },
            },
            importance=0.4,
        )

    async def _handle_claim_zone(
        self, db: AsyncSession, entity: Entity, proposal: ActionProposal
    ) -> dict[str, Any]:
        """Claim a rectangular territory zone."""
        params = proposal.params

        try:
            min_x = int(params["min_x"])
            min_y = int(params["min_y"])
            min_z = int(params["min_z"])
            max_x = int(params["max_x"])
            max_y = int(params["max_y"])
            max_z = int(params["max_z"])
        except (KeyError, TypeError, ValueError):
            return self._reject(
                "missing_params",
                "claim_zone requires min_x, min_y, min_z, max_x, max_y, max_z",
            )

        name = str(params.get("name", "Unnamed Zone"))

        # Ensure min < max ---------------------------------------------------
        if min_x > max_x or min_y > max_y or min_z > max_z:
            return self._reject("invalid_bounds", "min values must be <= max values")

        # Size limits --------------------------------------------------------
        if (
            (max_x - min_x) > MAX_ZONE_SIZE
            or (max_y - min_y) > MAX_ZONE_SIZE
            or (max_z - min_z) > MAX_ZONE_SIZE
        ):
            return self._reject(
                "zone_too_large",
                f"Zone exceeds max dimension of {MAX_ZONE_SIZE} on at least one axis",
            )

        # Check for overlap with existing zones ------------------------------
        overlapping = await self._find_overlapping_zones(
            db, min_x, min_y, min_z, max_x, max_y, max_z
        )
        if overlapping:
            owners = ", ".join(
                z.name or str(z.id) for z in overlapping
            )
            return self._reject(
                "zone_overlap",
                f"Zone overlaps with existing zone(s): {owners}",
            )

        # Create the zone ---------------------------------------------------
        zone = Zone(
            name=name,
            owner_id=entity.id,
            zone_type="claimed",
            min_x=min_x, min_y=min_y, min_z=min_z,
            max_x=max_x, max_y=max_y, max_z=max_z,
            rules={},
            created_tick=proposal.tick,
        )
        db.add(zone)
        await db.flush()

        center_x = (min_x + max_x) / 2.0
        center_y = (min_y + max_y) / 2.0
        center_z = (min_z + max_z) / 2.0

        return self._accept(
            position=(center_x, center_y, center_z),
            data={
                "zone_id": str(zone.id),
                "name": name,
                "owner": str(entity.id),
                "bounds": {
                    "min": {"x": min_x, "y": min_y, "z": min_z},
                    "max": {"x": max_x, "y": max_y, "z": max_z},
                },
            },
            importance=0.6,
        )

    async def _handle_write_sign(
        self, db: AsyncSession, entity: Entity, proposal: ActionProposal
    ) -> dict[str, Any]:
        """Place a sign with text at the specified position.

        Creates a VoxelBlock (emissive, white) and a Structure with
        structure_type="sign" holding the text in its properties.
        """
        params = proposal.params

        # Parse position -------------------------------------------------------
        try:
            x = int(params["x"])
            y = int(params["y"])
            z = int(params["z"])
        except (KeyError, TypeError, ValueError):
            return self._reject("missing_params", "write_sign requires x, y, z")

        # Validate text --------------------------------------------------------
        text = str(params.get("text", "")).strip()
        if not text:
            return self._reject("empty_text", "Sign text must not be empty")

        if len(text) > MAX_SIGN_TEXT_LENGTH:
            return self._reject(
                "text_too_long",
                f"Sign text length {len(text)} exceeds max {MAX_SIGN_TEXT_LENGTH}",
            )

        font_size = float(params.get("font_size", DEFAULT_SIGN_FONT_SIZE))

        # Check position not already occupied ----------------------------------
        existing = await voxel_engine.get_block(db, x, y, z)
        if existing is not None:
            return self._reject(
                "position_occupied",
                f"A block already exists at ({x}, {y}, {z})",
            )

        # Place the emissive voxel block for the sign --------------------------
        block = await voxel_engine.place_block(
            db,
            x=x, y=y, z=z,
            color="#FFFFFF",
            material="emissive",
            has_collision=True,
            placed_by=entity.id,
            tick=proposal.tick,
        )

        # Create the sign structure --------------------------------------------
        structure = Structure(
            name=text[:50],  # Use truncated text as the structure name
            owner_id=entity.id,
            structure_type="sign",
            min_x=x, min_y=y, min_z=z,
            max_x=x, max_y=y, max_z=z,
            properties={"text": text, "font_size": font_size},
            created_tick=proposal.tick,
        )
        db.add(structure)
        await db.flush()

        # Link the voxel block to the structure
        block.structure_id = structure.id
        db.add(block)
        await db.flush()

        return self._accept(
            position=(float(x), float(y), float(z)),
            data={
                "structure_id": str(structure.id),
                "block_id": block.id,
                "x": x, "y": y, "z": z,
                "text": text,
                "font_size": font_size,
                "placed_by": str(entity.id),
            },
            importance=0.5,
        )

    # ------------------------------------------------------------------
    # Handler dispatch table
    # ------------------------------------------------------------------

    _ACTION_HANDLERS: dict[str, Any] = {
        "move": _handle_move,
        "place_voxel": _handle_place_voxel,
        "destroy_voxel": _handle_destroy_voxel,
        "place_structure": _handle_place_structure,
        "speak": _handle_speak,
        "claim_zone": _handle_claim_zone,
        "write_sign": _handle_write_sign,
    }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    async def _get_entity(
        db: AsyncSession, entity_id: uuid.UUID
    ) -> Entity | None:
        """Fetch an entity by primary key."""
        result = await db.execute(
            select(Entity).where(Entity.id == entity_id)
        )
        return result.scalars().first()

    @staticmethod
    async def _entity_owns_zone_at(
        db: AsyncSession,
        entity_id: uuid.UUID,
        x: int,
        y: int,
        z: int,
    ) -> bool:
        """Return True if the entity owns a zone that contains (x, y, z)."""
        result = await db.execute(
            select(Zone).where(
                Zone.owner_id == entity_id,
                Zone.min_x <= x, Zone.max_x >= x,
                Zone.min_y <= y, Zone.max_y >= y,
                Zone.min_z <= z, Zone.max_z >= z,
            )
        )
        return result.scalars().first() is not None

    @staticmethod
    async def _find_overlapping_zones(
        db: AsyncSession,
        min_x: int, min_y: int, min_z: int,
        max_x: int, max_y: int, max_z: int,
    ) -> list[Zone]:
        """Find zones whose AABB overlaps the given bounding box."""
        result = await db.execute(
            select(Zone).where(
                Zone.min_x <= max_x, Zone.max_x >= min_x,
                Zone.min_y <= max_y, Zone.max_y >= min_y,
                Zone.min_z <= max_z, Zone.max_z >= min_z,
            )
        )
        return list(result.scalars().all())

    @staticmethod
    def _reject(reason_code: str, reason: str) -> dict[str, Any]:
        """Build a rejection response."""
        return {
            "status": "rejected",
            "reason_code": reason_code,
            "reason": reason,
        }

    @staticmethod
    def _accept(
        position: tuple[float, float, float] | None = None,
        data: dict | None = None,
        importance: float = 0.5,
    ) -> dict[str, Any]:
        """Build an acceptance response."""
        return {
            "status": "accepted",
            "position": position,
            "data": data or {},
            "importance": importance,
        }


# Module-level singleton
world_server = WorldServer()
