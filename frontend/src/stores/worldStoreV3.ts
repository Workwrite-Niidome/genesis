/**
 * GENESIS v3 World Store (Zustand)
 *
 * Manages 3D world state: entities, voxels, world metadata.
 */
import { create } from 'zustand';
import { getSocket } from '../services/socket';
import { api } from '../services/api';
import type {
  EntityV3, Voxel, VoxelUpdate, WorldStateV3,
  SocketEntityPosition, SocketSpeechEvent,
} from '../types/v3';
import type { SagaChapter } from '../types/world';

// ── Real-time event feed types ──────────────────────────────
export interface WorldEvent {
  id: string;
  type: 'conflict' | 'speech' | 'death' | 'god_crisis' | 'god_observation' | 'god_succession';
  tick: number;
  timestamp: number;
  data: any;
}

export interface SuccessionEvent {
  candidate: string;
  worthy: boolean;
  tick: number;
}

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

  // Real-time event feed (last 50)
  recentEvents: WorldEvent[];

  // God succession ceremony
  successionEvent: SuccessionEvent | null;

  // Timeline / Archive data
  sagas: SagaChapter[];
  timelineEvents: Array<{
    id: string;
    event_type: string;
    importance: number;
    title: string;
    description?: string;
    tick_number: number;
    created_at: string;
    metadata_?: Record<string, any>;
  }>;
  timelineLoading: boolean;

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

  addEvent: (event: WorldEvent) => void;

  setSuccessionEvent: (event: SuccessionEvent) => void;
  clearSuccessionEvent: () => void;

  setPaused: (paused: boolean) => void;
  setTimeSpeed: (speed: number) => void;

  // Timeline / Archive actions
  fetchSagas: () => Promise<void>;
  fetchTimeline: (page?: number) => Promise<void>;
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
  recentEvents: [],
  successionEvent: null,
  sagas: [],
  timelineEvents: [],
  timelineLoading: false,

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

  removeEntity: (entityId) => {
    const prev = get();
    const newMap = new Map(prev.entities);
    newMap.delete(entityId);
    // If the removed entity was selected, emit observer_unfocus
    if (prev.selectedEntityId === entityId) {
      const socket = getSocket();
      if (socket?.connected) {
        socket.emit('observer_unfocus', {});
      }
    }
    set({
      entities: newMap,
      entityCount: newMap.size,
      selectedEntityId: prev.selectedEntityId === entityId ? null : prev.selectedEntityId,
    });
  },

  selectEntity: (entityId) => {
    const prev = get().selectedEntityId;
    // Emit observer tracking events via Socket.IO
    const socket = getSocket();
    if (socket?.connected) {
      // Unfocus the previously selected entity (if any)
      if (prev !== null) {
        socket.emit('observer_unfocus', {});
      }
      // Focus the newly selected entity (if any)
      if (entityId !== null) {
        socket.emit('observer_focus', { entity_id: entityId });
      }
    }
    set({ selectedEntityId: entityId });
  },

  getEntity: (entityId) => get().entities.get(entityId),

  addVoxelUpdates: (updates) => set((prev) => ({
    pendingVoxelUpdates: [...prev.pendingVoxelUpdates, ...updates],
  })),

  clearVoxelUpdates: () => set({ pendingVoxelUpdates: [] }),

  addSpeechEvent: (event) => set((prev) => ({
    recentSpeech: [...prev.recentSpeech.slice(-49), event],
  })),

  addEvent: (event) => set((prev) => ({
    recentEvents: [...prev.recentEvents.slice(-49), event],
  })),

  setSuccessionEvent: (event) => set({ successionEvent: event }),
  clearSuccessionEvent: () => set({ successionEvent: null }),

  setPaused: (paused) => set({ isPaused: paused }),
  setTimeSpeed: (speed) => set({ timeSpeed: speed }),

  // Timeline / Archive actions
  fetchSagas: async () => {
    try {
      const data = await api.saga.getChapters(50);
      set({ sagas: Array.isArray(data) ? data : [] });
    } catch {
      set({ sagas: [] });
    }
  },

  fetchTimeline: async (page = 1) => {
    set({ timelineLoading: true });
    try {
      const limit = page * 50;
      const data = await api.history.getTimeline(limit);
      const normalized = (data || []).map((raw: any) => ({
        id: raw.id,
        event_type: raw.event_type || raw.type || 'unknown',
        importance: raw.importance ?? 0.5,
        title: raw.title || '',
        description: raw.description,
        tick_number: raw.tick_number ?? 0,
        created_at: raw.created_at || raw.timestamp || '',
        metadata_: raw.metadata_ || {},
      }));
      set({ timelineEvents: normalized, timelineLoading: false });
    } catch {
      set({ timelineEvents: [], timelineLoading: false });
    }
  },
}));
