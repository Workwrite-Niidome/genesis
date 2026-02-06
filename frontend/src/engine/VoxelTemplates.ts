/**
 * GENESIS v3 VoxelTemplates
 *
 * Beautiful voxel structures for the initial world.
 * All structures are pure voxel data - rendered by VoxelRenderer.
 * Enhanced with Japanese fantasy anime-inspired architecture.
 */
import type { Voxel } from '../types/v3';

// Colors - より鮮やかで美しい色彩
const RED = '#e63946';           // 鳥居の赤 (明るく)
const DARK_RED = '#9d0208';      // 濃い赤アクセント
const GOLD = '#ffc300';          // 黄金の装飾 (輝き)
const STONE = '#8d99ae';         // 石灰色 (明るく)
const DARK_STONE = '#6c757d';    // 濃い石
const LIGHT_STONE = '#adb5bd';   // 明るい石
const WOOD = '#8b5a2b';          // 木の茶色 (明るく)
const DARK_WOOD = '#5d4037';     // 濃い木
const PINK = '#ff85a1';          // 桜色 (鮮やか)
const LIGHT_PINK = '#ffc2d1';    // 薄いピンク
const WATER = '#4cc9f0';         // 水色 (明るく)
const LANTERN_LIGHT = '#ffd60a'; // 灯籠の光 (明るく)
const LEAF_GREEN = '#40916c';    // 木の葉の緑 (将来使用)
const BARK = '#6f4e37';          // 木の樹皮

// Emissive colors for bloom effects - アニメ風の発光色
const EMISSIVE_RED = '#ff3333';     // 発光する赤（鳥居用）
const EMISSIVE_GOLD = '#ffaa00';    // 発光する金（装飾用）
const EMISSIVE_CYAN = '#00ffff';    // 発光するシアン（アクセント用）

// Pagoda colors
const PAGODA_RED = '#c41e3a';       // 塔の赤
const PAGODA_DARK = '#8b0000';      // 塔の濃い赤

// 未使用変数の警告を回避
void LEAF_GREEN;

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
 * Glowing Torii Gate with emissive outline effect.
 * Creates a magical, anime-style torii with glowing edges.
 */
function createGlowingToriiGate(offsetX = 0, offsetZ = 0): Voxel[] {
  const voxels: Voxel[] = [];

  // Pillars (height 14) with emissive outline
  for (let y = 0; y < 14; y++) {
    // Left pillar - core
    voxels.push({ x: offsetX - 5, y, z: offsetZ, color: DARK_RED, material: 'solid', hasCollision: true });
    voxels.push({ x: offsetX - 4, y, z: offsetZ, color: RED, material: 'solid', hasCollision: true });
    // Left pillar - emissive edges
    voxels.push({ x: offsetX - 6, y, z: offsetZ, color: EMISSIVE_RED, material: 'emissive', hasCollision: false });
    voxels.push({ x: offsetX - 5, y, z: offsetZ - 1, color: EMISSIVE_RED, material: 'emissive', hasCollision: false });
    voxels.push({ x: offsetX - 5, y, z: offsetZ + 1, color: EMISSIVE_RED, material: 'emissive', hasCollision: false });

    // Right pillar - core
    voxels.push({ x: offsetX + 4, y, z: offsetZ, color: RED, material: 'solid', hasCollision: true });
    voxels.push({ x: offsetX + 5, y, z: offsetZ, color: DARK_RED, material: 'solid', hasCollision: true });
    // Right pillar - emissive edges
    voxels.push({ x: offsetX + 6, y, z: offsetZ, color: EMISSIVE_RED, material: 'emissive', hasCollision: false });
    voxels.push({ x: offsetX + 5, y, z: offsetZ - 1, color: EMISSIVE_RED, material: 'emissive', hasCollision: false });
    voxels.push({ x: offsetX + 5, y, z: offsetZ + 1, color: EMISSIVE_RED, material: 'emissive', hasCollision: false });
  }

  // Top beam (kasagi) - main with emissive outline
  for (let x = -7; x <= 7; x++) {
    voxels.push({ x: offsetX + x, y: 14, z: offsetZ, color: RED, material: 'solid', hasCollision: true });
    voxels.push({ x: offsetX + x, y: 15, z: offsetZ, color: DARK_RED, material: 'solid', hasCollision: true });
    // Top emissive edge
    voxels.push({ x: offsetX + x, y: 16, z: offsetZ, color: EMISSIVE_RED, material: 'emissive', hasCollision: false });
  }

  // Top beam curve ends with glow
  voxels.push({ x: offsetX - 8, y: 15, z: offsetZ, color: DARK_RED, material: 'solid', hasCollision: true });
  voxels.push({ x: offsetX + 8, y: 15, z: offsetZ, color: DARK_RED, material: 'solid', hasCollision: true });
  voxels.push({ x: offsetX - 8, y: 16, z: offsetZ, color: EMISSIVE_RED, material: 'emissive', hasCollision: false });
  voxels.push({ x: offsetX + 8, y: 16, z: offsetZ, color: EMISSIVE_RED, material: 'emissive', hasCollision: false });
  voxels.push({ x: offsetX - 9, y: 16, z: offsetZ, color: EMISSIVE_RED, material: 'emissive', hasCollision: false });
  voxels.push({ x: offsetX + 9, y: 16, z: offsetZ, color: EMISSIVE_RED, material: 'emissive', hasCollision: false });

  // Lower beam (nuki) with glow
  for (let x = -5; x <= 5; x++) {
    voxels.push({ x: offsetX + x, y: 10, z: offsetZ, color: RED, material: 'solid', hasCollision: true });
    // Emissive underline
    voxels.push({ x: offsetX + x, y: 9, z: offsetZ, color: EMISSIVE_GOLD, material: 'emissive', hasCollision: false });
  }

  // Golden ornaments on top - multiple glowing points
  voxels.push({ x: offsetX, y: 17, z: offsetZ, color: EMISSIVE_GOLD, material: 'emissive', hasCollision: true });
  voxels.push({ x: offsetX - 1, y: 16, z: offsetZ, color: EMISSIVE_GOLD, material: 'emissive', hasCollision: false });
  voxels.push({ x: offsetX + 1, y: 16, z: offsetZ, color: EMISSIVE_GOLD, material: 'emissive', hasCollision: false });

  // Cyan accent orbs floating near pillars
  voxels.push({ x: offsetX - 7, y: 8, z: offsetZ, color: EMISSIVE_CYAN, material: 'emissive', hasCollision: false });
  voxels.push({ x: offsetX + 7, y: 8, z: offsetZ, color: EMISSIVE_CYAN, material: 'emissive', hasCollision: false });
  voxels.push({ x: offsetX - 7, y: 4, z: offsetZ, color: EMISSIVE_CYAN, material: 'emissive', hasCollision: false });
  voxels.push({ x: offsetX + 7, y: 4, z: offsetZ, color: EMISSIVE_CYAN, material: 'emissive', hasCollision: false });

  return voxels;
}

/**
 * 5-story Pagoda with emissive lanterns.
 * Traditional Japanese pagoda with fantasy anime styling.
 */
function createPagoda(x: number, z: number, height = 5): Voxel[] {
  const voxels: Voxel[] = [];
  const floorHeight = 6; // Height per floor
  const baseWidth = 7;   // Base floor width

  // Foundation/Platform
  for (let dx = -baseWidth - 1; dx <= baseWidth + 1; dx++) {
    for (let dz = -baseWidth - 1; dz <= baseWidth + 1; dz++) {
      voxels.push({
        x: x + dx,
        y: 0,
        z: z + dz,
        color: STONE,
        material: 'solid',
        hasCollision: true,
      });
    }
  }

  // Build each floor
  for (let floor = 0; floor < height; floor++) {
    const floorY = 1 + floor * floorHeight;
    const floorWidth = baseWidth - floor; // Each floor gets narrower

    // Floor platform
    for (let dx = -floorWidth; dx <= floorWidth; dx++) {
      for (let dz = -floorWidth; dz <= floorWidth; dz++) {
        voxels.push({
          x: x + dx,
          y: floorY,
          z: z + dz,
          color: DARK_WOOD,
          material: 'solid',
          hasCollision: true,
        });
      }
    }

    // Walls (hollow interior)
    for (let dy = 1; dy < floorHeight - 2; dy++) {
      for (let dx = -floorWidth; dx <= floorWidth; dx++) {
        for (let dz = -floorWidth; dz <= floorWidth; dz++) {
          const isEdge = Math.abs(dx) === floorWidth || Math.abs(dz) === floorWidth;
          if (isEdge) {
            voxels.push({
              x: x + dx,
              y: floorY + dy,
              z: z + dz,
              color: PAGODA_RED,
              material: 'solid',
              hasCollision: true,
            });
          }
        }
      }
    }

    // Roof (curved eaves)
    const roofY = floorY + floorHeight - 2;
    const roofWidth = floorWidth + 2;
    for (let dx = -roofWidth; dx <= roofWidth; dx++) {
      for (let dz = -roofWidth; dz <= roofWidth; dz++) {
        const dist = Math.max(Math.abs(dx), Math.abs(dz));
        if (dist <= roofWidth) {
          // Main roof
          voxels.push({
            x: x + dx,
            y: roofY,
            z: z + dz,
            color: PAGODA_DARK,
            material: 'solid',
            hasCollision: true,
          });
          // Curved edge (corners go up)
          if (dist === roofWidth && (Math.abs(dx) === roofWidth || Math.abs(dz) === roofWidth)) {
            voxels.push({
              x: x + dx,
              y: roofY + 1,
              z: z + dz,
              color: PAGODA_DARK,
              material: 'solid',
              hasCollision: true,
            });
          }
        }
      }
    }

    // Emissive lanterns on each floor corner
    const lanternOffset = floorWidth + 1;
    const lanternY = floorY + 2;
    const lanternPositions = [
      [-lanternOffset, -lanternOffset],
      [-lanternOffset, lanternOffset],
      [lanternOffset, -lanternOffset],
      [lanternOffset, lanternOffset],
    ];
    for (const [ldx, ldz] of lanternPositions) {
      // Lantern body
      voxels.push({
        x: x + ldx,
        y: lanternY,
        z: z + ldz,
        color: EMISSIVE_GOLD,
        material: 'emissive',
        hasCollision: false,
      });
      voxels.push({
        x: x + ldx,
        y: lanternY + 1,
        z: z + ldz,
        color: EMISSIVE_RED,
        material: 'emissive',
        hasCollision: false,
      });
    }

    // Gold decorations on roof corners
    voxels.push({ x: x - roofWidth, y: roofY + 2, z: z - roofWidth, color: EMISSIVE_GOLD, material: 'emissive', hasCollision: false });
    voxels.push({ x: x - roofWidth, y: roofY + 2, z: z + roofWidth, color: EMISSIVE_GOLD, material: 'emissive', hasCollision: false });
    voxels.push({ x: x + roofWidth, y: roofY + 2, z: z - roofWidth, color: EMISSIVE_GOLD, material: 'emissive', hasCollision: false });
    voxels.push({ x: x + roofWidth, y: roofY + 2, z: z + roofWidth, color: EMISSIVE_GOLD, material: 'emissive', hasCollision: false });
  }

  // Spire on top
  const topY = 1 + height * floorHeight;
  for (let dy = 0; dy < 5; dy++) {
    voxels.push({
      x,
      y: topY + dy,
      z,
      color: EMISSIVE_GOLD,
      material: 'emissive',
      hasCollision: true,
    });
  }
  // Spire orb
  voxels.push({ x, y: topY + 5, z, color: EMISSIVE_CYAN, material: 'emissive', hasCollision: false });
  voxels.push({ x: x - 1, y: topY + 4, z, color: EMISSIVE_CYAN, material: 'emissive', hasCollision: false });
  voxels.push({ x: x + 1, y: topY + 4, z, color: EMISSIVE_CYAN, material: 'emissive', hasCollision: false });
  voxels.push({ x, y: topY + 4, z: z - 1, color: EMISSIVE_CYAN, material: 'emissive', hasCollision: false });
  voxels.push({ x, y: topY + 4, z: z + 1, color: EMISSIVE_CYAN, material: 'emissive', hasCollision: false });

  return voxels;
}

/**
 * Curved wooden bridge over water.
 * Creates an arched bridge between two points.
 */
function createBridge(startX: number, startZ: number, endX: number, endZ: number): Voxel[] {
  const voxels: Voxel[] = [];

  const dx = endX - startX;
  const dz = endZ - startZ;
  const length = Math.sqrt(dx * dx + dz * dz);
  const steps = Math.ceil(length);

  // Normalize direction
  const dirX = dx / length;
  const dirZ = dz / length;

  // Perpendicular for width
  const perpX = -dirZ;
  const perpZ = dirX;

  const bridgeWidth = 3;
  const maxArchHeight = 4;

  for (let i = 0; i <= steps; i++) {
    const t = i / steps;
    const currentX = Math.round(startX + dx * t);
    const currentZ = Math.round(startZ + dz * t);

    // Arch curve (parabola)
    const archHeight = Math.round(maxArchHeight * Math.sin(t * Math.PI));

    // Bridge deck
    for (let w = -bridgeWidth; w <= bridgeWidth; w++) {
      const wx = Math.round(currentX + perpX * w);
      const wz = Math.round(currentZ + perpZ * w);

      // Main deck
      voxels.push({
        x: wx,
        y: archHeight,
        z: wz,
        color: WOOD,
        material: 'solid',
        hasCollision: true,
      });

      // Support pillars at edges
      if (Math.abs(w) === bridgeWidth && i % 4 === 0) {
        for (let py = 0; py < archHeight; py++) {
          voxels.push({
            x: wx,
            y: py,
            z: wz,
            color: DARK_WOOD,
            material: 'solid',
            hasCollision: true,
          });
        }
      }
    }

    // Railings on both sides
    const railHeight = archHeight + 1;
    for (const side of [-bridgeWidth, bridgeWidth]) {
      const railX = Math.round(currentX + perpX * side);
      const railZ = Math.round(currentZ + perpZ * side);

      // Railing post
      voxels.push({
        x: railX,
        y: railHeight,
        z: railZ,
        color: DARK_RED,
        material: 'solid',
        hasCollision: true,
      });

      // Lantern on posts every 5 steps
      if (i % 5 === 0 && i > 0 && i < steps) {
        voxels.push({
          x: railX,
          y: railHeight + 1,
          z: railZ,
          color: EMISSIVE_GOLD,
          material: 'emissive',
          hasCollision: false,
        });
      }
    }
  }

  // Water underneath the bridge
  const waterY = -1;
  for (let i = 0; i <= steps; i++) {
    const t = i / steps;
    const currentX = Math.round(startX + dx * t);
    const currentZ = Math.round(startZ + dz * t);

    for (let w = -bridgeWidth - 2; w <= bridgeWidth + 2; w++) {
      const wx = Math.round(currentX + perpX * w);
      const wz = Math.round(currentZ + perpZ * w);
      voxels.push({
        x: wx,
        y: waterY,
        z: wz,
        color: WATER,
        material: 'liquid',
        hasCollision: false,
      });
    }
  }

  return voxels;
}

/**
 * Stone path with red torii gates every 10 units.
 * Creates a shrine approach path (sando).
 */
function createShrinePath(startX: number, startZ: number, length: number, direction: 'x' | 'z'): Voxel[] {
  const voxels: Voxel[] = [];

  for (let i = 0; i < length; i++) {
    const x = direction === 'x' ? startX + i : startX;
    const z = direction === 'z' ? startZ + i : startZ;
    const color = i % 2 === 0 ? LIGHT_STONE : STONE;

    // Main path block
    voxels.push({ x, y: 0, z, color, material: 'solid', hasCollision: true });

    // Width of path (5 blocks for grander appearance)
    if (direction === 'x') {
      voxels.push({ x, y: 0, z: z - 2, color, material: 'solid', hasCollision: true });
      voxels.push({ x, y: 0, z: z - 1, color, material: 'solid', hasCollision: true });
      voxels.push({ x, y: 0, z: z + 1, color, material: 'solid', hasCollision: true });
      voxels.push({ x, y: 0, z: z + 2, color, material: 'solid', hasCollision: true });
    } else {
      voxels.push({ x: x - 2, y: 0, z, color, material: 'solid', hasCollision: true });
      voxels.push({ x: x - 1, y: 0, z, color, material: 'solid', hasCollision: true });
      voxels.push({ x: x + 1, y: 0, z, color, material: 'solid', hasCollision: true });
      voxels.push({ x: x + 2, y: 0, z, color, material: 'solid', hasCollision: true });
    }

    // Small torii gate every 10 units
    if (i > 0 && i % 10 === 0 && i < length - 5) {
      const toriiHeight = 8;

      if (direction === 'x') {
        // Pillars
        for (let y = 0; y < toriiHeight; y++) {
          voxels.push({ x, y, z: z - 3, color: RED, material: 'solid', hasCollision: true });
          voxels.push({ x, y, z: z + 3, color: RED, material: 'solid', hasCollision: true });
        }
        // Top beam
        for (let dz = -4; dz <= 4; dz++) {
          voxels.push({ x, y: toriiHeight, z: z + dz, color: DARK_RED, material: 'solid', hasCollision: true });
        }
        // Emissive top
        voxels.push({ x, y: toriiHeight + 1, z, color: EMISSIVE_RED, material: 'emissive', hasCollision: false });
      } else {
        // Pillars
        for (let y = 0; y < toriiHeight; y++) {
          voxels.push({ x: x - 3, y, z, color: RED, material: 'solid', hasCollision: true });
          voxels.push({ x: x + 3, y, z, color: RED, material: 'solid', hasCollision: true });
        }
        // Top beam
        for (let dx = -4; dx <= 4; dx++) {
          voxels.push({ x: x + dx, y: toriiHeight, z, color: DARK_RED, material: 'solid', hasCollision: true });
        }
        // Emissive top
        voxels.push({ x, y: toriiHeight + 1, z, color: EMISSIVE_RED, material: 'emissive', hasCollision: false });
      }
    }
  }

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
 * Enhanced with Japanese fantasy anime-inspired cityscape.
 */
export function generateInitialWorld(): Voxel[] {
  const allVoxels: Voxel[] = [];

  // Central glowing torii gate (replaces basic torii)
  allVoxels.push(...createGlowingToriiGate(0, 0));

  // Shrine paths with torii gates extending from main torii
  allVoxels.push(...createShrinePath(-50, 0, 50, 'x'));  // West path
  allVoxels.push(...createShrinePath(1, 0, 50, 'x'));    // East path
  allVoxels.push(...createShrinePath(0, -50, 50, 'z')); // North path
  allVoxels.push(...createShrinePath(0, 1, 50, 'z'));   // South path

  // Pagodas at specified positions
  allVoxels.push(...createPagoda(-40, 30, 5));  // West pagoda
  allVoxels.push(...createPagoda(40, -30, 5));  // East pagoda

  // Curved bridge over water
  allVoxels.push(...createBridge(-30, -30, -20, -20));

  // Stone lanterns along the paths
  const lanternPositions = [
    [-15, 6], [-15, -6], [15, 6], [15, -6],
    [6, -15], [-6, -15], [6, 15], [-6, 15],
    [-25, 6], [-25, -6], [25, 6], [25, -6],
    [-35, 6], [-35, -6], [35, 6], [35, -6],
    [6, -25], [-6, -25], [6, 25], [-6, 25],
    [6, -35], [-6, -35], [6, 35], [-6, 35],
  ];
  for (const [x, z] of lanternPositions) {
    allVoxels.push(...createStoneLantern(x, z));
  }

  // Shrine at the end of the north path
  allVoxels.push(...createShrine(0, -45));

  // Cherry trees scattered around (more trees for anime atmosphere)
  const treePositions = [
    [-20, 15], [20, 15], [-20, -20], [20, -20],
    [-35, 10], [35, 10], [0, 35], [-15, 35], [15, 35],
    [-50, 25], [50, -25], [-45, -15], [45, 15],
    [-30, 40], [30, 40], [-25, -40], [25, -40],
    [-55, 0], [55, 0], [0, 45], [0, -55],
  ];
  for (const [x, z] of treePositions) {
    allVoxels.push(...createCherryTree(x, z));
  }

  // Ponds for reflection and atmosphere
  allVoxels.push(...createPond(-35, 20, 6));  // Near west pagoda
  allVoxels.push(...createPond(35, -20, 6));  // Near east pagoda
  allVoxels.push(...createPond(25, 35, 5));   // Additional pond
  allVoxels.push(...createPond(-45, -35, 4)); // Small pond near bridge

  return allVoxels;
}

/**
 * VoxelTemplates - export for use.
 */
export const VoxelTemplates = {
  createToriiGate,
  createGlowingToriiGate,
  createStoneLantern,
  createStonePath,
  createShrinePath,
  createCherryTree,
  createShrine,
  createPond,
  createPagoda,
  createBridge,
  generateInitialWorld,
};
