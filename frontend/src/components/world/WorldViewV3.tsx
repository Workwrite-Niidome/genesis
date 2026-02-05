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
import { BuildingTool } from './BuildingTool';
import { api } from '../../services/api';
import type { ActionProposal, Voxel, EntityV3 } from '../../types/v3';
import type { CameraMode } from '../../engine/Camera';
import type { BuildMode } from '../../engine/BuildingTool';

type MaterialType = 'solid' | 'emissive' | 'transparent' | 'glass';

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
  const [buildActive, setBuildActive] = useState(false);
  const [buildMode, setBuildMode] = useState<BuildMode>('none');
  const [buildColor, setBuildColor] = useState('#FF0000');
  const [buildMaterial, setBuildMaterial] = useState<MaterialType>('solid');
  const [cameraMode, setCameraMode] = useState<CameraMode>('observer');

  // Timeline panel state
  const [showTimeline, setShowTimeline] = useState(false);

  // God dialogue panel state
  const [showGodChat, setShowGodChat] = useState(false);

  // ── Build mode helpers ───────────────────────────────────────
  const openBuildMode = useCallback(() => {
    setBuildActive(true);
    setBuildMode('place');
  }, []);

  const closeBuildMode = useCallback(() => {
    setBuildActive(false);
    setBuildMode('none');
  }, []);

  const handleSetBuildMode = useCallback((mode: BuildMode) => {
    setBuildMode(mode);
  }, []);

  const handleSetBuildColor = useCallback((color: string) => {
    setBuildColor(color);
  }, []);

  const handleSetBuildMaterial = useCallback((material: MaterialType) => {
    setBuildMaterial(material);
  }, []);

  // Initialize scene
  useEffect(() => {
    if (!canvasRef.current || !labelContainerRef.current) return;

    const worldScene = new WorldScene({
      canvas: canvasRef.current,
      labelContainer: labelContainerRef.current,
      onProposal: async (proposal: ActionProposal) => {
        try {
          const API_BASE = import.meta.env.VITE_API_URL
            ? `${import.meta.env.VITE_API_URL}/api`
            : '/api';
          const token = localStorage.getItem('genesis_user_token');
          const headers: Record<string, string> = { 'Content-Type': 'application/json' };
          if (token) headers['Authorization'] = `Bearer ${token}`;

          if (proposal.action === 'place_voxel') {
            const resp = await fetch(`${API_BASE}/v3/building/place`, {
              method: 'POST',
              headers,
              body: JSON.stringify({
                agent_id: proposal.agentId,
                x: proposal.params.x,
                y: proposal.params.y,
                z: proposal.params.z,
                color: proposal.params.color || '#888888',
                material: proposal.params.material || 'solid',
              }),
            });
            if (!resp.ok) {
              const err = await resp.json().catch(() => ({}));
              console.warn('Place voxel rejected:', err);
            }
          } else if (proposal.action === 'destroy_voxel') {
            const resp = await fetch(`${API_BASE}/v3/building/destroy`, {
              method: 'POST',
              headers,
              body: JSON.stringify({
                agent_id: proposal.agentId,
                x: proposal.params.x,
                y: proposal.params.y,
                z: proposal.params.z,
              }),
            });
            if (!resp.ok) {
              const err = await resp.json().catch(() => ({}));
              console.warn('Destroy voxel rejected:', err);
            }
          } else if (proposal.action === 'paint_voxel') {
            // Paint = destroy existing block then place with new color/material.
            // Fire both sequentially so the position is freed before re-placing.
            const destroyResp = await fetch(`${API_BASE}/v3/building/destroy`, {
              method: 'POST',
              headers,
              body: JSON.stringify({
                agent_id: proposal.agentId,
                x: proposal.params.x,
                y: proposal.params.y,
                z: proposal.params.z,
              }),
            });
            if (destroyResp.ok) {
              await fetch(`${API_BASE}/v3/building/place`, {
                method: 'POST',
                headers,
                body: JSON.stringify({
                  agent_id: proposal.agentId,
                  x: proposal.params.x,
                  y: proposal.params.y,
                  z: proposal.params.z,
                  color: proposal.params.color || '#888888',
                  material: proposal.params.material || 'solid',
                }),
              });
            } else {
              console.warn('Paint failed at destroy step');
            }
          }
        } catch (err) {
          console.warn('Building action failed:', err);
        }
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

  // Load initial world data (voxels, entities, structures)
  useEffect(() => {
    if (!sceneRef.current) return;
    const scene = sceneRef.current;
    const store = useWorldStoreV3.getState();

    // Fetch world state
    api.v3.getWorldState().then((state: any) => {
      store.setWorldState({
        tickNumber: state.tick,
        entityCount: state.entity_count,
        voxelCount: state.voxel_count,
        isPaused: state.is_paused,
        timeSpeed: state.time_speed,
        godEntityId: state.god?.id || null,
        godPhase: state.god?.state?.god_phase || 'genesis',
      });
    }).catch(() => {});

    // Fetch initial voxels (large bounding box)
    api.v3.getVoxels({
      min_x: -200, max_x: 200,
      min_y: -10, max_y: 100,
      min_z: -200, max_z: 200,
    }).then((voxels: any[]) => {
      if (voxels && voxels.length > 0) {
        const mapped: Voxel[] = voxels.map((v: any) => ({
          x: v.x, y: v.y, z: v.z,
          color: v.color || '#888888',
          material: v.material || 'solid',
          hasCollision: v.has_collision !== false,
        }));
        scene.loadVoxels(mapped);
      }
    }).catch(() => {});

    // Fetch initial entities
    api.v3.getEntities(true, 200).then((data: any) => {
      if (data?.entities && data.entities.length > 0) {
        const entities: EntityV3[] = data.entities.map((e: any) => ({
          id: e.id,
          name: e.name,
          position: e.position,
          facing: e.facing || { x: 1, z: 0 },
          appearance: e.appearance || { bodyColor: '#4fc3f7', accentColor: '#ffffff', shape: 'humanoid', size: 1, emissive: false },
          personality: e.personality,
          state: e.state,
          isAlive: e.is_alive,
          isGod: e.is_god,
          metaAwareness: e.meta_awareness || 0,
          birthTick: e.birth_tick || 0,
          createdAt: e.created_at || '',
        }));
        store.setEntities(entities);
      }
    }).catch(() => {});

    // Fetch structures (signs, etc.)
    api.v3.getStructures().then((structures: any[]) => {
      if (structures && structures.length > 0) {
        scene.loadStructures(structures.map((s: any) => ({
          id: s.id,
          name: s.name,
          structureType: s.structure_type,
          bounds: {
            min: { x: s.min_x, y: s.min_y, z: s.min_z },
            max: { x: s.max_x, y: s.max_y, z: s.max_z },
          },
          properties: s.properties,
        })));
      }
    }).catch(() => {});
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

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

  // Build mode sync: push React state into the Three.js engine
  useEffect(() => {
    if (!sceneRef.current) return;
    sceneRef.current.setBuildMode(buildMode);
    sceneRef.current.setBuildColor(buildColor);
    // Map 'transparent' to 'glass' for the engine (which uses solid/glass/emissive/liquid)
    const engineMaterial = buildMaterial === 'transparent' ? 'glass' : buildMaterial;
    sceneRef.current.setBuildMaterial(engineMaterial as 'solid' | 'glass' | 'emissive' | 'liquid');
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

  // ── Global keyboard: B to open build mode ──────────────────
  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      // Ignore if typing in an input
      if (
        e.target instanceof HTMLInputElement ||
        e.target instanceof HTMLTextAreaElement
      ) {
        return;
      }

      if ((e.key === 'b' || e.key === 'B') && !buildActive) {
        openBuildMode();
      }
    };
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [buildActive, openBuildMode]);

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
          {/* Build mode toggle button */}
          <button
            onClick={() => buildActive ? closeBuildMode() : openBuildMode()}
            className={`
              px-2.5 py-1 rounded text-xs font-mono font-bold transition-all duration-150
              ${buildActive
                ? 'bg-emerald-600 text-white shadow-md shadow-emerald-600/30'
                : 'bg-white/10 text-white/70 hover:bg-white/20'
              }
            `}
            title="Toggle Build Mode (B)"
          >
            {buildActive ? 'Building' : 'Build'}
          </button>
          <div className="w-px h-4 bg-white/20 mx-1" />
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

      {/* Building Tool Panel (floating, bottom-center) */}
      <BuildingTool
        active={buildActive}
        buildMode={buildMode}
        buildColor={buildColor}
        buildMaterial={buildMaterial}
        onSetBuildMode={handleSetBuildMode}
        onSetBuildColor={handleSetBuildColor}
        onSetBuildMaterial={handleSetBuildMaterial}
        onClose={closeBuildMode}
      />

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
        <div>Click entity: Select | B: Build</div>
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
