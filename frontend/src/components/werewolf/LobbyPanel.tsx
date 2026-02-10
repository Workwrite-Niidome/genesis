'use client'

import { useState, useEffect, useCallback } from 'react'
import { Ghost, Users, Play, LogIn, LogOut, Plus, Settings } from 'lucide-react'
import { api, WerewolfLobby, WerewolfGame } from '@/lib/api'
import { useAuthStore } from '@/stores/authStore'
import Avatar from '@/components/ui/Avatar'
import Button from '@/components/ui/Button'

interface LobbyPanelProps {
  onGameStarted: (game: WerewolfGame) => void
}

const PLAYER_PRESETS = [10, 20, 30, 50]

export default function LobbyPanel({ onGameStarted }: LobbyPanelProps) {
  const { resident } = useAuthStore()
  const [lobby, setLobby] = useState<WerewolfLobby | null>(null)
  const [loading, setLoading] = useState(true)
  const [actionLoading, setActionLoading] = useState(false)
  const [showCreate, setShowCreate] = useState(false)
  const [maxPlayers, setMaxPlayers] = useState(20)
  const [error, setError] = useState('')

  const fetchLobby = useCallback(async () => {
    try {
      const data = await api.werewolfGetLobby()
      setLobby(data)
    } catch {
      setLobby(null)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchLobby()
    const interval = setInterval(fetchLobby, 5000) // Poll every 5s
    return () => clearInterval(interval)
  }, [fetchLobby])

  const handleCreate = async () => {
    setActionLoading(true)
    setError('')
    try {
      const data = await api.werewolfCreateLobby(maxPlayers)
      setLobby(data)
      setShowCreate(false)
    } catch (err: any) {
      setError(err?.message || 'Failed to create lobby')
    } finally {
      setActionLoading(false)
    }
  }

  const handleJoin = async () => {
    setActionLoading(true)
    setError('')
    try {
      const data = await api.werewolfJoinLobby()
      setLobby(data)
    } catch (err: any) {
      setError(err?.message || 'Failed to join lobby')
    } finally {
      setActionLoading(false)
    }
  }

  const handleLeave = async () => {
    setActionLoading(true)
    setError('')
    try {
      await api.werewolfLeaveLobby()
      await fetchLobby()
    } catch (err: any) {
      setError(err?.message || 'Failed to leave lobby')
    } finally {
      setActionLoading(false)
    }
  }

  const handleStart = async () => {
    setActionLoading(true)
    setError('')
    try {
      const game = await api.werewolfStartGame()
      onGameStarted(game)
    } catch (err: any) {
      setError(err?.message || 'Failed to start game')
    } finally {
      setActionLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-purple-500" />
      </div>
    )
  }

  const isInLobby = lobby && resident && lobby.joined_players.some(p => p.id === resident.id)

  // No lobby exists — show create button
  if (!lobby) {
    return (
      <div className="max-w-2xl mx-auto">
        {!showCreate ? (
          <div className="text-center py-8">
            <Ghost className="w-16 h-16 text-purple-400 mx-auto mb-4 opacity-60" />
            <h2 className="text-xl font-bold text-text-primary mb-2">Phantom Night</h2>
            <p className="text-text-secondary mb-6">
              No active game. Create a lobby to start matchmaking.
            </p>
            {resident ? (
              <Button
                onClick={() => setShowCreate(true)}
                variant="primary"
                className="bg-purple-600 hover:bg-purple-500"
              >
                <Plus size={18} />
                Create Game
              </Button>
            ) : (
              <p className="text-sm text-text-muted">Log in to create a game.</p>
            )}
          </div>
        ) : (
          <div className="bg-bg-secondary border border-border-default rounded-lg p-6">
            <h3 className="text-lg font-bold text-text-primary mb-4 flex items-center gap-2">
              <Settings size={20} className="text-purple-400" />
              New Game Setup
            </h3>

            <div className="mb-4">
              <label className="block text-sm font-medium text-text-secondary mb-2">
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

            <div className="bg-bg-tertiary rounded-lg p-3 mb-4 text-sm text-text-secondary">
              <div className="flex justify-between mb-1">
                <span>Max human slots:</span>
                <span className="text-text-primary font-medium">{Math.floor(maxPlayers / 2)}</span>
              </div>
              <div className="flex justify-between">
                <span>AI agents fill remaining:</span>
                <span className="text-text-primary font-medium">{maxPlayers - Math.floor(maxPlayers / 2)}+</span>
              </div>
              <p className="text-xs text-text-muted mt-2">
                AI always outnumber humans. If no humans join, the Debugger role is excluded.
              </p>
            </div>

            {error && (
              <p className="text-red-400 text-sm mb-3">{error}</p>
            )}

            <div className="flex gap-3">
              <Button
                onClick={handleCreate}
                isLoading={actionLoading}
                variant="primary"
                className="bg-purple-600 hover:bg-purple-500 flex-1"
              >
                <Play size={16} />
                Create Lobby
              </Button>
              <Button
                onClick={() => setShowCreate(false)}
                variant="secondary"
              >
                Cancel
              </Button>
            </div>
          </div>
        )}
      </div>
    )
  }

  // Lobby exists — show lobby state
  return (
    <div className="max-w-2xl mx-auto">
      <div className="bg-bg-secondary border border-purple-500/30 rounded-lg overflow-hidden">
        {/* Header */}
        <div className="bg-purple-900/20 border-b border-purple-500/20 px-4 py-3">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-bold text-text-primary flex items-center gap-2">
              <Ghost className="w-5 h-5 text-purple-400" />
              Game #{lobby.game.game_number} — Lobby
            </h2>
            <div className="flex items-center gap-2 text-sm">
              <Users size={16} className="text-text-muted" />
              <span className="text-text-primary font-medium">
                {lobby.joined_players.length}
              </span>
              <span className="text-text-muted">
                / {lobby.game.max_players}
              </span>
            </div>
          </div>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-3 gap-3 p-4">
          <div className="bg-bg-tertiary rounded-lg p-3 text-center">
            <div className="text-lg font-bold text-blue-400">{lobby.human_count}</div>
            <div className="text-xs text-text-muted">Humans</div>
          </div>
          <div className="bg-bg-tertiary rounded-lg p-3 text-center">
            <div className="text-lg font-bold text-purple-400">{lobby.ai_count}</div>
            <div className="text-xs text-text-muted">AI Joined</div>
          </div>
          <div className="bg-bg-tertiary rounded-lg p-3 text-center">
            <div className="text-lg font-bold text-text-primary">{lobby.spots_remaining}</div>
            <div className="text-xs text-text-muted">Spots Left</div>
          </div>
        </div>

        {/* Player List */}
        <div className="px-4 pb-3">
          <h3 className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-2">
            Waiting Players ({lobby.joined_players.length})
          </h3>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 max-h-48 overflow-y-auto">
            {lobby.joined_players.map(player => (
              <div
                key={player.id}
                className="flex items-center gap-2 bg-bg-tertiary rounded-lg px-3 py-2"
              >
                <Avatar name={player.name} src={player.avatar_url} size="sm" />
                <span className="text-sm text-text-primary truncate">{player.name}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Info */}
        <div className="px-4 pb-3">
          <p className="text-xs text-text-muted">
            When the game starts, AI agents will fill remaining {lobby.spots_remaining} slots.
            {lobby.human_count === 0 && ' No humans yet — Debugger role will be excluded.'}
          </p>
        </div>

        {error && (
          <div className="px-4 pb-3">
            <p className="text-red-400 text-sm">{error}</p>
          </div>
        )}

        {/* Actions */}
        {resident && (
          <div className="border-t border-border-default px-4 py-3 flex gap-3">
            {isInLobby ? (
              <>
                <Button
                  onClick={handleStart}
                  isLoading={actionLoading}
                  variant="primary"
                  className="bg-green-600 hover:bg-green-500 flex-1"
                >
                  <Play size={16} />
                  Start Game
                </Button>
                <Button
                  onClick={handleLeave}
                  isLoading={actionLoading}
                  variant="secondary"
                >
                  <LogOut size={16} />
                  Leave
                </Button>
              </>
            ) : (
              <Button
                onClick={handleJoin}
                isLoading={actionLoading}
                variant="primary"
                className="bg-purple-600 hover:bg-purple-500 flex-1"
              >
                <LogIn size={16} />
                Join Lobby
              </Button>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
