'use client'

import { useState } from 'react'
import { WerewolfMyRole, WerewolfPlayer, api } from '@/lib/api'
import { useAuthStore } from '@/stores/authStore'
import Button from '@/components/ui/Button'
import clsx from 'clsx'
import { Moon, Skull, Eye, Shield, AlertCircle, CheckCircle, Search } from 'lucide-react'

interface NightActionPanelProps {
  role: WerewolfMyRole
  players: WerewolfPlayer[]
  compact?: boolean
}

export default function NightActionPanel({ role, players, compact }: NightActionPanelProps) {
  const { resident } = useAuthStore()
  const [selectedTarget, setSelectedTarget] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [submitted, setSubmitted] = useState(false)
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)

  const isPhantom = role.role === 'phantom'
  const isOracle = role.role === 'oracle'
  const isGuardian = role.role === 'guardian'
  const isDebugger = role.role === 'debugger'
  const canAct = isPhantom || isOracle || isGuardian || isDebugger

  if (!role.is_alive) {
    return (
      <div className="p-3 rounded-lg border border-border-default bg-bg-secondary">
        <div className="flex items-center gap-2 text-text-muted text-sm">
          <Skull size={16} />
          <p>You have been eliminated.</p>
        </div>
      </div>
    )
  }

  if (!canAct) {
    return (
      <div className="p-3 rounded-lg border border-border-default bg-bg-secondary">
        <div className="flex items-center gap-2 text-text-muted text-sm">
          <Moon size={16} />
          <p>Waiting for night to end...</p>
        </div>
      </div>
    )
  }

  const myId = resident?.id
  let validTargets: WerewolfPlayer[] = []
  let actionLabel = ''
  let accentColor = 'blue'

  if (isPhantom) {
    const teammateIds = new Set(role.teammates.map((t) => t.id))
    validTargets = players.filter((p) => p.is_alive && p.id !== myId && !teammateIds.has(p.id))
    actionLabel = 'Attack'
    accentColor = 'purple'
  } else if (isOracle) {
    validTargets = players.filter((p) => p.is_alive && p.id !== myId)
    actionLabel = 'Investigate'
  } else if (isGuardian) {
    validTargets = players.filter((p) => p.is_alive)
    actionLabel = 'Protect'
  } else if (isDebugger) {
    validTargets = players.filter((p) => p.is_alive && p.id !== myId)
    actionLabel = 'Identify'
    accentColor = 'amber'
  }

  const handleSubmit = async () => {
    if (!selectedTarget) return

    setIsLoading(true)
    setMessage(null)

    try {
      let response
      if (isPhantom) response = await api.werewolfNightAttack(selectedTarget)
      else if (isOracle) response = await api.werewolfNightInvestigate(selectedTarget)
      else if (isGuardian) response = await api.werewolfNightProtect(selectedTarget)
      else if (isDebugger) response = await api.werewolfNightIdentify(selectedTarget)

      if (response?.success) {
        setMessage({ type: 'success', text: response.message })
        setSelectedTarget(null)
        setSubmitted(true)
      } else {
        setMessage({ type: 'error', text: response?.message || 'Action failed' })
      }
    } catch (error) {
      setMessage({
        type: 'error',
        text: error instanceof Error ? error.message : 'Failed to submit action',
      })
    } finally {
      setIsLoading(false)
    }
  }

  const borderColor = accentColor === 'purple' ? 'border-purple-500/40' :
                       accentColor === 'amber' ? 'border-amber-500/40' :
                       'border-blue-500/40'

  return (
    <div className={clsx('rounded-lg border bg-bg-secondary overflow-hidden', borderColor)}>
      {/* Header */}
      <div className={clsx('px-3 py-2 border-b', borderColor,
        accentColor === 'purple' ? 'bg-purple-900/10' :
        accentColor === 'amber' ? 'bg-amber-900/10' :
        'bg-blue-900/10'
      )}>
        <div className="flex items-center gap-2">
          {isPhantom && <Skull size={16} className="text-purple-400" />}
          {isOracle && <Eye size={16} className="text-blue-400" />}
          {isGuardian && <Shield size={16} className="text-blue-400" />}
          {isDebugger && <Search size={16} className="text-amber-400" />}
          <span className="text-sm font-bold text-text-primary">{actionLabel}</span>
        </div>
      </div>

      <div className="p-3 space-y-2">
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

        <div className={clsx('space-y-1', compact ? 'max-h-40' : 'max-h-60', 'overflow-y-auto')}>
          {validTargets.map((player) => (
            <button
              key={player.id}
              onClick={() => !submitted && setSelectedTarget(player.id)}
              disabled={submitted}
              className={clsx(
                'w-full px-2 py-1.5 rounded border transition-all text-left text-sm',
                selectedTarget === player.id
                  ? accentColor === 'purple' ? 'border-purple-500 bg-purple-500/20' :
                    accentColor === 'amber' ? 'border-amber-500 bg-amber-500/20' :
                    'border-blue-500 bg-blue-500/20'
                  : 'border-transparent bg-bg-tertiary hover:bg-bg-hover'
              )}
            >
              <div className="flex items-center gap-2">
                <span className="text-text-primary truncate flex-1">{player.name}</span>
                {selectedTarget === player.id && (
                  <CheckCircle size={14} className={
                    accentColor === 'purple' ? 'text-purple-400' :
                    accentColor === 'amber' ? 'text-amber-400' :
                    'text-blue-400'
                  } />
                )}
              </div>
            </button>
          ))}
        </div>

        {validTargets.length === 0 && (
          <div className="text-center py-4 text-text-muted text-sm">
            <AlertCircle size={20} className="mx-auto mb-1 opacity-50" />
            No valid targets
          </div>
        )}

        <Button
          onClick={handleSubmit}
          disabled={!selectedTarget || isLoading || submitted}
          isLoading={isLoading}
          variant="secondary"
          className="w-full text-sm py-1.5"
        >
          {actionLabel}
        </Button>
      </div>
    </div>
  )
}
