/**
 * useWorldSceneV3 — Extracted scene logic hook for GENESIS v3.
 *
 * Encapsulates all Three.js scene management (init, entity sync, voxels,
 * speech, build mode, camera) so both desktop WorldViewV3 and
 * MobileWorldViewV3 share identical 3D behaviour.
 */
import { useEffect, useRef, useCallback, useState } from 'react';
import { WorldScene } from '../engine/WorldScene';
import { useWorldStoreV3 } from '../stores/worldStoreV3';
import { api } from '../services/api';
import type { ActionProposal, Voxel, EntityV3 } from '../types/v3';
import type { CameraMode } from '../engine/Camera';
import type { BuildMode } from '../engine/BuildingTool';

export type MaterialType = 'solid' | 'emissive' | 'transparent' | 'glass';

export interface WorldSceneV3 {
  // Refs
  canvasRef: React.RefObject<HTMLCanvasElement | null>;
  labelContainerRef: React.RefObject<HTMLDivElement | null>;
  sceneRef: React.RefObject<WorldScene | null>;

  // Build state
  buildActive: boolean;
  buildMode: BuildMode;
  buildColor: string;
  buildMaterial: MaterialType;

  // Camera
  cameraMode: CameraMode;
  cameraPosition: { x: number; y: number; z: number } | null;

  // Panel visibility
  showTimeline: boolean;
  showGodChat: boolean;

  // Store selectors
  tickNumber: number;
  entityCount: number;
  voxelCount: number;
  selectedEntityId: string | null;

  // Callbacks
  openBuildMode: () => void;
  closeBuildMode: () => void;
  handleSetBuildMode: (mode: BuildMode) => void;
  handleSetBuildColor: (color: string) => void;
  handleSetBuildMaterial: (material: MaterialType) => void;
  handleCameraMode: (mode: CameraMode) => void;
  handleMiniMapPan: (worldX: number, worldZ: number) => void;
  setShowTimeline: (show: boolean) => void;
  setShowGodChat: (show: boolean) => void;
}

export function useWorldSceneV3(): WorldSceneV3 {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const labelContainerRef = useRef<HTMLDivElement | null>(null);
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

  // Panel visibility
  const [showTimeline, setShowTimeline] = useState(false);
  const [showGodChat, setShowGodChat] = useState(false);

  // Build mode helpers
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

  // Load initial world data
  useEffect(() => {
    if (!sceneRef.current) return;
    const scene = sceneRef.current;
    const store = useWorldStoreV3.getState();

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

  // Build mode sync
  useEffect(() => {
    if (!sceneRef.current) return;
    sceneRef.current.setBuildMode(buildMode);
    sceneRef.current.setBuildColor(buildColor);
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

  // Camera position sampling
  const [cameraPosition, setCameraPosition] = useState<{ x: number; y: number; z: number } | null>(null);

  useEffect(() => {
    const interval = setInterval(() => {
      if (sceneRef.current) {
        setCameraPosition(sceneRef.current.getCameraPosition());
      }
    }, 500);
    return () => clearInterval(interval);
  }, []);

  // MiniMap click-to-pan
  const handleMiniMapPan = useCallback((worldX: number, worldZ: number) => {
    sceneRef.current?.panTo(worldX, worldZ);
  }, []);

  // Global keyboard: B to open build mode
  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
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

  return {
    canvasRef,
    labelContainerRef,
    sceneRef,
    buildActive,
    buildMode,
    buildColor,
    buildMaterial,
    cameraMode,
    cameraPosition,
    showTimeline,
    showGodChat,
    tickNumber,
    entityCount,
    voxelCount,
    selectedEntityId,
    openBuildMode,
    closeBuildMode,
    handleSetBuildMode,
    handleSetBuildColor,
    handleSetBuildMaterial,
    handleCameraMode,
    handleMiniMapPan,
    setShowTimeline,
    setShowGodChat,
  };
}
