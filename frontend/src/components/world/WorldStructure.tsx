import { useMemo, useRef, useState } from 'react';
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
  const [hovered, setHovered] = useState(false);

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

    return {
      voxels: voxels.slice(0, 256).filter(
        (v) => Array.isArray(v) && v.length >= 4
      ),
      palette,
    };
  }, [artifact.id, artifact.content]);

  // Keep original AI colors for hologram
  const colors = useMemo(
    () => palette.map((hex) => new THREE.Color(hex)),
    [palette]
  );

  // Primary color for glow effects
  const primaryColor = palette[0] || '#7c5bf5';

  if (voxels.length === 0) return null;

  // Calculate center offset
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

  // Bounding box for hover detection
  const bounds = useMemo(() => {
    let minX = Infinity, maxX = -Infinity;
    let minY = Infinity, maxYVal = -Infinity;
    let minZ = Infinity, maxZ = -Infinity;
    for (const [x, y, z] of voxels) {
      minX = Math.min(minX, x); maxX = Math.max(maxX, x);
      minY = Math.min(minY, y); maxYVal = Math.max(maxYVal, y);
      minZ = Math.min(minZ, z); maxZ = Math.max(maxZ, z);
    }
    return {
      width: maxX - minX + 2,
      height: maxYVal - minY + 2,
      depth: maxZ - minZ + 2,
    };
  }, [voxels]);

  return (
    <group position={position}>
      {/* Invisible bounding box for hover detection */}
      <mesh
        position={[0, (bounds.height / 2) - center[1], 0]}
        onPointerEnter={() => setHovered(true)}
        onPointerLeave={() => setHovered(false)}
      >
        <boxGeometry args={[bounds.width, bounds.height, bounds.depth]} />
        <meshBasicMaterial visible={false} />
      </mesh>

      {/* Holographic voxels */}
      {voxels.map((v, i) => {
        const [x, y, z, colorIdx] = v;
        const color = colors[colorIdx % colors.length] || colors[0];
        return (
          <group
            key={i}
            position={[
              x - center[0],
              y - center[1] + 0.5,
              z - center[2],
            ]}
          >
            {/* Inner glowing cube */}
            <mesh>
              <boxGeometry args={[0.75, 0.75, 0.75]} />
              <meshStandardMaterial
                color={color}
                emissive={color}
                emissiveIntensity={hovered ? 0.8 : 0.5}
                transparent
                opacity={hovered ? 0.6 : 0.4}
                roughness={0.2}
                metalness={0.8}
              />
            </mesh>
            {/* Wireframe edge for hologram effect */}
            <mesh>
              <boxGeometry args={[0.8, 0.8, 0.8]} />
              <meshBasicMaterial
                color={color}
                wireframe
                transparent
                opacity={hovered ? 0.7 : 0.35}
              />
            </mesh>
          </group>
        );
      })}

      {/* Base glow ring */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -center[1] - 0.5, 0]}>
        <ringGeometry args={[bounds.width * 0.3, bounds.width * 0.5, 32]} />
        <meshBasicMaterial
          color={primaryColor}
          transparent
          opacity={hovered ? 0.3 : 0.1}
          side={THREE.DoubleSide}
        />
      </mesh>

      {/* Name label - only on hover */}
      {hovered && (
        <Html
          position={[0, maxY - center[1] + 2, 0]}
          center
          distanceFactor={150}
          zIndexRange={[100, 100]}
          style={{ pointerEvents: 'none' }}
        >
          <div
            style={{
              color: primaryColor,
              fontSize: '10px',
              fontWeight: 600,
              fontFamily: 'monospace',
              textShadow: `0 0 10px ${primaryColor}, 0 0 20px ${primaryColor}`,
              whiteSpace: 'nowrap',
              userSelect: 'none',
              background: 'rgba(6, 6, 12, 0.7)',
              padding: '3px 8px',
              borderRadius: '3px',
              border: `1px solid ${primaryColor}`,
              boxShadow: `0 0 15px ${primaryColor}40, inset 0 0 10px ${primaryColor}20`,
              animation: 'hologramFlicker 2s infinite',
            }}
          >
            {artifact.name}
          </div>
        </Html>
      )}
    </group>
  );
}
