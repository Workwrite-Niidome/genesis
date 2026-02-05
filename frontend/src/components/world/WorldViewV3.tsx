/**
 * GENESIS v3 World View
 *
 * Main 3D viewport component that renders the voxel world.
 * Connects the Three.js WorldScene to React state via Zustand.
 */
import { useEffect, useRef, useCallback, useState } from 'react';
import { WorldScene } from '../../engine/WorldScene';
import { useWorldStoreV3 } from '../../stores/worldStoreV3';
import { EventFeed } from './EventFeed';
import { EntityDetailPanel } from './EntityDetailPanel';
import { MiniMap } from './MiniMap';
import { EntityListPanel } from './EntityListPanel';
import { GodSuccessionOverlay } from './GodSuccessionOverlay';
import { TimelinePanel, TimelineToggleButton } from './TimelinePanel';
import { GodChatPanel, GodChatToggle } from './GodChatPanel';
import type { ActionProposal } from '../../types/v3';
import type { CameraMode } from '../../engine/Camera';
import type { BuildMode } from '../../engine/BuildingTool';

const BUILD_COLORS = [
  '#4fc3f7', '#81c784', '#ff8a65', '#ce93d8',
  '#fff176', '#ef5350', '#26c6da', '#ab47bc',
  '#8d6e63', '#78909c', '#ffffff', '#212121',
];

const BUILD_MATERIALS = ['solid', 'glass', 'emissive', 'liquid'] as const;

export function WorldViewV3() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const labelContainerRef = useRef<HTMLDivElement>(null);
  const sceneRef = useRef<WorldScene | null>(null);

  const entities = useWorldStoreV3(s => s.entities);
  const pendingVoxelUpdates = useWorldStoreV3(s => s.pendingVoxelUpdates);
  const clearVoxelUpdates = useWorldStoreV3(s => s.clearVoxelUpdates);
  const recentSpeech = useWorldStoreV3(s => s.recentSpeech);
  const selectEntity = useWorldStoreV3(s => s.selectEntity);
  const selectedEntityId = useWorldStoreV3(s => s.selectedEntityId);
  const tickNumber = useWorldStoreV3(s => s.tickNumber);
  const entityCount = useWorldStoreV3(s => s.entityCount);
  const voxelCount = useWorldStoreV3(s => s.voxelCount);

  // Build tool state
  const [buildMode, setBuildMode] = useState<BuildMode>('none');
  const [buildColor, setBuildColor] = useState('#4fc3f7');
  const [buildMaterial, setBuildMaterial] = useState<typeof BUILD_MATERIALS[number]>('solid');
  const [cameraMode, setCameraMode] = useState<CameraMode>('observer');

  // Timeline panel state
  const [showTimeline, setShowTimeline] = useState(false);

  // God dialogue panel state
  const [showGodChat, setShowGodChat] = useState(false);

  // Initialize scene
  useEffect(() => {
    if (!canvasRef.current || !labelContainerRef.current) return;

    const worldScene = new WorldScene({
      canvas: canvasRef.current,
      labelContainer: labelContainerRef.current,
      onProposal: (proposal: ActionProposal) => {
        // TODO: Send proposal to server via WebSocket
        console.log('Action proposal:', proposal);
      },
      onEntityClick: (entityId: string) => {
        selectEntity(entityId);
      },
    });

    sceneRef.current = worldScene;

    return () => {
      worldScene.dispose();
      sceneRef.current = null;
    };
  }, [selectEntity]);

  // Sync entities to scene
  useEffect(() => {
    if (!sceneRef.current) return;
    const entityArray = Array.from(entities.values());
    sceneRef.current.updateEntities(entityArray);
  }, [entities]);

  // Apply pending voxel updates
  useEffect(() => {
    if (!sceneRef.current || pendingVoxelUpdates.length === 0) return;
    sceneRef.current.applyVoxelUpdates(pendingVoxelUpdates);
    clearVoxelUpdates();
  }, [pendingVoxelUpdates, clearVoxelUpdates]);

  // Handle speech events
  useEffect(() => {
    if (!sceneRef.current || recentSpeech.length === 0) return;
    const latest = recentSpeech[recentSpeech.length - 1];
    sceneRef.current.handleSpeechEvent(latest);
  }, [recentSpeech]);

  // Build mode sync
  useEffect(() => {
    if (!sceneRef.current) return;
    sceneRef.current.setBuildMode(buildMode);
    sceneRef.current.setBuildColor(buildColor);
    sceneRef.current.setBuildMaterial(buildMaterial);
  }, [buildMode, buildColor, buildMaterial]);

  // Camera follow on entity select
  useEffect(() => {
    if (!sceneRef.current || !selectedEntityId) return;
    if (cameraMode !== 'observer') {
      sceneRef.current.followEntity(selectedEntityId);
    }
  }, [selectedEntityId, cameraMode]);

  const handleCameraMode = useCallback((mode: CameraMode) => {
    setCameraMode(mode);
    sceneRef.current?.setCameraMode(mode);
  }, []);

  // Camera position for EntityListPanel distance calculations
  const [cameraPosition, setCameraPosition] = useState<{ x: number; y: number; z: number } | null>(null);

  // Periodically sample camera position (every ~500ms) for the entity list
  useEffect(() => {
    const interval = setInterval(() => {
      if (sceneRef.current) {
        setCameraPosition(sceneRef.current.getCameraPosition());
      }
    }, 500);
    return () => clearInterval(interval);
  }, []);

  // MiniMap click-to-pan handler
  const handleMiniMapPan = useCallback((worldX: number, worldZ: number) => {
    sceneRef.current?.panTo(worldX, worldZ);
  }, []);

  return (
    <div className="relative w-full h-full bg-[#0a0a0f] overflow-hidden">
      {/* 3D Canvas */}
      <canvas
        ref={canvasRef}
        className="w-full h-full block"
        style={{ touchAction: 'none' }}
      />

      {/* Floating labels container */}
      <div
        ref={labelContainerRef}
        className="absolute inset-0 pointer-events-none overflow-hidden"
      />

      {/* HUD: Top bar */}
      <div className="absolute top-0 left-0 right-0 flex items-center justify-between px-4 py-2 bg-black/50 backdrop-blur-sm text-white/80 text-sm font-mono z-10">
        <div className="flex items-center gap-4">
          <span className="text-purple-400 font-bold">GENESIS v3</span>
          <span>T:{tickNumber.toLocaleString()}</span>
          <span>Entities:{entityCount}</span>
          <span>Voxels:{voxelCount}</span>
        </div>
        <div className="flex items-center gap-2">
          {/* God dialogue toggle */}
          <GodChatToggle
            isOpen={showGodChat}
            onClick={() => setShowGodChat(!showGodChat)}
          />
          <div className="w-px h-4 bg-white/20 mx-1" />
          {/* Camera mode buttons */}
          <button
            onClick={() => handleCameraMode('observer')}
            className={`px-2 py-1 rounded text-xs ${cameraMode === 'observer' ? 'bg-purple-600' : 'bg-white/10 hover:bg-white/20'}`}
          >
            Observer
          </button>
          <button
            onClick={() => handleCameraMode('third_person')}
            className={`px-2 py-1 rounded text-xs ${cameraMode === 'third_person' ? 'bg-purple-600' : 'bg-white/10 hover:bg-white/20'}`}
          >
            Follow
          </button>
          <div className="w-px h-4 bg-white/20 mx-1" />
          <TimelineToggleButton
            isOpen={showTimeline}
            onClick={() => setShowTimeline(!showTimeline)}
          />
        </div>
      </div>

      {/* Real-time event feed */}
      <EventFeed />

      {/* Build Tool Panel */}
      <div className="absolute bottom-4 left-1/2 -translate-x-1/2 flex items-center gap-2 bg-black/60 backdrop-blur-sm rounded-lg px-4 py-2 z-10">
        {/* Mode buttons */}
        <button
          onClick={() => setBuildMode(buildMode === 'place' ? 'none' : 'place')}
          className={`px-3 py-1 rounded text-xs font-mono ${buildMode === 'place' ? 'bg-green-600 text-white' : 'bg-white/10 text-white/70 hover:bg-white/20'}`}
        >
          Build
        </button>
        <button
          onClick={() => setBuildMode(buildMode === 'destroy' ? 'none' : 'destroy')}
          className={`px-3 py-1 rounded text-xs font-mono ${buildMode === 'destroy' ? 'bg-red-600 text-white' : 'bg-white/10 text-white/70 hover:bg-white/20'}`}
        >
          Break
        </button>

        {/* Color palette */}
        {buildMode === 'place' && (
          <>
            <div className="w-px h-6 bg-white/20 mx-1" />
            <div className="flex gap-1">
              {BUILD_COLORS.map((color) => (
                <button
                  key={color}
                  onClick={() => setBuildColor(color)}
                  className={`w-5 h-5 rounded border ${buildColor === color ? 'border-white scale-125' : 'border-white/20'}`}
                  style={{ backgroundColor: color }}
                />
              ))}
            </div>
            <div className="w-px h-6 bg-white/20 mx-1" />
            <div className="flex gap-1">
              {BUILD_MATERIALS.map((mat) => (
                <button
                  key={mat}
                  onClick={() => setBuildMaterial(mat)}
                  className={`px-2 py-1 rounded text-xs font-mono ${buildMaterial === mat ? 'bg-cyan-600 text-white' : 'bg-white/10 text-white/60'}`}
                >
                  {mat}
                </button>
              ))}
            </div>
          </>
        )}
      </div>

      {/* Entity Detail Panel (rich side panel) */}
      <EntityDetailPanel />

      {/* Entity list toggle + panel (top-left, after the EventFeed) */}
      <EntityListPanel cameraPosition={cameraPosition} />

      {/* Minimap (bottom-right) */}
      <MiniMap onPanTo={handleMiniMapPan} />

      {/* Controls hint */}
      <div className="absolute bottom-16 right-4 text-white/30 text-xs font-mono z-10">
        <div>WASD: Move | Space/C: Up/Down</div>
        <div>Right-drag: Look | Scroll: Zoom</div>
        <div>Click entity: Select</div>
      </div>

      {/* God Dialogue Panel (left side) */}
      <GodChatPanel visible={showGodChat} onClose={() => setShowGodChat(false)} />

      {/* God Succession Ceremony Overlay */}
      <GodSuccessionOverlay />

      {/* Timeline / Archive Panel (right side) */}
      <TimelinePanel visible={showTimeline} onClose={() => setShowTimeline(false)} />
    </div>
  );
}
