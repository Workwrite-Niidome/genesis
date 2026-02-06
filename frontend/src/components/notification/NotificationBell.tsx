'use client'

import { useEffect, useRef, useState, useCallback } from 'react'
import Link from 'next/link'
import { Bell, Check, Loader2 } from 'lucide-react'
import { useNotificationStore } from '@/stores/notificationStore'
import { useAuthStore } from '@/stores/authStore'
import NotificationItem from './NotificationItem'
import Button from '@/components/ui/Button'

const POLL_INTERVAL = 30000 // 30 seconds

export default function NotificationBell() {
  const [isOpen, setIsOpen] = useState(false)
  const dropdownRef = useRef<HTMLDivElement>(null)
  const buttonRef = useRef<HTMLButtonElement>(null)

  const { resident } = useAuthStore()
  const {
    notifications,
    unreadCount,
    isLoading,
    fetchNotifications,
    fetchUnreadCount,
    markRead,
    markAllRead,
  } = useNotificationStore()

  // Fetch unread count on mount and poll
  useEffect(() => {
    if (!resident) return

    fetchUnreadCount()

    const interval = setInterval(() => {
      fetchUnreadCount()
    }, POLL_INTERVAL)

    return () => clearInterval(interval)
  }, [resident, fetchUnreadCount])

  // Fetch notifications when dropdown opens
  useEffect(() => {
    if (isOpen && resident) {
      fetchNotifications(false, 10, true)
    }
  }, [isOpen, resident, fetchNotifications])

  // Close dropdown on outside click
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node) &&
        buttonRef.current &&
        !buttonRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false)
      }
    }

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside)
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [isOpen])

  // Close dropdown on escape key
  useEffect(() => {
    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setIsOpen(false)
      }
    }

    if (isOpen) {
      document.addEventListener('keydown', handleEscape)
    }

    return () => {
      document.removeEventListener('keydown', handleEscape)
    }
  }, [isOpen])

  const handleToggle = useCallback(() => {
    setIsOpen((prev) => !prev)
  }, [])

  const handleMarkAllRead = useCallback(async () => {
    await markAllRead()
  }, [markAllRead])

  const handleNotificationClick = useCallback(() => {
    setIsOpen(false)
  }, [])

  if (!resident) {
    return null
  }

  return (
    <div className="relative">
      {/* Bell Button */}
      <button
        ref={buttonRef}
        onClick={handleToggle}
        className="relative p-2 text-text-secondary hover:text-text-primary hover:bg-bg-tertiary rounded-md transition-colors"
        aria-label="Notifications"
        aria-expanded={isOpen}
        aria-haspopup="true"
      >
        <Bell size={20} />

        {/* Unread Badge */}
        {unreadCount > 0 && (
          <span className="absolute -top-0.5 -right-0.5 min-w-[18px] h-[18px] flex items-center justify-center px-1 text-xs font-medium bg-accent-gold text-bg-primary rounded-full">
            {unreadCount > 99 ? '99+' : unreadCount}
          </span>
        )}
      </button>

      {/* Dropdown */}
      {isOpen && (
        <div
          ref={dropdownRef}
          className="absolute right-0 mt-2 w-80 sm:w-96 bg-bg-secondary border border-border-default rounded-lg shadow-xl z-50 overflow-hidden"
        >
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-border-default bg-bg-tertiary">
            <h3 className="font-medium text-text-primary">Notifications</h3>
            {unreadCount > 0 && (
              <button
                onClick={handleMarkAllRead}
                className="flex items-center gap-1 text-xs text-accent-gold hover:text-accent-gold-dim transition-colors"
              >
                <Check size={14} />
                <span>全て既読にする</span>
              </button>
            )}
          </div>

          {/* Notifications List */}
          <div className="max-h-[400px] overflow-y-auto">
            {isLoading && notifications.length === 0 ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="w-6 h-6 animate-spin text-text-muted" />
              </div>
            ) : notifications.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-8 text-text-muted">
                <Bell size={32} className="mb-2 opacity-50" />
                <p className="text-sm">No notifications yet</p>
              </div>
            ) : (
              <div>
                {notifications.slice(0, 10).map((notification) => (
                  <NotificationItem
                    key={notification.id}
                    notification={notification}
                    onRead={markRead}
                    onClick={handleNotificationClick}
                    compact
                  />
                ))}
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="px-4 py-3 border-t border-border-default bg-bg-tertiary">
            <Link
              href="/notifications"
              onClick={() => setIsOpen(false)}
              className="block w-full text-center text-sm text-accent-gold hover:text-accent-gold-dim transition-colors"
            >
              View all notifications
            </Link>
          </div>
        </div>
      )}
    </div>
  )
}
