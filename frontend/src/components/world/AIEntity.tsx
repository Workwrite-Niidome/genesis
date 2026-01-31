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
  const glowRef = useRef<THREE.Mesh>(null);
  const selectAI = useAIStore((s) => s.selectAI);

  const color = useMemo(
    () => new THREE.Color(ai.appearance?.primaryColor || '#4fc3f7'),
    [ai.appearance?.primaryColor]
  );

  const size = (ai.appearance?.size || 10) * 0.3;

  useFrame(({ clock }) => {
    if (!meshRef.current) return;
    const t = clock.getElapsedTime();

    // Gentle floating animation
    meshRef.current.position.y = ai.position_y + Math.sin(t * 1.5 + ai.position_x) * 1.5;

    // Pulse effect
    if (ai.appearance?.pulse && glowRef.current) {
      const scale = 1 + Math.sin(t * 2) * 0.15;
      glowRef.current.scale.setScalar(scale);
    }
  });

  const geometry = useMemo(() => {
    switch (ai.appearance?.shape) {
      case 'square':
        return <boxGeometry args={[size, size, size * 0.3]} />;
      case 'triangle':
        return <coneGeometry args={[size * 0.6, size, 3]} />;
      default:
        return <sphereGeometry args={[size * 0.5, 16, 16]} />;
    }
  }, [ai.appearance?.shape, size]);

  return (
    <group position={[ai.position_x, ai.position_y, 0]}>
      {/* Main body */}
      <mesh
        ref={meshRef}
        onClick={() => selectAI(ai.id)}
        onPointerOver={(e) => {
          e.stopPropagation();
          document.body.style.cursor = 'pointer';
        }}
        onPointerOut={() => {
          document.body.style.cursor = 'default';
        }}
      >
        {geometry}
        <meshStandardMaterial
          color={color}
          emissive={color}
          emissiveIntensity={0.6}
          transparent
          opacity={0.9}
        />
      </mesh>

      {/* Glow aura */}
      {ai.appearance?.glow && (
        <mesh ref={glowRef}>
          <sphereGeometry args={[size * 0.9, 16, 16]} />
          <meshBasicMaterial
            color={color}
            transparent
            opacity={0.08}
            side={THREE.BackSide}
          />
        </mesh>
      )}

      {/* Point light per entity */}
      <pointLight color={color} intensity={0.3} distance={size * 8} />
    </group>
  );
}
