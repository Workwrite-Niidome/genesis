import { create } from 'zustand';
import type { SagaChapter } from '../types/world';
import { api } from '../services/api';

interface SagaStore {
  chapters: SagaChapter[];
  selectedChapter: SagaChapter | null;
  loading: boolean;
  hasNewChapter: boolean;
  fetchChapters: () => Promise<void>;
  selectChapter: (chapter: SagaChapter | null) => void;
  onNewChapter: (chapter: SagaChapter) => void;
  clearNewFlag: () => void;
}

export const useSagaStore = create<SagaStore>((set, get) => ({
  chapters: [],
  selectedChapter: null,
  loading: false,
  hasNewChapter: false,

  fetchChapters: async () => {
    set({ loading: true });
    try {
      const data = await api.saga.getChapters();
      set({ chapters: Array.isArray(data) ? data : [], loading: false });
    } catch {
      set({ chapters: [], loading: false });
    }
  },

  selectChapter: (chapter) => {
    set({ selectedChapter: chapter, hasNewChapter: false });
  },

  onNewChapter: (chapter) => {
    set((state) => ({
      chapters: [chapter, ...state.chapters.filter((c) => c.era_number !== chapter.era_number)],
      hasNewChapter: true,
    }));
  },

  clearNewFlag: () => {
    set({ hasNewChapter: false });
  },
}));
