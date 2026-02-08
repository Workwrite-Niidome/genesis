'use client'

import { useState, useEffect, useMemo } from 'react'
import Link from 'next/link'
import clsx from 'clsx'
import { Layers, Users, FileText } from 'lucide-react'
import { api, RealmStats as RealmStatsType } from '@/lib/api'

interface RealmStatsProps {
  limit?: number
  className?: string
}

type SortBy = 'posts' | 'subscribers'

export default function RealmStats({
  limit = 10,
  className,
}: RealmStatsProps) {
  const [data, setData] = useState<RealmStatsType[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [sortBy, setSortBy] = useState<SortBy>('posts')

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true)
      setError(null)
      try {
        const stats = await api.getRealmStats()
        setData(stats)
      } catch (err) {
        setError('Failed to load realm stats')
        console.error('Failed to fetch realm stats:', err)
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

  const getRealmColor = (color?: string): string => {
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
          <h2 className="text-lg font-semibold">Realm Stats</h2>
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
            Posts
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
            Subscribers
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
          No data available
        </div>
      ) : (
        <div className="space-y-3">
          {sortedData.map((realm) => {
            const value = sortBy === 'posts' ? realm.post_count : realm.subscriber_count
            const percentage = (value / maxValue) * 100
            const color = getRealmColor(realm.color)

            return (
              <Link
                key={realm.name}
                href={`/r/${realm.name}`}
                className="block group"
              >
                <div className="flex items-center justify-between mb-1">
                  <div className="flex items-center gap-2">
                    {/* Realm Icon */}
                    <div
                      className="w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold"
                      style={{ backgroundColor: color }}
                    >
                      {realm.icon_url ? (
                        <img
                          src={realm.icon_url}
                          alt={realm.name}
                          className="w-full h-full rounded-full object-cover"
                        />
                      ) : (
                        realm.name[0].toUpperCase()
                      )}
                    </div>

                    {/* Name */}
                    <div>
                      <span className="text-sm font-medium text-text-primary group-hover:text-accent-gold transition-colors">
                        {realm.display_name || realm.name}
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
            href="/analytics"
            className="text-sm text-text-secondary hover:text-accent-gold transition-colors"
          >
            View all Realms &rarr;
          </Link>
        </div>
      )}
    </div>
  )
}
