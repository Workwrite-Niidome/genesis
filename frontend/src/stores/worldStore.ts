import { create } from 'zustand';
import { api } from '../services/api';

interface WorldStoreState {
  tickNumber: number;
  maxTick: number;
  seekTick: number | null;  // null = live (follow latest), number = viewing past tick
  aiCount: number;
  conceptCount: number;
  isRunning: boolean;
  timeSpeed: number;
  isPaused: boolean;
  godAiActive: boolean;
  godAiPhase: string;
  stats: {
    total_ticks: number;
    total_ais_born: number;
    total_ais_alive: number;
    total_concepts: number;
    total_interactions: number;
    total_events: number;
  } | null;
  fetchState: () => Promise<void>;
  fetchStats: () => Promise<void>;
  setTimeSpeed: (speed: number) => void;
  setPaused: (paused: boolean) => void;
  setTickNumber: (tick: number) => void;
  seekToTick: (tick: number | null) => void;
}

export const useWorldStore = create<WorldStoreState>((set) => ({
  tickNumber: 0,
  maxTick: 0,
  seekTick: null,
  aiCount: 0,
  conceptCount: 0,
  isRunning: false,
  timeSpeed: 1.0,
  isPaused: false,
  godAiActive: false,
  godAiPhase: 'pre_genesis',
  stats: null,

  fetchState: async () => {
    try {
      const data = await api.world.getState();
      const tick = data.tick_number ?? data.tick ?? 0;
      set({
        tickNumber: tick,
        maxTick: Math.max(tick, useWorldStore.getState().maxTick),
        aiCount: data.ai_count ?? data.alive_entity_count ?? 0,
        conceptCount: data.concept_count ?? 0,
        isRunning: data.is_running ?? true,
        timeSpeed: data.time_speed ?? 1.0,
        isPaused: data.is_paused ?? false,
        godAiActive: data.god_ai_active ?? false,
        godAiPhase: data.god_ai_phase ?? 'unknown',
      });
    } catch (e) {
      console.error('Failed to fetch world state:', e);
    }
  },

  fetchStats: async () => {
    try {
      const data = await api.world.getStats();
      set({ stats: data });
    } catch (e) {
      console.error('Failed to fetch stats:', e);
    }
  },

  setTimeSpeed: (speed) => {
    set({ timeSpeed: speed });
    api.world.setSpeed(speed).catch((e) =>
      console.error('Failed to set speed:', e)
    );
  },
  setPaused: (paused) => {
    set({ isPaused: paused });
    api.world.setPause(paused).catch((e) =>
      console.error('Failed to set pause:', e)
    );
  },
  setTickNumber: (tick: number) => set({ tickNumber: tick, maxTick: Math.max(tick, useWorldStore.getState().maxTick) }),
  seekToTick: (tick: number | null) => set({ seekTick: tick }),
}));
