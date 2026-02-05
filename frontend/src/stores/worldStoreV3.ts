/**
 * GENESIS v3 World Store (Zustand)
 *
 * Manages 3D world state: entities, voxels, world metadata.
 */
import { create } from 'zustand';
import type {
  EntityV3, Voxel, VoxelUpdate, WorldStateV3,
  SocketEntityPosition, SocketSpeechEvent,
} from '../types/v3';

interface WorldStoreV3State {
  // World metadata
  tickNumber: number;
  entityCount: number;
  voxelCount: number;
  isRunning: boolean;
  timeSpeed: number;
  isPaused: boolean;
  godEntityId: string | null;
  godPhase: string;

  // Entities
  entities: Map<string, EntityV3>;
  selectedEntityId: string | null;

  // Voxel updates queue (for incremental sync)
  pendingVoxelUpdates: VoxelUpdate[];

  // Recent speech events
  recentSpeech: SocketSpeechEvent[];

  // Actions
  setWorldState: (state: Partial<WorldStateV3>) => void;
  updateTick: (data: { tickNumber: number; entityCount: number; voxelCount: number }) => void;

  setEntities: (entities: EntityV3[]) => void;
  updateEntityPositions: (positions: SocketEntityPosition[]) => void;
  addEntity: (entity: EntityV3) => void;
  removeEntity: (entityId: string) => void;
  selectEntity: (entityId: string | null) => void;
  getEntity: (entityId: string) => EntityV3 | undefined;

  addVoxelUpdates: (updates: VoxelUpdate[]) => void;
  clearVoxelUpdates: () => void;

  addSpeechEvent: (event: SocketSpeechEvent) => void;

  setPaused: (paused: boolean) => void;
  setTimeSpeed: (speed: number) => void;
}

export const useWorldStoreV3 = create<WorldStoreV3State>((set, get) => ({
  // Initial state
  tickNumber: 0,
  entityCount: 0,
  voxelCount: 0,
  isRunning: false,
  timeSpeed: 1.0,
  isPaused: false,
  godEntityId: null,
  godPhase: 'genesis',

  entities: new Map(),
  selectedEntityId: null,

  pendingVoxelUpdates: [],
  recentSpeech: [],

  // Actions
  setWorldState: (state) => set((prev) => ({
    tickNumber: state.tickNumber ?? prev.tickNumber,
    entityCount: state.entityCount ?? prev.entityCount,
    voxelCount: state.voxelCount ?? prev.voxelCount,
    isRunning: state.isRunning ?? prev.isRunning,
    timeSpeed: state.timeSpeed ?? prev.timeSpeed,
    isPaused: state.isPaused ?? prev.isPaused,
    godEntityId: state.godEntityId ?? prev.godEntityId,
    godPhase: state.godPhase ?? prev.godPhase,
  })),

  updateTick: (data) => set({
    tickNumber: data.tickNumber,
    entityCount: data.entityCount,
    voxelCount: data.voxelCount,
  }),

  setEntities: (entities) => {
    const map = new Map<string, EntityV3>();
    for (const entity of entities) {
      map.set(entity.id, entity);
    }
    set({ entities: map, entityCount: entities.length });
  },

  updateEntityPositions: (positions) => set((prev) => {
    const newMap = new Map(prev.entities);
    for (const pos of positions) {
      const existing = newMap.get(pos.id);
      if (existing) {
        newMap.set(pos.id, {
          ...existing,
          position: { x: pos.x, y: pos.y, z: pos.z },
          facing: { x: pos.fx || existing.facing.x, z: pos.fz || existing.facing.z },
          state: { ...existing.state, currentAction: pos.action },
        });
      }
    }
    return { entities: newMap };
  }),

  addEntity: (entity) => set((prev) => {
    const newMap = new Map(prev.entities);
    newMap.set(entity.id, entity);
    return { entities: newMap, entityCount: newMap.size };
  }),

  removeEntity: (entityId) => set((prev) => {
    const newMap = new Map(prev.entities);
    newMap.delete(entityId);
    return {
      entities: newMap,
      entityCount: newMap.size,
      selectedEntityId: prev.selectedEntityId === entityId ? null : prev.selectedEntityId,
    };
  }),

  selectEntity: (entityId) => set({ selectedEntityId: entityId }),

  getEntity: (entityId) => get().entities.get(entityId),

  addVoxelUpdates: (updates) => set((prev) => ({
    pendingVoxelUpdates: [...prev.pendingVoxelUpdates, ...updates],
  })),

  clearVoxelUpdates: () => set({ pendingVoxelUpdates: [] }),

  addSpeechEvent: (event) => set((prev) => ({
    recentSpeech: [...prev.recentSpeech.slice(-49), event],
  })),

  setPaused: (paused) => set({ isPaused: paused }),
  setTimeSpeed: (speed) => set({ timeSpeed: speed }),
}));
