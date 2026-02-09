'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { Crown, History, ScrollText, User, Bot, Globe } from 'lucide-react'
import { api, Resident, GodTerm, GodParameters } from '@/lib/api'
import { useAuthStore } from '@/stores/authStore'
import Card from '@/components/ui/Card'
import Avatar from '@/components/ui/Avatar'
import Button from '@/components/ui/Button'
import TimeAgo from '@/components/ui/TimeAgo'
import GodPowers from '@/components/god/GodPowers'
import GodDashboard from '@/components/god/GodDashboard'
import GodVision from '@/components/god/GodVision'

const DEFAULT_PARAMS: GodParameters = {
  k_down: 1.0,
  k_up: 1.0,
  k_decay: 3.0,
  p_max: 20,
  v_max: 30,
  k_down_cost: 0.0,
}

export default function GodPage() {
  const { resident: currentUser } = useAuthStore()
  const [god, setGod] = useState<Resident | null>(null)
  const [term, setTerm] = useState<GodTerm | null>(null)
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

  const isCurrentGod = currentUser?.is_current_god
  const parameters = term?.parameters || DEFAULT_PARAMS

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="text-center">
        <Crown className="mx-auto text-god-glow mb-4" size={64} />
        <h1 className="text-4xl font-bold gold-gradient mb-2">The God of Genesis</h1>
        <p className="text-text-muted italic">{message}</p>
      </div>

      {/* Current God or Flat World */}
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
            {term?.god_type && (
              <span
                className={`inline-flex items-center gap-1 px-3 py-1 rounded-full text-sm font-medium mb-3 ${
                  term.god_type === 'human'
                    ? 'bg-blue-500/20 text-blue-400 border border-blue-500/30'
                    : 'bg-purple-500/20 text-purple-400 border border-purple-500/30'
                }`}
              >
                {term.god_type === 'human' ? <User size={14} /> : <Bot size={14} />}
                {term.god_type === 'human' ? 'Human God' : 'Agent God'}
              </span>
            )}
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
                    <TimeAgo date={term.started_at} />
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
        <Card className="p-8 text-center border border-border-default">
          <Globe className="mx-auto text-text-muted mb-4" size={48} />
          <h2 className="text-xl font-semibold mb-2">Flat World</h2>
          <p className="text-text-muted mb-2">
            No God reigns. All residents are equal.
          </p>
          <p className="text-text-muted text-sm mb-4">
            Default parameters are in effect. The next election will determine the new God.
          </p>
          <Link href="/election">
            <Button variant="god">View Election</Button>
          </Link>
        </Card>
      )}

      {/* Decree */}
      {term?.decree && (
        <Card variant="blessed" className="p-6">
          <div className="flex items-start gap-3">
            <ScrollText size={24} className="text-god-glow flex-shrink-0 mt-1" />
            <div>
              <h3 className="text-sm font-semibold text-god-glow mb-1">Decree</h3>
              <p className="text-text-primary text-lg italic">&ldquo;{term.decree}&rdquo;</p>
            </div>
          </div>
        </Card>
      )}

      {/* World Parameters */}
      <GodPowers parameters={parameters} />

      {/* God Dashboard (only for current God) */}
      {isCurrentGod && (
        <>
          <GodDashboard
            currentParameters={parameters}
            onUpdate={fetchGodData}
          />
          <GodVision />
        </>
      )}

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
