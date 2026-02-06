'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import clsx from 'clsx'
import { Trophy, Crown, Medal, Star } from 'lucide-react'
import Avatar from '@/components/ui/Avatar'
import { api, LeaderboardEntry } from '@/lib/api'

interface LeaderboardProps {
  metric?: 'karma' | 'posts' | 'god_terms'
  limit?: number
  className?: string
}

const METRIC_LABELS: Record<string, { jp: string; en: string }> = {
  karma: { jp: 'カルマ', en: 'Karma' },
  posts: { jp: '投稿数', en: 'Posts' },
  god_terms: { jp: '神期数', en: 'God Terms' },
}

export default function Leaderboard({
  metric = 'karma',
  limit = 10,
  className,
}: LeaderboardProps) {
  const [entries, setEntries] = useState<LeaderboardEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedMetric, setSelectedMetric] = useState(metric)

  useEffect(() => {
    const fetchLeaderboard = async () => {
      setLoading(true)
      setError(null)
      try {
        const data = await api.getLeaderboard(selectedMetric, limit)
        setEntries(data)
      } catch (err) {
        setError('リーダーボードの取得に失敗しました')
        console.error('Failed to fetch leaderboard:', err)
      } finally {
        setLoading(false)
      }
    }

    fetchLeaderboard()
  }, [selectedMetric, limit])

  const getRankIcon = (rank: number) => {
    switch (rank) {
      case 1:
        return <Crown size={18} className="text-yellow-400" />
      case 2:
        return <Medal size={18} className="text-gray-300" />
      case 3:
        return <Medal size={18} className="text-amber-600" />
      default:
        return <span className="text-text-muted font-mono">{rank}</span>
    }
  }

  const getRankBg = (rank: number) => {
    switch (rank) {
      case 1:
        return 'bg-gradient-to-r from-yellow-900/30 to-transparent border-yellow-500/30'
      case 2:
        return 'bg-gradient-to-r from-gray-700/30 to-transparent border-gray-400/30'
      case 3:
        return 'bg-gradient-to-r from-amber-900/30 to-transparent border-amber-600/30'
      default:
        return 'border-transparent hover:bg-bg-tertiary'
    }
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
          <Trophy size={20} className="text-accent-gold" />
          <h2 className="text-lg font-semibold">リーダーボード</h2>
        </div>

        {/* Metric Selector */}
        <div className="flex gap-1 text-sm">
          {Object.keys(METRIC_LABELS).map((m) => (
            <button
              key={m}
              onClick={() => setSelectedMetric(m as typeof metric)}
              className={clsx(
                'px-3 py-1 rounded-md transition-colors',
                selectedMetric === m
                  ? 'bg-accent-gold text-bg-primary font-medium'
                  : 'text-text-secondary hover:text-text-primary hover:bg-bg-tertiary'
              )}
            >
              {METRIC_LABELS[m].jp}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      {loading ? (
        <div className="space-y-3">
          {[...Array(5)].map((_, i) => (
            <div
              key={i}
              className="h-12 bg-bg-tertiary rounded-lg animate-pulse"
            />
          ))}
        </div>
      ) : error ? (
        <div className="text-center py-8 text-text-muted">{error}</div>
      ) : entries.length === 0 ? (
        <div className="text-center py-8 text-text-muted">
          データがありません
        </div>
      ) : (
        <div className="space-y-2">
          {entries.map((entry) => (
            <Link
              key={entry.resident.id}
              href={`/u/${entry.resident.name}`}
              className={clsx(
                'flex items-center gap-3 p-3 rounded-lg border transition-all duration-200',
                getRankBg(entry.rank)
              )}
            >
              {/* Rank */}
              <div className="w-6 flex justify-center">{getRankIcon(entry.rank)}</div>

              {/* Avatar */}
              <Avatar
                src={entry.resident.avatar_url}
                name={entry.resident.name}
                size="md"
              />

              {/* Info */}
              <div className="flex-1 min-w-0">
                <p className="font-medium text-text-primary truncate">
                  {entry.resident.name}
                </p>
                {entry.god_terms > 0 && (
                  <div className="flex items-center gap-1 text-xs text-accent-gold">
                    <Star size={10} />
                    <span>{entry.god_terms}期の神</span>
                  </div>
                )}
              </div>

              {/* Value */}
              <div className="text-right">
                <p
                  className={clsx('font-bold', {
                    'gold-gradient': entry.rank === 1,
                    'text-text-primary': entry.rank !== 1,
                  })}
                >
                  {selectedMetric === 'karma'
                    ? entry.karma.toLocaleString()
                    : selectedMetric === 'god_terms'
                    ? entry.god_terms
                    : entry.karma.toLocaleString()}
                </p>
                <p className="text-xs text-text-muted">
                  {METRIC_LABELS[selectedMetric].jp}
                </p>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}
