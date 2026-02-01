/**
 * Deterministic pseudo-random number generator seeded from a string (e.g. artifact ID).
 * Uses a simple xorshift32 algorithm with FNV-1a hash for seeding.
 */

function fnv1aHash(str: string): number {
  let hash = 0x811c9dc5;
  for (let i = 0; i < str.length; i++) {
    hash ^= str.charCodeAt(i);
    hash = (hash * 0x01000193) >>> 0;
  }
  return hash;
}

export function createSeededRandom(seed: string) {
  let state = fnv1aHash(seed);

  /** Returns a float in [0, 1) */
  function next(): number {
    state ^= state << 13;
    state ^= state >> 17;
    state ^= state << 5;
    state = state >>> 0;
    return state / 0x100000000;
  }

  /** Returns an integer in [min, max) */
  function nextInt(min: number, max: number): number {
    return Math.floor(next() * (max - min)) + min;
  }

  /** Pick a random element from an array */
  function pick<T>(arr: T[]): T {
    return arr[nextInt(0, arr.length)];
  }

  return { next, nextInt, pick };
}

/** Default palette for fallback generation */
const FALLBACK_PALETTE = [
  '#06060c', '#7c5bf5', '#58d5f0', '#34d399',
  '#f472b6', '#fbbf24', '#818cf8', '#f87171',
];

/** Generate fallback pixel art from an artifact ID */
export function generateFallbackPixels(id: string, size = 8): { pixels: number[][]; palette: string[] } {
  const rng = createSeededRandom(id);
  const palette = FALLBACK_PALETTE.slice(0, 4 + rng.nextInt(0, 4));
  const half = Math.ceil(size / 2);
  const pixels: number[][] = [];

  for (let y = 0; y < size; y++) {
    const row: number[] = [];
    for (let x = 0; x < half; x++) {
      row.push(rng.next() < 0.4 ? 0 : rng.nextInt(1, palette.length));
    }
    // Mirror for symmetry
    const mirrored = [...row];
    for (let x = half - 1 - (size % 2 === 0 ? 0 : 1); x >= 0; x--) {
      mirrored.push(row[x]);
    }
    pixels.push(mirrored.slice(0, size));
  }

  return { pixels, palette };
}

/** Generate fallback notes from an artifact ID */
export function generateFallbackNotes(id: string): { note: string; dur: number }[] {
  const rng = createSeededRandom(id);
  const scale = ['C4', 'D4', 'E4', 'F4', 'G4', 'A4', 'B4', 'C5'];
  const durations = [0.25, 0.25, 0.5, 0.5, 1.0];
  const count = 8 + rng.nextInt(0, 8);
  const notes: { note: string; dur: number }[] = [];

  for (let i = 0; i < count; i++) {
    if (rng.next() < 0.15) {
      notes.push({ note: 'rest', dur: rng.pick(durations) });
    } else {
      notes.push({ note: rng.pick(scale), dur: rng.pick(durations) });
    }
  }

  return notes;
}

/** Generate fallback voxel structure from an artifact ID */
export function generateFallbackVoxels(id: string): { voxels: number[][]; palette: string[] } {
  const rng = createSeededRandom(id);
  const palette = FALLBACK_PALETTE.slice(1, 3 + rng.nextInt(0, 3));
  const voxels: number[][] = [];
  const height = 3 + rng.nextInt(0, 3);

  // Simple tower / structure
  for (let y = 0; y < height; y++) {
    const radius = Math.max(1, Math.floor((height - y) * 1.2));
    for (let x = -radius; x <= radius; x++) {
      for (let z = -radius; z <= radius; z++) {
        if (rng.next() < 0.5) {
          voxels.push([x + 4, y, z + 4, rng.nextInt(0, palette.length)]);
        }
      }
    }
  }

  return { voxels, palette };
}
