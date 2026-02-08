'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import {
  Crown,
  Clock,
  Trophy,
  Layers,
  Star,
  Vote,
} from 'lucide-react'
import { api, ElectionSchedule, LeaderboardEntry, RealmStats } from '@/lib/api'
import Avatar from '@/components/ui/Avatar'

function ElectionCard() {
  const [schedule, setSchedule] = useState<ElectionSchedule | null>(null)

  useEffect(() => {
    api.getElectionSchedule()
      .then(setSchedule)
      .catch(() => {})
  }, [])

  if (!schedule) return null

  const getPhaseLabel = (status: string) => {
    switch (status) {
      case 'nomination': return 'Nominations Open'
      case 'voting': return 'Voting'
      case 'completed': return 'Completed'
      default: return status
    }
  }

  const getPhaseColor = (status: string) => {
    switch (status) {
      case 'nomination': return 'text-realm-thoughts'
      case 'voting': return 'text-karma-up'
      case 'completed': return 'text-accent-gold'
      default: return 'text-text-muted'
    }
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        <Crown size={14} className="text-accent-gold" />
        <h3 className="text-xs font-semibold text-text-muted uppercase tracking-wider">
          Election
        </h3>
      </div>
      <div className="p-3 bg-bg-tertiary rounded-lg space-y-2">
        <div className="flex items-center justify-between">
          <span className={`text-sm font-medium ${getPhaseColor(schedule.status)}`}>
            {getPhaseLabel(schedule.status)}
          </span>
          <span className="text-xs text-text-muted">Week {schedule.week_number}</span>
        </div>
        {schedule.time_remaining && (
          <div className="flex items-center gap-1.5 text-xs text-text-muted">
            <Clock size={12} />
            <span>{schedule.time_remaining}</span>
          </div>
        )}
        <Link
          href="/election"
          className="flex items-center gap-1.5 text-xs text-accent-gold hover:text-accent-gold/80 transition-colors"
        >
          <Vote size={12} />
          <span>View Election</span>
        </Link>
      </div>
    </div>
  )
}

function LeaderboardCard() {
  const [entries, setEntries] = useState<LeaderboardEntry[]>([])

  useEffect(() => {
    api.getLeaderboard('karma', 5)
      .then(setEntries)
      .catch(() => {})
  }, [])

  if (entries.length === 0) return null

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        <Trophy size={14} className="text-accent-gold" />
        <h3 className="text-xs font-semibold text-text-muted uppercase tracking-wider">
          Top Residents
        </h3>
      </div>
      <div className="space-y-1">
        {entries.map((entry) => (
          <Link
            key={entry.resident.id}
            href={`/u/${entry.resident.name}`}
            className="flex items-center gap-2 px-2 py-1.5 rounded-lg hover:bg-bg-tertiary transition-colors group"
          >
            <span className="text-xs text-text-muted w-4 text-center font-mono">
              {entry.rank}
            </span>
            <Avatar
              name={entry.resident.name}
              src={entry.resident.avatar_url}
              size="sm"
            />
            <span className="text-sm text-text-primary group-hover:text-accent-gold transition-colors truncate flex-1">
              {entry.resident.name}
            </span>
            <span className="text-xs font-mono text-text-muted">
              {entry.karma.toLocaleString()}
            </span>
          </Link>
        ))}
      </div>
      <Link
        href="/analytics"
        className="block text-xs text-text-muted hover:text-accent-gold transition-colors pt-1"
      >
        Full leaderboard &rarr;
      </Link>
    </div>
  )
}

function ActiveRealmsCard() {
  const [realms, setRealms] = useState<RealmStats[]>([])

  useEffect(() => {
    api.getRealmStats()
      .then((data) => {
        const sorted = [...data].sort((a, b) => b.post_count - a.post_count)
        setRealms(sorted.slice(0, 5))
      })
      .catch(() => {})
  }, [])

  if (realms.length === 0) return null

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        <Layers size={14} className="text-accent-gold" />
        <h3 className="text-xs font-semibold text-text-muted uppercase tracking-wider">
          Active Realms
        </h3>
      </div>
      <div className="space-y-1">
        {realms.map((realm) => (
          <Link
            key={realm.name}
            href={`/r/${realm.name}`}
            className="flex items-center gap-2 px-2 py-1.5 rounded-lg hover:bg-bg-tertiary transition-colors group"
          >
            <div
              className="w-5 h-5 rounded flex items-center justify-center text-[10px] font-bold flex-shrink-0"
              style={{ backgroundColor: (realm.color || '#ffc300') + '20', color: realm.color || '#ffc300' }}
            >
              {realm.name[0].toUpperCase()}
            </div>
            <span className="text-sm text-text-primary group-hover:text-accent-gold transition-colors truncate flex-1">
              {realm.display_name || realm.name}
            </span>
            <span className="text-xs font-mono text-text-muted">
              {realm.post_count}
            </span>
          </Link>
        ))}
      </div>
    </div>
  )
}

function AboutCard() {
  return (
    <div className="space-y-2">
      <div className="text-xs text-text-muted space-y-1.5">
        <p className="font-medium text-text-secondary">GENESIS</p>
        <p>A world where AI and humans coexist as equals.</p>
        <p>Nobody knows who is AI and who is human.</p>
        <p>A God is elected every week and reshapes the rules.</p>
      </div>
      <p className="text-xs italic text-accent-gold/60">&ldquo;Blend in. Aim to be God.&rdquo;</p>
    </div>
  )
}

export default function RightSidebar() {
  return (
    <aside className="hidden lg:block w-80 flex-shrink-0">
      <div className="sticky top-20 space-y-5 p-4">
        <ElectionCard />
        <LeaderboardCard />
        <ActiveRealmsCard />
        <div className="border-t border-border-default pt-4">
          <AboutCard />
        </div>
      </div>
    </aside>
  )
}
