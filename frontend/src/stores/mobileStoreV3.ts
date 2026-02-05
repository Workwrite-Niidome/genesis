/**
 * Mobile-only UI state store for GENESIS v3.
 *
 * Manages tab navigation, bottom-sheet states, overlay visibility,
 * and hamburger menu state — all mobile-specific concerns that
 * never affect the desktop layout.
 */
import { create } from 'zustand';

export type MobileV3Tab = 'world' | 'entities' | 'events' | 'chat' | 'more';
export type SheetState = 'closed' | 'peek' | 'half' | 'full';

interface MobileStoreV3State {
  // Tab navigation
  activeTab: MobileV3Tab;
  setActiveTab: (tab: MobileV3Tab) => void;

  // Entity detail bottom sheet
  entitySheetState: SheetState;
  setEntitySheetState: (state: SheetState) => void;

  // Build tool bottom sheet
  buildSheetState: SheetState;
  setBuildSheetState: (state: SheetState) => void;

  // Full-screen overlays
  godChatOpen: boolean;
  setGodChatOpen: (open: boolean) => void;
  timelineOpen: boolean;
  setTimelineOpen: (open: boolean) => void;

  // Hamburger menu
  menuOpen: boolean;
  setMenuOpen: (open: boolean) => void;

  // MiniMap toggle
  miniMapVisible: boolean;
  setMiniMapVisible: (visible: boolean) => void;
}

export const useMobileStoreV3 = create<MobileStoreV3State>((set) => ({
  activeTab: 'world',
  setActiveTab: (tab) => set({ activeTab: tab }),

  entitySheetState: 'closed',
  setEntitySheetState: (state) => set({ entitySheetState: state }),

  buildSheetState: 'closed',
  setBuildSheetState: (state) => set({ buildSheetState: state }),

  godChatOpen: false,
  setGodChatOpen: (open) => set({ godChatOpen: open }),
  timelineOpen: false,
  setTimelineOpen: (open) => set({ timelineOpen: open }),

  menuOpen: false,
  setMenuOpen: (open) => set({ menuOpen: open }),

  miniMapVisible: false,
  setMiniMapVisible: (visible) => set({ miniMapVisible: visible }),
}));
