/**
 * MiniMap — Canvas-based 2D top-down minimap for GENESIS v3 observer view.
 *
 * Renders entity positions as colored dots on a small overlay in the
 * bottom-right corner.  Supports click-to-pan: clicking a position on the
 * minimap moves the 3D observer camera to that world coordinate.
 */
import { useRef, useEffect, useCallback } from 'react';
import { useWorldStoreV3 } from '../../stores/worldStoreV3';
import type { EntityV3 } from '../../types/v3';

// ── Constants ────────────────────────────────────────────────
const MAP_SIZE = 200;          // px (both width and height)
const PADDING = 16;            // world-space padding around entity spread
const DOT_RADIUS = 4;
const GRID_LINES = 6;
const PULSE_SPEED = 4;         // rad/s for rampage pulse

interface MiniMapProps {
  /** Called when the user clicks a world-space position on the map. */
  onPanTo?: (worldX: number, worldZ: number) => void;
}

export function MiniMap({ onPanTo }: MiniMapProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animRef = useRef<number>(0);

  // ── Compute the world bounding box from entity positions ────
  const boundsRef = useRef({ minX: -50, maxX: 50, minZ: -50, maxZ: 50 });

  const computeBounds = useCallback((ents: Map<string, EntityV3>) => {
    if (ents.size === 0) {
      boundsRef.current = { minX: -50, maxX: 50, minZ: -50, maxZ: 50 };
      return;
    }
    let minX = Infinity, maxX = -Infinity, minZ = Infinity, maxZ = -Infinity;
    for (const e of ents.values()) {
      if (!e.isAlive) continue;
      const { x, z } = e.position;
      if (x < minX) minX = x;
      if (x > maxX) maxX = x;
      if (z < minZ) minZ = z;
      if (z > maxZ) maxZ = z;
    }
    // Guard against single-point or all-dead
    if (!isFinite(minX)) {
      boundsRef.current = { minX: -50, maxX: 50, minZ: -50, maxZ: 50 };
      return;
    }
    const spanX = maxX - minX;
    const spanZ = maxZ - minZ;
    const span = Math.max(spanX, spanZ, 20); // minimum 20-unit span
    const cx = (minX + maxX) / 2;
    const cz = (minZ + maxZ) / 2;
    boundsRef.current = {
      minX: cx - span / 2 - PADDING,
      maxX: cx + span / 2 + PADDING,
      minZ: cz - span / 2 - PADDING,
      maxZ: cz + span / 2 + PADDING,
    };
  }, []);

  // ── World <-> canvas coordinate transforms ─────────────────
  const worldToCanvas = useCallback((wx: number, wz: number): [number, number] => {
    const { minX, maxX, minZ, maxZ } = boundsRef.current;
    const cx = ((wx - minX) / (maxX - minX)) * MAP_SIZE;
    const cy = ((wz - minZ) / (maxZ - minZ)) * MAP_SIZE;
    return [cx, cy];
  }, []);

  const canvasToWorld = useCallback((cx: number, cy: number): [number, number] => {
    const { minX, maxX, minZ, maxZ } = boundsRef.current;
    const wx = (cx / MAP_SIZE) * (maxX - minX) + minX;
    const wz = (cy / MAP_SIZE) * (maxZ - minZ) + minZ;
    return [wx, wz];
  }, []);

  // ── Draw loop ──────────────────────────────────────────────
  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const now = performance.now() / 1000;
    const ents = useWorldStoreV3.getState().entities;
    const selId = useWorldStoreV3.getState().selectedEntityId;

    computeBounds(ents);

    // Clear
    ctx.clearRect(0, 0, MAP_SIZE, MAP_SIZE);

    // Background
    ctx.fillStyle = 'rgba(0, 0, 0, 0.6)';
    ctx.fillRect(0, 0, MAP_SIZE, MAP_SIZE);

    // Grid lines
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.06)';
    ctx.lineWidth = 0.5;
    for (let i = 1; i < GRID_LINES; i++) {
      const pos = (i / GRID_LINES) * MAP_SIZE;
      ctx.beginPath();
      ctx.moveTo(pos, 0);
      ctx.lineTo(pos, MAP_SIZE);
      ctx.stroke();
      ctx.beginPath();
      ctx.moveTo(0, pos);
      ctx.lineTo(MAP_SIZE, pos);
      ctx.stroke();
    }

    // Draw entities
    for (const entity of ents.values()) {
      if (!entity.isAlive) continue;

      const [cx, cy] = worldToCanvas(entity.position.x, entity.position.z);

      // Determine color based on behavior mode
      let dotColor: string;
      const mode = entity.state.behaviorMode;
      if (mode === 'rampage') {
        // Pulse alpha for rampage
        const alpha = 0.6 + 0.4 * Math.sin(now * PULSE_SPEED);
        dotColor = `rgba(239, 68, 68, ${alpha})`; // red
      } else if (mode === 'desperate') {
        dotColor = '#f59e0b'; // amber
      } else {
        dotColor = '#22d3ee'; // cyan
      }

      const isHumanoid = entity.appearance.shape === 'humanoid';
      const isSelected = entity.id === selId;

      // Selected ring
      if (isSelected) {
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.9)';
        ctx.lineWidth = 1.5;
        ctx.beginPath();
        ctx.arc(cx, cy, DOT_RADIUS + 3, 0, Math.PI * 2);
        ctx.stroke();
      }

      ctx.fillStyle = dotColor;

      if (isHumanoid) {
        // Diamond shape for humanoid avatars
        ctx.beginPath();
        ctx.moveTo(cx, cy - DOT_RADIUS - 1);
        ctx.lineTo(cx + DOT_RADIUS + 1, cy);
        ctx.lineTo(cx, cy + DOT_RADIUS + 1);
        ctx.lineTo(cx - DOT_RADIUS - 1, cy);
        ctx.closePath();
        ctx.fill();
      } else {
        // Circle for other shapes
        ctx.beginPath();
        ctx.arc(cx, cy, DOT_RADIUS, 0, Math.PI * 2);
        ctx.fill();
      }
    }

    // Cardinal direction labels
    ctx.fillStyle = 'rgba(255, 255, 255, 0.35)';
    ctx.font = '9px monospace';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'top';
    ctx.fillText('N', MAP_SIZE / 2, 3);
    ctx.textBaseline = 'bottom';
    ctx.fillText('S', MAP_SIZE / 2, MAP_SIZE - 3);
    ctx.textBaseline = 'middle';
    ctx.textAlign = 'left';
    ctx.fillText('W', 4, MAP_SIZE / 2);
    ctx.textAlign = 'right';
    ctx.fillText('E', MAP_SIZE - 4, MAP_SIZE / 2);

    animRef.current = requestAnimationFrame(draw);
  }, [computeBounds, worldToCanvas]);

  // Start / stop animation loop
  useEffect(() => {
    animRef.current = requestAnimationFrame(draw);
    return () => {
      cancelAnimationFrame(animRef.current);
    };
  }, [draw]);

  // ── Click handler: pan 3D camera ──────────────────────────
  const handleClick = useCallback(
    (e: React.MouseEvent<HTMLCanvasElement>) => {
      if (!onPanTo) return;
      const rect = (e.target as HTMLCanvasElement).getBoundingClientRect();
      const cx = e.clientX - rect.left;
      const cy = e.clientY - rect.top;
      const [wx, wz] = canvasToWorld(cx, cy);
      onPanTo(wx, wz);
    },
    [canvasToWorld, onPanTo],
  );

  return (
    <div className="absolute bottom-20 right-4 z-10 select-none">
      <canvas
        ref={canvasRef}
        width={MAP_SIZE}
        height={MAP_SIZE}
        onClick={handleClick}
        className="rounded-lg border border-white/10 cursor-crosshair"
        style={{ width: MAP_SIZE, height: MAP_SIZE }}
      />
      {/* Label */}
      <div className="absolute top-1.5 left-2 text-[9px] font-mono text-white/40 tracking-wider uppercase pointer-events-none">
        Minimap
      </div>
    </div>
  );
}
