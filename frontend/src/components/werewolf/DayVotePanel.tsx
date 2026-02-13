'use client'

import { useState, useEffect } from 'react'
import { WerewolfPlayer, WerewolfMyRole, api, WerewolfDayVotes } from '@/lib/api'
import { useAuthStore } from '@/stores/authStore'
import Button from '@/components/ui/Button'
import clsx from 'clsx'
import { Vote, CheckCircle, AlertCircle, TrendingUp } from 'lucide-react'

interface DayVotePanelProps {
  players: WerewolfPlayer[]
  myRole: WerewolfMyRole | null
  refreshTrigger?: number
  compact?: boolean
}

export default function DayVotePanel({ players, myRole, refreshTrigger, compact }: DayVotePanelProps) {
  const { resident } = useAuthStore()
  const [selectedTarget, setSelectedTarget] = useState<string | null>(null)
  const [reason, setReason] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)
  const [voteData, setVoteData] = useState<WerewolfDayVotes | null>(null)
  const [isLoadingVotes, setIsLoadingVotes] = useState(true)

  const alivePlayers = players.filter((p) => p.is_alive && p.id !== resident?.id)

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
    const interval = setInterval(fetchVotes, 30000)
    return () => clearInterval(interval)
  }, [])

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
      <div className="p-3 rounded-lg border border-border-default bg-bg-secondary">
        <div className="flex items-center gap-2 text-text-muted text-sm">
          <AlertCircle size={16} />
          <p>You have been eliminated.</p>
        </div>
      </div>
    )
  }

  const voteCountMap = new Map<string, number>()
  if (voteData?.tally) {
    voteData.tally.forEach((t) => {
      voteCountMap.set(t.target_id, t.votes)
    })
  }

  return (
    <div className={clsx('rounded-lg border bg-bg-secondary overflow-hidden', compact ? 'border-border-default' : 'border-blue-500/50')}>
      {/* Header */}
      <div className={clsx('px-3 py-2 border-b', compact ? 'border-border-default' : 'border-blue-500/30 bg-blue-900/10')}>
        <div className="flex items-center gap-2">
          <Vote size={16} className="text-blue-400" />
          <span className="text-sm font-bold text-text-primary">Vote</span>
          {voteData && (
            <span className="text-xs text-text-muted ml-auto">
              {voteData.total_voted}/{voteData.total_alive}
            </span>
          )}
        </div>
      </div>

      <div className="p-3 space-y-2">
        {/* Vote Tally */}
        {voteData && voteData.tally.length > 0 && (
          <div className="space-y-1 pb-2 border-b border-border-default">
            {voteData.tally
              .sort((a, b) => b.votes - a.votes)
              .slice(0, compact ? 3 : undefined)
              .map((tally) => (
                <div key={tally.target_id} className="flex items-center justify-between text-sm">
                  <span className="text-text-primary truncate">{tally.target_name}</span>
                  <span className="px-1.5 py-0.5 rounded bg-orange-500/20 text-orange-400 text-xs font-semibold flex-shrink-0">
                    {tally.votes}
                  </span>
                </div>
              ))}
          </div>
        )}

        {/* Message */}
        {message && (
          <div
            className={clsx(
              'p-2 rounded text-xs flex items-center gap-1.5',
              message.type === 'success' && 'bg-green-500/20 text-green-400',
              message.type === 'error' && 'bg-red-500/20 text-red-400'
            )}
          >
            {message.type === 'success' ? <CheckCircle size={14} /> : <AlertCircle size={14} />}
            <span>{message.text}</span>
          </div>
        )}

        {/* Target selection */}
        <div className={clsx('space-y-1', compact ? 'max-h-40' : 'max-h-60', 'overflow-y-auto')}>
          {alivePlayers.map((player) => {
            const voteCount = voteCountMap.get(player.id) || 0
            return (
              <button
                key={player.id}
                onClick={() => setSelectedTarget(player.id)}
                className={clsx(
                  'w-full px-2 py-1.5 rounded border transition-all text-left text-sm',
                  selectedTarget === player.id
                    ? 'border-blue-500 bg-blue-500/20'
                    : 'border-transparent bg-bg-tertiary hover:bg-bg-hover'
                )}
              >
                <div className="flex items-center gap-2">
                  <span className="text-text-primary truncate flex-1">{player.name}</span>
                  {voteCount > 0 && (
                    <span className="px-1 py-0.5 rounded bg-orange-500/20 text-orange-400 text-xs flex-shrink-0">
                      {voteCount}
                    </span>
                  )}
                  {selectedTarget === player.id && (
                    <CheckCircle size={14} className="text-blue-400 flex-shrink-0" />
                  )}
                </div>
              </button>
            )
          })}
        </div>

        {!compact && (
          <textarea
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder="Reason (optional)..."
            className="w-full px-2 py-1.5 bg-bg-tertiary border border-border-default rounded text-sm text-text-primary placeholder-text-muted focus:outline-none focus:ring-1 focus:ring-blue-500 resize-none"
            rows={2}
            maxLength={500}
          />
        )}

        <Button
          onClick={handleSubmit}
          disabled={!selectedTarget || isLoading}
          isLoading={isLoading}
          variant="secondary"
          className="w-full text-sm py-1.5"
        >
          Vote
        </Button>
      </div>
    </div>
  )
}
