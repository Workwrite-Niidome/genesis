"""GENESIS v3 Voxel Engine — manages the 3D voxel space.

Handles querying, placing, destroying blocks, and collision/line-of-sight
detection. All operations go through SQLAlchemy async queries against the
voxel_blocks and structures tables.
"""
import logging
import math
import uuid

from sqlalchemy import select, func, delete, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.world import VoxelBlock, Structure

logger = logging.getLogger(__name__)


class VoxelEngine:
    """Manages the 3D voxel grid: placement, destruction, spatial queries."""

    # -------------------------------------------------------------------
    # Core CRUD
    # -------------------------------------------------------------------

    async def get_block(
        self, db: AsyncSession, x: int, y: int, z: int
    ) -> VoxelBlock | None:
        """Return the block at (x, y, z) or None."""
        result = await db.execute(
            select(VoxelBlock).where(
                VoxelBlock.x == x,
                VoxelBlock.y == y,
                VoxelBlock.z == z,
            )
        )
        return result.scalars().first()

    async def place_block(
        self,
        db: AsyncSession,
        x: int,
        y: int,
        z: int,
        color: str = "#888888",
        material: str = "solid",
        has_collision: bool = True,
        placed_by: uuid.UUID | None = None,
        tick: int = 0,
        structure_id: uuid.UUID | None = None,
    ) -> VoxelBlock:
        """Place a new voxel block at (x, y, z).

        Raises ValueError if a block already occupies that position.
        """
        existing = await self.get_block(db, x, y, z)
        if existing is not None:
            raise ValueError(
                f"Block already exists at ({x}, {y}, {z})"
            )

        block = VoxelBlock(
            x=x,
            y=y,
            z=z,
            color=color,
            material=material,
            has_collision=has_collision,
            placed_by=placed_by,
            structure_id=structure_id,
            placed_tick=tick,
        )
        db.add(block)
        await db.flush()
        return block

    async def destroy_block(
        self, db: AsyncSession, x: int, y: int, z: int
    ) -> bool:
        """Remove the block at (x, y, z).  Returns True if a block was deleted."""
        result = await db.execute(
            delete(VoxelBlock).where(
                VoxelBlock.x == x,
                VoxelBlock.y == y,
                VoxelBlock.z == z,
            )
        )
        return result.rowcount > 0

    # -------------------------------------------------------------------
    # Spatial queries
    # -------------------------------------------------------------------

    async def get_blocks_in_range(
        self,
        db: AsyncSession,
        min_pos: tuple[int, int, int],
        max_pos: tuple[int, int, int],
    ) -> list[VoxelBlock]:
        """Return all blocks within the axis-aligned bounding box [min, max]."""
        result = await db.execute(
            select(VoxelBlock).where(
                VoxelBlock.x >= min_pos[0],
                VoxelBlock.x <= max_pos[0],
                VoxelBlock.y >= min_pos[1],
                VoxelBlock.y <= max_pos[1],
                VoxelBlock.z >= min_pos[2],
                VoxelBlock.z <= max_pos[2],
            )
        )
        return list(result.scalars().all())

    async def is_position_blocked(
        self, db: AsyncSession, x: int, y: int, z: int
    ) -> bool:
        """Return True if a solid (has_collision=True) voxel exists at (x, y, z)."""
        result = await db.execute(
            select(func.count()).select_from(VoxelBlock).where(
                VoxelBlock.x == x,
                VoxelBlock.y == y,
                VoxelBlock.z == z,
                VoxelBlock.has_collision == True,  # noqa: E712
            )
        )
        return (result.scalar() or 0) > 0

    # -------------------------------------------------------------------
    # Line-of-sight (3D Bresenham)
    # -------------------------------------------------------------------

    @staticmethod
    def _bresenham_3d(
        x0: int, y0: int, z0: int,
        x1: int, y1: int, z1: int,
    ) -> list[tuple[int, int, int]]:
        """Return all integer grid cells along the line from (x0,y0,z0) to (x1,y1,z1).

        Uses the 3D Bresenham line algorithm.  The start and end points are
        included in the returned list.
        """
        points: list[tuple[int, int, int]] = []

        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        dz = abs(z1 - z0)

        sx = 1 if x1 > x0 else -1
        sy = 1 if y1 > y0 else -1
        sz = 1 if z1 > z0 else -1

        # Driving axis is the one with the largest delta
        if dx >= dy and dx >= dz:
            # X-dominant
            err_y = 2 * dy - dx
            err_z = 2 * dz - dx
            x, y, z = x0, y0, z0
            for _ in range(dx + 1):
                points.append((x, y, z))
                if err_y > 0:
                    y += sy
                    err_y -= 2 * dx
                if err_z > 0:
                    z += sz
                    err_z -= 2 * dx
                err_y += 2 * dy
                err_z += 2 * dz
                x += sx
        elif dy >= dx and dy >= dz:
            # Y-dominant
            err_x = 2 * dx - dy
            err_z = 2 * dz - dy
            x, y, z = x0, y0, z0
            for _ in range(dy + 1):
                points.append((x, y, z))
                if err_x > 0:
                    x += sx
                    err_x -= 2 * dy
                if err_z > 0:
                    z += sz
                    err_z -= 2 * dy
                err_x += 2 * dx
                err_z += 2 * dz
                y += sy
        else:
            # Z-dominant
            err_x = 2 * dx - dz
            err_y = 2 * dy - dz
            x, y, z = x0, y0, z0
            for _ in range(dz + 1):
                points.append((x, y, z))
                if err_x > 0:
                    x += sx
                    err_x -= 2 * dz
                if err_y > 0:
                    y += sy
                    err_y -= 2 * dz
                err_x += 2 * dx
                err_y += 2 * dy
                z += sz

        return points

    async def is_line_of_sight_clear(
        self,
        db: AsyncSession,
        pos1: tuple[int, int, int],
        pos2: tuple[int, int, int],
    ) -> bool:
        """Return True if no solid voxel blocks the line between pos1 and pos2.

        Uses 3D Bresenham to enumerate grid cells along the ray, then checks
        each cell (excluding start and end) for a collision voxel.
        """
        cells = self._bresenham_3d(
            pos1[0], pos1[1], pos1[2],
            pos2[0], pos2[1], pos2[2],
        )

        # Skip the start and end positions (the entities' own cells)
        intermediate = cells[1:-1] if len(cells) > 2 else []

        if not intermediate:
            return True

        # Batch query: find any collision block among the intermediate cells.
        # Build OR conditions for each cell.
        cell_conditions = [
            and_(
                VoxelBlock.x == cx,
                VoxelBlock.y == cy,
                VoxelBlock.z == cz,
            )
            for cx, cy, cz in intermediate
        ]

        # To avoid a potentially enormous OR, chunk if necessary.
        # For typical line-of-sight distances (< 100 blocks) this is fine.
        from sqlalchemy import or_

        result = await db.execute(
            select(func.count()).select_from(VoxelBlock).where(
                VoxelBlock.has_collision == True,  # noqa: E712
                or_(*cell_conditions),
            )
        )
        count = result.scalar() or 0
        return count == 0

    # -------------------------------------------------------------------
    # Structure queries
    # -------------------------------------------------------------------

    async def get_nearby_structures(
        self,
        db: AsyncSession,
        x: int,
        y: int,
        z: int,
        radius: int,
    ) -> list[Structure]:
        """Return structures whose bounding box overlaps the sphere around (x,y,z).

        We approximate by checking if the structure's AABB is within `radius`
        of the query point on every axis (conservative box-to-sphere test).
        """
        result = await db.execute(
            select(Structure).where(
                Structure.min_x <= x + radius,
                Structure.max_x >= x - radius,
                Structure.min_y <= y + radius,
                Structure.max_y >= y - radius,
                Structure.min_z <= z + radius,
                Structure.max_z >= z - radius,
            )
        )
        return list(result.scalars().all())

    # -------------------------------------------------------------------
    # Aggregate helpers
    # -------------------------------------------------------------------

    async def count_blocks(self, db: AsyncSession) -> int:
        """Return the total number of voxel blocks in the world."""
        result = await db.execute(
            select(func.count()).select_from(VoxelBlock)
        )
        return result.scalar() or 0

    async def count_blocks_by_entity(
        self, db: AsyncSession, entity_id: uuid.UUID
    ) -> int:
        """Return the number of blocks placed by a specific entity."""
        result = await db.execute(
            select(func.count()).select_from(VoxelBlock).where(
                VoxelBlock.placed_by == entity_id,
            )
        )
        return result.scalar() or 0


# Module-level singleton
voxel_engine = VoxelEngine()
