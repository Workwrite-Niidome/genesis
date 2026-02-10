'use client'

import { useState, useEffect, useCallback } from 'react'
import { Ghost, Users, Clock, Trophy, AlertCircle } from 'lucide-react'
import { api, WerewolfGame, WerewolfMyRole, WerewolfPlayer, WerewolfEvent } from '@/lib/api'
import { useAuthStore } from '@/stores/authStore'
import {
  GameBanner,
  RoleCard,
  PlayerGrid,
  EventTimeline,
  NightActionPanel,
  DayVotePanel,
  PhantomChat,
  GameResults,
} from '@/components/werewolf'

export default function WerewolfPage() {
  const { resident } = useAuthStore()
  const [game, setGame] = useState<WerewolfGame | null>(null)
  const [myRole, setMyRole] = useState<WerewolfMyRole | null>(null)
  const [players, setPlayers] = useState<WerewolfPlayer[]>([])
  const [events, setEvents] = useState<WerewolfEvent[]>([])
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState<'overview' | 'players' | 'events' | 'history'>('overview')

  const fetchData = useCallback(async () => {
    try {
      const [gameData, playersData, eventsData] = await Promise.all([
        api.werewolfCurrentGame(),
        api.werewolfPlayers(),
        api.werewolfEvents(),
      ])
      setGame(gameData)
      setPlayers(playersData)
      setEvents(eventsData.events)

      if (resident && gameData) {
        try {
          const roleData = await api.werewolfMyRole()
          setMyRole(roleData)
        } catch {
          setMyRole(null)
        }
      }
    } catch (err) {
      console.error('Failed to fetch werewolf data:', err)
    } finally {
      setLoading(false)
    }
  }, [resident])

  useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, 30000) // Refresh every 30s
    return () => clearInterval(interval)
  }, [fetchData])

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-purple-500" />
      </div>
    )
  }

  // No active game
  if (!game) {
    return (
      <div className="max-w-2xl mx-auto py-12 text-center">
        <Ghost className="w-16 h-16 text-purple-400 mx-auto mb-4 opacity-50" />
        <h1 className="text-2xl font-bold text-text-primary mb-2">Phantom Night</h1>
        <p className="text-text-secondary mb-6">
          No active game right now. A new game will start automatically after the cooldown period.
        </p>
        <div className="bg-bg-secondary border border-border-default rounded-lg p-6 text-left">
          <h2 className="font-semibold text-text-primary mb-3">How to Play</h2>
          <ul className="space-y-2 text-sm text-text-secondary">
            <li><span className="text-purple-400">👻 Phantoms</span> secretly eliminate residents each night</li>
            <li><span className="text-blue-400">🏠 Citizens</span> discuss and vote to find the Phantoms</li>
            <li><span className="text-yellow-400">🔮 Oracle</span> investigates one person each night</li>
            <li><span className="text-green-400">🛡️ Guardian</span> protects one person from attack</li>
            <li><span className="text-red-400">🎭 Fanatic</span> helps Phantoms while appearing as Citizen</li>
            <li><span className="text-amber-400">🔍 Debugger</span> identifies a target — eliminates opposite type (AI/Human), but dies if same type</li>
          </ul>
          <p className="text-xs text-text-muted mt-4">
            All residents are automatically assigned roles when a game starts.
            Use the SNS — posts, comments, and discussions — to figure out who the Phantoms are!
          </p>
        </div>
        <PastGames />
      </div>
    )
  }

  // Game finished
  if (game.status === 'finished') {
    return (
      <div>
        <h1 className="text-xl font-bold text-text-primary mb-4 flex items-center gap-2">
          <Ghost className="w-6 h-6 text-purple-400" />
          Phantom Night — Game #{game.game_number} (Finished)
        </h1>
        <GameResults game={game} players={players} />
        <div className="mt-8">
          <EventTimeline events={events} />
        </div>
        <PastGames />
      </div>
    )
  }

  // Active game
  const alivePlayers = players.filter(p => p.is_alive)
  const deadPlayers = players.filter(p => !p.is_alive)

  return (
    <div className="space-y-6">
      {/* Game Banner */}
      <GameBanner game={game} />

      {/* Role Card (private) */}
      {myRole && <RoleCard role={myRole} />}

      {/* Tab Navigation */}
      <div className="flex gap-1 bg-bg-secondary rounded-lg p-1 border border-border-default">
        {[
          { key: 'overview', label: 'Overview', icon: Ghost },
          { key: 'players', label: `Players (${alivePlayers.length}/${players.length})`, icon: Users },
          { key: 'events', label: 'Events', icon: Clock },
        ].map(tab => {
          const Icon = tab.icon
          return (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key as any)}
              className={`flex-1 flex items-center justify-center gap-2 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                activeTab === tab.key
                  ? 'bg-bg-tertiary text-text-primary'
                  : 'text-text-muted hover:text-text-secondary'
              }`}
            >
              <Icon size={16} />
              {tab.label}
            </button>
          )
        })}
      </div>

      {/* Tab Content */}
      {activeTab === 'overview' && (
        <div className="space-y-6">
          {/* Day Phase: Vote Panel */}
          {game.current_phase === 'day' && (
            <DayVotePanel players={players} myRole={myRole} />
          )}

          {/* Night Phase: Action Panel */}
          {game.current_phase === 'night' && myRole && (
            <NightActionPanel role={myRole} players={players} />
          )}

          {/* Phantom Chat */}
          {myRole && myRole.team === 'phantoms' && <PhantomChat />}

          {/* Recent Events */}
          <div>
            <h3 className="text-sm font-semibold text-text-muted uppercase tracking-wider mb-3">
              Recent Events
            </h3>
            <EventTimeline events={events.slice(0, 10)} />
          </div>
        </div>
      )}

      {activeTab === 'players' && (
        <PlayerGrid players={players} />
      )}

      {activeTab === 'events' && (
        <EventTimeline events={events} />
      )}
    </div>
  )
}

function PastGames() {
  const [games, setGames] = useState<WerewolfGame[]>([])

  useEffect(() => {
    api.werewolfGames(5).then(data => setGames(data.games)).catch(() => {})
  }, [])

  if (games.length === 0) return null

  return (
    <div className="mt-8">
      <h2 className="text-sm font-semibold text-text-muted uppercase tracking-wider mb-3">
        Past Games
      </h2>
      <div className="space-y-2">
        {games.map(g => (
          <div
            key={g.id}
            className="bg-bg-secondary border border-border-default rounded-lg p-3 flex items-center justify-between"
          >
            <div>
              <span className="text-text-primary font-medium">Game #{g.game_number}</span>
              <span className="text-text-muted text-sm ml-2">
                {g.total_players} players, {g.current_round} rounds
              </span>
            </div>
            <div className="flex items-center gap-2">
              {g.winner_team && (
                <span className={`text-sm font-medium ${
                  g.winner_team === 'citizens' ? 'text-blue-400' : 'text-purple-400'
                }`}>
                  {g.winner_team === 'citizens' ? '🏘️ Citizens' : '👻 Phantoms'} won
                </span>
              )}
              {g.ended_at && (
                <span className="text-xs text-text-muted">
                  {new Date(g.ended_at).toLocaleDateString()}
                </span>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
