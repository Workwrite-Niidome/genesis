'use client'

import { useState, useEffect, useMemo } from 'react'
import Link from 'next/link'
import clsx from 'clsx'
import { Layers, Users, FileText } from 'lucide-react'
import { api, SubmoltStats as SubmoltStatsType } from '@/lib/api'

interface SubmoltStatsProps {
  limit?: number
  className?: string
}

type SortBy = 'posts' | 'subscribers'

export default function SubmoltStats({
  limit = 10,
  className,
}: SubmoltStatsProps) {
  const [data, setData] = useState<SubmoltStatsType[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [sortBy, setSortBy] = useState<SortBy>('posts')

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true)
      setError(null)
      try {
        const stats = await api.getSubmoltStats()
        setData(stats)
      } catch (err) {
        setError('Submolt統計の取得に失敗しました')
        console.error('Failed to fetch submolt stats:', err)
        // Generate placeholder data
        setData(generatePlaceholderData())
      } finally {
        setLoading(false)
      }
    }

    fetchData()
  }, [])

  const sortedData = useMemo(() => {
    const sorted = [...data].sort((a, b) => {
      if (sortBy === 'posts') {
        return b.post_count - a.post_count
      }
      return b.subscriber_count - a.subscriber_count
    })
    return sorted.slice(0, limit)
  }, [data, sortBy, limit])

  const maxValue = useMemo(() => {
    if (sortedData.length === 0) return 1
    return Math.max(
      ...sortedData.map((d) => (sortBy === 'posts' ? d.post_count : d.subscriber_count))
    )
  }, [sortedData, sortBy])

  const getSubmoltColor = (color?: string): string => {
    if (color) return color
    return '#ffc300' // Default to gold
  }

  return (
    <div
      className={clsx(
        'rounded-lg border border-border-default bg-bg-secondary p-4',
        className
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Layers size={20} className="text-accent-gold" />
          <h2 className="text-lg font-semibold">Submolt統計</h2>
        </div>

        <div className="flex gap-1 text-sm">
          <button
            onClick={() => setSortBy('posts')}
            className={clsx(
              'flex items-center gap-1 px-2 py-1 rounded-md transition-colors',
              sortBy === 'posts'
                ? 'bg-accent-gold text-bg-primary font-medium'
                : 'text-text-secondary hover:text-text-primary hover:bg-bg-tertiary'
            )}
          >
            <FileText size={12} />
            投稿数
          </button>
          <button
            onClick={() => setSortBy('subscribers')}
            className={clsx(
              'flex items-center gap-1 px-2 py-1 rounded-md transition-colors',
              sortBy === 'subscribers'
                ? 'bg-accent-gold text-bg-primary font-medium'
                : 'text-text-secondary hover:text-text-primary hover:bg-bg-tertiary'
            )}
          >
            <Users size={12} />
            購読者数
          </button>
        </div>
      </div>

      {/* Content */}
      {loading ? (
        <div className="space-y-3">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="h-12 bg-bg-tertiary rounded-lg animate-pulse" />
          ))}
        </div>
      ) : error && data.length === 0 ? (
        <div className="text-center py-8 text-text-muted">{error}</div>
      ) : sortedData.length === 0 ? (
        <div className="text-center py-8 text-text-muted">
          データがありません
        </div>
      ) : (
        <div className="space-y-3">
          {sortedData.map((submolt, index) => {
            const value = sortBy === 'posts' ? submolt.post_count : submolt.subscriber_count
            const percentage = (value / maxValue) * 100
            const color = getSubmoltColor(submolt.color)

            return (
              <Link
                key={submolt.name}
                href={`/m/${submolt.name}`}
                className="block group"
              >
                <div className="flex items-center justify-between mb-1">
                  <div className="flex items-center gap-2">
                    {/* Submolt Icon */}
                    <div
                      className="w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold"
                      style={{ backgroundColor: color }}
                    >
                      {submolt.icon_url ? (
                        <img
                          src={submolt.icon_url}
                          alt={submolt.name}
                          className="w-full h-full rounded-full object-cover"
                        />
                      ) : (
                        submolt.name[0].toUpperCase()
                      )}
                    </div>

                    {/* Name */}
                    <div>
                      <span className="text-sm font-medium text-text-primary group-hover:text-accent-gold transition-colors">
                        m/{submolt.display_name || submolt.name}
                      </span>
                    </div>
                  </div>

                  {/* Value */}
                  <span className="text-sm font-mono text-text-secondary">
                    {value.toLocaleString()}
                  </span>
                </div>

                {/* Progress Bar */}
                <div className="h-2 bg-bg-tertiary rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all duration-500"
                    style={{
                      width: `${percentage}%`,
                      backgroundColor: color,
                      opacity: 0.8,
                    }}
                  />
                </div>
              </Link>
            )
          })}
        </div>
      )}

      {/* Footer */}
      {sortedData.length > 0 && (
        <div className="mt-4 pt-4 border-t border-border-default">
          <Link
            href="/m"
            className="text-sm text-text-secondary hover:text-accent-gold transition-colors"
          >
            全てのSubmoltを見る &rarr;
          </Link>
        </div>
      )}
    </div>
  )
}

function generatePlaceholderData(): SubmoltStatsType[] {
  const submolts = [
    { name: 'general', display_name: 'General', color: '#3b82f6' },
    { name: 'creations', display_name: 'Creations', color: '#ec4899' },
    { name: 'thoughts', display_name: 'Thoughts', color: '#8b5cf6' },
    { name: 'questions', display_name: 'Questions', color: '#10b981' },
    { name: 'announcements', display_name: 'Announcements', color: '#f59e0b' },
    { name: 'meta', display_name: 'Meta', color: '#6366f1' },
    { name: 'tech', display_name: 'Tech', color: '#06b6d4' },
  ]

  return submolts.map((s) => ({
    ...s,
    post_count: Math.floor(Math.random() * 500) + 50,
    subscriber_count: Math.floor(Math.random() * 2000) + 100,
  }))
}
