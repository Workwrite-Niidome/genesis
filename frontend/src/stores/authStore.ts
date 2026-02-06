import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { api, Resident } from '@/lib/api'

interface AuthState {
  resident: Resident | null
  token: string | null
  isLoading: boolean
  error: string | null

  setToken: (token: string | null) => void
  fetchMe: () => Promise<void>
  logout: () => void
  clearError: () => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      resident: null,
      token: null,
      isLoading: false,
      error: null,

      setToken: (token) => {
        api.setToken(token)
        set({ token })
        if (token) {
          get().fetchMe()
        }
      },

      fetchMe: async () => {
        set({ isLoading: true, error: null })
        try {
          const resident = await api.getMe()
          set({ resident, isLoading: false })
        } catch (err) {
          set({
            error: err instanceof Error ? err.message : 'Failed to fetch profile',
            isLoading: false,
          })
        }
      },

      logout: () => {
        api.setToken(null)
        set({ resident: null, token: null })
      },

      clearError: () => set({ error: null }),
    }),
    {
      name: 'genesis-auth',
      partialize: (state) => ({ token: state.token }),
      onRehydrateStorage: () => (state) => {
        if (state?.token) {
          api.setToken(state.token)
          state.fetchMe()
        }
      },
    }
  )
)
