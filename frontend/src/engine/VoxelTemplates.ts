/**
 * GENESIS v3 VoxelTemplates
 *
 * Beautiful voxel structures for the initial world.
 * All structures are pure voxel data - rendered by VoxelRenderer.
 * Enhanced with "Cho-Kaguya-hime" Cyberpunk Japanese Fantasy style.
 *
 * Inspired by: Lantern sea around torii, Japanese townhouses,
 * pagodas, modern buildings fusion, waterfront setting.
 */
import type { Voxel } from '../types/v3';

// ========================================
// Basic Colors
// ========================================
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
const BARK = '#6f4e37';          // 木の樹皮

// ========================================
// Cyberpunk Japanese Colors (New)
// ========================================
const LANTERN_GOLD = '#ffcc66';   // 灯籠の暖かい金色 (emissive)
const PAPER_WHITE = '#fff8e8';    // 障子の和紙色
const WOOD_RED = '#8b2500';       // 赤い木造柱
const ROOF_GRAY = '#3a3a3a';      // 瓦屋根のグレー
const WINDOW_WARM = '#ffdd99';    // 暖かい窓の光 (emissive)
const SAKURA_PINK = '#ffb7c5';    // 桜のピンク
const NEON_CYAN = '#00ffff';      // サイバーパンク シアン (emissive)
const NEON_PINK = '#ff66aa';      // サイバーパンク ピンク (emissive)
const NEON_PURPLE = '#aa66ff';    // サイバーパンク パープル (emissive)
const DEEP_WATER = '#1a5276';     // 深い水面
const BUILDING_GRAY = '#2c3e50';  // 近代ビルのグレー
const BUILDING_DARK = '#1a252f';  // 近代ビルの濃いグレー
const GLASS_BLUE = '#5dade2';     // ガラス窓のブルー

// Emissive colors for bloom effects - アニメ風の発光色
const EMISSIVE_RED = '#ff3333';     // 発光する赤（鳥居用）
const EMISSIVE_GOLD = '#ffaa00';    // 発光する金（装飾用）
const EMISSIVE_CYAN = '#00ffff';    // 発光するシアン（アクセント用）

// Pagoda colors
const PAGODA_RED = '#c41e3a';       // 塔の赤
const PAGODA_DARK = '#8b0000';      // 塔の濃い赤

// ========================================
// Helper: Seeded random for consistent generation
// ========================================
function seededRandom(seed: number): () => number {
  let s = seed;
  return () => {
    s = (s * 1103515245 + 12345) & 0x7fffffff;
    return s / 0x7fffffff;
  };
}

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
 * MASSIVE Glowing Torii Gate - 超巨大な発光鳥居
 * Central landmark of the cyberpunk Japanese town.
 */
function createMassiveToriiGate(offsetX = 0, offsetZ = 0): Voxel[] {
  const voxels: Voxel[] = [];
  const height = 30;
  const pillarSpacing = 12;

  // Giant Pillars with emissive outline
  for (let y = 0; y < height; y++) {
    // Left pillar - 3x3 core
    for (let dx = -1; dx <= 1; dx++) {
      for (let dz = -1; dz <= 1; dz++) {
        voxels.push({
          x: offsetX - pillarSpacing + dx, y, z: offsetZ + dz,
          color: RED, material: 'solid', hasCollision: true
        });
      }
    }
    // Right pillar - 3x3 core
    for (let dx = -1; dx <= 1; dx++) {
      for (let dz = -1; dz <= 1; dz++) {
        voxels.push({
          x: offsetX + pillarSpacing + dx, y, z: offsetZ + dz,
          color: RED, material: 'solid', hasCollision: true
        });
      }
    }

    // Emissive edges every 3 blocks
    if (y % 3 === 0) {
      voxels.push({ x: offsetX - pillarSpacing - 2, y, z: offsetZ, color: EMISSIVE_RED, material: 'emissive', hasCollision: false });
      voxels.push({ x: offsetX + pillarSpacing + 2, y, z: offsetZ, color: EMISSIVE_RED, material: 'emissive', hasCollision: false });
      voxels.push({ x: offsetX - pillarSpacing, y, z: offsetZ - 2, color: NEON_CYAN, material: 'emissive', hasCollision: false });
      voxels.push({ x: offsetX + pillarSpacing, y, z: offsetZ - 2, color: NEON_CYAN, material: 'emissive', hasCollision: false });
    }
  }

  // Top beam (kasagi) - massive
  for (let x = -pillarSpacing - 5; x <= pillarSpacing + 5; x++) {
    for (let dz = -1; dz <= 1; dz++) {
      voxels.push({ x: offsetX + x, y: height, z: offsetZ + dz, color: RED, material: 'solid', hasCollision: true });
      voxels.push({ x: offsetX + x, y: height + 1, z: offsetZ + dz, color: DARK_RED, material: 'solid', hasCollision: true });
      voxels.push({ x: offsetX + x, y: height + 2, z: offsetZ + dz, color: DARK_RED, material: 'solid', hasCollision: true });
    }
    // Emissive top edge
    voxels.push({ x: offsetX + x, y: height + 3, z: offsetZ, color: EMISSIVE_RED, material: 'emissive', hasCollision: false });
  }

  // Curved beam ends
  for (let i = 0; i < 4; i++) {
    voxels.push({ x: offsetX - pillarSpacing - 6 - i, y: height + 2 + i, z: offsetZ, color: DARK_RED, material: 'solid', hasCollision: true });
    voxels.push({ x: offsetX + pillarSpacing + 6 + i, y: height + 2 + i, z: offsetZ, color: DARK_RED, material: 'solid', hasCollision: true });
    voxels.push({ x: offsetX - pillarSpacing - 6 - i, y: height + 3 + i, z: offsetZ, color: EMISSIVE_RED, material: 'emissive', hasCollision: false });
    voxels.push({ x: offsetX + pillarSpacing + 6 + i, y: height + 3 + i, z: offsetZ, color: EMISSIVE_RED, material: 'emissive', hasCollision: false });
  }

  // Lower beam (nuki) with golden glow
  for (let x = -pillarSpacing; x <= pillarSpacing; x++) {
    voxels.push({ x: offsetX + x, y: height - 8, z: offsetZ, color: RED, material: 'solid', hasCollision: true });
    voxels.push({ x: offsetX + x, y: height - 9, z: offsetZ, color: EMISSIVE_GOLD, material: 'emissive', hasCollision: false });
  }

  // Central golden ornaments
  for (let dy = 0; dy < 5; dy++) {
    voxels.push({ x: offsetX, y: height + 4 + dy, z: offsetZ, color: EMISSIVE_GOLD, material: 'emissive', hasCollision: true });
  }

  // Floating cyan orbs around the torii
  const orbPositions = [
    [-pillarSpacing - 3, height - 5], [pillarSpacing + 3, height - 5],
    [-pillarSpacing - 3, height - 15], [pillarSpacing + 3, height - 15],
    [-pillarSpacing - 3, 10], [pillarSpacing + 3, 10],
    [0, height + 6],
  ];
  for (const [ox, oy] of orbPositions) {
    voxels.push({ x: offsetX + ox, y: oy, z: offsetZ, color: NEON_CYAN, material: 'emissive', hasCollision: false });
  }

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
 * Japanese Townhouse (Machiya) - 日本風の町家
 * Red wooden pillars, shoji windows with warm light, tile roof.
 * @param x - X position
 * @param z - Z position
 * @param size - 1=small, 2=medium, 3=large
 */
function createJapaneseTownHouse(x: number, z: number, size: 1 | 2 | 3 = 2): Voxel[] {
  const voxels: Voxel[] = [];

  const width = 4 + size * 2;
  const depth = 3 + size * 2;
  const height = 4 + size * 2;

  // Foundation/Platform
  for (let dx = -1; dx <= width + 1; dx++) {
    for (let dz = -1; dz <= depth + 1; dz++) {
      voxels.push({
        x: x + dx, y: 0, z: z + dz,
        color: DARK_STONE, material: 'solid', hasCollision: true,
      });
    }
  }

  // Floor
  for (let dx = 0; dx <= width; dx++) {
    for (let dz = 0; dz <= depth; dz++) {
      voxels.push({
        x: x + dx, y: 1, z: z + dz,
        color: DARK_WOOD, material: 'solid', hasCollision: true,
      });
    }
  }

  // Walls with red wooden pillars and shoji windows
  for (let dy = 2; dy <= height; dy++) {
    // Back wall
    for (let dx = 0; dx <= width; dx++) {
      const isPillar = dx === 0 || dx === width || dx === Math.floor(width / 2);
      if (isPillar) {
        voxels.push({
          x: x + dx, y: dy, z: z,
          color: WOOD_RED, material: 'solid', hasCollision: true,
        });
      } else if (dy >= 3 && dy <= height - 1) {
        // Shoji window (glowing)
        voxels.push({
          x: x + dx, y: dy, z: z,
          color: WINDOW_WARM, material: 'emissive', hasCollision: true,
        });
      } else {
        voxels.push({
          x: x + dx, y: dy, z: z,
          color: PAPER_WHITE, material: 'solid', hasCollision: true,
        });
      }
    }

    // Front wall (with entrance gap)
    for (let dx = 0; dx <= width; dx++) {
      const isPillar = dx === 0 || dx === width;
      const isEntrance = dx >= Math.floor(width / 2) - 1 && dx <= Math.floor(width / 2) + 1 && dy <= 3;

      if (isEntrance) continue;

      if (isPillar) {
        voxels.push({
          x: x + dx, y: dy, z: z + depth,
          color: WOOD_RED, material: 'solid', hasCollision: true,
        });
      } else if (dy >= 3 && dy <= height - 1) {
        voxels.push({
          x: x + dx, y: dy, z: z + depth,
          color: WINDOW_WARM, material: 'emissive', hasCollision: true,
        });
      } else {
        voxels.push({
          x: x + dx, y: dy, z: z + depth,
          color: PAPER_WHITE, material: 'solid', hasCollision: true,
        });
      }
    }

    // Side walls
    for (let dz = 1; dz < depth; dz++) {
      const isPillar = dz === 1 || dz === depth - 1;
      // Left wall
      if (isPillar) {
        voxels.push({ x, y: dy, z: z + dz, color: WOOD_RED, material: 'solid', hasCollision: true });
      } else if (dy >= 3 && dy <= height - 1) {
        voxels.push({ x, y: dy, z: z + dz, color: WINDOW_WARM, material: 'emissive', hasCollision: true });
      } else {
        voxels.push({ x, y: dy, z: z + dz, color: PAPER_WHITE, material: 'solid', hasCollision: true });
      }
      // Right wall
      if (isPillar) {
        voxels.push({ x: x + width, y: dy, z: z + dz, color: WOOD_RED, material: 'solid', hasCollision: true });
      } else if (dy >= 3 && dy <= height - 1) {
        voxels.push({ x: x + width, y: dy, z: z + dz, color: WINDOW_WARM, material: 'emissive', hasCollision: true });
      } else {
        voxels.push({ x: x + width, y: dy, z: z + dz, color: PAPER_WHITE, material: 'solid', hasCollision: true });
      }
    }
  }

  // Tile Roof (kawara)
  const roofOverhang = 2;
  for (let layer = 0; layer <= 2; layer++) {
    const roofY = height + 1 + layer;
    const shrink = layer;
    for (let dx = -roofOverhang + shrink; dx <= width + roofOverhang - shrink; dx++) {
      for (let dz = -roofOverhang + shrink; dz <= depth + roofOverhang - shrink; dz++) {
        voxels.push({
          x: x + dx, y: roofY, z: z + dz,
          color: ROOF_GRAY, material: 'solid', hasCollision: true,
        });
      }
    }
  }

  // Roof ridge ornament
  for (let dx = 1; dx < width; dx++) {
    voxels.push({
      x: x + dx, y: height + 4, z: z + Math.floor(depth / 2),
      color: ROOF_GRAY, material: 'solid', hasCollision: true,
    });
  }

  // Hanging lantern at entrance
  voxels.push({
    x: x + Math.floor(width / 2), y: height, z: z + depth + 1,
    color: LANTERN_GOLD, material: 'emissive', hasCollision: false,
  });

  return voxels;
}

/**
 * Floating Lantern (Toro-Nagashi style) - 水面に浮かぶランタン
 * Single lantern floating on water.
 */
function createFloatingLantern(x: number, z: number, seed: number): Voxel[] {
  const voxels: Voxel[] = [];
  const rand = seededRandom(seed);

  // Water base (y = 0)
  voxels.push({
    x, y: 0, z,
    color: DEEP_WATER, material: 'liquid', hasCollision: false,
  });

  // Lantern base (floating)
  voxels.push({
    x, y: 1, z,
    color: DARK_WOOD, material: 'solid', hasCollision: false,
  });

  // Lantern body (emissive)
  const lanternColor = rand() > 0.5 ? LANTERN_GOLD : EMISSIVE_GOLD;
  voxels.push({
    x, y: 2, z,
    color: lanternColor, material: 'emissive', hasCollision: false,
  });

  return voxels;
}

/**
 * Lantern Sea (Toro-Nagashi) - 灯籠流し
 * Creates hundreds of floating lanterns around a center point.
 * @param centerX - Center X position
 * @param centerZ - Center Z position
 * @param radius - Radius of the lantern sea
 * @param count - Number of lanterns
 */
function createLanternSea(centerX: number, centerZ: number, radius: number, count: number): Voxel[] {
  const voxels: Voxel[] = [];
  const rand = seededRandom(centerX * 1000 + centerZ);

  // Water surface
  for (let dx = -radius; dx <= radius; dx += 2) {
    for (let dz = -radius; dz <= radius; dz += 2) {
      const dist = Math.sqrt(dx * dx + dz * dz);
      if (dist <= radius) {
        voxels.push({
          x: centerX + dx, y: 0, z: centerZ + dz,
          color: DEEP_WATER, material: 'liquid', hasCollision: false,
        });
      }
    }
  }

  // Place lanterns (limited to avoid performance issues)
  const actualCount = Math.min(count, 500);
  const placed = new Set<string>();
  let attempts = 0;

  while (placed.size < actualCount && attempts < actualCount * 3) {
    const angle = rand() * Math.PI * 2;
    const r = rand() * (radius - 2) + 2;
    const lx = Math.round(centerX + Math.cos(angle) * r);
    const lz = Math.round(centerZ + Math.sin(angle) * r);
    const key = `${lx},${lz}`;

    if (!placed.has(key)) {
      placed.add(key);
      voxels.push(...createFloatingLantern(lx, lz, lx * 100 + lz));
    }
    attempts++;
  }

  return voxels;
}

/**
 * Street Lanterns (Chochin) - 提灯が連なる通り
 * Creates a row of hanging paper lanterns along a street.
 */
function createStreetLanterns(
  startX: number,
  startZ: number,
  length: number,
  direction: 'x' | 'z'
): Voxel[] {
  const voxels: Voxel[] = [];
  const spacing = 3;
  const height = 4;

  for (let i = 0; i < length; i += spacing) {
    const x = direction === 'x' ? startX + i : startX;
    const z = direction === 'z' ? startZ + i : startZ;

    // Support post
    for (let y = 0; y < height; y++) {
      voxels.push({
        x, y, z,
        color: DARK_WOOD, material: 'solid', hasCollision: true,
      });
    }

    // Horizontal wire
    const wireLength = 2;
    for (let w = -wireLength; w <= wireLength; w++) {
      const wx = direction === 'x' ? x : x + w;
      const wz = direction === 'z' ? z : z + w;
      voxels.push({
        x: wx, y: height, z: wz,
        color: DARK_WOOD, material: 'solid', hasCollision: false,
      });
    }

    // Lanterns hanging from wire
    for (let w = -wireLength; w <= wireLength; w++) {
      if (w === 0) continue; // Skip center post
      const wx = direction === 'x' ? x : x + w;
      const wz = direction === 'z' ? z : z + w;
      const lanternColor = (i + w) % 6 < 3 ? LANTERN_GOLD : EMISSIVE_RED;
      voxels.push({
        x: wx, y: height - 1, z: wz,
        color: lanternColor, material: 'emissive', hasCollision: false,
      });
    }
  }

  // Stone path underneath
  for (let i = 0; i < length; i++) {
    const x = direction === 'x' ? startX + i : startX;
    const z = direction === 'z' ? startZ + i : startZ;
    const perpOffset = direction === 'x' ? 'z' : 'x';

    for (let p = -2; p <= 2; p++) {
      const px = perpOffset === 'x' ? x + p : x;
      const pz = perpOffset === 'z' ? z + p : z;
      voxels.push({
        x: px, y: 0, z: pz,
        color: i % 2 === 0 ? LIGHT_STONE : STONE, material: 'solid', hasCollision: true,
      });
    }
  }

  return voxels;
}

/**
 * Modern Building with glowing windows - 窓が光る近代ビル
 * Cyberpunk-style building with neon accents.
 */
function createModernBuilding(x: number, z: number, width: number, height: number): Voxel[] {
  const voxels: Voxel[] = [];
  const depth = Math.max(4, Math.floor(width * 0.8));
  const rand = seededRandom(x * 1000 + z * 100 + height);

  // Building core - only draw exterior walls to save voxels
  for (let dy = 0; dy < height; dy++) {
    // Bottom and top floors are solid
    if (dy === 0 || dy === height - 1) {
      for (let dx = 0; dx < width; dx++) {
        for (let dz = 0; dz < depth; dz++) {
          voxels.push({
            x: x + dx, y: dy, z: z + dz,
            color: BUILDING_DARK, material: 'solid', hasCollision: true,
          });
        }
      }
      continue;
    }

    // Walls only
    for (let dx = 0; dx < width; dx++) {
      for (let dz = 0; dz < depth; dz++) {
        const isEdge = dx === 0 || dx === width - 1 || dz === 0 || dz === depth - 1;
        if (!isEdge) continue;

        const isWindow = dy > 1 && dy < height - 2 &&
                        (dx > 0 && dx < width - 1) || (dz > 0 && dz < depth - 1);

        if (isWindow && rand() > 0.4) {
          // Lit window
          const windowColor = rand() > 0.7 ? NEON_CYAN :
                             rand() > 0.5 ? WINDOW_WARM : GLASS_BLUE;
          voxels.push({
            x: x + dx, y: dy, z: z + dz,
            color: windowColor, material: 'emissive', hasCollision: true,
          });
        } else {
          voxels.push({
            x: x + dx, y: dy, z: z + dz,
            color: dy % 5 === 0 ? BUILDING_DARK : BUILDING_GRAY,
            material: 'solid', hasCollision: true,
          });
        }
      }
    }
  }

  // Neon accents on edges
  const neonColors = [NEON_CYAN, NEON_PINK, NEON_PURPLE];
  const neonColor = neonColors[Math.floor(rand() * 3)];

  // Vertical neon lines
  for (let dy = 0; dy < height; dy += 2) {
    voxels.push({ x: x - 1, y: dy, z, color: neonColor, material: 'emissive', hasCollision: false });
    voxels.push({ x: x + width, y: dy, z, color: neonColor, material: 'emissive', hasCollision: false });
  }

  // Rooftop antenna/spire
  const spireHeight = Math.floor(height * 0.2);
  for (let dy = 0; dy < spireHeight; dy++) {
    voxels.push({
      x: x + Math.floor(width / 2),
      y: height + dy,
      z: z + Math.floor(depth / 2),
      color: dy === spireHeight - 1 ? NEON_CYAN : BUILDING_DARK,
      material: dy === spireHeight - 1 ? 'emissive' : 'solid',
      hasCollision: true,
    });
  }

  return voxels;
}

/**
 * Sakura Tree - 桜の木
 * Cherry blossom tree with pink flowers.
 */
function createSakuraTree(x: number, z: number): Voxel[] {
  const voxels: Voxel[] = [];
  const rand = seededRandom(x * 100 + z);

  // Trunk
  const trunkHeight = 5 + Math.floor(rand() * 3);
  for (let y = 0; y < trunkHeight; y++) {
    voxels.push({ x, y, z, color: BARK, material: 'solid', hasCollision: true });
    // Add some trunk width at base
    if (y < 2) {
      voxels.push({ x: x + 1, y, z, color: BARK, material: 'solid', hasCollision: true });
      voxels.push({ x: x - 1, y, z, color: BARK, material: 'solid', hasCollision: true });
      voxels.push({ x, y, z: z + 1, color: BARK, material: 'solid', hasCollision: true });
      voxels.push({ x, y, z: z - 1, color: BARK, material: 'solid', hasCollision: true });
    }
  }

  // Canopy (sakura blossoms)
  const canopyY = trunkHeight;
  const canopyRadius = 4;

  for (let dy = 0; dy <= canopyRadius; dy++) {
    const r = canopyRadius - Math.floor(dy * 0.6);
    for (let dx = -r; dx <= r; dx++) {
      for (let dz = -r; dz <= r; dz++) {
        const dist = Math.sqrt(dx * dx + dz * dz);
        if (dist <= r + 0.5 && rand() > 0.3) {
          const color = rand() > 0.4 ? SAKURA_PINK :
                       rand() > 0.3 ? LIGHT_PINK : PINK;
          voxels.push({
            x: x + dx, y: canopyY + dy, z: z + dz,
            color, material: 'solid', hasCollision: false,
          });
        }
      }
    }
  }

  // Falling petals (emissive for magical effect)
  for (let i = 0; i < 5; i++) {
    const px = x + Math.floor(rand() * 8) - 4;
    const py = Math.floor(rand() * trunkHeight);
    const pz = z + Math.floor(rand() * 8) - 4;
    voxels.push({
      x: px, y: py, z: pz,
      color: SAKURA_PINK, material: 'emissive', hasCollision: false,
    });
  }

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
  const rand = seededRandom(x * 100 + z);

  for (let dy = 0; dy <= canopyRadius; dy++) {
    const r = canopyRadius - Math.floor(dy * 0.7);
    for (let dx = -r; dx <= r; dx++) {
      for (let dz = -r; dz <= r; dz++) {
        const dist = Math.sqrt(dx * dx + dz * dz);
        if (dist <= r + 0.5) {
          const color = rand() > 0.3 ? PINK : LIGHT_PINK;
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
 * "Cho-Kaguya-hime" Cyberpunk Japanese Fantasy Townscape.
 *
 * Features:
 * - Central massive torii with lantern sea (toro-nagashi)
 * - Japanese townhouse district
 * - Multiple pagodas
 * - Lantern-lit main street
 * - Modern buildings in distance
 * - Sakura trees scattered throughout
 */
export function generateInitialWorld(): Voxel[] {
  const allVoxels: Voxel[] = [];

  // ========================================
  // Central Feature: Massive Torii Gate
  // ========================================
  allVoxels.push(...createMassiveToriiGate(0, 0));

  // ========================================
  // Lantern Sea around the Torii (Toro-Nagashi)
  // ========================================
  // Front lantern sea (main area)
  allVoxels.push(...createLanternSea(0, 30, 35, 300));
  // Side lantern clusters
  allVoxels.push(...createLanternSea(-30, 15, 15, 80));
  allVoxels.push(...createLanternSea(30, 15, 15, 80));
  // Back reflection pool
  allVoxels.push(...createLanternSea(0, -25, 20, 100));

  // ========================================
  // Japanese Town District (East Side)
  // ========================================
  // Row of townhouses along the waterfront
  allVoxels.push(...createJapaneseTownHouse(45, -10, 2));
  allVoxels.push(...createJapaneseTownHouse(45, 5, 3));
  allVoxels.push(...createJapaneseTownHouse(45, 20, 2));
  allVoxels.push(...createJapaneseTownHouse(45, 33, 1));

  // Second row of townhouses
  allVoxels.push(...createJapaneseTownHouse(58, -5, 3));
  allVoxels.push(...createJapaneseTownHouse(58, 12, 2));
  allVoxels.push(...createJapaneseTownHouse(58, 27, 2));

  // ========================================
  // Japanese Town District (West Side)
  // ========================================
  allVoxels.push(...createJapaneseTownHouse(-55, -10, 2));
  allVoxels.push(...createJapaneseTownHouse(-55, 5, 3));
  allVoxels.push(...createJapaneseTownHouse(-55, 20, 2));

  allVoxels.push(...createJapaneseTownHouse(-68, -5, 2));
  allVoxels.push(...createJapaneseTownHouse(-68, 15, 3));

  // ========================================
  // Main Lantern Street (Connecting Areas)
  // ========================================
  allVoxels.push(...createStreetLanterns(-40, -20, 80, 'x'));
  allVoxels.push(...createStreetLanterns(0, 50, 40, 'z'));

  // ========================================
  // Pagodas (Landmarks)
  // ========================================
  // Main 5-story pagoda (west)
  allVoxels.push(...createPagoda(-50, 45, 5));
  // Smaller pagoda (east)
  allVoxels.push(...createPagoda(55, 50, 4));
  // Additional pagoda in town
  allVoxels.push(...createPagoda(-70, -25, 3));

  // ========================================
  // Modern Buildings (Background - Far Distance)
  // ========================================
  // Tall buildings in the distance (northeast)
  allVoxels.push(...createModernBuilding(80, -50, 8, 35));
  allVoxels.push(...createModernBuilding(92, -45, 6, 45));
  allVoxels.push(...createModernBuilding(85, -35, 7, 28));

  // Buildings in the distance (northwest)
  allVoxels.push(...createModernBuilding(-85, -50, 7, 40));
  allVoxels.push(...createModernBuilding(-95, -40, 6, 30));

  // Buildings in the distance (south)
  allVoxels.push(...createModernBuilding(75, 70, 8, 38));
  allVoxels.push(...createModernBuilding(-80, 75, 7, 32));

  // ========================================
  // Sakura Trees (Throughout the Town)
  // ========================================
  const sakuraPositions = [
    // Near torii
    [-20, 10], [20, 10], [-15, -15], [15, -15],
    // In town districts
    [40, 0], [40, 25], [52, 15],
    [-45, 0], [-45, 25], [-52, 15],
    // Near pagodas
    [-58, 40], [-42, 50], [50, 42], [62, 55],
    // Along streets
    [-25, -20], [25, -20], [0, 55], [0, 70],
    // Additional scattered
    [-35, 30], [35, 30], [-30, -35], [30, -35],
  ];

  for (const [sx, sz] of sakuraPositions) {
    allVoxels.push(...createSakuraTree(sx, sz));
  }

  // ========================================
  // Traditional Elements (Shrine Path & Lanterns)
  // ========================================
  // Path from torii to shrine
  allVoxels.push(...createShrinePath(0, -50, 25, 'z'));

  // Shrine at the end of path
  allVoxels.push(...createShrine(0, -55));

  // Stone lanterns along paths
  const lanternPositions = [
    [-15, 6], [-15, -6], [15, 6], [15, -6],
    [6, -15], [-6, -15], [6, 60], [-6, 60],
    [-25, 6], [-25, -6], [25, 6], [25, -6],
    [6, -35], [-6, -35],
    // Additional lanterns near townhouses
    [42, 0], [42, 18], [-42, 0], [-42, 18],
  ];
  for (const [lx, lz] of lanternPositions) {
    allVoxels.push(...createStoneLantern(lx, lz));
  }

  // ========================================
  // Bridges Connecting Areas
  // ========================================
  allVoxels.push(...createBridge(-25, 25, -35, 35));
  allVoxels.push(...createBridge(25, 25, 35, 35));

  // ========================================
  // Additional Atmosphere: Small Ponds
  // ========================================
  allVoxels.push(...createPond(-60, 30, 5));
  allVoxels.push(...createPond(65, 35, 4));

  return allVoxels;
}

/**
 * VoxelTemplates - export for use.
 */
export const VoxelTemplates = {
  // Original functions
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

  // New Cyberpunk Japanese functions
  createMassiveToriiGate,
  createJapaneseTownHouse,
  createLanternSea,
  createStreetLanterns,
  createModernBuilding,
  createSakuraTree,
  createFloatingLantern,

  // Main generator
  generateInitialWorld,
};
