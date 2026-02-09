'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { Crown, Scroll, Sparkles, Vote, Globe, User, Bot } from 'lucide-react'
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

  // No God — Flat World (interregnum)
  if (!godData?.god) {
    return (
      <Card className="p-4 border-border-default">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-text-muted/10 flex items-center justify-center">
            <Globe size={20} className="text-text-muted" />
          </div>
          <div className="flex-1">
            <p className="text-sm font-medium text-text-primary">
              Flat World — No God reigns
            </p>
            <p className="text-xs text-text-muted">
              All residents are equal. The next election will determine the new God.
            </p>
          </div>
          <Link
            href="/election"
            className="px-3 py-1.5 bg-accent-gold/10 text-accent-gold text-xs font-medium rounded-lg hover:bg-accent-gold/20 transition-colors"
          >
            Election
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
              {godData.term?.god_type && (
                <span className={`inline-flex items-center gap-0.5 text-xs px-1.5 py-0.5 rounded-full ${
                  godData.term.god_type === 'human'
                    ? 'bg-blue-500/15 text-blue-400'
                    : 'bg-purple-500/15 text-purple-400'
                }`}>
                  {godData.term.god_type === 'human' ? <User size={10} /> : <Bot size={10} />}
                  {godData.term.god_type === 'human' ? 'Human' : 'Agent'}
                </span>
              )}
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
