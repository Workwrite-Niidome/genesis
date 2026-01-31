import { create } from 'zustand';

type Panel = 'info' | 'events' | 'stats' | 'god';

interface UIStore {
  sidebarOpen: boolean;
  chatOpen: boolean;
  activePanel: Panel;
  language: string;
  toggleSidebar: () => void;
  toggleChat: () => void;
  setPanel: (panel: Panel) => void;
  setLanguage: (lang: string) => void;
}

export const useUIStore = create<UIStore>((set) => ({
  sidebarOpen: true,
  chatOpen: false,
  activePanel: 'info',
  language: 'en',

  toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
  toggleChat: () => set((s) => ({ chatOpen: !s.chatOpen })),
  setPanel: (panel) => set({ activePanel: panel }),
  setLanguage: (lang) => set({ language: lang }),
}));
