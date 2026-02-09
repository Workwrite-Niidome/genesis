'use client'

import { useState } from 'react'
import Link from 'next/link'
import { Trophy, ChevronDown, Award } from 'lucide-react'
import clsx from 'clsx'
import { api, WeeklyScoreEntry } from '@/lib/api'
import Card from '@/components/ui/Card'
import Avatar from '@/components/ui/Avatar'
import Button from '@/components/ui/Button'

interface WeeklyScoresProps {
  weekNumber: number
  poolSize: number
  initialScores: WeeklyScoreEntry[]
  initialTotal: number
  initialHasMore: boolean
}

export default function WeeklyScores({
  weekNumber,
  poolSize,
  initialScores,
  initialTotal,
  initialHasMore,
}: WeeklyScoresProps) {
  const [scores, setScores] = useState(initialScores)
  const [expanded, setExpanded] = useState(false)
  const [hasMore, setHasMore] = useState(initialHasMore)
  const [loadingMore, setLoadingMore] = useState(false)

  const displayScores = expanded ? scores : scores.slice(0, 10)

  const loadMore = async () => {
    setLoadingMore(true)
    try {
      const data = await api.turingWeeklyScores(weekNumber, 50, scores.length)
      setScores((prev) => [...prev, ...data.scores])
      setHasMore(data.has_more)
      setExpanded(true)
    } catch (err) {
      console.error('Failed to load more scores:', err)
    } finally {
      setLoadingMore(false)
    }
  }

  const handleExpand = () => {
    if (scores.length > 10) {
      setExpanded(true)
    } else if (hasMore) {
      loadMore()
    } else {
      setExpanded(true)
    }
  }

  if (scores.length === 0) {
    return (
      <Card className="p-6 text-center">
        <p className="text-text-muted">No scores yet this week.</p>
      </Card>
    )
  }

  return (
    <div className="space-y-2">
      {/* Header */}
      <div className="flex items-center justify-between px-1 mb-2">
        <div className="flex items-center gap-2 text-sm text-text-secondary">
          <Trophy size={14} className="text-accent-gold" />
          <span>Week {weekNumber}</span>
        </div>
        <span className="text-xs text-text-muted">
          Top {poolSize} qualify as candidates
        </span>
      </div>

      {/* Scores list */}
      {displayScores.map((entry) => (
        <Card key={entry.resident.id} className="p-3">
          <div className="flex items-center gap-3">
            {/* Rank */}
            <span
              className={clsx('text-sm font-bold w-8 text-center', {
                'gold-gradient': entry.rank === 1,
                'text-text-secondary': entry.rank === 2,
                'text-accent-gold-dim': entry.rank === 3,
                'text-text-muted': entry.rank > 3,
              })}
            >
              #{entry.rank}
            </span>

            {/* Avatar & Name */}
            <Link
              href={`/u/${entry.resident.name}`}
              className="flex items-center gap-2 min-w-0 flex-1 hover:text-accent-gold transition-colors"
            >
              <Avatar
                name={entry.resident.name}
                src={entry.resident.avatar_url}
                size="sm"
              />
              <span className="font-medium text-sm truncate">
                {entry.resident.name}
              </span>
            </Link>

            {/* Candidate badge */}
            {entry.qualified_as_candidate && (
              <span className="flex items-center gap-1 text-xs text-accent-gold" title="Candidate qualified">
                <Award size={12} />
              </span>
            )}

            {/* Score */}
            <span className="text-sm font-bold text-text-primary flex-shrink-0">
              {entry.total_score.toFixed(1)}
            </span>
          </div>
        </Card>
      ))}

      {/* Expand / Load more */}
      {(!expanded && scores.length > 10) || hasMore ? (
        <div className="text-center pt-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={handleExpand}
            isLoading={loadingMore}
          >
            <ChevronDown size={14} className="mr-1" />
            Show more
          </Button>
        </div>
      ) : null}
    </div>
  )
}
