import { useRef, useMemo, useState } from 'react';
import { useFrame } from '@react-three/fiber';
import { Html } from '@react-three/drei';
import * as THREE from 'three';
import { useAIStore } from '../../stores/aiStore';
import type { AIEntity as AIEntityType } from '../../types/world';

// LOD distance thresholds
const LOD_NEAR = 120;   // Full detail
const LOD_MID = 300;    // Reduced detail (no rings, simpler halo)
const LOD_FAR = 600;    // Minimal (no halo, no label, no point light)

interface Props {
  ai: AIEntityType;
}

export default function AIEntity({ ai }: Props) {
  const meshRef = useRef<THREE.Mesh>(null);
  const wireRef = useRef<THREE.Mesh>(null);
  const ringRef = useRef<THREE.Group>(null);
  const haloRef = useRef<THREE.Mesh>(null);
  const selectAI = useAIStore((s) => s.selectAI);
  const [lod, setLod] = useState<'near' | 'mid' | 'far'>('near');
  const [hovered, setHovered] = useState(false);

  const color = useMemo(
    () => new THREE.Color(ai.appearance?.primaryColor || '#7c5bf5'),
    [ai.appearance?.primaryColor]
  );

  const colorHex = ai.appearance?.primaryColor || '#7c5bf5';
  const size = (ai.appearance?.size || 10) * 0.25;
  const hash = ai.id.charCodeAt(0) + ai.id.charCodeAt(1);
  const speed = 0.5 + (hash % 10) * 0.05;
  // Calculate Z position from AI id hash for 3D depth distribution
  const zHash = ai.id.charCodeAt(2) + ai.id.charCodeAt(4);
  const positionZ = ((zHash % 7) - 3) * 25; // Range: -75 to +75

  useFrame(({ clock, camera }) => {
    if (!meshRef.current) return;
    const t = clock.getElapsedTime();

    // Compute distance to camera for LOD
    const dx = camera.position.x - ai.position_x;
    const dy = camera.position.y - ai.position_y;
    const dz = camera.position.z;
    const dist = Math.sqrt(dx * dx + dy * dy + dz * dz);
    const newLod = dist < LOD_NEAR ? 'near' : dist < LOD_MID ? 'mid' : 'far';
    if (newLod !== lod) setLod(newLod);

    // Smooth floating motion
    meshRef.current.position.y = ai.position_y + Math.sin(t * speed + hash) * 1.5;
    meshRef.current.rotation.y = t * 0.15 + hash;
    meshRef.current.rotation.x = Math.sin(t * 0.1 + hash) * 0.2;

    // Sync wireframe with core
    if (wireRef.current) {
      wireRef.current.position.y = meshRef.current.position.y;
      wireRef.current.rotation.y = meshRef.current.rotation.y;
      wireRef.current.rotation.x = meshRef.current.rotation.x;
    }

    // Orbit ring
    if (ringRef.current) {
      ringRef.current.rotation.z = t * 0.25 + hash;
      ringRef.current.rotation.x = Math.sin(t * 0.15) * 0.4;
    }

    // Halo breathe effect
    if (haloRef.current) {
      const breathe = 0.8 + Math.sin(t * 0.6 + hash) * 0.2;
      haloRef.current.scale.setScalar(breathe);
      (haloRef.current.material as THREE.MeshBasicMaterial).opacity =
        (hovered ? 0.08 : 0.04) + Math.sin(t * 0.4 + hash) * 0.02;
    }
  });

  const geometryArgs = useMemo(() => {
    switch (ai.appearance?.shape) {
      case 'square':
        return { type: 'octahedron', args: [size * 0.55, 0] as [number, number] };
      case 'triangle':
        return { type: 'tetrahedron', args: [size * 0.6, 0] as [number, number] };
      default:
        return { type: 'icosahedron', args: [size * 0.45, 1] as [number, number] };
    }
  }, [ai.appearance?.shape, size]);

  const GeometryComponent = useMemo(() => {
    switch (geometryArgs.type) {
      case 'octahedron':
        return <octahedronGeometry args={geometryArgs.args} />;
      case 'tetrahedron':
        return <tetrahedronGeometry args={geometryArgs.args} />;
      default:
        return <icosahedronGeometry args={geometryArgs.args} />;
    }
  }, [geometryArgs]);

  // Slightly larger wireframe geometry
  const WireframeGeometry = useMemo(() => {
    const scale = 1.08;
    switch (geometryArgs.type) {
      case 'octahedron':
        return <octahedronGeometry args={[geometryArgs.args[0] * scale, geometryArgs.args[1]]} />;
      case 'tetrahedron':
        return <tetrahedronGeometry args={[geometryArgs.args[0] * scale, geometryArgs.args[1]]} />;
      default:
        return <icosahedronGeometry args={[geometryArgs.args[0] * scale, geometryArgs.args[1]]} />;
    }
  }, [geometryArgs]);

  return (
    <group position={[ai.position_x, ai.position_y, positionZ]}>
      {/* Outer halo glow (near + mid only) */}
      {lod !== 'far' && (
        <mesh ref={haloRef}>
          <sphereGeometry args={[size * 2.5, lod === 'near' ? 16 : 8, lod === 'near' ? 16 : 8]} />
          <meshBasicMaterial color={color} transparent opacity={0.04} side={THREE.BackSide} />
        </mesh>
      )}

      {/* Core body - holographic style */}
      <mesh
        ref={meshRef}
        onClick={() => selectAI(ai.id)}
        onPointerEnter={(e) => { e.stopPropagation(); setHovered(true); document.body.style.cursor = 'pointer'; }}
        onPointerLeave={() => { setHovered(false); document.body.style.cursor = 'default'; }}
      >
        {GeometryComponent}
        <meshStandardMaterial
          color={color}
          emissive={color}
          emissiveIntensity={hovered ? 1.4 : 0.9}
          roughness={0.1}
          metalness={0.9}
          transparent
          opacity={hovered ? 0.7 : 0.5}
        />
      </mesh>

      {/* Wireframe overlay for hologram effect */}
      <mesh ref={wireRef}>
        {WireframeGeometry}
        <meshBasicMaterial
          color={color}
          wireframe
          transparent
          opacity={hovered ? 0.6 : 0.3}
        />
      </mesh>

      {/* Primary orbit ring - neon glow */}
      {lod === 'near' && (
        <group ref={ringRef}>
          {/* Inner bright core */}
          <mesh>
            <torusGeometry args={[size * 1.3, 0.05, 8, 64]} />
            <meshStandardMaterial
              color={color}
              emissive={color}
              emissiveIntensity={hovered ? 2.5 : 1.5}
              transparent
              opacity={hovered ? 0.9 : 0.7}
            />
          </mesh>
          {/* Outer glow halo */}
          <mesh>
            <torusGeometry args={[size * 1.3, 0.15, 8, 64]} />
            <meshBasicMaterial color={color} transparent opacity={hovered ? 0.2 : 0.08} />
          </mesh>
        </group>
      )}

      {/* Secondary orbit ring - neon accent */}
      {lod === 'near' && (
        <group rotation={[Math.PI / 3, hash * 0.1, 0]}>
          <mesh>
            <torusGeometry args={[size * 1.6, 0.04, 8, 48]} />
            <meshStandardMaterial
              color={color}
              emissive={color}
              emissiveIntensity={hovered ? 2.0 : 1.2}
              transparent
              opacity={hovered ? 0.8 : 0.5}
            />
          </mesh>
          {/* Outer glow */}
          <mesh>
            <torusGeometry args={[size * 1.6, 0.12, 8, 48]} />
            <meshBasicMaterial color={color} transparent opacity={hovered ? 0.15 : 0.05} />
          </mesh>
        </group>
      )}

      {/* Base ring on ground */}
      {lod === 'near' && (
        <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -size * 2, 0]}>
          <ringGeometry args={[size * 0.8, size * 1.2, 32]} />
          <meshBasicMaterial color={color} transparent opacity={hovered ? 0.2 : 0.08} side={THREE.DoubleSide} />
        </mesh>
      )}

      {/* Inner point light for bloom */}
      {lod !== 'far' && (
        <pointLight color={color} intensity={hovered ? 0.9 : 0.5} distance={size * 12} decay={2} />
      )}

      {/* Floating name label - holographic style */}
      {lod !== 'far' && ai.name && (
        <Html
          position={[0, size * 3.5, 0]}
          center
          distanceFactor={150}
          zIndexRange={[0, 0]}
          style={{ pointerEvents: 'none' }}
        >
          <div
            style={{
              color: colorHex,
              fontSize: '10px',
              fontWeight: 600,
              fontFamily: 'monospace',
              textShadow: `0 0 8px ${colorHex}, 0 0 16px ${colorHex}60`,
              whiteSpace: 'nowrap',
              userSelect: 'none',
              opacity: hovered ? 1 : 0.7,
              background: hovered ? `${colorHex}15` : 'transparent',
              padding: hovered ? '2px 6px' : '0',
              borderRadius: '3px',
              border: hovered ? `1px solid ${colorHex}40` : 'none',
              transition: 'all 0.2s ease',
            }}
          >
            {ai.name}
          </div>
        </Html>
      )}
    </group>
  );
}
