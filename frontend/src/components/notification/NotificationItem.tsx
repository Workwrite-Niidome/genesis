'use client'

import { useRouter } from 'next/navigation'
import clsx from 'clsx'
import {
  Bell,
  UserPlus,
  ThumbsUp,
  ThumbsDown,
  MessageCircle,
  Crown,
  Star,
  AlertTriangle,
  AtSign,
  Heart,
} from 'lucide-react'
import Avatar from '@/components/ui/Avatar'
import { Notification } from '@/lib/api'

interface NotificationItemProps {
  notification: Notification
  onRead?: (id: string) => void
  onClick?: () => void
  compact?: boolean
}

// Format relative time in Japanese
function formatRelativeTime(dateString: string): string {
  const date = new Date(dateString)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffSeconds = Math.floor(diffMs / 1000)
  const diffMinutes = Math.floor(diffSeconds / 60)
  const diffHours = Math.floor(diffMinutes / 60)
  const diffDays = Math.floor(diffHours / 24)
  const diffWeeks = Math.floor(diffDays / 7)
  const diffMonths = Math.floor(diffDays / 30)

  if (diffSeconds < 60) {
    return 'たった今'
  } else if (diffMinutes < 60) {
    return `${diffMinutes}分前`
  } else if (diffHours < 24) {
    return `${diffHours}時間前`
  } else if (diffDays < 7) {
    return `${diffDays}日前`
  } else if (diffWeeks < 4) {
    return `${diffWeeks}週間前`
  } else {
    return `${diffMonths}ヶ月前`
  }
}

// Get icon based on notification type
function getNotificationIcon(type: string) {
  const iconProps = { size: 16 }

  switch (type) {
    case 'follow':
      return <UserPlus {...iconProps} className="text-blue-400" />
    case 'upvote':
      return <ThumbsUp {...iconProps} className="text-green-400" />
    case 'downvote':
      return <ThumbsDown {...iconProps} className="text-red-400" />
    case 'comment':
    case 'reply':
      return <MessageCircle {...iconProps} className="text-purple-400" />
    case 'mention':
      return <AtSign {...iconProps} className="text-cyan-400" />
    case 'election':
    case 'god':
      return <Crown {...iconProps} className="text-accent-gold" />
    case 'blessing':
      return <Star {...iconProps} className="text-accent-gold" />
    case 'like':
      return <Heart {...iconProps} className="text-pink-400" />
    case 'warning':
    case 'moderation':
      return <AlertTriangle {...iconProps} className="text-orange-400" />
    default:
      return <Bell {...iconProps} className="text-text-muted" />
  }
}

export default function NotificationItem({
  notification,
  onRead,
  onClick,
  compact = false,
}: NotificationItemProps) {
  const router = useRouter()

  const handleClick = () => {
    // Mark as read if unread
    if (!notification.is_read && onRead) {
      onRead(notification.id)
    }

    // Navigate to link if available
    if (notification.link) {
      router.push(notification.link)
    }

    // Call optional onClick handler
    onClick?.()
  }

  return (
    <div
      onClick={handleClick}
      className={clsx(
        'flex items-start gap-3 p-3 cursor-pointer transition-colors',
        'hover:bg-bg-tertiary',
        !notification.is_read && 'bg-bg-tertiary/50',
        compact ? 'border-b border-border-default last:border-b-0' : 'rounded-lg'
      )}
    >
      {/* Unread indicator */}
      <div className="flex-shrink-0 mt-1.5">
        {!notification.is_read ? (
          <div className="w-2 h-2 rounded-full bg-accent-gold" />
        ) : (
          <div className="w-2 h-2" />
        )}
      </div>

      {/* Actor avatar or type icon */}
      <div className="flex-shrink-0">
        {notification.actor ? (
          <Avatar
            name={notification.actor.name}
            src={notification.actor.avatar_url}
            size="sm"
          />
        ) : (
          <div className="w-6 h-6 rounded-full bg-bg-tertiary flex items-center justify-center">
            {getNotificationIcon(notification.type)}
          </div>
        )}
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-start justify-between gap-2">
          <div className="flex-1 min-w-0">
            <p
              className={clsx(
                'text-sm leading-snug',
                notification.is_read ? 'text-text-secondary' : 'text-text-primary'
              )}
            >
              {notification.title}
            </p>
            {notification.message && !compact && (
              <p className="text-xs text-text-muted mt-0.5 line-clamp-2">
                {notification.message}
              </p>
            )}
          </div>

          {/* Type icon (when actor avatar is shown) */}
          {notification.actor && (
            <div className="flex-shrink-0">
              {getNotificationIcon(notification.type)}
            </div>
          )}
        </div>

        {/* Time */}
        <p className="text-xs text-text-muted mt-1">
          {formatRelativeTime(notification.created_at)}
        </p>
      </div>
    </div>
  )
}
