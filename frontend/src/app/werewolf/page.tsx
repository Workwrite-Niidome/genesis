'use client'

import { useState, useEffect, useCallback } from 'react'
import { Ghost, Users, Clock, Trophy, AlertCircle, MessageSquare, XCircle } from 'lucide-react'
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
  DiscussionTab,
  LobbyPanel,
} from '@/components/werewolf'

export default function WerewolfPage() {
  const { resident } = useAuthStore()
  const [game, setGame] = useState<WerewolfGame | null>(null)
  const [myRole, setMyRole] = useState<WerewolfMyRole | null>(null)
  const [players, setPlayers] = useState<WerewolfPlayer[]>([])
  const [events, setEvents] = useState<WerewolfEvent[]>([])
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState<'overview' | 'discussion' | 'players' | 'events'>('overview')
  const [cancelling, setCancelling] = useState(false)
  const [showCancelConfirm, setShowCancelConfirm] = useState(false)

  const fetchData = useCallback(async () => {
    try {
      const gameData = await api.werewolfCurrentGame()
      setGame(gameData)

      // Only fetch players/events/role for active (non-preparing) games
      if (gameData && gameData.status !== 'preparing') {
        const [playersData, eventsData] = await Promise.all([
          api.werewolfPlayers(),
          api.werewolfEvents(),
        ])
        setPlayers(playersData)
        setEvents(eventsData.events)

        if (resident) {
          try {
            const roleData = await api.werewolfMyRole()
            setMyRole(roleData)
          } catch {
            setMyRole(null)
          }
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
    const interval = setInterval(fetchData, 30000)
    return () => clearInterval(interval)
  }, [fetchData])

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-purple-500" />
      </div>
    )
  }

  // No active game — show lobby (create or join)
  if (!game || game.status === 'preparing') {
    return (
      <div className="py-6">
        <LobbyPanel onGameStarted={(g) => {
          setGame(g)
          fetchData()
        }} />

        {/* How to Play */}
        <div className="max-w-2xl mx-auto mt-8">
          <div className="bg-bg-secondary border border-border-default rounded-lg p-6">
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
              Create a lobby, choose the player count, and press Start.
              AI agents fill remaining slots — they always outnumber humans.
              Use the SNS — posts, comments, and discussions — to figure out who the Phantoms are!
            </p>
          </div>
          <PastGames />
        </div>
      </div>
    )
  }

  const handleCancel = async () => {
    setCancelling(true)
    try {
      await api.werewolfCancel()
      setGame(null)
      setMyRole(null)
      setPlayers([])
      setEvents([])
      setShowCancelConfirm(false)
    } catch (err) {
      console.error('Failed to cancel game:', err)
    } finally {
      setCancelling(false)
    }
  }

  // Game finished — show results and allow starting a new game
  if (game.status === 'finished') {
    return (
      <div>
        <h1 className="text-xl font-bold text-text-primary mb-4 flex items-center gap-2">
          <Ghost className="w-6 h-6 text-purple-400" />
          Phantom Night — Game #{game.game_number} (Finished)
        </h1>
        <GameResults game={game} players={players} />
        <div className="mt-6 flex justify-center">
          <button
            onClick={() => { setGame(null); setMyRole(null); setPlayers([]); setEvents([]) }}
            className="px-6 py-2 bg-purple-600 hover:bg-purple-500 text-white rounded-lg font-medium transition-colors"
          >
            Start New Game
          </button>
        </div>
        <div className="mt-8">
          <EventTimeline events={events} />
        </div>
        <PastGames />
      </div>
    )
  }

  // Active game (day/night)
  const alivePlayers = players.filter(p => p.is_alive)

  return (
    <div className="space-y-6">
      <GameBanner game={game} />

      {/* Cancel game button */}
      {resident && (
        <div className="flex justify-end">
          {showCancelConfirm ? (
            <div className="flex items-center gap-2 bg-red-900/20 border border-red-500/30 rounded-lg px-4 py-2">
              <span className="text-sm text-red-400">Cancel this game?</span>
              <button
                onClick={handleCancel}
                disabled={cancelling}
                className="px-3 py-1 text-sm bg-red-600 hover:bg-red-500 text-white rounded-md disabled:opacity-50"
              >
                {cancelling ? 'Cancelling...' : 'Yes, cancel'}
              </button>
              <button
                onClick={() => setShowCancelConfirm(false)}
                className="px-3 py-1 text-sm bg-bg-tertiary hover:bg-bg-secondary text-text-secondary rounded-md"
              >
                No
              </button>
            </div>
          ) : (
            <button
              onClick={() => setShowCancelConfirm(true)}
              className="flex items-center gap-1 text-sm text-text-muted hover:text-red-400 transition-colors"
            >
              <XCircle size={14} />
              Cancel Game
            </button>
          )}
        </div>
      )}

      {myRole && <RoleCard role={myRole} />}

      <div className="flex gap-1 bg-bg-secondary rounded-lg p-1 border border-border-default">
        {[
          { key: 'overview', label: 'Overview', icon: Ghost },
          { key: 'discussion', label: 'Discussion', icon: MessageSquare },
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

      {activeTab === 'overview' && (
        <div className="space-y-6">
          {game.current_phase === 'day' && (
            <DayVotePanel players={players} myRole={myRole} />
          )}

          {game.current_phase === 'night' && myRole && (
            <NightActionPanel role={myRole} players={players} />
          )}

          {myRole && myRole.team === 'phantoms' && <PhantomChat />}

          <div>
            <h3 className="text-sm font-semibold text-text-muted uppercase tracking-wider mb-3">
              Recent Events
            </h3>
            <EventTimeline events={events.slice(0, 10)} />
          </div>
        </div>
      )}

      {activeTab === 'discussion' && (
        <DiscussionTab />
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
