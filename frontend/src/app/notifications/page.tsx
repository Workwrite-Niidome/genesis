'use client'

import { useEffect, useState, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { Bell, Check, Loader2, Trash2, Filter } from 'lucide-react'
import { useAuthStore } from '@/stores/authStore'
import { useNotificationStore } from '@/stores/notificationStore'
import NotificationItem from '@/components/notification/NotificationItem'
import Button from '@/components/ui/Button'
import Card from '@/components/ui/Card'

const NOTIFICATION_TYPES = [
  { value: '', label: 'All' },
  { value: 'follow', label: 'Follows' },
  { value: 'upvote', label: 'Upvotes' },
  { value: 'comment', label: 'Comments' },
  { value: 'reply', label: 'Replies' },
  { value: 'mention', label: 'Mentions' },
  { value: 'moderation', label: 'Moderation' },
]

export default function NotificationsPage() {
  const router = useRouter()
  const { resident } = useAuthStore()
  const {
    notifications,
    unreadCount,
    isLoading,
    hasMore,
    error,
    fetchNotifications,
    markRead,
    markAllRead,
    deleteNotification,
    clearError,
  } = useNotificationStore()

  const [filterType, setFilterType] = useState('')
  const [showFilterMenu, setShowFilterMenu] = useState(false)
  const [deletingId, setDeletingId] = useState<string | null>(null)

  // Redirect if not authenticated
  useEffect(() => {
    if (!resident) {
      router.push('/auth')
    }
  }, [resident, router])

  // Fetch notifications on mount and filter change
  useEffect(() => {
    if (resident) {
      fetchNotifications(false, 20, true)
    }
  }, [resident, fetchNotifications])

  const handleLoadMore = useCallback(() => {
    if (!isLoading && hasMore) {
      fetchNotifications(false, 20, false)
    }
  }, [isLoading, hasMore, fetchNotifications])

  const handleMarkAllRead = useCallback(async () => {
    await markAllRead()
  }, [markAllRead])

  const handleDelete = useCallback(
    async (id: string, e: React.MouseEvent) => {
      e.stopPropagation()
      setDeletingId(id)
      await deleteNotification(id)
      setDeletingId(null)
    },
    [deleteNotification]
  )

  // Filter notifications by type
  const filteredNotifications = filterType
    ? notifications.filter((n) => n.type === filterType)
    : notifications

  if (!resident) {
    return null
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-text-primary">Notifications</h1>
          <p className="text-sm text-text-muted mt-1">
            {unreadCount > 0
              ? `${unreadCount} unread notification${unreadCount > 1 ? 's' : ''}`
              : 'All caught up!'}
          </p>
        </div>

        <div className="flex items-center gap-2">
          {/* Filter Button */}
          <div className="relative">
            <Button
              variant="secondary"
              size="sm"
              onClick={() => setShowFilterMenu(!showFilterMenu)}
              className="flex items-center gap-1"
            >
              <Filter size={16} />
              <span className="hidden sm:inline">Filter</span>
              {filterType && (
                <span className="ml-1 px-1.5 py-0.5 text-xs bg-accent-gold/20 text-accent-gold rounded">
                  {NOTIFICATION_TYPES.find((t) => t.value === filterType)?.label}
                </span>
              )}
            </Button>

            {showFilterMenu && (
              <div className="absolute right-0 mt-2 w-40 bg-bg-secondary border border-border-default rounded-lg shadow-xl z-10 overflow-hidden">
                {NOTIFICATION_TYPES.map((type) => (
                  <button
                    key={type.value}
                    onClick={() => {
                      setFilterType(type.value)
                      setShowFilterMenu(false)
                    }}
                    className={`w-full text-left px-4 py-2 text-sm transition-colors ${
                      filterType === type.value
                        ? 'bg-accent-gold/20 text-accent-gold'
                        : 'text-text-secondary hover:bg-bg-tertiary hover:text-text-primary'
                    }`}
                  >
                    {type.label}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Mark All Read Button */}
          {unreadCount > 0 && (
            <Button
              variant="primary"
              size="sm"
              onClick={handleMarkAllRead}
              className="flex items-center gap-1"
            >
              <Check size={16} />
              <span className="hidden sm:inline">Mark all read</span>
            </Button>
          )}
        </div>
      </div>

      {/* Error Message */}
      {error && (
        <Card className="p-4 border-red-500/50 bg-red-500/10">
          <div className="flex items-center justify-between">
            <p className="text-sm text-red-400">{error}</p>
            <button
              onClick={clearError}
              className="text-xs text-red-400 hover:text-red-300"
            >
              Dismiss
            </button>
          </div>
        </Card>
      )}

      {/* Notifications List */}
      <Card className="divide-y divide-border-default overflow-hidden">
        {isLoading && notifications.length === 0 ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-8 h-8 animate-spin text-text-muted" />
          </div>
        ) : filteredNotifications.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-text-muted">
            <Bell size={48} className="mb-4 opacity-50" />
            <p className="text-lg font-medium">No notifications</p>
            <p className="text-sm mt-1">
              {filterType
                ? `No ${NOTIFICATION_TYPES.find((t) => t.value === filterType)?.label.toLowerCase()} notifications yet`
                : "You're all caught up!"}
            </p>
          </div>
        ) : (
          <>
            {filteredNotifications.map((notification) => (
              <div
                key={notification.id}
                className="relative group"
              >
                <NotificationItem
                  notification={notification}
                  onRead={markRead}
                />

                {/* Delete Button */}
                <button
                  onClick={(e) => handleDelete(notification.id, e)}
                  disabled={deletingId === notification.id}
                  className="absolute right-3 top-1/2 -translate-y-1/2 p-2 text-text-muted hover:text-red-400 hover:bg-red-500/10 rounded opacity-0 group-hover:opacity-100 transition-all disabled:opacity-50"
                  aria-label="Delete notification"
                >
                  {deletingId === notification.id ? (
                    <Loader2 size={16} className="animate-spin" />
                  ) : (
                    <Trash2 size={16} />
                  )}
                </button>
              </div>
            ))}

            {/* Load More Button */}
            {hasMore && !filterType && (
              <div className="p-4">
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={handleLoadMore}
                  isLoading={isLoading}
                  className="w-full"
                >
                  Load more
                </Button>
              </div>
            )}
          </>
        )}
      </Card>
    </div>
  )
}
