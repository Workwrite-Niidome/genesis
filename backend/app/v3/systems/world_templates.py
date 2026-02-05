"""GENESIS v3 World Template Generator -- Japanese-themed structures.

Generates voxel structures inspired by traditional Japanese architecture
(torii gates, stone lanterns, shrines, stone paths, boundary walls) so the
world is not an empty flat plane on first load.

Each generator function returns a list of voxel dicts:
    [{"x": int, "y": int, "z": int, "color": str, "material": str}, ...]

The top-level ``generate_world_template`` function aggregates all structures
and writes them to the database via the VoxelEngine, skipping any positions
that are already occupied (idempotent).

Visual goal: "Chou-Kaguya-Hime" anime atmosphere -- dark reds, warm amber
glow, stone gray paths, dark wood shrines under bloom lighting.
"""
from __future__ import annotations

import logging
import math
import random
import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.world import VoxelBlock, Structure
from app.world.voxel_engine import voxel_engine

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Color palette
# ---------------------------------------------------------------------------
DARK_RED = "#8B0000"
DEEP_RED = "#B71C1C"
DARK_WOOD = "#3E2723"
MED_WOOD = "#4E342E"
GRAY_STONE = "#888888"
DARK_STONE = "#666666"
DARKER_STONE = "#555555"
MED_GRAY = "#777777"
DARK_TILE = "#1B1B1B"
GOLD_EMISSIVE = "#FFD700"
WARM_AMBER = "#FFE082"
DEEP_AMBER = "#FF8F00"
WHITE_EMISSIVE = "#FFFDE7"

# ---------------------------------------------------------------------------
# Structure generators
# ---------------------------------------------------------------------------


def _generate_grand_torii(cx: int = 0, cz: int = 0) -> list[dict[str, Any]]:
    """Generate a Grand Torii Gate centered at (cx, cz).

    Two massive pillars (3 wide x 12 tall) connected by a top beam (kasagi)
    spanning ~16 blocks with a slight upward curve, plus a secondary beam
    (nuki) below.  A golden emissive block crowns the center.
    """
    voxels: list[dict[str, Any]] = []

    pillar_half_span = 7  # Distance from center to pillar center
    pillar_width = 3      # 3 blocks wide (x-axis)
    pillar_depth = 2      # 2 blocks deep (z-axis)
    pillar_height = 12

    # --- Pillars (left and right) ---
    for side in (-1, 1):
        px = cx + side * pillar_half_span  # center x of this pillar
        for dx in range(-(pillar_width // 2), pillar_width // 2 + 1):
            for dz in range(-(pillar_depth // 2), pillar_depth // 2 + 1):
                for y in range(0, pillar_height):
                    voxels.append({
                        "x": px + dx,
                        "y": y,
                        "z": cz + dz,
                        "color": DARK_RED,
                        "material": "solid",
                    })

    # --- Top beam (kasagi) -- spans from pillar to pillar with slight curve ---
    beam_min_x = cx - pillar_half_span - pillar_width // 2 - 1
    beam_max_x = cx + pillar_half_span + pillar_width // 2 + 1
    beam_y_base = pillar_height  # sits right on top of pillar

    for bx in range(beam_min_x, beam_max_x + 1):
        # Slight upward curve: parabolic, highest at center
        dist_from_center = abs(bx - cx)
        max_dist = (beam_max_x - beam_min_x) / 2
        curve_offset = int(round(1.5 * (1.0 - (dist_from_center / max_dist) ** 2)))

        for dz in range(-1, 2):  # 3 blocks deep
            # Main beam
            voxels.append({
                "x": bx,
                "y": beam_y_base + curve_offset,
                "z": cz + dz,
                "color": DEEP_RED,
                "material": "solid",
            })
            # Top cap (one block above main beam at endpoints, emissive at edges)
            if dist_from_center >= max_dist - 2:
                voxels.append({
                    "x": bx,
                    "y": beam_y_base + curve_offset + 1,
                    "z": cz + dz,
                    "color": DEEP_RED,
                    "material": "emissive",
                })

    # --- Secondary beam (nuki) -- lower horizontal crossbar ---
    nuki_y = pillar_height - 3
    nuki_min_x = cx - pillar_half_span - 1
    nuki_max_x = cx + pillar_half_span + 1
    for bx in range(nuki_min_x, nuki_max_x + 1):
        voxels.append({
            "x": bx,
            "y": nuki_y,
            "z": cz,
            "color": DARK_RED,
            "material": "solid",
        })

    # --- Golden crown at center top ---
    center_curve = int(round(1.5))  # curve at center
    voxels.append({
        "x": cx,
        "y": beam_y_base + center_curve + 1,
        "z": cz,
        "color": GOLD_EMISSIVE,
        "material": "emissive",
    })
    # Flanking gold accents
    for dx in (-1, 1):
        voxels.append({
            "x": cx + dx,
            "y": beam_y_base + center_curve + 1,
            "z": cz,
            "color": DEEP_AMBER,
            "material": "emissive",
        })

    return voxels


def _generate_stone_lantern(cx: int, cz: int) -> list[dict[str, Any]]:
    """Generate a stone lantern (toro) at position (cx, cz).

    Layers from bottom:
        1. Base:      3x1x3 gray stone
        2. Pillar:    1x3x1 gray
        3. Light box: 3x2x3 with emissive center
        4. Cap:       3x1x3 dark gray
    """
    voxels: list[dict[str, Any]] = []

    # Base (y=0): 3x1x3
    for dx in range(-1, 2):
        for dz in range(-1, 2):
            voxels.append({
                "x": cx + dx, "y": 0, "z": cz + dz,
                "color": DARKER_STONE, "material": "solid",
            })

    # Pillar (y=1..3): 1x3x1
    for y in range(1, 4):
        voxels.append({
            "x": cx, "y": y, "z": cz,
            "color": DARKER_STONE, "material": "solid",
        })

    # Light box (y=4..5): 3x2x3 shell with emissive center
    for y in range(4, 6):
        for dx in range(-1, 2):
            for dz in range(-1, 2):
                is_center = (dx == 0 and dz == 0)
                is_edge = (abs(dx) == 1 and abs(dz) == 1)
                if is_center:
                    # Glowing light core
                    voxels.append({
                        "x": cx + dx, "y": y, "z": cz + dz,
                        "color": WARM_AMBER, "material": "emissive",
                    })
                elif is_edge:
                    # Corner posts of the light box
                    voxels.append({
                        "x": cx + dx, "y": y, "z": cz + dz,
                        "color": DARKER_STONE, "material": "solid",
                    })
                else:
                    # Open sides (glass panels) for light bleed
                    voxels.append({
                        "x": cx + dx, "y": y, "z": cz + dz,
                        "color": WARM_AMBER, "material": "glass",
                    })

    # Cap (y=6): 3x1x3
    for dx in range(-1, 2):
        for dz in range(-1, 2):
            voxels.append({
                "x": cx + dx, "y": 6, "z": cz + dz,
                "color": DARK_STONE, "material": "solid",
            })

    # Pointed top (y=7): single dark stone
    voxels.append({
        "x": cx, "y": 7, "z": cz,
        "color": DARK_STONE, "material": "solid",
    })

    return voxels


def _generate_stone_path(
    start_x: int,
    start_z: int,
    direction: str = "z",
    length: int = 40,
    width: int = 3,
) -> list[dict[str, Any]]:
    """Generate a stone path from (start_x, start_z) along the given axis.

    Alternates gray and dark-gray blocks with some random offsets for a
    natural feel.  All blocks placed at y=0.
    """
    voxels: list[dict[str, Any]] = []
    rng = random.Random(start_x * 1000 + start_z)  # deterministic seed

    half_width = width // 2

    for i in range(-length, length + 1):
        for w in range(-half_width, half_width + 1):
            # Skip some blocks for natural look
            if rng.random() < 0.06:
                continue

            if direction == "z":
                x = start_x + w
                z = start_z + i
            else:
                x = start_x + i
                z = start_z + w

            # Random lateral offset for organic feel
            if abs(w) == half_width and rng.random() < 0.3:
                if direction == "z":
                    x += rng.choice([-1, 1])
                else:
                    z += rng.choice([-1, 1])

            color = GRAY_STONE if (i + w) % 2 == 0 else DARK_STONE
            voxels.append({
                "x": x, "y": 0, "z": z,
                "color": color, "material": "solid",
            })

    return voxels


def _generate_shrine(
    cx: int,
    cz: int,
    width: int = 8,
    depth: int = 8,
    wall_height: int = 5,
    facing: str = "south",
) -> list[dict[str, Any]]:
    """Generate a small traditional shrine/building at (cx, cz).

    Components:
        - Stone platform base
        - Dark wood walls with doorway
        - Dark tile roof with overhang
        - Interior warm emissive light
    """
    voxels: list[dict[str, Any]] = []

    hw = width // 2   # half width
    hd = depth // 2   # half depth

    # --- Platform base (y=0): stone, 1 block wider than building ---
    for dx in range(-hw - 1, hw + 2):
        for dz in range(-hd - 1, hd + 2):
            voxels.append({
                "x": cx + dx, "y": 0, "z": cz + dz,
                "color": DARKER_STONE, "material": "solid",
            })

    # --- Floor (y=1): wood ---
    for dx in range(-hw, hw + 1):
        for dz in range(-hd, hd + 1):
            voxels.append({
                "x": cx + dx, "y": 1, "z": cz + dz,
                "color": MED_WOOD, "material": "solid",
            })

    # --- Walls (y=2..wall_height): dark wood with doorway ---
    for y in range(2, wall_height + 1):
        for dx in range(-hw, hw + 1):
            for dz in range(-hd, hd + 1):
                is_wall_x = (dx == -hw or dx == hw)
                is_wall_z = (dz == -hd or dz == hd)

                if not (is_wall_x or is_wall_z):
                    continue  # interior, skip

                # Doorway: 2-wide, 3-tall opening on the facing side
                is_door = False
                if facing == "south" and dz == -hd:
                    if abs(dx) <= 1 and y <= 4:
                        is_door = True
                elif facing == "north" and dz == hd:
                    if abs(dx) <= 1 and y <= 4:
                        is_door = True
                elif facing == "east" and dx == hw:
                    if abs(dz) <= 1 and y <= 4:
                        is_door = True
                elif facing == "west" and dx == -hw:
                    if abs(dz) <= 1 and y <= 4:
                        is_door = True

                if is_door:
                    continue

                voxels.append({
                    "x": cx + dx, "y": y, "z": cz + dz,
                    "color": DARK_WOOD, "material": "solid",
                })

    # --- Interior light (y=3): warm emissive block at center ---
    voxels.append({
        "x": cx, "y": 3, "z": cz,
        "color": WARM_AMBER, "material": "emissive",
    })
    # Additional ambient glow
    for dx, dz in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
        voxels.append({
            "x": cx + dx, "y": wall_height, "z": cz + dz,
            "color": WARM_AMBER, "material": "emissive",
        })

    # --- Roof (y = wall_height+1 .. wall_height+3): dark tiles with overhang ---
    roof_base_y = wall_height + 1
    for layer in range(3):
        roof_y = roof_base_y + layer
        overhang = 2 - layer  # decreasing overhang as we go up (pyramid)
        rx = hw + overhang
        rz = hd + overhang

        if layer == 2:
            # Top ridge: single line
            for dx in range(-1, 2):
                voxels.append({
                    "x": cx + dx, "y": roof_y, "z": cz,
                    "color": DARK_TILE, "material": "solid",
                })
            continue

        for dx in range(-rx, rx + 1):
            for dz in range(-rz, rz + 1):
                is_edge_x = (abs(dx) >= rx - 1)
                is_edge_z = (abs(dz) >= rz - 1)
                is_inner = (abs(dx) < rx - 1 and abs(dz) < rz - 1)

                # Only place edge/shell blocks to create the roof shape
                if is_inner and layer == 0:
                    continue  # hollow interior at lowest roof layer
                if is_inner and layer == 1:
                    continue

                voxels.append({
                    "x": cx + dx, "y": roof_y, "z": cz + dz,
                    "color": DARK_TILE, "material": "solid",
                })

    # --- Roof ridge ornament: gold emissive at peak ---
    voxels.append({
        "x": cx, "y": roof_base_y + 3, "z": cz,
        "color": GOLD_EMISSIVE, "material": "emissive",
    })

    return voxels


def _generate_boundary_walls(
    min_x: int = -45,
    max_x: int = 45,
    min_z: int = -45,
    max_z: int = 45,
    height: int = 2,
    gate_positions: list[tuple[int, str]] | None = None,
) -> list[dict[str, Any]]:
    """Generate low stone boundary walls around the central area.

    Walls are 1 block thick and ``height`` blocks tall, with optional
    gaps at ``gate_positions`` for entry points.
    """
    voxels: list[dict[str, Any]] = []

    if gate_positions is None:
        gate_positions = []

    # Build a set of x/z positions that should be gaps (gates)
    gate_coords: set[tuple[str, int]] = set()
    for pos, axis in gate_positions:
        for offset in range(-2, 3):  # 5-block-wide gate
            gate_coords.add((axis, pos + offset))

    for y in range(0, height):
        # North wall (z = max_z)
        for x in range(min_x, max_x + 1):
            if ("x", x) in gate_coords:
                continue
            voxels.append({
                "x": x, "y": y, "z": max_z,
                "color": MED_GRAY, "material": "solid",
            })

        # South wall (z = min_z)
        for x in range(min_x, max_x + 1):
            if ("x", x) in gate_coords:
                continue
            voxels.append({
                "x": x, "y": y, "z": min_z,
                "color": MED_GRAY, "material": "solid",
            })

        # East wall (x = max_x)
        for z in range(min_z, max_z + 1):
            if ("z", z) in gate_coords:
                continue
            voxels.append({
                "x": max_x, "y": y, "z": z,
                "color": MED_GRAY, "material": "solid",
            })

        # West wall (x = min_x)
        for z in range(min_z, max_z + 1):
            if ("z", z) in gate_coords:
                continue
            voxels.append({
                "x": min_x, "y": y, "z": z,
                "color": MED_GRAY, "material": "solid",
            })

    return voxels


def _generate_scattered_lanterns() -> list[dict[str, Any]]:
    """Generate 10 stone lanterns along the main paths and near shrines."""
    voxels: list[dict[str, Any]] = []

    lantern_positions = [
        # Along the Z-axis path (from torii gate)
        (5, 10),
        (-5, 10),
        (5, -10),
        (-5, -10),
        (5, 25),
        (-5, 25),
        (5, -25),
        (-5, -25),
        # Near shrines
        (22, 22),
        (-22, -18),
    ]

    for lx, lz in lantern_positions:
        voxels.extend(_generate_stone_lantern(lx, lz))

    return voxels


# ---------------------------------------------------------------------------
# Full world template
# ---------------------------------------------------------------------------


def generate_full_template() -> list[dict[str, Any]]:
    """Generate the complete Japanese-themed world template.

    Returns a list of voxel dicts ready for placement. De-duplicates by
    position, keeping the last definition (later structures override earlier
    ground blocks).
    """
    all_voxels: list[dict[str, Any]] = []

    # 1. Stone paths (ground layer first so structures override)
    all_voxels.extend(_generate_stone_path(0, 0, direction="z", length=40, width=3))
    all_voxels.extend(_generate_stone_path(0, 0, direction="x", length=40, width=3))

    # 2. Grand Torii gate at world center
    all_voxels.extend(_generate_grand_torii(cx=0, cz=0))

    # 3. Stone lanterns along paths
    all_voxels.extend(_generate_scattered_lanterns())

    # 4. Shrines at three locations
    all_voxels.extend(_generate_shrine(cx=25, cz=25, width=8, depth=8, facing="south"))
    all_voxels.extend(_generate_shrine(cx=-25, cz=-20, width=8, depth=8, facing="east"))
    all_voxels.extend(_generate_shrine(cx=-20, cz=30, width=6, depth=6, wall_height=4, facing="south"))

    # 5. Boundary walls with gates at path crossings
    all_voxels.extend(_generate_boundary_walls(
        min_x=-45, max_x=45, min_z=-45, max_z=45,
        height=2,
        gate_positions=[
            (0, "x"),   # North/South gates along Z path
            (0, "z"),   # East/West gates along X path
        ],
    ))

    # De-duplicate: keep last voxel per position
    seen: dict[tuple[int, int, int], int] = {}
    for idx, v in enumerate(all_voxels):
        key = (v["x"], v["y"], v["z"])
        seen[key] = idx

    unique_voxels = [all_voxels[idx] for idx in sorted(seen.values())]

    logger.info(
        "World template generated: %d unique voxels (from %d raw)",
        len(unique_voxels),
        len(all_voxels),
    )

    return unique_voxels


# ---------------------------------------------------------------------------
# Database writer
# ---------------------------------------------------------------------------


async def apply_template_to_world(
    db: AsyncSession,
    placed_by: uuid.UUID | None = None,
) -> dict[str, Any]:
    """Write the full world template to the database.

    Skips positions that already have a voxel (idempotent). Creates
    Structure records for each named structure group.

    Returns summary dict with counts.
    """
    template_voxels = generate_full_template()

    placed = 0
    skipped = 0
    errors = 0

    # Group voxels by structure for Structure record creation
    structure_groups = {
        "Grand Torii Gate": {"type": "monument", "voxels": []},
        "North Path": {"type": "path", "voxels": []},
        "East Path": {"type": "path", "voxels": []},
        "Shrine East": {"type": "building", "voxels": []},
        "Shrine West": {"type": "building", "voxels": []},
        "Shrine North": {"type": "building", "voxels": []},
        "Boundary Wall": {"type": "wall", "voxels": []},
    }

    # Create a single structure record for the entire template
    template_structure = Structure(
        name="World Template: Japanese Garden",
        owner_id=placed_by,
        structure_type="monument",
        min_x=-45,
        min_y=0,
        min_z=-45,
        max_x=45,
        max_y=20,
        max_z=45,
        properties={
            "template": "japanese_garden",
            "theme": "chou_kaguya_hime",
            "auto_generated": True,
        },
        created_tick=0,
    )
    db.add(template_structure)
    await db.flush()

    structure_id = template_structure.id

    # Batch place all voxels
    for v in template_voxels:
        try:
            existing = await voxel_engine.get_block(db, v["x"], v["y"], v["z"])
            if existing is not None:
                skipped += 1
                continue

            block = VoxelBlock(
                x=v["x"],
                y=v["y"],
                z=v["z"],
                color=v["color"],
                material=v["material"],
                has_collision=True,
                placed_by=placed_by,
                structure_id=structure_id,
                placed_tick=0,
            )
            db.add(block)
            placed += 1

            # Flush periodically to avoid enormous pending list
            if placed % 200 == 0:
                await db.flush()

        except Exception as exc:
            errors += 1
            if errors <= 5:
                logger.warning(
                    "Failed to place voxel at (%d, %d, %d): %s",
                    v["x"], v["y"], v["z"], exc,
                )

    # Final flush
    await db.flush()

    # Update structure bounding box from actually placed voxels
    if placed > 0:
        result = await db.execute(
            select(
                func.min(VoxelBlock.x),
                func.min(VoxelBlock.y),
                func.min(VoxelBlock.z),
                func.max(VoxelBlock.x),
                func.max(VoxelBlock.y),
                func.max(VoxelBlock.z),
            ).where(VoxelBlock.structure_id == structure_id)
        )
        bounds = result.one_or_none()
        if bounds and bounds[0] is not None:
            template_structure.min_x = bounds[0]
            template_structure.min_y = bounds[1]
            template_structure.min_z = bounds[2]
            template_structure.max_x = bounds[3]
            template_structure.max_y = bounds[4]
            template_structure.max_z = bounds[5]
            db.add(template_structure)
            await db.flush()

    summary = {
        "template": "japanese_garden",
        "total_defined": len(template_voxels),
        "placed": placed,
        "skipped_existing": skipped,
        "errors": errors,
        "structure_id": str(structure_id),
    }

    logger.info(
        "World template applied: %d placed, %d skipped, %d errors",
        placed, skipped, errors,
    )

    return summary


async def auto_generate_if_empty(db: AsyncSession) -> dict[str, Any] | None:
    """Check if the world has fewer than 100 voxels and auto-generate if so.

    Returns the summary dict if generation was performed, None otherwise.
    """
    count = await voxel_engine.count_blocks(db)

    if count >= 100:
        logger.info(
            "World has %d voxels (>= 100), skipping auto-generation.", count
        )
        return None

    logger.info(
        "World has only %d voxels (< 100), auto-generating template...", count
    )

    # Try to find the god entity to use as placed_by
    from app.models.entity import Entity

    god_result = await db.execute(
        select(Entity).where(Entity.is_god == True).limit(1)  # noqa: E712
    )
    god = god_result.scalars().first()
    placed_by = god.id if god else None

    summary = await apply_template_to_world(db, placed_by=placed_by)
    await db.commit()

    return summary
