import { create } from 'zustand'
import { api, Notification } from '@/lib/api'

interface NotificationState {
  notifications: Notification[]
  unreadCount: number
  isLoading: boolean
  error: string | null
  hasMore: boolean
  offset: number

  fetchNotifications: (unreadOnly?: boolean, limit?: number, reset?: boolean) => Promise<void>
  fetchUnreadCount: () => Promise<void>
  markRead: (id: string) => Promise<void>
  markAllRead: () => Promise<void>
  deleteNotification: (id: string) => Promise<void>
  clearError: () => void
}

export const useNotificationStore = create<NotificationState>((set, get) => ({
  notifications: [],
  unreadCount: 0,
  isLoading: false,
  error: null,
  hasMore: true,
  offset: 0,

  fetchNotifications: async (unreadOnly = false, limit = 20, reset = false) => {
    const currentOffset = reset ? 0 : get().offset
    set({ isLoading: true, error: null })

    try {
      const response = await api.getNotifications(unreadOnly, limit, currentOffset)
      set((state) => ({
        notifications: reset
          ? response.notifications
          : [...state.notifications, ...response.notifications],
        hasMore: response.has_more,
        offset: currentOffset + response.notifications.length,
        isLoading: false,
      }))
    } catch (err) {
      set({
        error: err instanceof Error ? err.message : 'Failed to fetch notifications',
        isLoading: false,
      })
    }
  },

  fetchUnreadCount: async () => {
    try {
      const response = await api.getUnreadCount()
      set({ unreadCount: response.count })
    } catch (err) {
      // Silently fail for count updates
      console.error('Failed to fetch unread count:', err)
    }
  },

  markRead: async (id: string) => {
    try {
      await api.markNotificationRead(id)
      set((state) => ({
        notifications: state.notifications.map((n) =>
          n.id === id ? { ...n, is_read: true } : n
        ),
        unreadCount: Math.max(0, state.unreadCount - 1),
      }))
    } catch (err) {
      set({
        error: err instanceof Error ? err.message : 'Failed to mark notification as read',
      })
    }
  },

  markAllRead: async () => {
    try {
      await api.markAllNotificationsRead()
      set((state) => ({
        notifications: state.notifications.map((n) => ({ ...n, is_read: true })),
        unreadCount: 0,
      }))
    } catch (err) {
      set({
        error: err instanceof Error ? err.message : 'Failed to mark all as read',
      })
    }
  },

  deleteNotification: async (id: string) => {
    try {
      await api.deleteNotification(id)
      set((state) => {
        const notification = state.notifications.find((n) => n.id === id)
        const wasUnread = notification && !notification.is_read
        return {
          notifications: state.notifications.filter((n) => n.id !== id),
          unreadCount: wasUnread ? Math.max(0, state.unreadCount - 1) : state.unreadCount,
        }
      })
    } catch (err) {
      set({
        error: err instanceof Error ? err.message : 'Failed to delete notification',
      })
    }
  },

  clearError: () => set({ error: null }),
}))
