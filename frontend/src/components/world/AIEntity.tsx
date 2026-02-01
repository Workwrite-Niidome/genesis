import { useRef, useMemo } from 'react';
import { useFrame } from '@react-three/fiber';
import { Html } from '@react-three/drei';
import * as THREE from 'three';
import { useAIStore } from '../../stores/aiStore';
import type { AIEntity as AIEntityType } from '../../types/world';

interface Props {
  ai: AIEntityType;
}

export default function AIEntity({ ai }: Props) {
  const meshRef = useRef<THREE.Mesh>(null);
  const ringRef = useRef<THREE.Mesh>(null);
  const haloRef = useRef<THREE.Mesh>(null);
  const selectAI = useAIStore((s) => s.selectAI);

  const color = useMemo(
    () => new THREE.Color(ai.appearance?.primaryColor || '#7c5bf5'),
    [ai.appearance?.primaryColor]
  );

  const size = (ai.appearance?.size || 10) * 0.25;
  const hash = ai.id.charCodeAt(0) + ai.id.charCodeAt(1);
  const speed = 0.5 + (hash % 10) * 0.05;

  useFrame(({ clock }) => {
    if (!meshRef.current) return;
    const t = clock.getElapsedTime();

    // Smooth floating motion
    meshRef.current.position.y = ai.position_y + Math.sin(t * speed + hash) * 1.5;
    meshRef.current.rotation.y = t * 0.15 + hash;
    meshRef.current.rotation.x = Math.sin(t * 0.1 + hash) * 0.2;

    // Orbit ring
    if (ringRef.current) {
      ringRef.current.rotation.z = t * 0.25 + hash;
      ringRef.current.rotation.x = Math.sin(t * 0.15) * 0.4;
    }

    // Halo breathe effect
    if (haloRef.current) {
      const breathe = 0.8 + Math.sin(t * 0.6 + hash) * 0.2;
      haloRef.current.scale.setScalar(breathe);
      (haloRef.current.material as THREE.MeshBasicMaterial).opacity = 0.04 + Math.sin(t * 0.4 + hash) * 0.02;
    }
  });

  const geometry = useMemo(() => {
    switch (ai.appearance?.shape) {
      case 'square':
        return <octahedronGeometry args={[size * 0.55, 0]} />;
      case 'triangle':
        return <tetrahedronGeometry args={[size * 0.6, 0]} />;
      default:
        return <icosahedronGeometry args={[size * 0.45, 1]} />;
    }
  }, [ai.appearance?.shape, size]);

  return (
    <group position={[ai.position_x, ai.position_y, 0]}>
      {/* Outer halo glow */}
      <mesh ref={haloRef}>
        <sphereGeometry args={[size * 2.5, 16, 16]} />
        <meshBasicMaterial color={color} transparent opacity={0.04} side={THREE.BackSide} />
      </mesh>

      {/* Core body */}
      <mesh
        ref={meshRef}
        onClick={() => selectAI(ai.id)}
        onPointerOver={(e) => { e.stopPropagation(); document.body.style.cursor = 'pointer'; }}
        onPointerOut={() => { document.body.style.cursor = 'default'; }}
      >
        {geometry}
        <meshStandardMaterial
          color={color}
          emissive={color}
          emissiveIntensity={1.0}
          roughness={0.15}
          metalness={0.6}
          transparent
          opacity={0.95}
        />
      </mesh>

      {/* Orbit ring */}
      <mesh ref={ringRef}>
        <torusGeometry args={[size * 1.3, 0.06, 8, 64]} />
        <meshBasicMaterial color={color} transparent opacity={0.12} />
      </mesh>

      {/* Second orbit ring (offset) */}
      <mesh rotation={[Math.PI / 3, hash * 0.1, 0]}>
        <torusGeometry args={[size * 1.6, 0.04, 8, 48]} />
        <meshBasicMaterial color={color} transparent opacity={0.06} />
      </mesh>

      {/* Inner point light for bloom */}
      <pointLight color={color} intensity={0.6} distance={size * 12} decay={2} />

      {/* Floating name label */}
      {ai.name && (
        <Html
          position={[0, size * 3.5, 0]}
          center
          distanceFactor={150}
          zIndexRange={[0, 0]}
          style={{ pointerEvents: 'none' }}
        >
          <div
            style={{
              color: ai.appearance?.primaryColor || '#7c5bf5',
              fontSize: '11px',
              fontWeight: 600,
              fontFamily: 'monospace',
              textShadow: `0 0 8px ${ai.appearance?.primaryColor || '#7c5bf5'}80, 0 0 20px rgba(0,0,0,0.8)`,
              whiteSpace: 'nowrap',
              userSelect: 'none',
              opacity: 0.9,
            }}
          >
            {ai.name}
          </div>
        </Html>
      )}
    </group>
  );
}
