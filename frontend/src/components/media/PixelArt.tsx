import { useRef, useEffect } from 'react';
import { generateFallbackPixels } from '../../lib/seedRandom';

interface PixelArtProps {
  artifact: { id: string; content?: any };
  size?: number;
  className?: string;
}

export default function PixelArt({ artifact, size = 200, className }: PixelArtProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const content = artifact.content || {};
    let pixels: number[][] = content.pixels;
    let palette: string[] = content.palette;
    const gridSize: number = content.size || 8;

    // Fallback: generate from artifact ID if no pixel data
    if (!pixels || !Array.isArray(pixels) || pixels.length === 0) {
      const fallback = generateFallbackPixels(artifact.id, gridSize);
      pixels = fallback.pixels;
      palette = fallback.palette;
    }

    if (!palette || !Array.isArray(palette) || palette.length === 0) {
      palette = ['#06060c', '#7c5bf5', '#58d5f0', '#34d399'];
    }

    const rows = pixels.length;
    const cols = rows > 0 ? (pixels[0]?.length || 0) : 0;
    if (rows === 0 || cols === 0) return;

    const cellSize = Math.floor(size / Math.max(rows, cols));
    const canvasSize = cellSize * Math.max(rows, cols);

    canvas.width = canvasSize;
    canvas.height = canvasSize;

    // Clear
    ctx.fillStyle = palette[0] || '#06060c';
    ctx.fillRect(0, 0, canvasSize, canvasSize);

    // Draw pixels
    for (let y = 0; y < rows; y++) {
      const row = pixels[y];
      if (!Array.isArray(row)) continue;
      for (let x = 0; x < cols; x++) {
        const colorIndex = row[x];
        if (typeof colorIndex !== 'number') continue;
        const color = palette[colorIndex % palette.length];
        if (!color) continue;
        ctx.fillStyle = color;
        ctx.fillRect(x * cellSize, y * cellSize, cellSize, cellSize);
      }
    }
  }, [artifact.id, artifact.content, size]);

  return (
    <canvas
      ref={canvasRef}
      className={className}
      style={{
        width: size,
        height: size,
        imageRendering: 'pixelated',
      }}
    />
  );
}

/** Small thumbnail version for list items */
export function PixelArtThumb({ artifact }: { artifact: { id: string; content?: any } }) {
  return (
    <PixelArt
      artifact={artifact}
      size={40}
      className="rounded"
    />
  );
}
