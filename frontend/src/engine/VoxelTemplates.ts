/**
 * GENESIS v3 VoxelTemplates
 *
 * Beautiful voxel structures for the initial world.
 * All structures are pure voxel data - rendered by VoxelRenderer.
 * Enhanced with "Cho-Kaguya-hime" Cyberpunk Japanese Fantasy style.
 *
 * Inspired by: Lantern sea around torii, Japanese townhouses,
 * pagodas, modern buildings fusion, waterfront setting.
 *
 * Layout Structure (3x Expanded):
 * - Center: Massive Torii Gate + Lantern Sea (radius 0-120 - water area, no buildings)
 * - Inner Ring: Waterfront buildings, engawa (radius 120-145)
 * - Middle Ring: Main town (radius 145-200)
 * - Outer Ring: Pagodas, tall buildings (radius 200-250)
 * - Far Outer: Modern skyscrapers (radius 250+)
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

// ========================================
// New Colors for Enhanced Town (追加色定義)
// ========================================
const TATAMI_GREEN = '#8b9556';     // 畳
const SHOJI_CREAM = '#f5f0e1';      // 障子
const TILE_DARK = '#2a2a2a';        // 瓦（暗い）
const TILE_GRAY = '#4a4a4a';        // 瓦（明るい）
const LANTERN_RED = '#cc3333';      // 赤提灯
const COLUMN_VERMILLION = '#c41e3a'; // 朱色の柱
const ENGAWA_WOOD = '#a67c52';      // 縁側の木
const FUSUMA_BEIGE = '#d4c4a8';     // 襖のベージュ

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
 * Central landmark - FULLY EMISSIVE for maximum glow effect.
 */
function createMassiveToriiGate(offsetX = 0, offsetZ = 0): Voxel[] {
  const voxels: Voxel[] = [];
  const height = 30;
  const pillarSpacing = 12;

  // Giant Pillars - EMISSIVE for glow (clean design, no extra decorations)
  for (let y = 0; y < height; y++) {
    // Left pillar - 3x3 core - EMISSIVE RED
    for (let dx = -1; dx <= 1; dx++) {
      for (let dz = -1; dz <= 1; dz++) {
        voxels.push({
          x: offsetX - pillarSpacing + dx, y, z: offsetZ + dz,
          color: EMISSIVE_RED, material: 'emissive', hasCollision: true
        });
      }
    }
    // Right pillar - 3x3 core - EMISSIVE RED
    for (let dx = -1; dx <= 1; dx++) {
      for (let dz = -1; dz <= 1; dz++) {
        voxels.push({
          x: offsetX + pillarSpacing + dx, y, z: offsetZ + dz,
          color: EMISSIVE_RED, material: 'emissive', hasCollision: true
        });
      }
    }
  }

  // Top beam (kasagi) - massive - EMISSIVE
  for (let x = -pillarSpacing - 5; x <= pillarSpacing + 5; x++) {
    for (let dz = -1; dz <= 1; dz++) {
      voxels.push({ x: offsetX + x, y: height, z: offsetZ + dz, color: EMISSIVE_RED, material: 'emissive', hasCollision: true });
      voxels.push({ x: offsetX + x, y: height + 1, z: offsetZ + dz, color: EMISSIVE_RED, material: 'emissive', hasCollision: true });
      voxels.push({ x: offsetX + x, y: height + 2, z: offsetZ + dz, color: DARK_RED, material: 'emissive', hasCollision: true });
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

  // Central golden ornament on top (single elegant piece)
  for (let dy = 0; dy < 3; dy++) {
    voxels.push({ x: offsetX, y: height + 4 + dy, z: offsetZ, color: EMISSIVE_GOLD, material: 'emissive', hasCollision: true });
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
 * Detailed Japanese Townhouse (Machiya) - 詳細な日本家屋
 * Multi-floor with shoji windows (lattice pattern), warm light, eave lanterns, tiled roof
 * @param x - X position
 * @param z - Z position
 * @param floors - Number of floors (1-4)
 * @param width - Building width (4-10)
 * @param depth - Building depth (4-8)
 */
function createDetailedTownHouse(
  x: number,
  z: number,
  floors: number = 2,
  width: number = 6,
  depth: number = 5
): Voxel[] {
  const voxels: Voxel[] = [];
  const floorHeight = 4;
  const totalHeight = floors * floorHeight;

  // Foundation/Platform (stone base)
  for (let dx = -1; dx <= width; dx++) {
    for (let dz = -1; dz <= depth; dz++) {
      voxels.push({
        x: x + dx, y: 0, z: z + dz,
        color: DARK_STONE, material: 'solid', hasCollision: true,
      });
    }
  }

  // Build each floor
  for (let floor = 0; floor < floors; floor++) {
    const floorY = 1 + floor * floorHeight;

    // Floor/Tatami
    for (let dx = 0; dx < width; dx++) {
      for (let dz = 0; dz < depth; dz++) {
        const isTatami = dx > 0 && dx < width - 1 && dz > 0 && dz < depth - 1;
        voxels.push({
          x: x + dx, y: floorY, z: z + dz,
          color: isTatami ? TATAMI_GREEN : DARK_WOOD,
          material: 'solid', hasCollision: true,
        });
      }
    }

    // Walls with pillars and shoji windows
    for (let dy = 1; dy < floorHeight; dy++) {
      const wallY = floorY + dy;

      // Back wall
      for (let dx = 0; dx < width; dx++) {
        const isPillar = dx === 0 || dx === width - 1 || (dx % 3 === 0);
        if (isPillar) {
          voxels.push({
            x: x + dx, y: wallY, z: z,
            color: COLUMN_VERMILLION, material: 'solid', hasCollision: true,
          });
        } else if (dy === 1 || dy === floorHeight - 1) {
          // Frame
          voxels.push({
            x: x + dx, y: wallY, z: z,
            color: DARK_WOOD, material: 'solid', hasCollision: true,
          });
        } else {
          // Shoji window with lattice pattern (emissive warm light)
          const isLattice = (dx + dy) % 2 === 0;
          voxels.push({
            x: x + dx, y: wallY, z: z,
            color: isLattice ? SHOJI_CREAM : WINDOW_WARM,
            material: isLattice ? 'solid' : 'emissive',
            hasCollision: true,
          });
        }
      }

      // Front wall (with entrance on ground floor)
      for (let dx = 0; dx < width; dx++) {
        const isPillar = dx === 0 || dx === width - 1 || (dx % 3 === 0);
        const isEntrance = floor === 0 && dx >= Math.floor(width / 2) - 1 && dx <= Math.floor(width / 2) && dy < 3;

        if (isEntrance) continue;

        if (isPillar) {
          voxels.push({
            x: x + dx, y: wallY, z: z + depth - 1,
            color: COLUMN_VERMILLION, material: 'solid', hasCollision: true,
          });
        } else if (dy === 1 || dy === floorHeight - 1) {
          voxels.push({
            x: x + dx, y: wallY, z: z + depth - 1,
            color: DARK_WOOD, material: 'solid', hasCollision: true,
          });
        } else {
          const isLattice = (dx + dy) % 2 === 0;
          voxels.push({
            x: x + dx, y: wallY, z: z + depth - 1,
            color: isLattice ? SHOJI_CREAM : WINDOW_WARM,
            material: isLattice ? 'solid' : 'emissive',
            hasCollision: true,
          });
        }
      }

      // Side walls
      for (let dz = 1; dz < depth - 1; dz++) {
        const isPillar = dz % 2 === 0;
        // Left wall
        if (isPillar || dy === 1 || dy === floorHeight - 1) {
          voxels.push({
            x, y: wallY, z: z + dz,
            color: isPillar ? COLUMN_VERMILLION : DARK_WOOD,
            material: 'solid', hasCollision: true,
          });
        } else {
          voxels.push({
            x, y: wallY, z: z + dz,
            color: FUSUMA_BEIGE, material: 'solid', hasCollision: true,
          });
        }
        // Right wall
        if (isPillar || dy === 1 || dy === floorHeight - 1) {
          voxels.push({
            x: x + width - 1, y: wallY, z: z + dz,
            color: isPillar ? COLUMN_VERMILLION : DARK_WOOD,
            material: 'solid', hasCollision: true,
          });
        } else {
          voxels.push({
            x: x + width - 1, y: wallY, z: z + dz,
            color: FUSUMA_BEIGE, material: 'solid', hasCollision: true,
          });
        }
      }
    }
  }

  // Tile Roof (kawara) - stepped layers
  const roofOverhang = 2;
  for (let layer = 0; layer <= 3; layer++) {
    const roofY = totalHeight + 1 + layer;
    const shrink = Math.floor(layer * 0.7);
    for (let dx = -roofOverhang + shrink; dx < width + roofOverhang - shrink; dx++) {
      for (let dz = -roofOverhang + shrink; dz < depth + roofOverhang - shrink; dz++) {
        const isEdge = dx === -roofOverhang + shrink || dx === width + roofOverhang - shrink - 1 ||
                      dz === -roofOverhang + shrink || dz === depth + roofOverhang - shrink - 1;
        voxels.push({
          x: x + dx, y: roofY, z: z + dz,
          color: isEdge ? TILE_GRAY : TILE_DARK,
          material: 'solid', hasCollision: true,
        });
      }
    }
  }

  // Roof ridge
  for (let dx = 0; dx < width; dx++) {
    voxels.push({
      x: x + dx, y: totalHeight + 5, z: z + Math.floor(depth / 2),
      color: TILE_GRAY, material: 'solid', hasCollision: true,
    });
  }

  // Eave lanterns (chochin) - hanging from each floor
  for (let floor = 0; floor < floors; floor++) {
    const lanternY = 1 + (floor + 1) * floorHeight - 1;
    // Front lanterns
    for (let dx = 2; dx < width - 1; dx += 3) {
      const lanternColor = dx % 2 === 0 ? LANTERN_RED : LANTERN_GOLD;
      voxels.push({
        x: x + dx, y: lanternY, z: z + depth,
        color: lanternColor, material: 'emissive', hasCollision: false,
      });
    }
  }

  // Ground floor entrance noren (curtain hint)
  voxels.push({
    x: x + Math.floor(width / 2), y: 3, z: z + depth,
    color: LANTERN_RED, material: 'emissive', hasCollision: false,
  });

  return voxels;
}

/**
 * Japanese Townhouse (Machiya) - 日本風の町家 (Original - kept for compatibility)
 */
function createJapaneseTownHouse(x: number, z: number, size: 1 | 2 | 3 = 2): Voxel[] {
  // Use new detailed function with mapped parameters
  const floors = size;
  const width = 4 + size * 2;
  const depth = 3 + size * 2;
  return createDetailedTownHouse(x, z, floors, width, depth);
}

/**
 * Town Block - 複数の建物がまとまった区画
 * Creates a cluster of buildings with narrow alleys
 * @param centerX - Center X position
 * @param centerZ - Center Z position
 * @param size - Block size (1=small, 2=medium, 3=large)
 */
function createTownBlock(centerX: number, centerZ: number, size: 1 | 2 | 3 = 2): Voxel[] {
  const voxels: Voxel[] = [];
  const rand = seededRandom(centerX * 1000 + centerZ);

  const buildingCount = size + 2; // 3-5 buildings per block
  const blockRadius = size * 8;

  // Place buildings in the block
  const placedAreas: Array<{ x: number; z: number; w: number; d: number }> = [];

  for (let i = 0; i < buildingCount; i++) {
    let attempts = 0;
    let placed = false;

    while (!placed && attempts < 20) {
      const bWidth = Math.floor(rand() * 3) + 4 + size;
      const bDepth = Math.floor(rand() * 2) + 4 + size;
      const bFloors = Math.floor(rand() * 3) + 1;

      const bx = centerX + Math.floor(rand() * blockRadius * 2) - blockRadius;
      const bz = centerZ + Math.floor(rand() * blockRadius * 2) - blockRadius;

      // Check for overlap (allow 1-2 block spacing)
      let overlaps = false;
      for (const area of placedAreas) {
        if (bx < area.x + area.w + 2 && bx + bWidth + 2 > area.x &&
            bz < area.z + area.d + 2 && bz + bDepth + 2 > area.z) {
          overlaps = true;
          break;
        }
      }

      if (!overlaps) {
        voxels.push(...createDetailedTownHouse(bx, bz, bFloors, bWidth, bDepth));
        placedAreas.push({ x: bx, z: bz, w: bWidth, d: bDepth });
        placed = true;
      }
      attempts++;
    }
  }

  // Narrow stone alleys between buildings
  for (let i = 0; i < placedAreas.length - 1; i++) {
    const a1 = placedAreas[i];
    const a2 = placedAreas[i + 1];
    const startX = a1.x + a1.w;
    const endX = a2.x;
    const midZ = Math.floor((a1.z + a2.z + a1.d) / 2);

    if (startX < endX) {
      for (let px = startX; px < endX; px++) {
        voxels.push({
          x: px, y: 0, z: midZ,
          color: LIGHT_STONE, material: 'solid', hasCollision: true,
        });
      }
    }
  }

  // Shared well or small plaza in center
  if (rand() > 0.5) {
    const wellX = centerX;
    const wellZ = centerZ;
    // Well structure
    for (let dx = -1; dx <= 1; dx++) {
      for (let dz = -1; dz <= 1; dz++) {
        voxels.push({
          x: wellX + dx, y: 0, z: wellZ + dz,
          color: STONE, material: 'solid', hasCollision: true,
        });
        if (Math.abs(dx) === 1 || Math.abs(dz) === 1) {
          voxels.push({
            x: wellX + dx, y: 1, z: wellZ + dz,
            color: DARK_STONE, material: 'solid', hasCollision: true,
          });
        }
      }
    }
    // Well roof
    for (let dx = -1; dx <= 1; dx++) {
      voxels.push({
        x: wellX + dx, y: 3, z: wellZ,
        color: DARK_WOOD, material: 'solid', hasCollision: true,
      });
    }
    voxels.push({
      x: wellX, y: 4, z: wellZ,
      color: TILE_DARK, material: 'solid', hasCollision: true,
    });
  }

  return voxels;
}

/**
 * Waterfront Building - 水面に面した建物
 * Building with engawa (veranda) and stairs to water
 * @param x - X position
 * @param z - Z position
 * @param facing - Direction facing water ('n', 's', 'e', 'w')
 */
function createWaterfrontBuilding(
  x: number,
  z: number,
  facing: 'n' | 's' | 'e' | 'w' = 's'
): Voxel[] {
  const voxels: Voxel[] = [];
  const width = 8;
  const depth = 6;
  const floors = 2;

  // Main building (slightly elevated)
  voxels.push(...createDetailedTownHouse(x, z, floors, width, depth));

  // Engawa (wooden veranda) facing water
  const engawaWidth = width + 2;
  const engawaDepth = 3;

  let engawaX = x - 1;
  let engawaZ = z;
  let stairX = x + Math.floor(width / 2);
  let stairZ = z;

  switch (facing) {
    case 's':
      engawaZ = z + depth;
      stairZ = z + depth + engawaDepth;
      break;
    case 'n':
      engawaZ = z - engawaDepth;
      stairZ = z - engawaDepth - 1;
      break;
    case 'e':
      engawaX = x + width;
      stairX = x + width + engawaDepth;
      break;
    case 'w':
      engawaX = x - engawaDepth;
      stairX = x - engawaDepth - 1;
      break;
  }

  // Engawa platform
  if (facing === 's' || facing === 'n') {
    for (let dx = 0; dx < engawaWidth; dx++) {
      for (let dz = 0; dz < engawaDepth; dz++) {
        // Wooden deck
        voxels.push({
          x: engawaX + dx, y: 1, z: engawaZ + dz,
          color: ENGAWA_WOOD, material: 'solid', hasCollision: true,
        });
        // Support pillars on edges
        if ((dx === 0 || dx === engawaWidth - 1) && dz === engawaDepth - 1) {
          for (let py = 0; py <= 1; py++) {
            voxels.push({
              x: engawaX + dx, y: py, z: engawaZ + dz,
              color: DARK_WOOD, material: 'solid', hasCollision: true,
            });
          }
        }
      }
    }

    // Railing
    for (let dx = 0; dx < engawaWidth; dx++) {
      voxels.push({
        x: engawaX + dx, y: 2, z: engawaZ + (facing === 's' ? engawaDepth - 1 : 0),
        color: DARK_WOOD, material: 'solid', hasCollision: true,
      });
    }

    // Stairs to water
    for (let step = 0; step < 3; step++) {
      const stepZ = facing === 's' ? stairZ + step : stairZ - step;
      for (let dx = -1; dx <= 1; dx++) {
        voxels.push({
          x: stairX + dx, y: -step, z: stepZ,
          color: STONE, material: 'solid', hasCollision: true,
        });
      }
    }
  }

  // Lanterns on engawa posts
  voxels.push({
    x: engawaX, y: 3, z: engawaZ + (facing === 's' ? engawaDepth - 1 : 0),
    color: LANTERN_GOLD, material: 'emissive', hasCollision: false,
  });
  voxels.push({
    x: engawaX + engawaWidth - 1, y: 3, z: engawaZ + (facing === 's' ? engawaDepth - 1 : 0),
    color: LANTERN_GOLD, material: 'emissive', hasCollision: false,
  });

  return voxels;
}

/**
 * Lantern Row - 提灯の列
 * Creates a dense row of alternating red and gold lanterns
 * @param x - Start X position
 * @param z - Start Z position
 * @param length - Length of the row
 * @param direction - Direction ('x' or 'z')
 */
function createLanternRow(
  x: number,
  z: number,
  length: number,
  direction: 'x' | 'z'
): Voxel[] {
  const voxels: Voxel[] = [];
  const spacing = 2; // Dense spacing
  const height = 5;

  for (let i = 0; i <= length; i += spacing) {
    const px = direction === 'x' ? x + i : x;
    const pz = direction === 'z' ? z + i : z;

    // Support post
    for (let y = 0; y < height; y++) {
      voxels.push({
        x: px, y, z: pz,
        color: DARK_WOOD, material: 'solid', hasCollision: true,
      });
    }

    // Horizontal wire
    const wireLength = 3;
    for (let w = -wireLength; w <= wireLength; w++) {
      const wx = direction === 'z' ? px + w : px;
      const wz = direction === 'x' ? pz + w : pz;
      voxels.push({
        x: wx, y: height, z: wz,
        color: DARK_WOOD, material: 'solid', hasCollision: false,
      });

      // Lanterns - alternating colors, dense
      if (w !== 0) {
        const lanternColor = (i + Math.abs(w)) % 4 < 2 ? LANTERN_RED : LANTERN_GOLD;
        voxels.push({
          x: wx, y: height - 1, z: wz,
          color: lanternColor, material: 'emissive', hasCollision: false,
        });
      }
    }
  }

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

  // No water base blocks - the scene has a water plane shader already

  // Place lanterns (sparse distribution for aesthetic appeal)
  // Limit count and ensure minimum spacing between lanterns
  const actualCount = Math.min(count, 150); // Reduced from 300
  const placed = new Set<string>();
  const minSpacing = 8; // Minimum distance between lanterns
  let attempts = 0;

  while (placed.size < actualCount && attempts < actualCount * 5) {
    const angle = rand() * Math.PI * 2;
    const r = 5 + rand() * (radius - 10); // Keep away from center and edge
    const lx = Math.round(centerX + Math.cos(angle) * r);
    const lz = Math.round(centerZ + Math.sin(angle) * r);
    const key = `${lx},${lz}`;

    // Check spacing from existing lanterns
    let tooClose = false;
    for (const existingKey of placed) {
      const [ex, ez] = existingKey.split(',').map(Number);
      const dist = Math.sqrt((lx - ex) ** 2 + (lz - ez) ** 2);
      if (dist < minSpacing) {
        tooClose = true;
        break;
      }
    }

    if (!tooClose && !placed.has(key)) {
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
 * Detailed 5-story Pagoda with enhanced decoration
 * Traditional Japanese pagoda with fantasy anime styling.
 * @param x - X position
 * @param z - Z position
 * @param floors - Number of floors (3-7)
 */
function createDetailedPagoda(x: number, z: number, floors: number = 5): Voxel[] {
  const voxels: Voxel[] = [];
  const floorHeight = 5;
  const baseWidth = 6 + floors;

  // Foundation/Platform (larger)
  for (let dx = -baseWidth - 2; dx <= baseWidth + 2; dx++) {
    for (let dz = -baseWidth - 2; dz <= baseWidth + 2; dz++) {
      voxels.push({
        x: x + dx, y: 0, z: z + dz,
        color: STONE, material: 'solid', hasCollision: true,
      });
    }
  }

  // Steps leading to entrance
  for (let step = 1; step <= 2; step++) {
    for (let dx = -3; dx <= 3; dx++) {
      voxels.push({
        x: x + dx, y: step, z: z + baseWidth + step,
        color: LIGHT_STONE, material: 'solid', hasCollision: true,
      });
    }
  }

  // Build each floor
  for (let floor = 0; floor < floors; floor++) {
    const floorY = 1 + floor * floorHeight;
    const floorWidth = baseWidth - floor;

    // Floor platform
    for (let dx = -floorWidth; dx <= floorWidth; dx++) {
      for (let dz = -floorWidth; dz <= floorWidth; dz++) {
        voxels.push({
          x: x + dx, y: floorY, z: z + dz,
          color: DARK_WOOD, material: 'solid', hasCollision: true,
        });
      }
    }

    // Walls with pillars and decorative windows
    for (let dy = 1; dy < floorHeight - 2; dy++) {
      for (let dx = -floorWidth; dx <= floorWidth; dx++) {
        for (let dz = -floorWidth; dz <= floorWidth; dz++) {
          const isEdge = Math.abs(dx) === floorWidth || Math.abs(dz) === floorWidth;
          const isCorner = Math.abs(dx) === floorWidth && Math.abs(dz) === floorWidth;

          if (isCorner) {
            // Corner pillars
            voxels.push({
              x: x + dx, y: floorY + dy, z: z + dz,
              color: COLUMN_VERMILLION, material: 'solid', hasCollision: true,
            });
          } else if (isEdge) {
            // Windows or walls
            const isWindow = dy > 0 && dy < floorHeight - 3 &&
                            (Math.abs(dx) < floorWidth - 1 || Math.abs(dz) < floorWidth - 1);
            if (isWindow && (dx + dz) % 2 === 0) {
              voxels.push({
                x: x + dx, y: floorY + dy, z: z + dz,
                color: WINDOW_WARM, material: 'emissive', hasCollision: true,
              });
            } else {
              voxels.push({
                x: x + dx, y: floorY + dy, z: z + dz,
                color: PAGODA_RED, material: 'solid', hasCollision: true,
              });
            }
          }
        }
      }
    }

    // Roof (curved eaves with multiple layers)
    const roofY = floorY + floorHeight - 2;
    const roofWidth = floorWidth + 2;

    for (let layer = 0; layer < 2; layer++) {
      for (let dx = -roofWidth + layer; dx <= roofWidth - layer; dx++) {
        for (let dz = -roofWidth + layer; dz <= roofWidth - layer; dz++) {
          const dist = Math.max(Math.abs(dx), Math.abs(dz));
          if (dist <= roofWidth - layer) {
            voxels.push({
              x: x + dx, y: roofY + layer, z: z + dz,
              color: layer === 0 ? TILE_DARK : TILE_GRAY,
              material: 'solid', hasCollision: true,
            });
          }
        }
      }
    }

    // Curved corner tips
    const corners = [
      [-roofWidth, -roofWidth], [-roofWidth, roofWidth],
      [roofWidth, -roofWidth], [roofWidth, roofWidth],
    ];
    for (const [cdx, cdz] of corners) {
      voxels.push({
        x: x + cdx, y: roofY + 2, z: z + cdz,
        color: TILE_GRAY, material: 'solid', hasCollision: true,
      });
      // Golden ornament on corner
      voxels.push({
        x: x + cdx, y: roofY + 3, z: z + cdz,
        color: EMISSIVE_GOLD, material: 'emissive', hasCollision: false,
      });
    }

    // Lanterns on each floor corner (inside roof)
    const lanternOffset = floorWidth;
    const lanternY = floorY + 2;
    const lanternPositions = [
      [-lanternOffset, -lanternOffset],
      [-lanternOffset, lanternOffset],
      [lanternOffset, -lanternOffset],
      [lanternOffset, lanternOffset],
    ];
    for (const [ldx, ldz] of lanternPositions) {
      voxels.push({
        x: x + ldx, y: lanternY, z: z + ldz,
        color: LANTERN_RED, material: 'emissive', hasCollision: false,
      });
    }
  }

  // Spire on top (sorin)
  const topY = 1 + floors * floorHeight;
  // Base ring
  for (let dx = -1; dx <= 1; dx++) {
    for (let dz = -1; dz <= 1; dz++) {
      voxels.push({
        x: x + dx, y: topY, z: z + dz,
        color: EMISSIVE_GOLD, material: 'emissive', hasCollision: true,
      });
    }
  }
  // Spire shaft
  for (let dy = 1; dy < 8; dy++) {
    voxels.push({
      x, y: topY + dy, z,
      color: dy < 6 ? GOLD : EMISSIVE_GOLD,
      material: dy >= 6 ? 'emissive' : 'solid',
      hasCollision: true,
    });
  }
  // Rings around spire
  for (let ring = 0; ring < 3; ring++) {
    const ringY = topY + 2 + ring * 2;
    for (const offset of [-1, 1]) {
      voxels.push({ x: x + offset, y: ringY, z, color: GOLD, material: 'solid', hasCollision: false });
      voxels.push({ x, y: ringY, z: z + offset, color: GOLD, material: 'solid', hasCollision: false });
    }
  }
  // Top orb
  voxels.push({ x, y: topY + 8, z, color: EMISSIVE_CYAN, material: 'emissive', hasCollision: false });
  voxels.push({ x: x - 1, y: topY + 7, z, color: NEON_CYAN, material: 'emissive', hasCollision: false });
  voxels.push({ x: x + 1, y: topY + 7, z, color: NEON_CYAN, material: 'emissive', hasCollision: false });
  voxels.push({ x, y: topY + 7, z: z - 1, color: NEON_CYAN, material: 'emissive', hasCollision: false });
  voxels.push({ x, y: topY + 7, z: z + 1, color: NEON_CYAN, material: 'emissive', hasCollision: false });

  return voxels;
}

/**
 * 5-story Pagoda with emissive lanterns (Original - kept for compatibility)
 */
function createPagoda(x: number, z: number, height = 5): Voxel[] {
  return createDetailedPagoda(x, z, height);
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
 * Shop building with signage - 商店
 * Small shop with noren curtain and signage
 */
function createShopBuilding(x: number, z: number, shopType: 'food' | 'goods' | 'tea' = 'food'): Voxel[] {
  const voxels: Voxel[] = [];
  const width = 5;
  const depth = 4;
  const height = 8;

  // Base building
  voxels.push(...createDetailedTownHouse(x, z, 2, width, depth));

  // Shop-specific decorations
  const signColor = shopType === 'food' ? LANTERN_RED :
                   shopType === 'tea' ? LANTERN_GOLD : NEON_CYAN;

  // Noren (shop curtain) - indicated by colored blocks
  for (let dx = 1; dx < width - 1; dx++) {
    voxels.push({
      x: x + dx, y: 2, z: z + depth,
      color: signColor, material: 'emissive', hasCollision: false,
    });
    voxels.push({
      x: x + dx, y: 3, z: z + depth,
      color: signColor, material: 'emissive', hasCollision: false,
    });
  }

  // Sign lantern
  voxels.push({
    x: x + Math.floor(width / 2), y: height, z: z + depth + 1,
    color: LANTERN_GOLD, material: 'emissive', hasCollision: false,
  });

  return voxels;
}

// ========================================
// NEW: Terrain and Diverse Building Types
// ========================================

/**
 * Create a raised terrain platform/hill with natural stone edges.
 */
function createTerrainHill(x: number, z: number, radius: number, height: number): Voxel[] {
  const voxels: Voxel[] = [];

  for (let dx = -radius; dx <= radius; dx++) {
    for (let dz = -radius; dz <= radius; dz++) {
      const dist = Math.sqrt(dx * dx + dz * dz);
      if (dist <= radius) {
        // Height decreases toward edges
        const localHeight = Math.max(1, Math.floor(height * (1 - dist / radius * 0.6)));
        for (let dy = 0; dy < localHeight; dy++) {
          const isEdge = dist > radius - 2;
          voxels.push({
            x: x + dx, y: dy, z: z + dz,
            color: isEdge ? STONE : (dy === localHeight - 1 ? TATAMI_GREEN : DARK_STONE),
            material: 'solid', hasCollision: true,
          });
        }
      }
    }
  }
  return voxels;
}

/**
 * Create a stone staircase between two heights.
 */
function createStaircase(x: number, z: number, startY: number, endY: number, direction: 'x' | 'z', length: number): Voxel[] {
  const voxels: Voxel[] = [];
  const steps = Math.abs(endY - startY);
  const stepLength = Math.floor(length / steps);
  const goingUp = endY > startY;

  for (let i = 0; i <= steps; i++) {
    const currentY = goingUp ? startY + i : startY - i;
    const stepStart = i * stepLength;

    // Create step platform
    for (let s = 0; s < stepLength; s++) {
      const sx = direction === 'x' ? x + stepStart + s : x;
      const sz = direction === 'z' ? z + stepStart + s : z;

      // Step surface
      voxels.push({
        x: sx, y: currentY, z: sz,
        color: LIGHT_STONE, material: 'solid', hasCollision: true,
      });
      // Side walls
      for (let side = -1; side <= 1; side += 2) {
        const wallX = direction === 'z' ? sx + side : sx;
        const wallZ = direction === 'x' ? sz + side : sz;
        voxels.push({
          x: wallX, y: currentY, z: wallZ,
          color: STONE, material: 'solid', hasCollision: true,
        });
      }
    }
  }
  return voxels;
}

/**
 * Create a wooden watchtower.
 */
function createWatchTower(x: number, z: number, baseY: number = 0): Voxel[] {
  const voxels: Voxel[] = [];
  const height = 12;

  // Four corner pillars
  const corners = [[-1, -1], [-1, 1], [1, -1], [1, 1]];
  for (const [dx, dz] of corners) {
    for (let y = baseY; y < baseY + height; y++) {
      voxels.push({
        x: x + dx * 2, y, z: z + dz * 2,
        color: DARK_WOOD, material: 'solid', hasCollision: true,
      });
    }
  }

  // Platform at top
  for (let dx = -3; dx <= 3; dx++) {
    for (let dz = -3; dz <= 3; dz++) {
      voxels.push({
        x: x + dx, y: baseY + height, z: z + dz,
        color: WOOD, material: 'solid', hasCollision: true,
      });
    }
  }

  // Railing
  for (let dx = -3; dx <= 3; dx++) {
    voxels.push({ x: x + dx, y: baseY + height + 1, z: z - 3, color: DARK_WOOD, material: 'solid', hasCollision: true });
    voxels.push({ x: x + dx, y: baseY + height + 1, z: z + 3, color: DARK_WOOD, material: 'solid', hasCollision: true });
  }
  for (let dz = -3; dz <= 3; dz++) {
    voxels.push({ x: x - 3, y: baseY + height + 1, z: z + dz, color: DARK_WOOD, material: 'solid', hasCollision: true });
    voxels.push({ x: x + 3, y: baseY + height + 1, z: z + dz, color: DARK_WOOD, material: 'solid', hasCollision: true });
  }

  // Roof
  for (let dy = 0; dy < 3; dy++) {
    const size = 4 - dy;
    for (let dx = -size; dx <= size; dx++) {
      voxels.push({
        x: x + dx, y: baseY + height + 2 + dy, z: z,
        color: TILE_DARK, material: 'solid', hasCollision: true,
      });
      voxels.push({
        x: x, y: baseY + height + 2 + dy, z: z + dx,
        color: TILE_DARK, material: 'solid', hasCollision: true,
      });
    }
  }

  // Lantern at top
  voxels.push({ x: x, y: baseY + height + 5, z: z, color: LANTERN_GOLD, material: 'emissive', hasCollision: false });

  return voxels;
}

/**
 * Create a traditional tea house with veranda.
 */
function createTeaHouse(x: number, z: number, baseY: number = 0): Voxel[] {
  const voxels: Voxel[] = [];
  const width = 8;
  const depth = 6;
  const height = 5;

  // Raised floor platform
  for (let dx = -1; dx <= width + 1; dx++) {
    for (let dz = -1; dz <= depth + 1; dz++) {
      voxels.push({
        x: x + dx, y: baseY, z: z + dz,
        color: ENGAWA_WOOD, material: 'solid', hasCollision: true,
      });
    }
  }

  // Tatami floor
  for (let dx = 0; dx < width; dx++) {
    for (let dz = 0; dz < depth; dz++) {
      voxels.push({
        x: x + dx, y: baseY + 1, z: z + dz,
        color: TATAMI_GREEN, material: 'solid', hasCollision: true,
      });
    }
  }

  // Corner posts
  const posts = [[0, 0], [width - 1, 0], [0, depth - 1], [width - 1, depth - 1]];
  for (const [px, pz] of posts) {
    for (let y = baseY + 1; y < baseY + height; y++) {
      voxels.push({
        x: x + px, y, z: z + pz,
        color: COLUMN_VERMILLION, material: 'solid', hasCollision: true,
      });
    }
  }

  // Shoji screens (partial walls)
  for (let dx = 1; dx < width - 1; dx++) {
    if (dx % 2 === 0) {
      for (let y = baseY + 2; y < baseY + height - 1; y++) {
        voxels.push({ x: x + dx, y, z: z, color: SHOJI_CREAM, material: 'solid', hasCollision: true });
      }
    }
  }

  // Low roof with wide eaves
  for (let dx = -2; dx <= width + 1; dx++) {
    for (let dz = -2; dz <= depth + 1; dz++) {
      voxels.push({
        x: x + dx, y: baseY + height, z: z + dz,
        color: TILE_GRAY, material: 'solid', hasCollision: true,
      });
    }
  }

  // Lantern at entrance
  voxels.push({ x: x + Math.floor(width / 2), y: baseY + height - 1, z: z - 1, color: LANTERN_RED, material: 'emissive', hasCollision: false });

  return voxels;
}

/**
 * Create a market stall.
 */
function createMarketStall(x: number, z: number, baseY: number = 0, type: 'food' | 'goods' | 'lantern'): Voxel[] {
  const voxels: Voxel[] = [];

  // Counter
  for (let dx = 0; dx < 4; dx++) {
    voxels.push({ x: x + dx, y: baseY, z: z, color: WOOD, material: 'solid', hasCollision: true });
    voxels.push({ x: x + dx, y: baseY + 1, z: z, color: WOOD, material: 'solid', hasCollision: true });
  }

  // Support posts
  voxels.push({ x: x, y: baseY + 2, z: z, color: DARK_WOOD, material: 'solid', hasCollision: true });
  voxels.push({ x: x + 3, y: baseY + 2, z: z, color: DARK_WOOD, material: 'solid', hasCollision: true });
  voxels.push({ x: x, y: baseY + 3, z: z, color: DARK_WOOD, material: 'solid', hasCollision: true });
  voxels.push({ x: x + 3, y: baseY + 3, z: z, color: DARK_WOOD, material: 'solid', hasCollision: true });

  // Cloth canopy
  const canopyColor = type === 'food' ? LANTERN_RED : type === 'goods' ? NEON_PURPLE : LANTERN_GOLD;
  for (let dx = -1; dx <= 4; dx++) {
    voxels.push({ x: x + dx, y: baseY + 4, z: z, color: canopyColor, material: 'solid', hasCollision: true });
    voxels.push({ x: x + dx, y: baseY + 4, z: z - 1, color: canopyColor, material: 'solid', hasCollision: true });
  }

  // Display items based on type
  if (type === 'lantern') {
    voxels.push({ x: x + 1, y: baseY + 2, z: z, color: LANTERN_GOLD, material: 'emissive', hasCollision: false });
    voxels.push({ x: x + 2, y: baseY + 2, z: z, color: LANTERN_RED, material: 'emissive', hasCollision: false });
  }

  return voxels;
}

/**
 * Generate the complete initial world template.
 * "Cho-Kaguya-hime" Cyberpunk Japanese Fantasy Townscape.
 *
 * Layout:
 * - Center (radius 0-40): Torii + Lantern Sea (water area)
 * - Inner Ring (radius 40-50): Waterfront buildings
 * - Middle Ring (radius 50-90): Main town (dense)
 * - Outer Ring (radius 90-120): High-rise buildings, pagodas
 *
 * Scale: 10x compared to original
 * - Town houses: 150+ buildings
 * - Shops: 50+ buildings
 * - Pagodas: 8-10
 * - Lantern rows: 20+
 * - Sakura trees: 50+
 * - Modern buildings: 15+
 */
export function generateInitialWorld(): Voxel[] {
  const allVoxels: Voxel[] = [];
  const rand = seededRandom(42);

  // ========================================
  // Central Feature: Massive Torii Gate (at origin)
  // ========================================
  allVoxels.push(...createMassiveToriiGate(0, 0));

  // ========================================
  // Lantern Sea around the Torii (radius ~100, inside water zone)
  // Water zone is radius 120 - no buildings here (3x expanded)
  // ========================================
  // Main lantern sea surrounding torii - expanded
  allVoxels.push(...createLanternSea(0, 0, 100, 120)); // Sparse elegant distribution

  // ========================================
  // Inner Ring: Waterfront Buildings (radius 120-140)
  // Buildings facing the water with engawa (3x expanded)
  // ========================================
  const waterfrontPositions: Array<{ x: number; z: number; facing: 'n' | 's' | 'e' | 'w' }> = [
    // North side (facing south toward water)
    { x: -100, z: -130, facing: 's' },
    { x: -60, z: -135, facing: 's' },
    { x: -20, z: -138, facing: 's' },
    { x: 20, z: -138, facing: 's' },
    { x: 60, z: -135, facing: 's' },
    { x: 100, z: -130, facing: 's' },
    // South side (facing north toward water)
    { x: -100, z: 130, facing: 'n' },
    { x: -60, z: 135, facing: 'n' },
    { x: -20, z: 138, facing: 'n' },
    { x: 20, z: 138, facing: 'n' },
    { x: 60, z: 135, facing: 'n' },
    { x: 100, z: 130, facing: 'n' },
    // East side (facing west toward water)
    { x: 130, z: -90, facing: 'w' },
    { x: 135, z: -50, facing: 'w' },
    { x: 138, z: -10, facing: 'w' },
    { x: 138, z: 30, facing: 'w' },
    { x: 135, z: 70, facing: 'w' },
    { x: 130, z: 100, facing: 'w' },
    // West side (facing east toward water)
    { x: -130, z: -90, facing: 'e' },
    { x: -135, z: -50, facing: 'e' },
    { x: -138, z: -10, facing: 'e' },
    { x: -138, z: 30, facing: 'e' },
    { x: -135, z: 70, facing: 'e' },
    { x: -130, z: 100, facing: 'e' },
  ];

  for (const pos of waterfrontPositions) {
    allVoxels.push(...createWaterfrontBuilding(pos.x, pos.z, pos.facing));
  }

  // ========================================
  // Middle Ring: Main Town (radius 140-200)
  // Dense Japanese townscape with multiple blocks (3x expanded)
  // ========================================

  // Town Blocks (clusters of buildings)
  const townBlockPositions = [
    // Northeast quadrant
    { x: 155, z: -165, size: 3 as const },
    { x: 175, z: -145, size: 2 as const },
    { x: 160, z: -180, size: 2 as const },
    { x: 190, z: -155, size: 3 as const },
    // Northwest quadrant
    { x: -155, z: -165, size: 3 as const },
    { x: -175, z: -145, size: 2 as const },
    { x: -160, z: -180, size: 2 as const },
    { x: -190, z: -155, size: 3 as const },
    // Southeast quadrant
    { x: 155, z: 165, size: 3 as const },
    { x: 175, z: 145, size: 2 as const },
    { x: 160, z: 180, size: 2 as const },
    { x: 190, z: 155, size: 3 as const },
    // Southwest quadrant
    { x: -155, z: 165, size: 3 as const },
    { x: -175, z: 145, size: 2 as const },
    { x: -160, z: 180, size: 2 as const },
    { x: -190, z: 155, size: 3 as const },
  ];

  for (const block of townBlockPositions) {
    allVoxels.push(...createTownBlock(block.x, block.z, block.size));
  }

  // ========================================
  // Terrain Elevation: Hills and Raised Areas
  // ========================================
  const hillPositions = [
    { x: 200, z: -200, radius: 15, height: 6 },   // NE corner hill
    { x: -210, z: -195, radius: 12, height: 5 },  // NW corner hill
    { x: 195, z: 205, radius: 14, height: 7 },    // SE corner hill
    { x: -205, z: 200, radius: 13, height: 5 },   // SW corner hill
    { x: 170, z: 0, radius: 10, height: 4 },      // East hill
    { x: -175, z: 0, radius: 11, height: 4 },     // West hill
  ];

  for (const hill of hillPositions) {
    allVoxels.push(...createTerrainHill(hill.x, hill.z, hill.radius, hill.height));
  }

  // ========================================
  // Staircases connecting elevations
  // ========================================
  // Stairs to NE hill
  allVoxels.push(...createStaircase(200, -185, 0, 5, 'z', 12));
  // Stairs to SE hill
  allVoxels.push(...createStaircase(195, 190, 0, 6, 'z', 14));
  // Stairs to NW hill
  allVoxels.push(...createStaircase(-210, -180, 0, 4, 'z', 10));
  // Stairs to SW hill
  allVoxels.push(...createStaircase(-205, 185, 0, 4, 'z', 10));

  // ========================================
  // Watch Towers on hills
  // ========================================
  allVoxels.push(...createWatchTower(200, -200, 6));   // On NE hill
  allVoxels.push(...createWatchTower(-205, 200, 5));   // On SW hill

  // ========================================
  // Tea Houses (scattered throughout town)
  // ========================================
  allVoxels.push(...createTeaHouse(180, -150, 0));     // NE area
  allVoxels.push(...createTeaHouse(-185, 155, 0));     // SW area
  allVoxels.push(...createTeaHouse(150, 175, 0));      // SE area
  allVoxels.push(...createTeaHouse(-155, -180, 0));    // NW area
  // Tea house on elevated terrain
  allVoxels.push(...createTeaHouse(195, 198, 7));      // On SE hill

  // ========================================
  // Market Stalls (busy market area)
  // ========================================
  const marketPositions: Array<{ x: number; z: number; type: 'food' | 'goods' | 'lantern' }> = [
    { x: 145, z: -140, type: 'food' },
    { x: 150, z: -140, type: 'goods' },
    { x: 155, z: -140, type: 'lantern' },
    { x: -145, z: 145, type: 'food' },
    { x: -150, z: 145, type: 'goods' },
    { x: -155, z: 145, type: 'lantern' },
    { x: 140, z: 150, type: 'food' },
    { x: 145, z: 150, type: 'goods' },
    { x: -140, z: -150, type: 'lantern' },
    { x: -145, z: -150, type: 'food' },
  ];

  for (const stall of marketPositions) {
    allVoxels.push(...createMarketStall(stall.x, stall.z, 0, stall.type));
  }

  // Additional individual detailed town houses (filling gaps)
  const detailedHousePositions: Array<{ x: number; z: number; floors: number; w: number; d: number }> = [];

  // Generate many houses in middle ring (3x expanded: radius 145-195)
  for (let angle = 0; angle < Math.PI * 2; angle += Math.PI / 16) {
    for (let r = 145; r <= 195; r += 25) {
      const hx = Math.round(Math.cos(angle) * r);
      const hz = Math.round(Math.sin(angle) * r);
      // Skip if too close to town blocks
      let skip = false;
      for (const block of townBlockPositions) {
        const dist = Math.sqrt((hx - block.x) ** 2 + (hz - block.z) ** 2);
        if (dist < 20) {
          skip = true;
          break;
        }
      }
      if (!skip) {
        detailedHousePositions.push({
          x: hx,
          z: hz,
          floors: Math.floor(rand() * 3) + 1,
          w: Math.floor(rand() * 4) + 5,
          d: Math.floor(rand() * 3) + 4,
        });
      }
    }
  }

  // Add houses (limit to prevent voxel overflow)
  const maxHouses = 80;
  for (let i = 0; i < Math.min(detailedHousePositions.length, maxHouses); i++) {
    const h = detailedHousePositions[i];
    allVoxels.push(...createDetailedTownHouse(h.x, h.z, h.floors, h.w, h.d));
  }

  // Shops scattered throughout (3x expanded - radius 145+)
  const shopPositions: Array<{ x: number; z: number; type: 'food' | 'goods' | 'tea' }> = [
    // Near waterfront (just outside water zone at radius 130-150)
    { x: -75, z: -145, type: 'food' },
    { x: 45, z: -148, type: 'tea' },
    { x: 135, z: 75, type: 'goods' },
    { x: -120, z: 100, type: 'food' },
    // In town (radius 150-180)
    { x: 165, z: -155, type: 'food' },
    { x: 175, z: -135, type: 'tea' },
    { x: -158, z: -162, type: 'goods' },
    { x: -172, z: -142, type: 'food' },
    { x: 168, z: 165, type: 'tea' },
    { x: 155, z: 180, type: 'goods' },
    { x: -162, z: 162, type: 'food' },
    { x: -175, z: 178, type: 'tea' },
    // More shops (various locations)
    { x: 180, z: -60, type: 'food' },
    { x: -178, z: 45, type: 'goods' },
    { x: 172, z: 105, type: 'tea' },
    { x: -168, z: -45, type: 'food' },
  ];

  for (const shop of shopPositions) {
    allVoxels.push(...createShopBuilding(shop.x, shop.z, shop.type));
  }

  // ========================================
  // Lantern Rows (streets with lanterns - 3x expanded)
  // ========================================
  const lanternRowConfigs = [
    // Main streets radiating from waterfront to outer town (radius 125-200)
    { x: 125, z: 0, length: 80, dir: 'x' as const },
    { x: -205, z: 0, length: 80, dir: 'x' as const },
    { x: 0, z: 125, length: 80, dir: 'z' as const },
    { x: 0, z: -205, length: 80, dir: 'z' as const },
    // Cross streets in town (radius 150-190)
    { x: 140, z: -160, length: 50, dir: 'x' as const },
    { x: -190, z: -160, length: 50, dir: 'x' as const },
    { x: 140, z: 160, length: 50, dir: 'x' as const },
    { x: -190, z: 160, length: 50, dir: 'x' as const },
    { x: 160, z: -180, length: 45, dir: 'z' as const },
    { x: -160, z: -180, length: 45, dir: 'z' as const },
    { x: 160, z: 140, length: 45, dir: 'z' as const },
    { x: -160, z: 140, length: 45, dir: 'z' as const },
    // Additional dense streets
    { x: 175, z: -90, length: 35, dir: 'z' as const },
    { x: -175, z: -90, length: 35, dir: 'z' as const },
    { x: 175, z: 90, length: 35, dir: 'z' as const },
    { x: -175, z: 90, length: 35, dir: 'z' as const },
    { x: 145, z: 175, length: 40, dir: 'x' as const },
    { x: -185, z: 175, length: 40, dir: 'x' as const },
    { x: 145, z: -175, length: 40, dir: 'x' as const },
    { x: -185, z: -175, length: 40, dir: 'x' as const },
  ];

  for (const config of lanternRowConfigs) {
    allVoxels.push(...createLanternRow(config.x, config.z, config.length, config.dir));
  }

  // ========================================
  // Outer Ring: Pagodas (radius 200-250 - 3x expanded)
  // ========================================
  const pagodaPositions = [
    { x: -210, z: -210, floors: 5 },
    { x: 215, z: -205, floors: 5 },
    { x: -220, z: 200, floors: 5 },
    { x: 210, z: 210, floors: 5 },
    { x: 0, z: -230, floors: 7 },   // Large central north
    { x: 0, z: 235, floors: 7 },    // Large central south
    { x: -240, z: 0, floors: 6 },   // Large west
    { x: 245, z: 0, floors: 6 },    // Large east
    { x: -180, z: -220, floors: 4 },
    { x: 185, z: -215, floors: 4 },
    // Additional pagodas for larger town
    { x: -225, z: -100, floors: 5 },
    { x: 230, z: 95, floors: 5 },
    { x: -100, z: 225, floors: 4 },
    { x: 105, z: -228, floors: 4 },
  ];

  for (const pagoda of pagodaPositions) {
    allVoxels.push(...createDetailedPagoda(pagoda.x, pagoda.z, pagoda.floors));
  }

  // ========================================
  // Modern Buildings (Background - Outer Ring - 3x expanded to radius 250+)
  // ========================================
  const modernBuildingPositions = [
    // Far corners (radius 260-300)
    { x: 260, z: -265, w: 8, h: 45 },
    { x: 280, z: -240, w: 6, h: 38 },
    { x: 270, z: -220, w: 7, h: 42 },
    { x: -265, z: -260, w: 8, h: 48 },
    { x: -285, z: -235, w: 6, h: 35 },
    { x: -275, z: -210, w: 7, h: 40 },
    { x: 265, z: 255, w: 8, h: 44 },
    { x: 280, z: 235, w: 6, h: 36 },
    { x: 270, z: 215, w: 7, h: 41 },
    { x: -270, z: 250, w: 8, h: 46 },
    { x: -285, z: 230, w: 6, h: 34 },
    { x: -275, z: 205, w: 7, h: 39 },
    // Along outer edges
    { x: 290, z: -100, w: 7, h: 50 },
    { x: 295, z: 60, w: 6, h: 42 },
    { x: -295, z: -90, w: 7, h: 48 },
    { x: -290, z: 75, w: 6, h: 44 },
    // Additional modern buildings for scale
    { x: 250, z: -150, w: 8, h: 55 },
    { x: -255, z: 145, w: 8, h: 52 },
    { x: 150, z: 260, w: 7, h: 46 },
    { x: -145, z: -265, w: 7, h: 48 },
  ];

  for (const bld of modernBuildingPositions) {
    allVoxels.push(...createModernBuilding(bld.x, bld.z, bld.w, bld.h));
  }

  // ========================================
  // Sakura Trees (Throughout the Town - 3x expanded, radius 125+)
  // ========================================
  const sakuraPositions: Array<[number, number]> = [];

  // Generate sakura positions throughout the map (radius 130-250)
  for (let i = 0; i < 100; i++) {
    const angle = rand() * Math.PI * 2;
    const r = 130 + rand() * 120; // radius 130-250
    const sx = Math.round(Math.cos(angle) * r);
    const sz = Math.round(Math.sin(angle) * r);
    sakuraPositions.push([sx, sz]);
  }

  // Additional specific positions (outside water zone radius 120)
  const additionalSakura: Array<[number, number]> = [
    // Near waterfront (just outside water zone)
    [-125, 60], [125, 60], [-125, -60], [125, -60],
    [60, 125], [-60, 125], [60, -125], [-60, -125],
    // Near pagodas
    [-205, -200], [210, -195], [-215, 195], [205, 205],
    // Along streets
    [150, 30], [-150, 30], [150, -30], [-150, -30],
    [30, 150], [-30, 150], [30, -150], [-30, -150],
    // Additional throughout town
    [170, 100], [-170, 100], [170, -100], [-170, -100],
    [100, 170], [-100, 170], [100, -170], [-100, -170],
  ];

  sakuraPositions.push(...additionalSakura);

  for (const [sx, sz] of sakuraPositions) {
    // Skip if inside water zone (radius 120)
    const dist = Math.sqrt(sx * sx + sz * sz);
    if (dist > 125) {
      allVoxels.push(...createSakuraTree(sx, sz));
    }
  }

  // ========================================
  // Shrine and Approach Path (3x expanded - radius 200+)
  // ========================================
  // Northeast shrine
  allVoxels.push(...createShrinePath(150, -210, 40, 'z'));
  allVoxels.push(...createShrine(150, -250));

  // Southwest shrine
  allVoxels.push(...createShrinePath(-150, 190, 35, 'z'));
  allVoxels.push(...createShrine(-150, 230));

  // Additional shrines for larger town
  allVoxels.push(...createShrinePath(-220, -150, 30, 'x'));
  allVoxels.push(...createShrine(-250, -150));
  allVoxels.push(...createShrinePath(200, 160, 30, 'x'));
  allVoxels.push(...createShrine(240, 160));

  // ========================================
  // Stone Lanterns along paths (3x expanded - radius 130+)
  // ========================================
  const stoneLanternPositions: Array<[number, number]> = [
    // Near waterfront (just outside water zone)
    [-130, 30], [-130, -30], [130, 30], [130, -30],
    [30, 130], [-30, 130], [30, -130], [-30, -130],
    // Along main streets
    [140, 15], [160, 15], [180, 15], [200, 15],
    [-140, -15], [-160, -15], [-180, -15], [-200, -15],
    [15, 140], [15, 160], [15, 180], [15, 200],
    [-15, -140], [-15, -160], [-15, -180], [-15, -200],
    // Near shrines
    [145, -245], [155, -245],
    [-145, 225], [-155, 225],
    // In town plazas
    [165, -165], [-165, -165], [165, 165], [-165, 165],
    [185, -185], [-185, -185], [185, 185], [-185, 185],
  ];

  for (const [lx, lz] of stoneLanternPositions) {
    allVoxels.push(...createStoneLantern(lx, lz));
  }

  // ========================================
  // Bridges Connecting Areas (3x expanded - crossing water zone radius 0-120)
  // ========================================
  // Bridges across the water zone (from center to waterfront at radius 125)
  // North bridges
  allVoxels.push(...createBridge(-50, -90, -50, -130));
  allVoxels.push(...createBridge(50, -90, 50, -130));
  // South bridges
  allVoxels.push(...createBridge(-50, 90, -50, 130));
  allVoxels.push(...createBridge(50, 90, 50, 130));
  // East bridges
  allVoxels.push(...createBridge(90, -50, 130, -50));
  allVoxels.push(...createBridge(90, 50, 130, 50));
  // West bridges
  allVoxels.push(...createBridge(-90, -50, -130, -50));
  allVoxels.push(...createBridge(-90, 50, -130, 50));
  // Diagonal bridges
  allVoxels.push(...createBridge(-70, -70, -100, -100));
  allVoxels.push(...createBridge(70, -70, 100, -100));
  allVoxels.push(...createBridge(-70, 70, -100, 100));
  allVoxels.push(...createBridge(70, 70, 100, 100));

  // ========================================
  // Additional Ponds in Town (3x expanded - radius 150+)
  // ========================================
  allVoxels.push(...createPond(-175, 150, 8));
  allVoxels.push(...createPond(180, -160, 7));
  allVoxels.push(...createPond(-185, -175, 7));
  allVoxels.push(...createPond(190, 170, 8));
  // Additional ponds for larger town
  allVoxels.push(...createPond(-150, -200, 6));
  allVoxels.push(...createPond(155, 195, 6));
  allVoxels.push(...createPond(200, -140, 5));
  allVoxels.push(...createPond(-195, 145, 5));

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

  // New detailed functions
  createDetailedTownHouse,
  createTownBlock,
  createWaterfrontBuilding,
  createLanternRow,
  createDetailedPagoda,
  createShopBuilding,

  // Main generator
  generateInitialWorld,
};
