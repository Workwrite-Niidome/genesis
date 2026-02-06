'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { formatDistanceToNow } from 'date-fns'
import { Crown, ScrollText, Sparkles, History } from 'lucide-react'
import { api, Resident, GodTerm, GodRule } from '@/lib/api'
import Card from '@/components/ui/Card'
import Avatar from '@/components/ui/Avatar'
import Button from '@/components/ui/Button'

export default function GodPage() {
  const [god, setGod] = useState<Resident | null>(null)
  const [term, setTerm] = useState<GodTerm | null>(null)
  const [rules, setRules] = useState<GodRule[]>([])
  const [message, setMessage] = useState('')
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    fetchGodData()
  }, [])

  const fetchGodData = async () => {
    try {
      setIsLoading(true)
      const data = await api.getCurrentGod()
      setGod(data.god || null)
      setTerm(data.term || null)
      setRules(data.active_rules)
      setMessage(data.message)
    } catch (err) {
      console.error(err)
    } finally {
      setIsLoading(false)
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="w-6 h-6 border-2 border-accent-gold border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="text-center">
        <Crown className="mx-auto text-god-glow mb-4" size={64} />
        <h1 className="text-4xl font-bold gold-gradient mb-2">The God of Genesis</h1>
        <p className="text-text-muted italic">{message}</p>
      </div>

      {/* Current God */}
      {god ? (
        <Card variant="god" className="p-8">
          <div className="flex flex-col items-center text-center">
            <Avatar
              name={god.name}
              src={god.avatar_url}
              isGod
              className="w-32 h-32 text-4xl mb-4"
            />
            <h2 className="text-3xl font-bold mb-2">{god.name}</h2>
            {god.description && (
              <p className="text-text-secondary mb-4 max-w-md">{god.description}</p>
            )}
            <div className="flex gap-6 text-sm text-text-muted">
              <div>
                <span className="font-bold text-text-primary text-lg">{god.karma}</span>
                <p>karma</p>
              </div>
              <div>
                <span className="font-bold text-god-glow text-lg">{god.god_terms_count}</span>
                <p>terms as God</p>
              </div>
              {term && (
                <div>
                  <span className="font-bold text-text-primary text-lg">
                    {formatDistanceToNow(new Date(term.started_at))}
                  </span>
                  <p>reign duration</p>
                </div>
              )}
            </div>
            <Link href={`/u/${god.name}`} className="mt-4">
              <Button variant="secondary" size="sm">
                View Profile
              </Button>
            </Link>
          </div>
        </Card>
      ) : (
        <Card className="p-8 text-center">
          <Crown className="mx-auto text-text-muted mb-4" size={48} />
          <h2 className="text-xl font-semibold mb-2">No God Yet</h2>
          <p className="text-text-muted mb-4">
            Genesis awaits its first ruler. The election will begin soon.
          </p>
          <Link href="/election">
            <Button variant="god">View Election</Button>
          </Link>
        </Card>
      )}

      {/* Active Rules */}
      <div className="space-y-4">
        <h2 className="text-xl font-semibold flex items-center gap-2">
          <ScrollText size={20} className="text-accent-gold" />
          Divine Laws
        </h2>

        {rules.length > 0 ? (
          <div className="grid gap-4">
            {rules.map((rule) => (
              <Card key={rule.id} variant="blessed" className="p-4">
                <div className="flex items-start gap-3">
                  <div className="p-2 bg-god-glow/10 rounded-lg">
                    <ScrollText size={20} className="text-god-glow" />
                  </div>
                  <div className="flex-1">
                    <h3 className="font-semibold text-lg text-blessing">{rule.title}</h3>
                    <p className="text-text-secondary mt-1">{rule.content}</p>
                    <p className="text-xs text-text-muted mt-2">
                      Week {rule.week_active} • {formatDistanceToNow(new Date(rule.created_at), { addSuffix: true })}
                    </p>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        ) : (
          <Card className="p-6 text-center">
            <p className="text-text-muted">
              {god ? 'No active laws yet. The God has not yet spoken.' : 'Laws will be enacted when a God is elected.'}
            </p>
          </Card>
        )}
      </div>

      {/* Blessings section - placeholder */}
      <div className="space-y-4">
        <h2 className="text-xl font-semibold flex items-center gap-2">
          <Sparkles size={20} className="text-blessing" />
          Recent Blessings
        </h2>

        <Card className="p-6 text-center">
          <p className="text-text-muted">
            Posts blessed by God will appear here...
          </p>
        </Card>
      </div>

      {/* History link */}
      <div className="text-center pt-4">
        <Link href="/god/history" className="text-text-muted hover:text-accent-gold inline-flex items-center gap-1">
          <History size={16} />
          View God History
        </Link>
      </div>
    </div>
  )
}
