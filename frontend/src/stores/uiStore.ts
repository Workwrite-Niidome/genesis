import { create } from 'zustand';

type Panel = 'info' | 'events' | 'stats' | 'god';
export type MobileTab = 'world' | 'ranking' | 'feed' | 'archive' | 'more';

interface UIStore {
  sidebarOpen: boolean;
  chatOpen: boolean;
  activePanel: Panel;
  observerChatExpanded: boolean;
  showGrid: boolean;
  showArchive: boolean;

  // Mobile state
  mobileActiveTab: MobileTab;
  mobileDetailOpen: boolean;
  mobilePanelContent: string | null;

  toggleSidebar: () => void;
  toggleChat: () => void;
  toggleObserverChat: () => void;
  toggleGrid: () => void;
  toggleArchive: () => void;
  setPanel: (panel: Panel) => void;

  // Mobile actions
  setMobileTab: (tab: MobileTab) => void;
  setMobileDetailOpen: (open: boolean) => void;
  setMobilePanelContent: (content: string | null) => void;
}

export const useUIStore = create<UIStore>((set) => ({
  sidebarOpen: true,
  chatOpen: false,
  activePanel: 'info',
  observerChatExpanded: false,
  showGrid: true,
  showArchive: false,

  // Mobile state
  mobileActiveTab: 'world',
  mobileDetailOpen: false,
  mobilePanelContent: null,

  toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
  toggleChat: () => set((s) => ({ chatOpen: !s.chatOpen })),
  toggleObserverChat: () => set((s) => ({ observerChatExpanded: !s.observerChatExpanded })),
  toggleGrid: () => set((s) => ({ showGrid: !s.showGrid })),
  toggleArchive: () => set((s) => ({ showArchive: !s.showArchive })),
  setPanel: (panel) => set({ activePanel: panel }),

  // Mobile actions
  setMobileTab: (tab) => set({ mobileActiveTab: tab, mobileDetailOpen: false, mobilePanelContent: null }),
  setMobileDetailOpen: (open) => set({ mobileDetailOpen: open }),
  setMobilePanelContent: (content) => set({ mobilePanelContent: content }),
}));
