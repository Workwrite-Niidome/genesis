import { Suspense } from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls, Stars } from '@react-three/drei';
import { EffectComposer, Bloom, Vignette } from '@react-three/postprocessing';
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
          <ambientLight intensity={0.06} />
          <pointLight position={[0, 0, 150]} intensity={0.25} color="#7c5bf5" />
          <pointLight position={[100, -100, 80]} intensity={0.12} color="#58d5f0" />
          <pointLight position={[-120, 60, 60]} intensity={0.08} color="#34d399" />

          <Stars
            radius={600}
            depth={200}
            count={5000}
            factor={2.5}
            saturation={0.05}
            fade
            speed={0.2}
          />

          <GridBackground />

          {ais.map((ai) => (
            <AIEntity key={ai.id} ai={ai} />
          ))}

          {/* Post-processing for mystical glow */}
          <EffectComposer>
            <Bloom
              intensity={0.8}
              luminanceThreshold={0.2}
              luminanceSmoothing={0.9}
              mipmapBlur
            />
            <Vignette eskil={false} offset={0.1} darkness={0.8} />
          </EffectComposer>

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

      {godAiPhase === 'pre_genesis' && <VoidOverlay />}
    </div>
  );
}
