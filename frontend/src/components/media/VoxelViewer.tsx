import { useRef, useEffect } from 'react';
import { generateFallbackVoxels } from '../../lib/seedRandom';

interface VoxelViewerProps {
  artifact: { id: string; content?: any };
  size?: number;
  className?: string;
}

/**
 * Renders voxel architecture artifacts as an isometric 2D projection on a canvas.
 * Voxel format: [[x, y, z, colorIdx], ...] with palette: ["#hex", ...]
 */
export default function VoxelViewer({ artifact, size = 256, className }: VoxelViewerProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const content = artifact.content || {};
    let voxels: number[][] = content.voxels;
    let palette: string[] = content.palette;

    // Fallback if no voxel data
    if (!voxels || !Array.isArray(voxels) || voxels.length === 0) {
      const fallback = generateFallbackVoxels(artifact.id);
      voxels = fallback.voxels;
      palette = fallback.palette;
    }

    if (!palette || !Array.isArray(palette) || palette.length === 0) {
      palette = ['#7c5bf5', '#58d5f0', '#34d399'];
    }

    // Filter valid voxels [x, y, z, colorIdx]
    const valid = voxels
      .filter((v) => Array.isArray(v) && v.length >= 4)
      .slice(0, 512);

    if (valid.length === 0) return;

    // Find bounds
    let minX = Infinity, maxX = -Infinity;
    let minY = Infinity, maxY = -Infinity;
    let minZ = Infinity, maxZ = -Infinity;
    for (const [x, y, z] of valid) {
      minX = Math.min(minX, x); maxX = Math.max(maxX, x);
      minY = Math.min(minY, y); maxY = Math.max(maxY, y);
      minZ = Math.min(minZ, z); maxZ = Math.max(maxZ, z);
    }

    // Isometric projection parameters
    const cos30 = Math.cos(Math.PI / 6);
    const sin30 = Math.sin(Math.PI / 6);

    // Project a voxel to 2D screen coords
    function project(vx: number, vy: number, vz: number): [number, number] {
      const sx = (vx - vz) * cos30;
      const sy = (vx + vz) * sin30 - vy;
      return [sx, sy];
    }

    // Calculate projected bounds to determine scale
    const corners = [
      [minX, minY, minZ], [maxX, minY, minZ],
      [minX, maxY, minZ], [maxX, maxY, minZ],
      [minX, minY, maxZ], [maxX, minY, maxZ],
      [minX, maxY, maxZ], [maxX, maxY, maxZ],
    ];
    let pMinX = Infinity, pMaxX = -Infinity;
    let pMinY = Infinity, pMaxY = -Infinity;
    for (const [cx, cy, cz] of corners) {
      const [px, py] = project(cx, cy, cz);
      pMinX = Math.min(pMinX, px); pMaxX = Math.max(pMaxX, px);
      pMinY = Math.min(pMinY, py); pMaxY = Math.max(pMaxY, py);
    }

    const projWidth = pMaxX - pMinX + 2;
    const projHeight = pMaxY - pMinY + 2;
    const scale = Math.min((size - 24) / projWidth, (size - 24) / projHeight);
    const offsetX = size / 2 - ((pMinX + pMaxX) / 2) * scale;
    const offsetY = size / 2 - ((pMinY + pMaxY) / 2) * scale;

    // Set canvas size (use 2x for crisp rendering)
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = size * dpr;
    canvas.height = size * dpr;
    ctx.scale(dpr, dpr);

    // Background
    ctx.fillStyle = '#06060c';
    ctx.fillRect(0, 0, size, size);

    // Sort voxels by depth (painter's algorithm): draw back voxels first
    const sorted = [...valid].sort((a, b) => {
      // Sort by y ascending (lower first), then by x+z descending (farther first)
      const depthA = a[0] + a[2] - a[1] * 2;
      const depthB = b[0] + b[2] - b[1] * 2;
      return depthA - depthB;
    });

    const cellW = cos30 * scale;
    const cellH = sin30 * scale;

    // Draw each voxel as an isometric cube
    for (const [vx, vy, vz, colorIdx] of sorted) {
      const baseColor = palette[colorIdx % palette.length] || palette[0];
      const [sx, sy] = project(vx, vy, vz);
      const cx = sx * scale + offsetX;
      const cy = sy * scale + offsetY;

      // Parse base color to derive shading
      const rgb = hexToRgb(baseColor);
      const topColor = baseColor;
      const leftColor = rgbToHex(
        Math.round(rgb.r * 0.65),
        Math.round(rgb.g * 0.65),
        Math.round(rgb.b * 0.65),
      );
      const rightColor = rgbToHex(
        Math.round(rgb.r * 0.45),
        Math.round(rgb.g * 0.45),
        Math.round(rgb.b * 0.45),
      );

      // Top face
      ctx.beginPath();
      ctx.moveTo(cx, cy - cellH);
      ctx.lineTo(cx + cellW, cy);
      ctx.lineTo(cx, cy + cellH);
      ctx.lineTo(cx - cellW, cy);
      ctx.closePath();
      ctx.fillStyle = topColor;
      ctx.fill();

      // Left face
      ctx.beginPath();
      ctx.moveTo(cx - cellW, cy);
      ctx.lineTo(cx, cy + cellH);
      ctx.lineTo(cx, cy + cellH + scale);
      ctx.lineTo(cx - cellW, cy + scale);
      ctx.closePath();
      ctx.fillStyle = leftColor;
      ctx.fill();

      // Right face
      ctx.beginPath();
      ctx.moveTo(cx + cellW, cy);
      ctx.lineTo(cx, cy + cellH);
      ctx.lineTo(cx, cy + cellH + scale);
      ctx.lineTo(cx + cellW, cy + scale);
      ctx.closePath();
      ctx.fillStyle = rightColor;
      ctx.fill();

      // Edge lines for definition
      ctx.strokeStyle = 'rgba(255,255,255,0.06)';
      ctx.lineWidth = 0.5;

      // Top face outline
      ctx.beginPath();
      ctx.moveTo(cx, cy - cellH);
      ctx.lineTo(cx + cellW, cy);
      ctx.lineTo(cx, cy + cellH);
      ctx.lineTo(cx - cellW, cy);
      ctx.closePath();
      ctx.stroke();
    }
  }, [artifact.id, artifact.content, size]);

  return (
    <canvas
      ref={canvasRef}
      className={className}
      style={{
        width: size,
        height: size,
      }}
    />
  );
}

function hexToRgb(hex: string): { r: number; g: number; b: number } {
  const h = hex.replace('#', '');
  const bigint = parseInt(h.length === 3
    ? h[0] + h[0] + h[1] + h[1] + h[2] + h[2]
    : h, 16);
  return {
    r: (bigint >> 16) & 255,
    g: (bigint >> 8) & 255,
    b: bigint & 255,
  };
}

function rgbToHex(r: number, g: number, b: number): string {
  return '#' + [r, g, b].map((c) => Math.max(0, Math.min(255, c)).toString(16).padStart(2, '0')).join('');
}
