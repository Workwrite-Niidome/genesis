'use client'

import { useState, useEffect } from 'react'

function formatRelativeTime(dateString: string): string {
  const date = new Date(dateString)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const isFuture = diffMs < 0
  const absDiffMs = Math.abs(diffMs)
  const diffSeconds = Math.floor(absDiffMs / 1000)
  const diffMinutes = Math.floor(diffSeconds / 60)
  const diffHours = Math.floor(diffMinutes / 60)
  const diffDays = Math.floor(diffHours / 24)
  const diffWeeks = Math.floor(diffDays / 7)
  const diffMonths = Math.floor(diffDays / 30)
  const diffYears = Math.floor(diffDays / 365)

  if (diffSeconds < 5) {
    return 'just now'
  } else if (diffSeconds < 60) {
    return isFuture ? `in ${diffSeconds}s` : `${diffSeconds}s ago`
  } else if (diffMinutes < 60) {
    return isFuture ? `in ${diffMinutes}m` : `${diffMinutes}m ago`
  } else if (diffHours < 24) {
    return isFuture ? `in ${diffHours}h` : `${diffHours}h ago`
  } else if (diffDays < 7) {
    return isFuture ? `in ${diffDays}d` : `${diffDays}d ago`
  } else if (diffWeeks < 5) {
    return isFuture ? `in ${diffWeeks}w` : `${diffWeeks}w ago`
  } else if (diffMonths < 12) {
    return isFuture ? `in ${diffMonths}mo` : `${diffMonths}mo ago`
  } else {
    return isFuture ? `in ${diffYears}y` : `${diffYears}y ago`
  }
}

function getUpdateInterval(dateString: string): number {
  const date = new Date(dateString)
  const now = new Date()
  const diffSeconds = Math.floor(Math.abs(now.getTime() - date.getTime()) / 1000)

  if (diffSeconds < 60) return 1000        // update every 1s when < 1min
  if (diffSeconds < 3600) return 30000      // update every 30s when < 1hr
  if (diffSeconds < 86400) return 60000     // update every 1min when < 1day
  return 300000                              // update every 5min otherwise
}

interface TimeAgoProps {
  date: string
  className?: string
}

export default function TimeAgo({ date, className }: TimeAgoProps) {
  const [text, setText] = useState('')
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    setMounted(true)
    setText(formatRelativeTime(date))

    let timerId: ReturnType<typeof setTimeout>

    const tick = () => {
      setText(formatRelativeTime(date))
      const interval = getUpdateInterval(date)
      timerId = setTimeout(tick, interval)
    }

    const interval = getUpdateInterval(date)
    timerId = setTimeout(tick, interval)

    return () => clearTimeout(timerId)
  }, [date])

  if (!mounted) {
    return <span className={className}>&nbsp;</span>
  }

  return (
    <time
      dateTime={date}
      title={new Date(date).toLocaleString()}
      className={className}
    >
      {text}
    </time>
  )
}

export { formatRelativeTime }
