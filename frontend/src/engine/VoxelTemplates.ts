/**
 * GENESIS v3 VoxelTemplates
 *
 * Beautiful voxel structures for the initial world.
 * All structures are pure voxel data - rendered by VoxelRenderer.
 */
import type { Voxel } from '../types/v3';

// Colors
const RED = '#c41e3a';           // Torii red
const DARK_RED = '#8b0000';      // Darker red accent
const GOLD = '#ffd700';          // Golden ornaments
const STONE = '#707070';         // Stone gray
const DARK_STONE = '#505050';    // Darker stone
const LIGHT_STONE = '#909090';   // Light stone
const WOOD = '#5d4037';          // Wood brown
const DARK_WOOD = '#3e2723';     // Dark wood
const PINK = '#ffb6c1';          // Cherry blossom
const LIGHT_PINK = '#ffc0cb';    // Light pink
const WATER = '#1e90ff';         // Water blue
const LANTERN_LIGHT = '#ffcc00'; // Lantern glow
const LEAF_GREEN = '#228b22';    // Tree leaves
const BARK = '#4a3728';          // Tree bark

/**
 * Grand Torii Gate at origin.
 */
function createToriiGate(offsetX = 0, offsetZ = 0): Voxel[] {
  const voxels: Voxel[] = [];

  // Pillars (height 12)
  for (let y = 0; y < 12; y++) {
    // Left pillar
    voxels.push({ x: offsetX - 4, y, z: offsetZ, color: RED, material: 'solid', hasCollision: true });
    voxels.push({ x: offsetX - 3, y, z: offsetZ, color: RED, material: 'solid', hasCollision: true });
    // Right pillar
    voxels.push({ x: offsetX + 3, y, z: offsetZ, color: RED, material: 'solid', hasCollision: true });
    voxels.push({ x: offsetX + 4, y, z: offsetZ, color: RED, material: 'solid', hasCollision: true });
  }

  // Top beam (kasagi) - main
  for (let x = -6; x <= 6; x++) {
    voxels.push({ x: offsetX + x, y: 12, z: offsetZ, color: RED, material: 'solid', hasCollision: true });
    voxels.push({ x: offsetX + x, y: 13, z: offsetZ, color: DARK_RED, material: 'solid', hasCollision: true });
  }

  // Top beam curve ends
  voxels.push({ x: offsetX - 7, y: 13, z: offsetZ, color: DARK_RED, material: 'solid', hasCollision: true });
  voxels.push({ x: offsetX + 7, y: 13, z: offsetZ, color: DARK_RED, material: 'solid', hasCollision: true });
  voxels.push({ x: offsetX - 7, y: 14, z: offsetZ, color: DARK_RED, material: 'solid', hasCollision: true });
  voxels.push({ x: offsetX + 7, y: 14, z: offsetZ, color: DARK_RED, material: 'solid', hasCollision: true });

  // Lower beam (nuki)
  for (let x = -4; x <= 4; x++) {
    voxels.push({ x: offsetX + x, y: 9, z: offsetZ, color: RED, material: 'solid', hasCollision: true });
  }

  // Golden ornament on top
  voxels.push({ x: offsetX, y: 14, z: offsetZ, color: GOLD, material: 'emissive', hasCollision: true });

  return voxels;
}

/**
 * Stone Lantern (toro).
 */
function createStoneLantern(x: number, z: number): Voxel[] {
  const voxels: Voxel[] = [];

  // Base
  voxels.push({ x, y: 0, z, color: STONE, material: 'solid', hasCollision: true });
  voxels.push({ x: x + 1, y: 0, z, color: STONE, material: 'solid', hasCollision: true });
  voxels.push({ x, y: 0, z: z + 1, color: STONE, material: 'solid', hasCollision: true });
  voxels.push({ x: x + 1, y: 0, z: z + 1, color: STONE, material: 'solid', hasCollision: true });

  // Pillar
  voxels.push({ x, y: 1, z, color: DARK_STONE, material: 'solid', hasCollision: true });
  voxels.push({ x, y: 2, z, color: DARK_STONE, material: 'solid', hasCollision: true });
  voxels.push({ x, y: 3, z, color: DARK_STONE, material: 'solid', hasCollision: true });

  // Light box (emissive)
  voxels.push({ x, y: 4, z, color: LANTERN_LIGHT, material: 'emissive', hasCollision: true });
  voxels.push({ x: x + 1, y: 4, z, color: LANTERN_LIGHT, material: 'emissive', hasCollision: true });
  voxels.push({ x, y: 4, z: z + 1, color: LANTERN_LIGHT, material: 'emissive', hasCollision: true });
  voxels.push({ x: x + 1, y: 4, z: z + 1, color: LANTERN_LIGHT, material: 'emissive', hasCollision: true });

  // Roof
  for (let dx = -1; dx <= 2; dx++) {
    for (let dz = -1; dz <= 2; dz++) {
      voxels.push({ x: x + dx, y: 5, z: z + dz, color: STONE, material: 'solid', hasCollision: true });
    }
  }

  // Top cap
  voxels.push({ x, y: 6, z, color: DARK_STONE, material: 'solid', hasCollision: true });
  voxels.push({ x: x + 1, y: 6, z, color: DARK_STONE, material: 'solid', hasCollision: true });
  voxels.push({ x, y: 6, z: z + 1, color: DARK_STONE, material: 'solid', hasCollision: true });
  voxels.push({ x: x + 1, y: 6, z: z + 1, color: DARK_STONE, material: 'solid', hasCollision: true });
  voxels.push({ x, y: 7, z, color: DARK_STONE, material: 'solid', hasCollision: true });

  return voxels;
}

/**
 * Stone path (horizontal line of slabs).
 */
function createStonePath(startX: number, startZ: number, length: number, direction: 'x' | 'z'): Voxel[] {
  const voxels: Voxel[] = [];

  for (let i = 0; i < length; i++) {
    const x = direction === 'x' ? startX + i : startX;
    const z = direction === 'z' ? startZ + i : startZ;
    const color = i % 2 === 0 ? LIGHT_STONE : STONE;

    // Main path block
    voxels.push({ x, y: 0, z, color, material: 'solid', hasCollision: true });

    // Width of path (3 blocks)
    if (direction === 'x') {
      voxels.push({ x, y: 0, z: z - 1, color, material: 'solid', hasCollision: true });
      voxels.push({ x, y: 0, z: z + 1, color, material: 'solid', hasCollision: true });
    } else {
      voxels.push({ x: x - 1, y: 0, z, color, material: 'solid', hasCollision: true });
      voxels.push({ x: x + 1, y: 0, z, color, material: 'solid', hasCollision: true });
    }
  }

  return voxels;
}

/**
 * Cherry blossom tree.
 */
function createCherryTree(x: number, z: number): Voxel[] {
  const voxels: Voxel[] = [];

  // Trunk
  for (let y = 0; y < 6; y++) {
    voxels.push({ x, y, z, color: BARK, material: 'solid', hasCollision: true });
  }

  // Canopy (sphere-ish shape of pink voxels)
  const canopyY = 6;
  const canopyRadius = 4;

  for (let dy = 0; dy <= canopyRadius; dy++) {
    const r = canopyRadius - Math.floor(dy * 0.7);
    for (let dx = -r; dx <= r; dx++) {
      for (let dz = -r; dz <= r; dz++) {
        const dist = Math.sqrt(dx * dx + dz * dz);
        if (dist <= r + 0.5) {
          const color = Math.random() > 0.3 ? PINK : LIGHT_PINK;
          voxels.push({
            x: x + dx,
            y: canopyY + dy,
            z: z + dz,
            color,
            material: 'solid',
            hasCollision: false,
          });
        }
      }
    }
  }

  return voxels;
}

/**
 * Small shrine building.
 */
function createShrine(offsetX: number, offsetZ: number): Voxel[] {
  const voxels: Voxel[] = [];

  // Platform
  for (let x = -3; x <= 3; x++) {
    for (let z = -2; z <= 2; z++) {
      voxels.push({
        x: offsetX + x,
        y: 0,
        z: offsetZ + z,
        color: STONE,
        material: 'solid',
        hasCollision: true,
      });
    }
  }

  // Floor
  for (let x = -2; x <= 2; x++) {
    for (let z = -1; z <= 1; z++) {
      voxels.push({
        x: offsetX + x,
        y: 1,
        z: offsetZ + z,
        color: WOOD,
        material: 'solid',
        hasCollision: true,
      });
    }
  }

  // Walls
  for (let y = 2; y <= 4; y++) {
    // Back wall
    for (let x = -2; x <= 2; x++) {
      voxels.push({
        x: offsetX + x,
        y,
        z: offsetZ - 1,
        color: DARK_WOOD,
        material: 'solid',
        hasCollision: true,
      });
    }
    // Side walls
    voxels.push({ x: offsetX - 2, y, z: offsetZ, color: DARK_WOOD, material: 'solid', hasCollision: true });
    voxels.push({ x: offsetX - 2, y, z: offsetZ + 1, color: DARK_WOOD, material: 'solid', hasCollision: true });
    voxels.push({ x: offsetX + 2, y, z: offsetZ, color: DARK_WOOD, material: 'solid', hasCollision: true });
    voxels.push({ x: offsetX + 2, y, z: offsetZ + 1, color: DARK_WOOD, material: 'solid', hasCollision: true });
  }

  // Roof
  for (let x = -3; x <= 3; x++) {
    for (let z = -2; z <= 2; z++) {
      voxels.push({
        x: offsetX + x,
        y: 5,
        z: offsetZ + z,
        color: DARK_RED,
        material: 'solid',
        hasCollision: true,
      });
    }
  }

  // Roof peak
  for (let x = -2; x <= 2; x++) {
    voxels.push({
      x: offsetX + x,
      y: 6,
      z: offsetZ,
      color: DARK_RED,
      material: 'solid',
      hasCollision: true,
    });
  }
  voxels.push({ x: offsetX, y: 7, z: offsetZ, color: GOLD, material: 'emissive', hasCollision: true });

  // Inner lantern
  voxels.push({ x: offsetX, y: 2, z: offsetZ - 1, color: LANTERN_LIGHT, material: 'emissive', hasCollision: false });

  return voxels;
}

/**
 * Pond (water blocks).
 */
function createPond(centerX: number, centerZ: number, radius: number): Voxel[] {
  const voxels: Voxel[] = [];

  for (let dx = -radius; dx <= radius; dx++) {
    for (let dz = -radius; dz <= radius; dz++) {
      const dist = Math.sqrt(dx * dx + dz * dz);
      if (dist <= radius) {
        // Edge stones
        if (dist > radius - 1.5) {
          voxels.push({
            x: centerX + dx,
            y: 0,
            z: centerZ + dz,
            color: DARK_STONE,
            material: 'solid',
            hasCollision: true,
          });
        } else {
          // Water
          voxels.push({
            x: centerX + dx,
            y: 0,
            z: centerZ + dz,
            color: WATER,
            material: 'liquid',
            hasCollision: false,
          });
        }
      }
    }
  }

  return voxels;
}

/**
 * Generate the complete initial world template.
 */
export function generateInitialWorld(): Voxel[] {
  const allVoxels: Voxel[] = [];

  // Central torii gate
  allVoxels.push(...createToriiGate(0, 0));

  // Stone path extending from torii (both directions)
  allVoxels.push(...createStonePath(-30, 0, 60, 'x'));
  allVoxels.push(...createStonePath(0, -30, 60, 'z'));

  // Stone lanterns along the path
  const lanternPositions = [
    [-15, 4], [-15, -4], [15, 4], [15, -4],
    [4, -15], [-4, -15], [4, 15], [-4, 15],
    [-25, 4], [-25, -4], [25, 4], [25, -4],
  ];
  for (const [x, z] of lanternPositions) {
    allVoxels.push(...createStoneLantern(x, z));
  }

  // Shrine at the end of the path
  allVoxels.push(...createShrine(0, -35));

  // Cherry trees scattered around
  const treePositions = [
    [-20, 15], [20, 15], [-20, -20], [20, -20],
    [-30, 0], [30, 0], [0, 25], [-15, 25], [15, 25],
  ];
  for (const [x, z] of treePositions) {
    allVoxels.push(...createCherryTree(x, z));
  }

  // Pond to the side
  allVoxels.push(...createPond(-25, 20, 6));
  allVoxels.push(...createPond(25, -25, 5));

  return allVoxels;
}

/**
 * VoxelTemplates - export for use.
 */
export const VoxelTemplates = {
  createToriiGate,
  createStoneLantern,
  createStonePath,
  createCherryTree,
  createShrine,
  createPond,
  generateInitialWorld,
};
