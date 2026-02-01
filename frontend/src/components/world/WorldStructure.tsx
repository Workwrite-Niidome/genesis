import { useMemo } from 'react';
import { Html } from '@react-three/drei';
import * as THREE from 'three';
import { generateFallbackVoxels } from '../../lib/seedRandom';

interface StructureProps {
  artifact: {
    id: string;
    name: string;
    content?: any;
    creator_name?: string;
  };
  position: [number, number, number];
}

export default function WorldStructure({ artifact, position }: StructureProps) {
  const { voxels, palette } = useMemo(() => {
    const content = artifact.content || {};
    let voxels: number[][] = content.voxels;
    let palette: string[] = content.palette;

    if (!voxels || !Array.isArray(voxels) || voxels.length === 0) {
      const fallback = generateFallbackVoxels(artifact.id);
      voxels = fallback.voxels;
      palette = fallback.palette;
    }

    if (!palette || !Array.isArray(palette) || palette.length === 0) {
      palette = ['#7c5bf5', '#58d5f0', '#34d399'];
    }

    // Limit voxels and validate
    return {
      voxels: voxels.slice(0, 256).filter(
        (v) => Array.isArray(v) && v.length >= 4
      ),
      palette,
    };
  }, [artifact.id, artifact.content]);

  const colors = useMemo(
    () => palette.map((hex) => new THREE.Color(hex)),
    [palette]
  );

  if (voxels.length === 0) return null;

  // Calculate center offset to position the structure at its center
  const center = useMemo(() => {
    let cx = 0, cy = 0, cz = 0;
    for (const [x, y, z] of voxels) {
      cx += x; cy += y; cz += z;
    }
    const n = voxels.length;
    return [cx / n, cy / n, cz / n] as [number, number, number];
  }, [voxels]);

  // Find the max height for label placement
  const maxY = useMemo(
    () => Math.max(...voxels.map((v) => v[1])) + 1,
    [voxels]
  );

  return (
    <group position={position}>
      {/* Voxels */}
      {voxels.map((v, i) => {
        const [x, y, z, colorIdx] = v;
        const color = colors[colorIdx % colors.length] || colors[0];
        return (
          <mesh
            key={i}
            position={[
              x - center[0],
              y - center[1] + 0.5,
              z - center[2],
            ]}
          >
            <boxGeometry args={[0.9, 0.9, 0.9]} />
            <meshStandardMaterial
              color={color}
              emissive={color}
              emissiveIntensity={0.3}
              roughness={0.4}
              metalness={0.3}
            />
          </mesh>
        );
      })}

      {/* Name label */}
      <Html
        position={[0, maxY - center[1] + 2, 0]}
        center
        distanceFactor={150}
        zIndexRange={[0, 0]}
        style={{ pointerEvents: 'none' }}
      >
        <div
          style={{
            color: palette[0] || '#7c5bf5',
            fontSize: '9px',
            fontWeight: 600,
            fontFamily: 'monospace',
            textShadow: `0 0 6px ${palette[0] || '#7c5bf5'}60, 0 0 16px rgba(0,0,0,0.8)`,
            whiteSpace: 'nowrap',
            userSelect: 'none',
            opacity: 0.8,
            background: 'rgba(6, 6, 12, 0.6)',
            padding: '1px 4px',
            borderRadius: '2px',
          }}
        >
          {artifact.name}
        </div>
      </Html>
    </group>
  );
}
