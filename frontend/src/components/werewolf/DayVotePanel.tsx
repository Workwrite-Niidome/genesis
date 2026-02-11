'use client'

import { useState, useEffect } from 'react'
import { WerewolfPlayer, WerewolfMyRole, api, WerewolfDayVotes } from '@/lib/api'
import { useAuthStore } from '@/stores/authStore'
import Card from '@/components/ui/Card'
import Button from '@/components/ui/Button'
import Avatar from '@/components/ui/Avatar'
import clsx from 'clsx'
import { Vote, CheckCircle, AlertCircle, TrendingUp } from 'lucide-react'

interface DayVotePanelProps {
  players: WerewolfPlayer[]
  myRole: WerewolfMyRole | null
  refreshTrigger?: number
}

export default function DayVotePanel({ players, myRole, refreshTrigger }: DayVotePanelProps) {
  const { resident } = useAuthStore()
  const [selectedTarget, setSelectedTarget] = useState<string | null>(null)
  const [reason, setReason] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)
  const [voteData, setVoteData] = useState<WerewolfDayVotes | null>(null)
  const [isLoadingVotes, setIsLoadingVotes] = useState(true)

  const alivePlayers = players.filter((p) => p.is_alive && p.id !== resident?.id)

  // Fetch current vote tally
  const fetchVotes = async () => {
    try {
      setIsLoadingVotes(true)
      const data = await api.werewolfDayVotes()
      setVoteData(data)
    } catch (error) {
      console.error('Failed to fetch votes:', error)
    } finally {
      setIsLoadingVotes(false)
    }
  }

  useEffect(() => {
    fetchVotes()
    const interval = setInterval(fetchVotes, 60000) // Fallback (WebSocket is primary)
    return () => clearInterval(interval)
  }, [])

  // WebSocket-triggered refresh
  useEffect(() => {
    if (refreshTrigger && refreshTrigger > 0) {
      fetchVotes()
    }
  }, [refreshTrigger])

  const handleSubmit = async () => {
    if (!selectedTarget) return

    setIsLoading(true)
    setMessage(null)

    try {
      const response = await api.werewolfDayVote(selectedTarget, reason || undefined)

      if (response.success) {
        setMessage({ type: 'success', text: response.message })
        setSelectedTarget(null)
        setReason('')
        // Refresh vote tally
        await fetchVotes()
      } else {
        setMessage({ type: 'error', text: response.message || 'Vote failed' })
      }
    } catch (error) {
      setMessage({
        type: 'error',
        text: error instanceof Error ? error.message : 'Failed to submit vote',
      })
    } finally {
      setIsLoading(false)
    }
  }

  if (!myRole?.is_alive) {
    return (
      <Card className="p-6">
        <div className="flex items-center gap-3 text-text-muted">
          <AlertCircle size={20} />
          <p>You have been eliminated and cannot vote.</p>
        </div>
      </Card>
    )
  }

  // Create vote count map
  const voteCountMap = new Map<string, number>()
  if (voteData?.tally) {
    voteData.tally.forEach((t) => {
      voteCountMap.set(t.target_id, t.votes)
    })
  }

  return (
    <div className="space-y-4">
      {/* Current Vote Tally */}
      {voteData && voteData.tally.length > 0 && (
        <Card className="p-4 border-orange-500/50 bg-gradient-to-br from-orange-900/10 to-amber-900/10">
          <div className="flex items-center gap-2 mb-3">
            <TrendingUp size={18} className="text-orange-400" />
            <h3 className="font-bold text-text-primary">Current Vote Tally</h3>
            <span className="text-xs text-text-muted ml-auto">
              {voteData.total_voted} / {voteData.total_alive} voted
            </span>
          </div>
          <div className="space-y-2">
            {voteData.tally
              .sort((a, b) => b.votes - a.votes)
              .map((tally) => (
                <div
                  key={tally.target_id}
                  className="flex items-center justify-between p-2 rounded bg-bg-tertiary"
                >
                  <span className="font-medium text-text-primary">{tally.target_name}</span>
                  <span className="px-2 py-1 rounded-full bg-orange-500/20 text-orange-400 text-sm font-semibold">
                    {tally.votes} vote{tally.votes !== 1 ? 's' : ''}
                  </span>
                </div>
              ))}
          </div>
        </Card>
      )}

      {/* Vote Form */}
      <Card className="p-6 border-blue-500/50 bg-gradient-to-br from-blue-900/10 to-indigo-900/10">
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2 rounded-lg bg-blue-500/20 text-blue-400">
            <Vote size={20} />
          </div>
          <div>
            <h3 className="text-lg font-bold text-text-primary">Cast Your Vote</h3>
            <p className="text-sm text-text-secondary">
              Vote to eliminate a suspected phantom
            </p>
          </div>
        </div>

        {message && (
          <div
            className={clsx(
              'p-3 rounded-lg mb-4 flex items-center gap-2',
              message.type === 'success' &&
                'bg-green-500/20 text-green-400 border border-green-500/30',
              message.type === 'error' && 'bg-red-500/20 text-red-400 border border-red-500/30'
            )}
          >
            {message.type === 'success' ? <CheckCircle size={18} /> : <AlertCircle size={18} />}
            <span className="text-sm">{message.text}</span>
          </div>
        )}

        <div className="space-y-2 mb-4 max-h-80 overflow-y-auto">
          {alivePlayers.map((player) => {
            const voteCount = voteCountMap.get(player.id) || 0

            return (
              <button
                key={player.id}
                onClick={() => setSelectedTarget(player.id)}
                className={clsx(
                  'w-full p-3 rounded-lg border transition-all text-left',
                  selectedTarget === player.id
                    ? 'border-blue-500 bg-blue-500/20'
                    : 'border-border-default bg-bg-tertiary hover:bg-bg-hover hover:border-border-hover'
                )}
              >
                <div className="flex items-center gap-3">
                  <Avatar src={player.avatar_url} name={player.name} size="sm" />
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-text-primary truncate">{player.name}</p>
                    <p className="text-xs text-text-secondary">{player.karma} karma</p>
                  </div>
                  <div className="flex items-center gap-2">
                    {voteCount > 0 && (
                      <span className="px-2 py-1 rounded-full bg-orange-500/20 text-orange-400 text-xs font-semibold">
                        {voteCount}
                      </span>
                    )}
                    {selectedTarget === player.id && (
                      <CheckCircle size={18} className="text-blue-400" />
                    )}
                  </div>
                </div>
              </button>
            )
          })}
        </div>

        {alivePlayers.length === 0 && (
          <div className="text-center py-8 text-text-muted">
            <AlertCircle size={32} className="mx-auto mb-2 opacity-50" />
            <p>No players available to vote for</p>
          </div>
        )}

        <div className="mb-4">
          <label className="block text-sm font-medium text-text-secondary mb-2">
            Reason (optional)
          </label>
          <textarea
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder="Explain why you're voting for this player..."
            className="w-full px-3 py-2 bg-bg-tertiary border border-border-default rounded-lg text-text-primary placeholder-text-muted focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
            rows={3}
            maxLength={500}
          />
          <p className="text-xs text-text-muted mt-1">{reason.length} / 500</p>
        </div>

        <Button
          onClick={handleSubmit}
          disabled={!selectedTarget || isLoading}
          isLoading={isLoading}
          variant="secondary"
          className="w-full"
        >
          Submit Vote
        </Button>
      </Card>
    </div>
  )
}
