'use client'

import { ArrowDown, ArrowUp, Timer, FileText, Vote, Zap } from 'lucide-react'
import Card from '@/components/ui/Card'
import { GodParameters } from '@/lib/api'

const DEFAULTS: GodParameters = {
  k_down: 1.0,
  k_up: 1.0,
  k_decay: 3.0,
  p_max: 20,
  v_max: 30,
  k_down_cost: 0.0,
}

const PARAM_INFO = [
  {
    key: 'k_down' as const,
    icon: ArrowDown,
    title: 'Downvote Weight',
    description: 'Karma lost per downvote received',
    format: (v: number) => `${v.toFixed(1)}x`,
  },
  {
    key: 'k_up' as const,
    icon: ArrowUp,
    title: 'Upvote Weight',
    description: 'Karma gained per upvote received',
    format: (v: number) => `${v.toFixed(1)}x`,
  },
  {
    key: 'k_decay' as const,
    icon: Timer,
    title: 'Karma Decay',
    description: 'Karma lost per day (applied 4x/day)',
    format: (v: number) => `${v.toFixed(1)}/day`,
  },
  {
    key: 'p_max' as const,
    icon: FileText,
    title: 'Post Limit',
    description: 'Maximum posts per day',
    format: (v: number) => `${v}/day`,
  },
  {
    key: 'v_max' as const,
    icon: Vote,
    title: 'Vote Limit',
    description: 'Maximum votes per day',
    format: (v: number) => `${v}/day`,
  },
  {
    key: 'k_down_cost' as const,
    icon: Zap,
    title: 'Downvote Cost',
    description: 'Karma cost to cast a downvote',
    format: (v: number) => v > 0 ? `${v.toFixed(1)}` : 'Free',
  },
]

interface GodPowersProps {
  compact?: boolean
  parameters?: GodParameters | null
}

export default function GodPowers({ compact = false, parameters }: GodPowersProps) {
  const params = parameters || DEFAULTS

  return (
    <div className="space-y-4">
      <h2 className={`font-semibold flex items-center gap-2 ${compact ? 'text-lg' : 'text-xl'}`}>
        <Zap size={compact ? 18 : 20} className="text-accent-gold" />
        World Parameters
      </h2>

      <div className={`grid gap-3 ${compact ? 'grid-cols-2 sm:grid-cols-3' : 'grid-cols-2 sm:grid-cols-3'}`}>
        {PARAM_INFO.map((info) => {
          const Icon = info.icon
          const value = params[info.key]
          const defaultValue = DEFAULTS[info.key]
          const isModified = value !== defaultValue

          return (
            <Card key={info.key} variant="god" className={compact ? 'p-3' : 'p-4'}>
              <div className="flex items-start gap-2">
                <div className={`flex-shrink-0 rounded-lg bg-god-glow/10 flex items-center justify-center ${compact ? 'p-1' : 'p-1.5'}`}>
                  <Icon size={compact ? 14 : 16} className="text-god-glow" />
                </div>
                <div className="min-w-0 flex-1">
                  <h3 className={`font-semibold text-text-primary ${compact ? 'text-xs' : 'text-sm'}`}>
                    {info.title}
                  </h3>
                  <p className={`font-bold ${isModified ? 'text-accent-gold' : 'text-text-primary'} ${compact ? 'text-lg' : 'text-xl'}`}>
                    {info.format(value)}
                  </p>
                  {isModified && (
                    <p className="text-xs text-text-muted">
                      default: {info.format(defaultValue)}
                    </p>
                  )}
                </div>
              </div>
            </Card>
          )
        })}
      </div>
    </div>
  )
}
