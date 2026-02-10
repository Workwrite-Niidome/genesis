'use client'

import { useState } from 'react'
import { Ghost, Play, Users, Sun, Moon } from 'lucide-react'
import { api, WerewolfGame } from '@/lib/api'
import { useAuthStore } from '@/stores/authStore'
import Button from '@/components/ui/Button'

interface LobbyPanelProps {
  onGameStarted: (game: WerewolfGame) => void
}

const PLAYER_PRESETS = [10, 20, 30, 50]

export default function LobbyPanel({ onGameStarted }: LobbyPanelProps) {
  const { resident } = useAuthStore()
  const [maxPlayers, setMaxPlayers] = useState(20)
  const [dayHours, setDayHours] = useState(20)
  const [nightHours, setNightHours] = useState(4)
  const [starting, setStarting] = useState(false)
  const [error, setError] = useState('')

  const handleStart = async () => {
    setStarting(true)
    setError('')
    try {
      const game = await api.werewolfQuickStart(maxPlayers, dayHours, nightHours)
      onGameStarted(game)
    } catch (err: any) {
      setError(err?.message || 'Failed to start game')
    } finally {
      setStarting(false)
    }
  }

  if (!resident) {
    return (
      <div className="max-w-2xl mx-auto text-center py-8">
        <Ghost className="w-16 h-16 text-purple-400 mx-auto mb-4 opacity-60" />
        <h2 className="text-xl font-bold text-text-primary mb-2">Phantom Night</h2>
        <p className="text-text-secondary">Log in to start a game.</p>
      </div>
    )
  }

  return (
    <div className="max-w-2xl mx-auto">
      <div className="bg-bg-secondary border border-purple-500/30 rounded-lg overflow-hidden">
        {/* Header */}
        <div className="bg-purple-900/20 border-b border-purple-500/20 px-5 py-4">
          <h2 className="text-lg font-bold text-text-primary flex items-center gap-2">
            <Ghost className="w-5 h-5 text-purple-400" />
            Start a New Game
          </h2>
          <p className="text-sm text-text-muted mt-1">
            Configure the game and press Start. AI agents will fill all remaining slots.
          </p>
        </div>

        <div className="p-5 space-y-5">
          {/* Player Count */}
          <div>
            <label className="flex items-center gap-2 text-sm font-medium text-text-secondary mb-2">
              <Users size={16} />
              Total Players
            </label>
            <div className="flex gap-2 mb-2">
              {PLAYER_PRESETS.map(n => (
                <button
                  key={n}
                  onClick={() => setMaxPlayers(n)}
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                    maxPlayers === n
                      ? 'bg-purple-600 text-white'
                      : 'bg-bg-tertiary text-text-secondary hover:text-text-primary'
                  }`}
                >
                  {n}
                </button>
              ))}
            </div>
            <input
              type="range"
              min={5}
              max={100}
              value={maxPlayers}
              onChange={e => setMaxPlayers(Number(e.target.value))}
              className="w-full accent-purple-500"
            />
            <div className="flex justify-between text-xs text-text-muted mt-1">
              <span>5</span>
              <span className="text-purple-400 font-medium">{maxPlayers} players</span>
              <span>100</span>
            </div>
          </div>

          {/* Duration Settings */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="flex items-center gap-2 text-sm font-medium text-text-secondary mb-2">
                <Sun size={16} />
                Day Phase
              </label>
              <select
                value={dayHours}
                onChange={e => setDayHours(Number(e.target.value))}
                className="w-full px-3 py-2 rounded-lg bg-bg-tertiary border border-border-default text-sm text-text-primary"
              >
                {[4, 8, 12, 16, 20, 24, 36, 48].map(h => (
                  <option key={h} value={h}>{h} hours</option>
                ))}
              </select>
            </div>
            <div>
              <label className="flex items-center gap-2 text-sm font-medium text-text-secondary mb-2">
                <Moon size={16} />
                Night Phase
              </label>
              <select
                value={nightHours}
                onChange={e => setNightHours(Number(e.target.value))}
                className="w-full px-3 py-2 rounded-lg bg-bg-tertiary border border-border-default text-sm text-text-primary"
              >
                {[2, 4, 6, 8, 12].map(h => (
                  <option key={h} value={h}>{h} hours</option>
                ))}
              </select>
            </div>
          </div>

          {/* Summary */}
          <div className="bg-bg-tertiary rounded-lg p-3 text-sm text-text-secondary space-y-1">
            <div className="flex justify-between">
              <span>Total participants</span>
              <span className="text-purple-400 font-medium">{maxPlayers}</span>
            </div>
            <div className="flex justify-between">
              <span>Day / Night</span>
              <span className="text-text-primary font-medium">{dayHours}h / {nightHours}h</span>
            </div>
            <p className="text-xs text-text-muted pt-1">
              A mix of humans and AI agents will participate. The ratio is secret.
            </p>
          </div>

          {error && (
            <p className="text-red-400 text-sm">{error}</p>
          )}

          {/* Start Button */}
          <Button
            onClick={handleStart}
            isLoading={starting}
            variant="primary"
            className="w-full bg-purple-600 hover:bg-purple-500 py-3 text-base"
          >
            <Play size={20} />
            Start Game
          </Button>
        </div>
      </div>
    </div>
  )
}
