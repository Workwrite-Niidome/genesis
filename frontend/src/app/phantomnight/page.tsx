'use client'

import { useState, useEffect, useCallback } from 'react'
import { Ghost, XCircle } from 'lucide-react'
import { api, WerewolfGame, WerewolfMyRole, WerewolfPlayer, WerewolfEvent } from '@/lib/api'
import { useAuthStore } from '@/stores/authStore'
import { useGameWebSocket, RefreshScope } from '@/hooks/useGameWebSocket'
import {
  GameBanner,
  RoleCard,
  PlayerGrid,
  EventTimeline,
  NightActionPanel,
  DayVotePanel,
  PhantomChat,
  GameResults,
  ChatWindow,
  LobbyPanel,
} from '@/components/werewolf'

export default function WerewolfPage() {
  const { resident } = useAuthStore()
  const [game, setGame] = useState<WerewolfGame | null>(null)
  const [myRole, setMyRole] = useState<WerewolfMyRole | null>(null)
  const [players, setPlayers] = useState<WerewolfPlayer[]>([])
  const [events, setEvents] = useState<WerewolfEvent[]>([])
  const [loading, setLoading] = useState(true)
  const [cancelling, setCancelling] = useState(false)
  const [showCancelConfirm, setShowCancelConfirm] = useState(false)
  const [chatTrigger, setChatTrigger] = useState(0)
  const [phantomChatTrigger, setPhantomChatTrigger] = useState(0)
  const [votesTrigger, setVotesTrigger] = useState(0)

  const fetchData = useCallback(async () => {
    try {
      const gameData = await api.werewolfCurrentGame()
      setGame(gameData)

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

  const handleWSRefresh = useCallback((scope: RefreshScope) => {
    switch (scope) {
      case 'game':
      case 'players':
      case 'events':
      case 'phase_change':
        fetchData()
        break
      case 'chat':
        setChatTrigger(c => c + 1)
        break
      case 'phantom_chat':
        setPhantomChatTrigger(c => c + 1)
        break
      case 'votes':
        setVotesTrigger(c => c + 1)
        break
    }
  }, [fetchData])

  const { notify } = useGameWebSocket({
    gameId: game?.id && game.status !== 'preparing' && game.status !== 'finished' ? game.id : null,
    onRefresh: handleWSRefresh,
  })

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

  // No active game — show lobby
  if (!game || game.status === 'preparing') {
    return (
      <div className="py-6">
        <LobbyPanel onGameStarted={(g) => { setGame(g); fetchData() }} />

        <div className="max-w-2xl mx-auto mt-8">
          <div className="bg-bg-secondary border border-border-default rounded-lg p-6">
            <h2 className="font-semibold text-text-primary mb-3">How to Play</h2>
            <ul className="space-y-2 text-sm text-text-secondary">
              <li><span className="text-purple-400">Phantoms</span> secretly eliminate residents each night</li>
              <li><span className="text-blue-400">Citizens</span> discuss and vote to find the Phantoms</li>
              <li><span className="text-yellow-400">Oracle</span> investigates one person each night</li>
              <li><span className="text-green-400">Guardian</span> protects one person from attack</li>
              <li><span className="text-red-400">Fanatic</span> helps Phantoms while appearing as Citizen</li>
              <li><span className="text-amber-400">Debugger</span> identifies a target — eliminates opposite type (AI/Human), but dies if same type</li>
            </ul>
            <p className="text-xs text-text-muted mt-4">
              Create a lobby, choose speed and player count (5-15), then press Start.
              AI agents fill remaining slots. Use the chat to discuss who the Phantoms are!
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

  // Game finished — show results
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

  // Active game (day/night) — chat-centered layout
  const isDay = game.current_phase === 'day'
  const isAlive = myRole?.is_alive ?? false

  return (
    <div className="flex flex-col lg:flex-row gap-4 h-[calc(100vh-8rem)]">
      {/* Main: Chat */}
      <div className="flex-1 flex flex-col min-h-0 lg:min-h-full">
        <GameBanner game={game} onPhaseExpired={fetchData} compact />
        <div className="flex-1 mt-2 min-h-0">
          <ChatWindow
            refreshTrigger={chatTrigger}
            onMessageSent={() => notify('chat')}
            isDay={isDay}
            isAlive={isAlive}
          />
        </div>
      </div>

      {/* Sidebar */}
      <div className="w-full lg:w-80 flex-shrink-0 space-y-3 overflow-y-auto">
        {/* Cancel */}
        {resident && (
          <div className="flex justify-end">
            {showCancelConfirm ? (
              <div className="flex items-center gap-2 bg-red-900/20 border border-red-500/30 rounded-lg px-3 py-1.5 text-sm">
                <span className="text-red-400">Cancel?</span>
                <button
                  onClick={handleCancel}
                  disabled={cancelling}
                  className="px-2 py-0.5 bg-red-600 hover:bg-red-500 text-white rounded text-xs disabled:opacity-50"
                >
                  {cancelling ? '...' : 'Yes'}
                </button>
                <button
                  onClick={() => setShowCancelConfirm(false)}
                  className="px-2 py-0.5 bg-bg-tertiary text-text-secondary rounded text-xs"
                >
                  No
                </button>
              </div>
            ) : (
              <button
                onClick={() => setShowCancelConfirm(true)}
                className="flex items-center gap-1 text-xs text-text-muted hover:text-red-400 transition-colors"
              >
                <XCircle size={12} />
                Cancel
              </button>
            )}
          </div>
        )}

        {/* Role */}
        {myRole && <RoleCard role={myRole} compact />}

        {/* Players */}
        <PlayerGrid players={players} compact />

        {/* Day: Vote / Night: Action */}
        {isDay && (
          <DayVotePanel players={players} myRole={myRole} refreshTrigger={votesTrigger} compact />
        )}

        {!isDay && myRole && (
          <NightActionPanel role={myRole} players={players} compact />
        )}

        {/* Phantom Chat */}
        {myRole && myRole.team === 'phantoms' && (
          <PhantomChat refreshTrigger={phantomChatTrigger} compact />
        )}
      </div>
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
                  {g.winner_team === 'citizens' ? 'Citizens' : 'Phantoms'} won
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
