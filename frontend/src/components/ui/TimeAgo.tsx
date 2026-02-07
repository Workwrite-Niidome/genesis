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

  const suffix = isFuture ? '後' : '前'

  if (diffSeconds < 5) {
    return 'たった今'
  } else if (diffSeconds < 60) {
    return `${diffSeconds}秒${suffix}`
  } else if (diffMinutes < 60) {
    return `${diffMinutes}分${suffix}`
  } else if (diffHours < 24) {
    return `${diffHours}時間${suffix}`
  } else if (diffDays < 7) {
    return `${diffDays}日${suffix}`
  } else if (diffWeeks < 5) {
    return `${diffWeeks}週間${suffix}`
  } else if (diffMonths < 12) {
    return `${diffMonths}ヶ月${suffix}`
  } else {
    return `${diffYears}年${suffix}`
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
  const [text, setText] = useState(() => formatRelativeTime(date))

  useEffect(() => {
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

  return (
    <time
      dateTime={date}
      title={new Date(date).toLocaleString('ja-JP')}
      className={className}
    >
      {text}
    </time>
  )
}

export { formatRelativeTime }
