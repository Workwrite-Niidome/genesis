import { create } from 'zustand';

type Panel = 'info' | 'events' | 'stats' | 'god';

interface UIStore {
  sidebarOpen: boolean;
  chatOpen: boolean;
  activePanel: Panel;
  observerChatExpanded: boolean;
  showGrid: boolean;
  showArchive: boolean;
  toggleSidebar: () => void;
  toggleChat: () => void;
  toggleObserverChat: () => void;
  toggleGrid: () => void;
  toggleArchive: () => void;
  setPanel: (panel: Panel) => void;
}

export const useUIStore = create<UIStore>((set) => ({
  sidebarOpen: true,
  chatOpen: false,
  activePanel: 'info',
  observerChatExpanded: false,
  showGrid: true,
  showArchive: false,

  toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
  toggleChat: () => set((s) => ({ chatOpen: !s.chatOpen })),
  toggleObserverChat: () => set((s) => ({ observerChatExpanded: !s.observerChatExpanded })),
  toggleGrid: () => set((s) => ({ showGrid: !s.showGrid })),
  toggleArchive: () => set((s) => ({ showArchive: !s.showArchive })),
  setPanel: (panel) => set({ activePanel: panel }),
}));
