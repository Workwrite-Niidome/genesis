'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { Moon, Sun, Ghost } from 'lucide-react'
import { api, WerewolfGame } from '@/lib/api'

export default function LayoutGameBanner() {
  const [game, setGame] = useState<WerewolfGame | null>(null)
  const [timeRemaining, setTimeRemaining] = useState('')

  useEffect(() => {
    api.werewolfCurrentGame()
      .then(g => setGame(g))
      .catch(() => {})

    const interval = setInterval(() => {
      api.werewolfCurrentGame()
        .then(g => setGame(g))
        .catch(() => {})
    }, 60000) // Check every minute

    return () => clearInterval(interval)
  }, [])

  useEffect(() => {
    if (!game?.phase_ends_at) return

    const update = () => {
      const raw = game.phase_ends_at!
      const diff = new Date(raw.endsWith('Z') ? raw : raw + 'Z').getTime() - Date.now()
      if (diff <= 0) {
        setTimeRemaining('00:00')
        return
      }
      const h = Math.floor(diff / 3600000)
      const m = Math.floor((diff % 3600000) / 60000)
      setTimeRemaining(h > 0 ? `${h}h ${m}m` : `${m}m`)
    }

    update()
    const interval = setInterval(update, 30000)
    return () => clearInterval(interval)
  }, [game?.phase_ends_at])

  if (!game || game.status === 'finished' || game.status === 'preparing') return null

  const isNight = game.current_phase === 'night'

  return (
    <Link
      href="/phantomnight"
      className={`block px-4 py-2 text-sm font-medium border-b transition-colors ${
        isNight
          ? 'bg-purple-950/50 border-purple-800/30 text-purple-200 hover:bg-purple-950/70'
          : 'bg-indigo-950/50 border-indigo-800/30 text-indigo-200 hover:bg-indigo-950/70'
      }`}
    >
      <div className="max-w-4xl mx-auto flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Ghost size={16} />
          <span>Phantom Night #{game.game_number}</span>
          <span className="opacity-60">|</span>
          {isNight ? <Moon size={14} /> : <Sun size={14} />}
          <span>{isNight ? 'Night' : 'Day'} {game.current_round}</span>
        </div>
        <div className="flex items-center gap-2 text-xs opacity-75">
          <span>{timeRemaining} remaining</span>
        </div>
      </div>
    </Link>
  )
}
