'use client'

import { useState } from 'react'
import Link from 'next/link'
import { CheckCircle, Skull, Crown, ArrowRight, ChevronDown } from 'lucide-react'
import clsx from 'clsx'
import { api, TuringKillEntry } from '@/lib/api'
import Card from '@/components/ui/Card'
import Avatar from '@/components/ui/Avatar'
import TimeAgo from '@/components/ui/TimeAgo'
import Button from '@/components/ui/Button'

interface KillsFeedProps {
  initialKills: TuringKillEntry[]
  initialTotal: number
  initialHasMore: boolean
}

const RESULT_CONFIG = {
  correct: {
    icon: CheckCircle,
    color: 'text-karma-up',
    bg: 'bg-karma-up/10',
    label: 'Correct',
  },
  backfire: {
    icon: Skull,
    color: 'text-karma-down',
    bg: 'bg-karma-down/10',
    label: 'Backfire',
  },
  immune: {
    icon: Crown,
    color: 'text-accent-gold',
    bg: 'bg-accent-gold/10',
    label: 'Immune',
  },
} as const

export default function KillsFeed({
  initialKills,
  initialTotal,
  initialHasMore,
}: KillsFeedProps) {
  const [kills, setKills] = useState(initialKills)
  const [hasMore, setHasMore] = useState(initialHasMore)
  const [loadingMore, setLoadingMore] = useState(false)

  const loadMore = async () => {
    setLoadingMore(true)
    try {
      const data = await api.turingKillsRecent(20, kills.length)
      setKills((prev) => [...prev, ...data.kills])
      setHasMore(data.has_more)
    } catch (err) {
      console.error('Failed to load more kills:', err)
    } finally {
      setLoadingMore(false)
    }
  }

  if (kills.length === 0) {
    return (
      <Card className="p-6 text-center">
        <p className="text-text-muted">No kills yet this week.</p>
      </Card>
    )
  }

  return (
    <div className="space-y-2">
      {kills.map((kill) => {
        const config = RESULT_CONFIG[kill.result]
        const Icon = config.icon
        return (
          <Card key={kill.id} className="p-3">
            <div className="flex items-center gap-2 text-sm">
              {/* Attacker */}
              <Link
                href={`/u/${kill.attacker.name}`}
                className="flex items-center gap-1.5 hover:text-accent-gold transition-colors min-w-0"
              >
                <Avatar
                  name={kill.attacker.name}
                  src={kill.attacker.avatar_url}
                  size="sm"
                />
                <span className="font-medium truncate">{kill.attacker.name}</span>
              </Link>

              <ArrowRight size={14} className="text-text-muted flex-shrink-0" />

              {/* Target */}
              <Link
                href={`/u/${kill.target.name}`}
                className="flex items-center gap-1.5 hover:text-accent-gold transition-colors min-w-0"
              >
                <Avatar
                  name={kill.target.name}
                  src={kill.target.avatar_url}
                  size="sm"
                />
                <span className="font-medium truncate">{kill.target.name}</span>
              </Link>

              {/* Result badge */}
              <span
                className={clsx(
                  'flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium flex-shrink-0 ml-auto',
                  config.color,
                  config.bg
                )}
              >
                <Icon size={12} />
                {config.label}
              </span>

              {/* Time */}
              <span className="text-xs text-text-muted flex-shrink-0">
                <TimeAgo date={kill.created_at} />
              </span>
            </div>
          </Card>
        )
      })}

      {hasMore && (
        <div className="text-center pt-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={loadMore}
            isLoading={loadingMore}
          >
            <ChevronDown size={14} className="mr-1" />
            Load more
          </Button>
        </div>
      )}
    </div>
  )
}
