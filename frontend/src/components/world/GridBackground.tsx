import { useMemo } from 'react';
import * as THREE from 'three';

export default function GridBackground() {
  const material = useMemo(
    () =>
      new THREE.LineBasicMaterial({
        color: new THREE.Color('#7c5bf5'),
        transparent: true,
        opacity: 0.03,
      }),
    []
  );

  const geometry = useMemo(() => {
    const points: THREE.Vector3[] = [];
    const size = 2000;
    const step = 40;

    for (let i = -size; i <= size; i += step) {
      points.push(new THREE.Vector3(i, -size, -8));
      points.push(new THREE.Vector3(i, size, -8));
      points.push(new THREE.Vector3(-size, i, -8));
      points.push(new THREE.Vector3(size, i, -8));
    }

    const geo = new THREE.BufferGeometry().setFromPoints(points);
    return geo;
  }, []);

  return <lineSegments geometry={geometry} material={material} />;
}
