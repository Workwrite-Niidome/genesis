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
    <div className="w-full h-full relative">
      <Canvas
        camera={{ position: [0, 0, 200], fov: 60, near: 0.1, far: 10000 }}
        gl={{ antialias: true, alpha: true }}
        style={{ background: '#050510' }}
      >
        <ambientLight intensity={0.15} />
        <pointLight position={[0, 0, 100]} intensity={0.5} color="#4fc3f7" />

        <Stars radius={500} depth={100} count={3000} factor={3} saturation={0.2} fade speed={0.5} />

        <GridBackground />

        {ais.map((ai) => (
          <AIEntity key={ai.id} ai={ai} />
        ))}

        <OrbitControls
          enableRotate={false}
          enablePan={true}
          enableZoom={true}
          minDistance={20}
          maxDistance={1000}
          zoomSpeed={0.8}
          panSpeed={1.2}
        />
      </Canvas>

      {/* Void overlay for pre-genesis */}
      {godAiPhase === 'pre_genesis' && <VoidOverlay />}
    </div>
  );
}
