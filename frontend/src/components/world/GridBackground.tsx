import { useMemo } from 'react';
import * as THREE from 'three';

export default function GridBackground() {
  const gridHelper = useMemo(() => {
    const size = 2000;
    const divisions = 100;
    const color1 = new THREE.Color('#1a1a3e');
    const color2 = new THREE.Color('#0a0a20');
    return { size, divisions, color1, color2 };
  }, []);

  return (
    <group position={[0, 0, -5]}>
      <gridHelper
        args={[
          gridHelper.size,
          gridHelper.divisions,
          gridHelper.color1,
          gridHelper.color2,
        ]}
        rotation={[Math.PI / 2, 0, 0]}
      />
    </group>
  );
}
