import { create } from 'zustand';
import { api } from '../services/api';

interface WorldStoreState {
  tickNumber: number;
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
}

export const useWorldStore = create<WorldStoreState>((set) => ({
  tickNumber: 0,
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
      set({
        tickNumber: data.tick_number,
        aiCount: data.ai_count,
        conceptCount: data.concept_count,
        isRunning: data.is_running,
        timeSpeed: data.time_speed,
        isPaused: data.is_paused,
        godAiActive: data.god_ai_active,
        godAiPhase: data.god_ai_phase,
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

  setTimeSpeed: (speed) => set({ timeSpeed: speed }),
  setPaused: (paused) => set({ isPaused: paused }),
}));
