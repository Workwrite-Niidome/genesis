'use client'

import { useState, useEffect, useCallback } from 'react'
import { Ghost, Play, Users, Clock, Zap, Timer, LogOut, RefreshCw, Flame } from 'lucide-react'
import { api, WerewolfGame, WerewolfLobby } from '@/lib/api'
import { useAuthStore } from '@/stores/authStore'
import Button from '@/components/ui/Button'

interface LobbyPanelProps {
  onGameStarted: (game: WerewolfGame) => void
}

const SPEED_PRESETS = [
  {
    key: 'casual',
    label: 'Casual',
    day: '18min',
    night: '6min',
    round: '~25min',
    description: 'Quick lunch-break games',
    icon: Flame,
    color: 'text-orange-400',
    bgColor: 'bg-orange-500/10 border-orange-500/30',
    activeColor: 'bg-orange-600 border-orange-500 text-white',
  },
  {
    key: 'quick',
    label: 'Quick',
    day: '3h',
    night: '1h',
    round: '4h',
    description: 'Fast games, quick rounds',
    icon: Zap,
    color: 'text-yellow-400',
    bgColor: 'bg-yellow-500/10 border-yellow-500/30',
    activeColor: 'bg-yellow-600 border-yellow-500 text-white',
  },
  {
    key: 'standard',
    label: 'Standard',
    day: '8h',
    night: '2h',
    round: '10h',
    description: 'Balanced for daily play',
    icon: Timer,
    color: 'text-purple-400',
    bgColor: 'bg-purple-500/10 border-purple-500/30',
    activeColor: 'bg-purple-600 border-purple-500 text-white',
  },
  {
    key: 'extended',
    label: 'Extended',
    day: '20h',
    night: '4h',
    round: '24h',
    description: 'Deep discussion, 1 round/day',
    icon: Clock,
    color: 'text-blue-400',
    bgColor: 'bg-blue-500/10 border-blue-500/30',
    activeColor: 'bg-blue-600 border-blue-500 text-white',
  },
] as const

const PLAYER_PRESETS = [10, 20, 30, 50]

export default function LobbyPanel({ onGameStarted }: LobbyPanelProps) {
  const { resident } = useAuthStore()
  const [maxPlayers, setMaxPlayers] = useState(20)
  const [speed, setSpeed] = useState<string>('standard')
  const [creating, setCreating] = useState(false)
  const [error, setError] = useState('')
  const [lobbies, setLobbies] = useState<WerewolfLobby[]>([])
  const [joiningId, setJoiningId] = useState<string | null>(null)
  const [myLobby, setMyLobby] = useState<WerewolfLobby | null>(null)
  const [starting, setStarting] = useState(false)
  const [leaving, setLeaving] = useState(false)

  const fetchLobbies = useCallback(async () => {
    try {
      const data = await api.werewolfGetLobbies()
      setLobbies(data)
      // Check if current user is in any lobby
      if (resident) {
        const mine = data.find(l =>
          l.players.some(p => p.id === resident.id)
        )
        setMyLobby(mine || null)
      }
    } catch {
      // silent
    }
  }, [resident])

  useEffect(() => {
    fetchLobbies()
    const interval = setInterval(fetchLobbies, 5000)
    return () => clearInterval(interval)
  }, [fetchLobbies])

  const handleCreate = async () => {
    setCreating(true)
    setError('')
    try {
      const game = await api.werewolfCreateGame(maxPlayers, speed)
      // After creating, the user is in a lobby — refresh lobbies
      await fetchLobbies()
      // If the game immediately started (shouldn't, but check), notify parent
      if (game.status !== 'preparing') {
        onGameStarted(game)
      }
    } catch (err: any) {
      setError(err?.message || 'Failed to create game')
    } finally {
      setCreating(false)
    }
  }

  const handleJoin = async (gameId: string) => {
    setJoiningId(gameId)
    setError('')
    try {
      await api.werewolfJoinGame(gameId)
      await fetchLobbies()
    } catch (err: any) {
      setError(err?.message || 'Failed to join game')
    } finally {
      setJoiningId(null)
    }
  }

  const handleLeave = async () => {
    if (!myLobby) return
    setLeaving(true)
    setError('')
    try {
      await api.werewolfLeaveGame(myLobby.id)
      setMyLobby(null)
      await fetchLobbies()
    } catch (err: any) {
      setError(err?.message || 'Failed to leave game')
    } finally {
      setLeaving(false)
    }
  }

  const handleStart = async () => {
    if (!myLobby) return
    setStarting(true)
    setError('')
    try {
      const game = await api.werewolfStartGame(myLobby.id)
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
        <p className="text-text-secondary">Log in to play.</p>
      </div>
    )
  }

  // If user is in a lobby — show waiting room
  if (myLobby) {
    const isCreator = myLobby.creator_id === resident.id
    const preset = SPEED_PRESETS.find(p => p.key === myLobby.speed) || SPEED_PRESETS[1]

    return (
      <div className="max-w-2xl mx-auto">
        <div className="bg-bg-secondary border border-purple-500/30 rounded-lg overflow-hidden">
          <div className="bg-purple-900/20 border-b border-purple-500/20 px-5 py-4">
            <h2 className="text-lg font-bold text-text-primary flex items-center gap-2">
              <Ghost className="w-5 h-5 text-purple-400" />
              Game #{myLobby.game_number} — Waiting Room
            </h2>
            <p className="text-sm text-text-muted mt-1">
              {preset.label} speed ({preset.day} day / {preset.night} night) — {myLobby.max_players} players
            </p>
          </div>

          <div className="p-5 space-y-4">
            {/* Players */}
            <div>
              <div className="flex items-center gap-2 text-sm font-medium text-text-secondary mb-3">
                <Users size={16} />
                Players ({myLobby.current_player_count} / {myLobby.human_cap} humans)
              </div>
              <div className="space-y-2">
                {myLobby.players.map(p => (
                  <div key={p.id} className="flex items-center gap-3 px-3 py-2 bg-bg-tertiary rounded-lg">
                    <div className="w-8 h-8 rounded-full bg-purple-500/20 flex items-center justify-center text-purple-400 text-sm font-bold">
                      {p.name.charAt(0).toUpperCase()}
                    </div>
                    <span className="text-sm text-text-primary">{p.name}</span>
                    {p.id === myLobby.creator_id && (
                      <span className="text-xs px-2 py-0.5 bg-purple-500/20 text-purple-400 rounded">Host</span>
                    )}
                  </div>
                ))}
              </div>
              <p className="text-xs text-text-muted mt-2">
                AI agents will fill remaining {(myLobby.max_players || 10) - myLobby.current_player_count} slots when the game starts.
              </p>
            </div>

            {error && <p className="text-red-400 text-sm">{error}</p>}

            <div className="flex gap-3">
              {isCreator && (
                <Button
                  onClick={handleStart}
                  isLoading={starting}
                  variant="primary"
                  className="flex-1 bg-purple-600 hover:bg-purple-500 py-3"
                >
                  <Play size={18} />
                  Start Game
                </Button>
              )}
              <Button
                onClick={handleLeave}
                isLoading={leaving}
                variant="secondary"
                className={isCreator ? '' : 'flex-1'}
              >
                <LogOut size={18} />
                {isCreator ? 'Cancel' : 'Leave'}
              </Button>
            </div>
          </div>
        </div>
      </div>
    )
  }

  // Not in a lobby — show create + open lobbies
  return (
    <div className="max-w-2xl mx-auto space-y-6">
      {/* Create Game */}
      <div className="bg-bg-secondary border border-purple-500/30 rounded-lg overflow-hidden">
        <div className="bg-purple-900/20 border-b border-purple-500/20 px-5 py-4">
          <h2 className="text-lg font-bold text-text-primary flex items-center gap-2">
            <Ghost className="w-5 h-5 text-purple-400" />
            Create a Game
          </h2>
          <p className="text-sm text-text-muted mt-1">
            Choose speed and player count. Other humans can join before you start.
          </p>
        </div>

        <div className="p-5 space-y-5">
          {/* Speed Presets */}
          <div>
            <label className="text-sm font-medium text-text-secondary mb-3 block">Game Speed</label>
            <div className="grid grid-cols-2 gap-3">
              {SPEED_PRESETS.map(preset => {
                const Icon = preset.icon
                const isActive = speed === preset.key
                return (
                  <button
                    key={preset.key}
                    onClick={() => setSpeed(preset.key)}
                    className={`p-3.5 rounded-lg border text-left transition-all ${
                      isActive ? preset.activeColor : preset.bgColor + ' hover:opacity-80'
                    }`}
                  >
                    <div className="flex items-center gap-2">
                      <Icon size={16} className={isActive ? 'text-white' : preset.color} />
                      <span className={`font-semibold text-sm ${isActive ? 'text-white' : 'text-text-primary'}`}>
                        {preset.label}
                      </span>
                      <span className={`text-xs ml-auto ${isActive ? 'text-white/70' : 'text-text-muted'}`}>
                        {preset.round}
                      </span>
                    </div>
                    <div className={`text-xs mt-1.5 ${isActive ? 'text-white/80' : 'text-text-muted'}`}>
                      Day {preset.day} / Night {preset.night}
                    </div>
                  </button>
                )
              })}
            </div>
          </div>

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

          {error && <p className="text-red-400 text-sm">{error}</p>}

          <Button
            onClick={handleCreate}
            isLoading={creating}
            variant="primary"
            className="w-full bg-purple-600 hover:bg-purple-500 py-3 text-base"
          >
            <Play size={20} />
            Create Game
          </Button>
        </div>
      </div>

      {/* Open Lobbies */}
      {lobbies.length > 0 && (
        <div className="bg-bg-secondary border border-border-default rounded-lg overflow-hidden">
          <div className="px-5 py-3 border-b border-border-default flex items-center justify-between">
            <h3 className="font-semibold text-text-primary flex items-center gap-2">
              <Users size={16} />
              Open Lobbies
            </h3>
            <button
              onClick={fetchLobbies}
              className="text-text-muted hover:text-text-primary transition-colors"
            >
              <RefreshCw size={14} />
            </button>
          </div>
          <div className="divide-y divide-border-default">
            {lobbies.map(lobby => {
              const preset = SPEED_PRESETS.find(p => p.key === lobby.speed)
              return (
                <div key={lobby.id} className="px-5 py-3 flex items-center justify-between">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium text-text-primary">
                        Game #{lobby.game_number}
                      </span>
                      {preset && (
                        <span className={`text-xs px-2 py-0.5 rounded ${preset.bgColor}`}>
                          {preset.label}
                        </span>
                      )}
                    </div>
                    <div className="text-xs text-text-muted mt-0.5">
                      by {lobby.creator_name || 'Unknown'} — {lobby.current_player_count}/{lobby.human_cap} humans — {lobby.max_players} total
                    </div>
                  </div>
                  <Button
                    onClick={() => handleJoin(lobby.id)}
                    isLoading={joiningId === lobby.id}
                    variant="secondary"
                    className="text-sm px-4 py-1.5"
                  >
                    Join
                  </Button>
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}
