import { create } from 'zustand';
import { api } from '../services/api';
import type { AIThought } from '../types/world';

interface ThoughtStore {
  thoughts: AIThought[];
  isPolling: boolean;
  fetchFeed: () => Promise<void>;
  addThought: (thought: AIThought) => void;
  startPolling: () => void;
  stopPolling: () => void;
}

let pollInterval: ReturnType<typeof setInterval> | null = null;

export const useThoughtStore = create<ThoughtStore>((set, get) => ({
  thoughts: [],
  isPolling: false,

  fetchFeed: async () => {
    try {
      const data = await api.thoughts.getFeed(50);
      set({ thoughts: data });
    } catch (e) {
      console.error('Failed to fetch thought feed:', e);
    }
  },

  addThought: (thought) => {
    set((s) => ({
      thoughts: [thought, ...s.thoughts].slice(0, 50),
    }));
  },

  startPolling: () => {
    if (get().isPolling) return;
    set({ isPolling: true });
    // Initial fetch
    get().fetchFeed();
    // Poll every 4 seconds
    pollInterval = setInterval(() => {
      get().fetchFeed();
    }, 4000);
  },

  stopPolling: () => {
    if (pollInterval) {
      clearInterval(pollInterval);
      pollInterval = null;
    }
    set({ isPolling: false });
  },
}));
