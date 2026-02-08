'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { Crown, Scroll, Sparkles, Vote } from 'lucide-react'
import { api, CurrentGodResponse } from '@/lib/api'
import Card from '@/components/ui/Card'
import Avatar from '@/components/ui/Avatar'

export default function GodBanner() {
  const [godData, setGodData] = useState<CurrentGodResponse | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    api.getCurrentGod()
      .then(setGodData)
      .catch(() => {})
      .finally(() => setIsLoading(false))
  }, [])

  if (isLoading) {
    return (
      <div className="h-24 bg-bg-secondary border border-border-default rounded-lg animate-pulse" />
    )
  }

  // No God — election state
  if (!godData?.god) {
    return (
      <Card className="p-4 border-accent-gold/30">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-accent-gold/10 flex items-center justify-center">
            <Vote size={20} className="text-accent-gold" />
          </div>
          <div className="flex-1">
            <p className="text-sm font-medium text-text-primary">
              Genesis awaits its God.
            </p>
            <p className="text-xs text-text-muted">
              Election in progress — cast your vote.
            </p>
          </div>
          <Link
            href="/election"
            className="px-3 py-1.5 bg-accent-gold/10 text-accent-gold text-xs font-medium rounded-lg hover:bg-accent-gold/20 transition-colors"
          >
            Vote
          </Link>
        </div>
      </Card>
    )
  }

  const { god, term, active_rules, weekly_theme } = godData

  return (
    <Card variant="god" className="p-4 overflow-hidden relative">
      {/* Subtle glow */}
      <div className="absolute inset-0 bg-gradient-to-r from-god-glow/5 via-transparent to-god-glow/5 pointer-events-none" />

      <div className="relative space-y-3">
        {/* God info */}
        <div className="flex items-center gap-3">
          <Link href={`/u/${god.name}`}>
            <Avatar
              name={god.name}
              src={god.avatar_url}
              size="lg"
              isGod
            />
          </Link>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <Crown size={14} className="text-god-glow flex-shrink-0" />
              <Link href={`/u/${god.name}`} className="font-semibold text-text-primary hover:text-god-glow transition-colors truncate">
                {god.name}
              </Link>
              <span className="text-xs text-god-glow">God of Genesis</span>
            </div>
            {weekly_theme && (
              <p className="text-xs text-text-muted mt-0.5">
                <Sparkles size={10} className="inline mr-1 text-accent-gold" />
                Theme: {weekly_theme}
              </p>
            )}
          </div>
        </div>

        {/* Decree */}
        {term?.decree && (
          <div className="pl-3 border-l-2 border-god-glow/40">
            <p className="text-xs text-god-glow font-medium mb-0.5">Decree</p>
            <p className="text-sm text-text-secondary italic line-clamp-2">
              &ldquo;{term.decree}&rdquo;
            </p>
          </div>
        )}

        {/* Active rules (compact) */}
        {active_rules.length > 0 && (
          <div className="flex items-center gap-2 flex-wrap">
            <Scroll size={12} className="text-text-muted flex-shrink-0" />
            {active_rules.slice(0, 3).map((rule) => (
              <span
                key={rule.id}
                className="text-xs px-2 py-0.5 bg-bg-tertiary rounded-full text-text-secondary"
              >
                {rule.title}
              </span>
            ))}
            {active_rules.length > 3 && (
              <Link href="/god" className="text-xs text-text-muted hover:text-accent-gold">
                +{active_rules.length - 3} more
              </Link>
            )}
          </div>
        )}
      </div>
    </Card>
  )
}
