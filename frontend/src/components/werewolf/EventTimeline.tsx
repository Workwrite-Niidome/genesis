'use client'

import { WerewolfEvent } from '@/lib/api'
import clsx from 'clsx'
import {
  Sun,
  Moon,
  Vote,
  Skull,
  Shield,
  PlayCircle,
  Trophy,
  AlertCircle,
  Search,
  XCircle,
} from 'lucide-react'

interface EventTimelineProps {
  events: WerewolfEvent[]
}

const EVENT_CONFIG: Record<
  string,
  { icon: any; color: string; bgColor: string; borderColor: string }
> = {
  game_start: {
    icon: PlayCircle,
    color: 'text-accent-gold',
    bgColor: 'bg-accent-gold/10',
    borderColor: 'border-accent-gold/30',
  },
  day_start: {
    icon: Sun,
    color: 'text-blue-400',
    bgColor: 'bg-blue-500/10',
    borderColor: 'border-blue-500/30',
  },
  night_start: {
    icon: Moon,
    color: 'text-purple-400',
    bgColor: 'bg-purple-500/10',
    borderColor: 'border-purple-500/30',
  },
  vote_elimination: {
    icon: Vote,
    color: 'text-orange-400',
    bgColor: 'bg-orange-500/10',
    borderColor: 'border-orange-500/30',
  },
  phantom_kill: {
    icon: Skull,
    color: 'text-red-400',
    bgColor: 'bg-red-500/10',
    borderColor: 'border-red-500/30',
  },
  protected: {
    icon: Shield,
    color: 'text-green-400',
    bgColor: 'bg-green-500/10',
    borderColor: 'border-green-500/30',
  },
  no_kill: {
    icon: AlertCircle,
    color: 'text-gray-400',
    bgColor: 'bg-gray-500/10',
    borderColor: 'border-gray-500/30',
  },
  game_end: {
    icon: Trophy,
    color: 'text-accent-gold',
    bgColor: 'bg-accent-gold/10',
    borderColor: 'border-accent-gold/30',
  },
  identifier_kill: {
    icon: Search,
    color: 'text-amber-400',
    bgColor: 'bg-amber-500/10',
    borderColor: 'border-amber-500/30',
  },
  identifier_backfire: {
    icon: XCircle,
    color: 'text-red-400',
    bgColor: 'bg-red-500/10',
    borderColor: 'border-red-500/30',
  },
}

export default function EventTimeline({ events }: EventTimelineProps) {
  // Sort events newest first
  const sortedEvents = [...events].sort(
    (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
  )

  return (
    <div className="space-y-4">
      {sortedEvents.map((event, idx) => {
        const config = EVENT_CONFIG[event.event_type] || EVENT_CONFIG.no_kill
        const Icon = config.icon
        const isLast = idx === sortedEvents.length - 1

        return (
          <div key={event.id} className="relative">
            {/* Timeline line */}
            {!isLast && (
              <div className="absolute left-5 top-10 bottom-0 w-0.5 bg-border-default" />
            )}

            <div className="flex gap-4">
              {/* Icon */}
              <div
                className={clsx(
                  'flex-shrink-0 w-10 h-10 rounded-full border-2 flex items-center justify-center z-10',
                  config.bgColor,
                  config.borderColor,
                  config.color
                )}
              >
                <Icon size={18} />
              </div>

              {/* Content */}
              <div className="flex-1 pb-6">
                <div className="flex items-start justify-between mb-1">
                  <div className="flex items-center gap-2">
                    <span
                      className={clsx(
                        'text-xs font-semibold px-2 py-0.5 rounded',
                        event.phase === 'day'
                          ? 'bg-blue-500/20 text-blue-400'
                          : event.phase === 'night'
                            ? 'bg-purple-500/20 text-purple-400'
                            : 'bg-bg-tertiary text-text-muted'
                      )}
                    >
                      {event.phase === 'day' && `Day ${event.round_number}`}
                      {event.phase === 'night' && `Night ${event.round_number}`}
                      {!event.phase && 'Game'}
                    </span>
                  </div>
                  <span className="text-xs text-text-muted">
                    {new Date(event.created_at).toLocaleString()}
                  </span>
                </div>

                <p className="text-sm text-text-primary mb-2">{event.message}</p>

                {/* Revealed role info */}
                {event.revealed_role && (
                  <div className="flex items-center gap-4 text-xs text-text-secondary">
                    {event.revealed_role && (
                      <span className="flex items-center gap-1">
                        <span className="text-text-muted">Role:</span>
                        <span className="font-semibold text-text-primary">
                          {event.revealed_role === 'phantom' && '👻 Phantom'}
                          {event.revealed_role === 'citizen' && '🏠 Citizen'}
                          {event.revealed_role === 'oracle' && '🔮 Oracle'}
                          {event.revealed_role === 'guardian' && '🛡️ Guardian'}
                          {event.revealed_role === 'fanatic' && '🎭 Fanatic'}
                          {event.revealed_role === 'debugger' && '🔍 Debugger'}
                        </span>
                      </span>
                    )}
                    {event.revealed_type && (
                      <span className="flex items-center gap-1">
                        <span className="text-text-muted">Type:</span>
                        <span className="font-semibold text-text-primary">
                          {event.revealed_type === 'human' ? '👤 Human' : '🤖 Agent'}
                        </span>
                      </span>
                    )}
                  </div>
                )}
              </div>
            </div>
          </div>
        )
      })}

      {sortedEvents.length === 0 && (
        <div className="text-center py-8 text-text-muted">
          <AlertCircle size={32} className="mx-auto mb-2 opacity-50" />
          <p>No events yet</p>
        </div>
      )}
    </div>
  )
}
