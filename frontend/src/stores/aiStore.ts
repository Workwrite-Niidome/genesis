import { create } from 'zustand';
import { api } from '../services/api';
import type { AIEntity, AIMemory } from '../types/world';

interface AIStore {
  ais: AIEntity[];
  selectedAI: AIEntity | null;
  selectedMemories: AIMemory[];
  fetchAIs: () => Promise<void>;
  selectAI: (id: string | null) => Promise<void>;
  updateAI: (ai: Partial<AIEntity> & { id: string }) => void;
  addAI: (ai: AIEntity) => void;
  removeAI: (id: string) => void;
}

export const useAIStore = create<AIStore>((set) => ({
  ais: [],
  selectedAI: null,
  selectedMemories: [],

  fetchAIs: async () => {
    try {
      const data = await api.ais.list();
      set({ ais: data });
    } catch (e) {
      console.error('Failed to fetch AIs:', e);
    }
  },

  selectAI: async (id) => {
    if (!id) {
      set({ selectedAI: null, selectedMemories: [] });
      return;
    }
    try {
      const [ai, memories] = await Promise.all([
        api.ais.get(id),
        api.ais.getMemories(id),
      ]);
      set({ selectedAI: ai, selectedMemories: memories });
    } catch (e) {
      console.error('Failed to fetch AI details:', e);
    }
  },

  updateAI: (update) => {
    set((s) => ({
      ais: s.ais.map((ai) => (ai.id === update.id ? { ...ai, ...update } : ai)),
      selectedAI:
        s.selectedAI?.id === update.id
          ? { ...s.selectedAI, ...update }
          : s.selectedAI,
    }));
  },

  addAI: (ai) => set((s) => ({ ais: [...s.ais, ai] })),
  removeAI: (id) => set((s) => ({ ais: s.ais.filter((a) => a.id !== id) })),
}));
