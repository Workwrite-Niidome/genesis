/**
 * GENESIS v3 World View
 *
 * Main 3D viewport component that renders the voxel world.
 * Connects the Three.js WorldScene to React state via Zustand.
 */
import { useEffect, useRef, useCallback, useState } from 'react';
import { WorldScene } from '../../engine/WorldScene';
import { useWorldStoreV3 } from '../../stores/worldStoreV3';
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

  const selectedEntity = selectedEntityId ? entities.get(selectedEntityId) : null;

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
        </div>
      </div>

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

      {/* Entity Info Panel */}
      {selectedEntity && (
        <div className="absolute top-14 right-4 w-72 bg-black/70 backdrop-blur-sm rounded-lg p-4 text-white/80 text-sm font-mono z-10">
          <div className="flex items-center justify-between mb-2">
            <span className="text-purple-400 font-bold">{selectedEntity.name}</span>
            <button
              onClick={() => selectEntity(null)}
              className="text-white/40 hover:text-white text-xs"
            >
              ✕
            </button>
          </div>
          <div className="space-y-1 text-xs">
            <div>Position: ({selectedEntity.position.x.toFixed(1)}, {selectedEntity.position.y.toFixed(1)}, {selectedEntity.position.z.toFixed(1)})</div>
            <div>Status: {selectedEntity.isAlive ? (selectedEntity.state.currentAction || 'idle') : 'DEAD'}</div>
            <div>Energy: {(selectedEntity.state.energy * 100).toFixed(0)}%</div>
            <div>Mode: {selectedEntity.state.behaviorMode}</div>
            <div>Meta-awareness: {selectedEntity.metaAwareness.toFixed(1)}</div>

            {/* Needs bar */}
            <div className="mt-2 space-y-1">
              <div className="text-white/50 text-xs">Needs:</div>
              {selectedEntity.state.needs && Object.entries(selectedEntity.state.needs).map(([key, val]) => (
                <div key={key} className="flex items-center gap-2">
                  <span className="w-24 text-white/50">{key}</span>
                  <div className="flex-1 h-1.5 bg-white/10 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-cyan-500 rounded-full"
                      style={{ width: `${Math.min(100, val as number)}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>

            {/* Personality highlights */}
            {selectedEntity.personality && (
              <div className="mt-2">
                <div className="text-white/50 text-xs mb-1">Personality:</div>
                <div className="flex flex-wrap gap-1">
                  {Object.entries(selectedEntity.personality)
                    .filter(([, v]) => (v as number) > 0.7 || (v as number) < 0.3)
                    .slice(0, 6)
                    .map(([key, val]) => (
                      <span
                        key={key}
                        className={`px-1.5 py-0.5 rounded text-xs ${(val as number) > 0.7 ? 'bg-green-900/50 text-green-300' : 'bg-red-900/50 text-red-300'}`}
                      >
                        {key}: {(val as number).toFixed(2)}
                      </span>
                    ))}
                </div>
              </div>
            )}

            <div className="mt-2 flex gap-2">
              <button
                onClick={() => {
                  handleCameraMode('third_person');
                  sceneRef.current?.followEntity(selectedEntity.id);
                }}
                className="px-2 py-1 bg-purple-600/50 hover:bg-purple-600 rounded text-xs"
              >
                Follow
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Controls hint */}
      <div className="absolute bottom-16 right-4 text-white/30 text-xs font-mono z-10">
        <div>WASD: Move | Space/C: Up/Down</div>
        <div>Right-drag: Look | Scroll: Zoom</div>
        <div>Click entity: Select</div>
      </div>
    </div>
  );
}
