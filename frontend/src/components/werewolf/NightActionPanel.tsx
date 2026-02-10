'use client'

import { useState } from 'react'
import { WerewolfMyRole, WerewolfPlayer, api } from '@/lib/api'
import Card from '@/components/ui/Card'
import Button from '@/components/ui/Button'
import Avatar from '@/components/ui/Avatar'
import clsx from 'clsx'
import { Moon, Skull, Eye, Shield, AlertCircle, CheckCircle, Search } from 'lucide-react'

interface NightActionPanelProps {
  role: WerewolfMyRole
  players: WerewolfPlayer[]
}

export default function NightActionPanel({ role, players }: NightActionPanelProps) {
  const [selectedTarget, setSelectedTarget] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)

  const isPhantom = role.role === 'phantom'
  const isOracle = role.role === 'oracle'
  const isGuardian = role.role === 'guardian'
  const isDebugger = role.role === 'debugger'
  const canAct = isPhantom || isOracle || isGuardian || isDebugger

  if (!role.is_alive) {
    return (
      <Card className="p-6">
        <div className="flex items-center gap-3 text-text-muted">
          <Skull size={20} />
          <p>You have been eliminated and cannot take night actions.</p>
        </div>
      </Card>
    )
  }

  if (!canAct) {
    return (
      <Card className="p-6">
        <div className="flex items-center gap-3 text-text-muted">
          <Moon size={20} />
          <div>
            <p className="font-medium text-text-primary mb-1">Waiting for night to end...</p>
            <p className="text-sm">
              As a {role.role === 'citizen' ? 'Citizen' : 'Fanatic'}, you have no special actions
              during the night. Rest and prepare for the day ahead.
            </p>
          </div>
        </div>
      </Card>
    )
  }

  // Get valid targets based on role
  let validTargets: WerewolfPlayer[] = []
  let actionTitle = ''
  let actionDescription = ''
  let actionIcon = Moon

  if (isPhantom) {
    // Phantoms can attack alive citizens (anyone not on their team)
    const teammateIds = new Set(role.teammates.map((t) => t.id))
    validTargets = players.filter(
      (p) => p.is_alive && p.id !== role.teammates[0]?.id && !teammateIds.has(p.id)
    )
    actionTitle = 'Select Attack Target'
    actionDescription = 'Choose a citizen to eliminate tonight'
    actionIcon = Skull
  } else if (isOracle) {
    // Oracle can investigate any alive player
    validTargets = players.filter((p) => p.is_alive)
    actionTitle = 'Select Investigation Target'
    actionDescription = 'Choose a player to investigate their true nature'
    actionIcon = Eye
  } else if (isGuardian) {
    // Guardian can protect any alive player
    validTargets = players.filter((p) => p.is_alive)
    actionTitle = 'Select Protection Target'
    actionDescription = 'Choose a player to protect from phantom attacks tonight'
    actionIcon = Shield
  } else if (isDebugger) {
    // Debugger can target any alive player (except self)
    validTargets = players.filter((p) => p.is_alive)
    actionTitle = 'Select Identification Target'
    actionDescription = 'If opposite type (AI/Human) → eliminated. If same type → you die.'
    actionIcon = Search
  }

  const handleSubmit = async () => {
    if (!selectedTarget) return

    setIsLoading(true)
    setMessage(null)

    try {
      let response

      if (isPhantom) {
        response = await api.werewolfNightAttack(selectedTarget)
      } else if (isOracle) {
        response = await api.werewolfNightInvestigate(selectedTarget)
      } else if (isGuardian) {
        response = await api.werewolfNightProtect(selectedTarget)
      } else if (isDebugger) {
        response = await api.werewolfNightIdentify(selectedTarget)
      }

      if (response?.success) {
        setMessage({ type: 'success', text: response.message })
        setSelectedTarget(null)
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

  const ActionIcon = actionIcon

  return (
    <Card
      className={clsx(
        'p-6',
        isPhantom && 'border-purple-500/50 bg-gradient-to-br from-purple-900/10 to-violet-900/10',
        (isOracle || isGuardian) &&
          'border-blue-500/50 bg-gradient-to-br from-blue-900/10 to-indigo-900/10',
        isDebugger && 'border-amber-500/50 bg-gradient-to-br from-amber-900/10 to-orange-900/10'
      )}
    >
      <div className="flex items-center gap-3 mb-4">
        <div
          className={clsx(
            'p-2 rounded-lg',
            isPhantom && 'bg-purple-500/20 text-purple-400',
            (isOracle || isGuardian) && 'bg-blue-500/20 text-blue-400',
            isDebugger && 'bg-amber-500/20 text-amber-400'
          )}
        >
          <ActionIcon size={20} />
        </div>
        <div>
          <h3 className="text-lg font-bold text-text-primary">{actionTitle}</h3>
          <p className="text-sm text-text-secondary">{actionDescription}</p>
        </div>
      </div>

      {message && (
        <div
          className={clsx(
            'p-3 rounded-lg mb-4 flex items-center gap-2',
            message.type === 'success' && 'bg-green-500/20 text-green-400 border border-green-500/30',
            message.type === 'error' && 'bg-red-500/20 text-red-400 border border-red-500/30'
          )}
        >
          {message.type === 'success' ? (
            <CheckCircle size={18} />
          ) : (
            <AlertCircle size={18} />
          )}
          <span className="text-sm">{message.text}</span>
        </div>
      )}

      <div className="space-y-2 mb-4 max-h-80 overflow-y-auto">
        {validTargets.map((player) => (
          <button
            key={player.id}
            onClick={() => setSelectedTarget(player.id)}
            className={clsx(
              'w-full p-3 rounded-lg border transition-all text-left',
              selectedTarget === player.id
                ? isPhantom
                  ? 'border-purple-500 bg-purple-500/20'
                  : isDebugger
                    ? 'border-amber-500 bg-amber-500/20'
                    : 'border-blue-500 bg-blue-500/20'
                : 'border-border-default bg-bg-tertiary hover:bg-bg-hover hover:border-border-hover'
            )}
          >
            <div className="flex items-center gap-3">
              <Avatar src={player.avatar_url} alt={player.name} size="sm" />
              <div className="flex-1 min-w-0">
                <p className="font-medium text-text-primary truncate">{player.name}</p>
                <p className="text-xs text-text-secondary">{player.karma} karma</p>
              </div>
              {selectedTarget === player.id && (
                <CheckCircle
                  size={18}
                  className={isPhantom ? 'text-purple-400' : isDebugger ? 'text-amber-400' : 'text-blue-400'}
                />
              )}
            </div>
          </button>
        ))}
      </div>

      {validTargets.length === 0 && (
        <div className="text-center py-8 text-text-muted">
          <AlertCircle size={32} className="mx-auto mb-2 opacity-50" />
          <p>No valid targets available</p>
        </div>
      )}

      <Button
        onClick={handleSubmit}
        disabled={!selectedTarget || isLoading}
        isLoading={isLoading}
        variant={isPhantom ? 'primary' : 'secondary'}
        className="w-full"
      >
        {isPhantom && 'Submit Attack'}
        {isOracle && 'Submit Investigation'}
        {isGuardian && 'Submit Protection'}
        {isDebugger && 'Submit Identification'}
      </Button>
    </Card>
  )
}
