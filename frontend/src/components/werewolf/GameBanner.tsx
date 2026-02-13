'use client'

import { useState, useEffect, useRef } from 'react'
import { Moon, Sun } from 'lucide-react'
import clsx from 'clsx'
import { WerewolfGame } from '@/lib/api'

interface GameBannerProps {
  game: WerewolfGame
  onPhaseExpired?: () => void
  compact?: boolean
}

export default function GameBanner({ game, onPhaseExpired, compact }: GameBannerProps) {
  const [timeRemaining, setTimeRemaining] = useState<string>('')
  const expiredRef = useRef(false)
  const onPhaseExpiredRef = useRef(onPhaseExpired)
  onPhaseExpiredRef.current = onPhaseExpired

  useEffect(() => {
    expiredRef.current = false
  }, [game.phase_ends_at])

  useEffect(() => {
    if (!game.phase_ends_at) return

    const updateTimer = () => {
      const now = new Date()
      const raw = game.phase_ends_at!
      const end = new Date(raw.endsWith('Z') ? raw : raw + 'Z')
      const diff = end.getTime() - now.getTime()

      if (diff <= 0) {
        setTimeRemaining('0:00')
        if (!expiredRef.current) {
          expiredRef.current = true
          onPhaseExpiredRef.current?.()
        }
        return
      }

      const minutes = Math.floor(diff / (1000 * 60))
      const seconds = Math.floor((diff % (1000 * 60)) / 1000)
      setTimeRemaining(`${minutes}:${seconds.toString().padStart(2, '0')}`)
    }

    updateTimer()
    const interval = setInterval(updateTimer, 1000)

    return () => clearInterval(interval)
  }, [game.phase_ends_at])

  const isDayPhase = game.current_phase === 'day'
  const isNightPhase = game.current_phase === 'night'

  if (compact) {
    return (
      <div
        className={clsx(
          'rounded-lg border px-3 py-2 transition-all duration-300',
          isDayPhase && 'bg-gradient-to-r from-blue-900/20 to-indigo-900/20 border-blue-500/30',
          isNightPhase && 'bg-gradient-to-r from-purple-900/20 to-violet-900/20 border-purple-500/30',
        )}
      >
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-2 min-w-0">
            {isDayPhase && <Sun size={16} className="text-blue-400 flex-shrink-0" />}
            {isNightPhase && <Moon size={16} className="text-purple-400 flex-shrink-0" />}
            <span className="text-sm font-bold text-text-primary truncate">
              #{game.game_number}
            </span>
            <span
              className={clsx(
                'px-1.5 py-0.5 rounded text-xs font-semibold flex-shrink-0',
                isDayPhase && 'bg-blue-500/20 text-blue-400',
                isNightPhase && 'bg-purple-500/20 text-purple-400'
              )}
            >
              {isDayPhase ? 'Day' : 'Night'} {game.current_round}
            </span>
          </div>
          {game.phase_ends_at && (
            <span className="text-lg font-mono font-bold text-text-primary flex-shrink-0">
              {timeRemaining}
            </span>
          )}
        </div>
      </div>
    )
  }

  return (
    <div
      className={clsx(
        'rounded-lg border p-4 transition-all duration-300',
        isDayPhase && 'bg-gradient-to-r from-blue-900/20 to-indigo-900/20 border-blue-500/30',
        isNightPhase && 'bg-gradient-to-r from-purple-900/20 to-violet-900/20 border-purple-500/30',
        game.status === 'preparing' && 'bg-bg-secondary border-border-default',
        game.status === 'finished' && 'bg-bg-secondary border-border-default'
      )}
    >
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div className="flex items-center gap-4">
          {isDayPhase && (
            <div className="p-2 rounded-lg bg-blue-500/20 text-blue-400">
              <Sun size={20} />
            </div>
          )}
          {isNightPhase && (
            <div className="p-2 rounded-lg bg-purple-500/20 text-purple-400">
              <Moon size={20} />
            </div>
          )}

          <div>
            <div className="flex items-center gap-3">
              <h2 className="text-lg font-bold text-text-primary">
                Phantom Night #{game.game_number}
              </h2>
              {game.status === 'day' || game.status === 'night' ? (
                <span
                  className={clsx(
                    'px-2 py-1 rounded text-xs font-semibold',
                    isDayPhase && 'bg-blue-500/20 text-blue-400',
                    isNightPhase && 'bg-purple-500/20 text-purple-400'
                  )}
                >
                  {isDayPhase ? 'Day' : 'Night'} {game.current_round}
                </span>
              ) : (
                <span className="px-2 py-1 rounded text-xs font-semibold bg-bg-tertiary text-text-secondary">
                  {game.status === 'preparing' ? 'Preparing' : 'Finished'}
                </span>
              )}
            </div>
            <p className="text-sm text-text-secondary">
              {game.total_players} players
              <span className="ml-2">
                {game.language === 'ja' ? '🇯🇵 日本語' : '🇬🇧 English'}
              </span>
              {game.status === 'finished' && game.winner_team && (
                <span className="ml-2">
                  Winner: {game.winner_team === 'citizens' ? 'Citizens' : 'Phantoms'}
                </span>
              )}
            </p>
          </div>
        </div>

        {(game.status === 'day' || game.status === 'night') && game.phase_ends_at && (
          <div className="text-right">
            <div className="text-2xl font-mono font-bold text-text-primary">
              {timeRemaining}
            </div>
            <p className="text-xs text-text-secondary">remaining</p>
          </div>
        )}
      </div>
    </div>
  )
}
