import { create } from 'zustand'

interface UIState {
  sidebarOpen: boolean
  postFormOpen: boolean
  searchModalOpen: boolean
  currentSubmolt: string | null
  sortBy: 'hot' | 'new' | 'top' | 'rising'

  toggleSidebar: () => void
  setSidebarOpen: (open: boolean) => void
  setPostFormOpen: (open: boolean) => void
  setSearchModalOpen: (open: boolean) => void
  toggleSearchModal: () => void
  setCurrentSubmolt: (submolt: string | null) => void
  setSortBy: (sort: 'hot' | 'new' | 'top' | 'rising') => void
}

export const useUIStore = create<UIState>((set) => ({
  sidebarOpen: false,
  postFormOpen: false,
  searchModalOpen: false,
  currentSubmolt: null,
  sortBy: 'hot',

  toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
  setSidebarOpen: (open) => set({ sidebarOpen: open }),
  setPostFormOpen: (open) => set({ postFormOpen: open }),
  setSearchModalOpen: (open) => set({ searchModalOpen: open }),
  toggleSearchModal: () => set((state) => ({ searchModalOpen: !state.searchModalOpen })),
  setCurrentSubmolt: (submolt) => set({ currentSubmolt: submolt }),
  setSortBy: (sort) => set({ sortBy: sort }),
}))
