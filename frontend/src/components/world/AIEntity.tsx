import { useRef, useMemo } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';
import { useAIStore } from '../../stores/aiStore';
import type { AIEntity as AIEntityType } from '../../types/world';

interface Props {
  ai: AIEntityType;
}

export default function AIEntity({ ai }: Props) {
  const meshRef = useRef<THREE.Mesh>(null);
  const ringRef = useRef<THREE.Mesh>(null);
  const selectAI = useAIStore((s) => s.selectAI);

  const color = useMemo(
    () => new THREE.Color(ai.appearance?.primaryColor || '#7c5bf5'),
    [ai.appearance?.primaryColor]
  );

  const size = (ai.appearance?.size || 10) * 0.25;
  const hash = ai.id.charCodeAt(0) + ai.id.charCodeAt(1);

  useFrame(({ clock }) => {
    if (!meshRef.current) return;
    const t = clock.getElapsedTime();

    // Subtle float
    meshRef.current.position.y = ai.position_y + Math.sin(t * 0.8 + hash) * 1.2;

    // Orbit ring rotation
    if (ringRef.current) {
      ringRef.current.rotation.z = t * 0.3 + hash;
      ringRef.current.rotation.x = Math.sin(t * 0.2) * 0.3;
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
      {/* Core */}
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
          emissiveIntensity={0.8}
          roughness={0.2}
          metalness={0.5}
          transparent
          opacity={0.95}
        />
      </mesh>

      {/* Orbit ring */}
      <mesh ref={ringRef}>
        <torusGeometry args={[size * 1.2, 0.08, 8, 48]} />
        <meshBasicMaterial color={color} transparent opacity={0.15} />
      </mesh>

      {/* Inner glow */}
      <pointLight color={color} intensity={0.4} distance={size * 10} decay={2} />
    </group>
  );
}
