import { Suspense } from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls, Stars } from '@react-three/drei';
import { useWorldStore } from '../../stores/worldStore';
import { useAIStore } from '../../stores/aiStore';
import AIEntity from './AIEntity';
import GridBackground from './GridBackground';
import VoidOverlay from './VoidOverlay';

export default function WorldCanvas() {
  const { godAiPhase } = useWorldStore();
  const { ais } = useAIStore();

  return (
    <div className="w-full h-full relative bg-bg">
      <Canvas
        camera={{ position: [0, 0, 200], fov: 60, near: 0.1, far: 10000 }}
        gl={{ antialias: true, alpha: true }}
        style={{ background: '#06060c' }}
      >
        <Suspense fallback={null}>
          <ambientLight intensity={0.08} />
          <pointLight position={[0, 0, 150]} intensity={0.3} color="#7c5bf5" />
          <pointLight position={[100, -100, 80]} intensity={0.15} color="#58d5f0" />

          <Stars
            radius={600}
            depth={150}
            count={4000}
            factor={2.5}
            saturation={0.1}
            fade
            speed={0.3}
          />

          <GridBackground />

          {ais.map((ai) => (
            <AIEntity key={ai.id} ai={ai} />
          ))}

          <OrbitControls
            enableRotate={false}
            enablePan={true}
            enableZoom={true}
            minDistance={30}
            maxDistance={800}
            zoomSpeed={0.6}
            panSpeed={1}
            dampingFactor={0.08}
            enableDamping
          />
        </Suspense>
      </Canvas>

      {/* Subtle vignette overlay */}
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          background: 'radial-gradient(ellipse at center, transparent 50%, rgba(6,6,12,0.6) 100%)',
        }}
      />

      {godAiPhase === 'pre_genesis' && <VoidOverlay />}
    </div>
  );
}
