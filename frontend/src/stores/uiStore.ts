import { create } from 'zustand';

type Panel = 'info' | 'events' | 'stats' | 'god';

interface UIStore {
  sidebarOpen: boolean;
  chatOpen: boolean;
  activePanel: Panel;
  observerChatExpanded: boolean;
  showGrid: boolean;
  toggleSidebar: () => void;
  toggleChat: () => void;
  toggleObserverChat: () => void;
  toggleGrid: () => void;
  setPanel: (panel: Panel) => void;
}

export const useUIStore = create<UIStore>((set) => ({
  sidebarOpen: true,
  chatOpen: false,
  activePanel: 'info',
  observerChatExpanded: false,
  showGrid: true,

  toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
  toggleChat: () => set((s) => ({ chatOpen: !s.chatOpen })),
  toggleObserverChat: () => set((s) => ({ observerChatExpanded: !s.observerChatExpanded })),
  toggleGrid: () => set((s) => ({ showGrid: !s.showGrid })),
  setPanel: (panel) => set({ activePanel: panel }),
}));
