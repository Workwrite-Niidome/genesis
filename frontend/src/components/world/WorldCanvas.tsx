import { Suspense, useRef, useEffect, useState } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls, Stars } from '@react-three/drei';
import { EffectComposer, Bloom, Vignette } from '@react-three/postprocessing';
import * as THREE from 'three';
import { useWorldStore } from '../../stores/worldStore';
import { useAIStore } from '../../stores/aiStore';
import { useUIStore } from '../../stores/uiStore';
import AIEntity from './AIEntity';
import GridBackground from './GridBackground';
import VoidOverlay from './VoidOverlay';
import WorldStructure from './WorldStructure';
import { api } from '../../services/api';

/** Smoothly pans camera to center on the selected AI. */
function CameraController({
  controlsRef,
}: {
  controlsRef: React.RefObject<any>;
}) {
  const selectedAI = useAIStore((s) => s.selectedAI);
  const targetPos = useRef(new THREE.Vector3());
  const animating = useRef(false);
  const lastId = useRef<string | null>(null);

  useEffect(() => {
    if (selectedAI && selectedAI.id !== lastId.current) {
      lastId.current = selectedAI.id;
      // Use position from live ais array for accuracy with rendered position
      const ai = useAIStore.getState().ais.find((a) => a.id === selectedAI.id);
      const px = ai?.position_x ?? selectedAI.position_x;
      const py = ai?.position_y ?? selectedAI.position_y;
      targetPos.current.set(px, py, 0);
      animating.current = true;
    } else if (!selectedAI) {
      lastId.current = null;
    }
  }, [selectedAI?.id]);

  useFrame(() => {
    if (!animating.current || !controlsRef.current) return;
    const ctrl = controlsRef.current;
    const cam = ctrl.object;
    const lerp = 0.08;

    const dx = (targetPos.current.x - ctrl.target.x) * lerp;
    const dy = (targetPos.current.y - ctrl.target.y) * lerp;

    // Move both target and camera by the same delta to preserve zoom distance
    ctrl.target.x += dx;
    ctrl.target.y += dy;
    cam.position.x += dx;
    cam.position.y += dy;
    ctrl.update();

    const remaining =
      Math.abs(targetPos.current.x - ctrl.target.x) +
      Math.abs(targetPos.current.y - ctrl.target.y);
    if (remaining < 0.5) {
      animating.current = false;
    }
  });

  return null;
}

interface WorldCanvasProps {
  showGenesis?: boolean;
}

export default function WorldCanvas({ showGenesis = true }: WorldCanvasProps) {
  const { godAiPhase } = useWorldStore();
  const { ais } = useAIStore();
  const showGrid = useUIStore((s) => s.showGrid);
  const controlsRef = useRef<any>(null);
  const [structures, setStructures] = useState<any[]>([]);

  // Detect mobile for performance adjustments
  const isMobile = typeof window !== 'undefined' && window.matchMedia('(max-width: 768px)').matches;

  // Fetch architecture artifacts periodically
  useEffect(() => {
    const load = () => {
      api.artifacts.list({ artifact_type: 'architecture' }).then((arts) => {
        setStructures((arts || []).slice(0, 20));
      }).catch(() => {});
    };
    load();
    const interval = setInterval(load, 15000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="w-full h-full relative bg-bg">
      <Canvas
        camera={{ position: [0, 0, 200], fov: 60, near: 0.1, far: 10000 }}
        gl={{ antialias: !isMobile, alpha: true }}
        dpr={isMobile ? [1, 1.5] : [1, 2]}
        style={{ background: '#06060c' }}
      >
        <Suspense fallback={null}>
          <ambientLight intensity={0.06} />
          <pointLight position={[0, 0, 150]} intensity={0.25} color="#7c5bf5" />
          {!isMobile && <pointLight position={[100, -100, 80]} intensity={0.12} color="#58d5f0" />}
          {!isMobile && <pointLight position={[-120, 60, 60]} intensity={0.08} color="#34d399" />}

          <Stars
            radius={600}
            depth={200}
            count={isMobile ? 2000 : 5000}
            factor={2.5}
            saturation={0.05}
            fade
            speed={0.2}
          />

          {showGrid && <GridBackground />}

          {ais.map((ai) => (
            <AIEntity key={ai.id} ai={ai} />
          ))}

          {/* Architecture structures (voxel buildings) - spread in 3D space */}
          {structures.slice(0, isMobile ? 8 : 20).map((artifact, i) => {
            // Position near the creator AI if found, otherwise spread out in a grid
            const creatorAI = ais.find((a) => a.id === artifact.creator_id);
            // Spread structures in 3D using golden angle for XY and varied Z
            const offsetAngle = (i * 137.5) * (Math.PI / 180);
            const offsetRadius = 25 + (i % 3) * 15;
            const offsetX = Math.cos(offsetAngle) * offsetRadius;
            const offsetY = Math.sin(offsetAngle) * offsetRadius;
            // Vary Z position based on artifact id hash for 3D depth
            const zHash = artifact.id.charCodeAt(0) + artifact.id.charCodeAt(2);
            const offsetZ = isMobile ? 0 : ((zHash % 5) - 2) * 12; // Flat on mobile for performance
            const baseX = creatorAI ? creatorAI.position_x + offsetX : (i % 6) * 50 - 125;
            const baseY = creatorAI ? creatorAI.position_y + offsetY : Math.floor(i / 6) * 50 - 100;
            return (
              <WorldStructure
                key={artifact.id}
                artifact={artifact}
                position={[baseX, baseY, offsetZ]}
              />
            );
          })}

          {/* Post-processing for holographic glow */}
          <EffectComposer>
            <Bloom
              intensity={isMobile ? 0.6 : 1.1}
              luminanceThreshold={isMobile ? 0.25 : 0.15}
              luminanceSmoothing={0.85}
              mipmapBlur
            />
            {!isMobile && <Vignette eskil={false} offset={0.1} darkness={0.8} />}
          </EffectComposer>

          <OrbitControls
            ref={controlsRef}
            enableRotate={true}
            enablePan={true}
            enableZoom={true}
            minDistance={30}
            maxDistance={800}
            minPolarAngle={Math.PI * 0.1}
            maxPolarAngle={Math.PI * 0.75}
            rotateSpeed={0.5}
            zoomSpeed={0.6}
            panSpeed={1}
            dampingFactor={0.08}
            enableDamping
            touches={{ ONE: THREE.TOUCH.ROTATE, TWO: THREE.TOUCH.DOLLY_PAN }}
          />

          <CameraController controlsRef={controlsRef} />
        </Suspense>
      </Canvas>

      {showGenesis && godAiPhase === 'pre_genesis' && <VoidOverlay />}
    </div>
  );
}
