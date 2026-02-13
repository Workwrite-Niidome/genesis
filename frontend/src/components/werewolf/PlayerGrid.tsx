'use client'

import { WerewolfPlayer } from '@/lib/api'
import clsx from 'clsx'
import { Skull } from 'lucide-react'

interface PlayerGridProps {
  players: WerewolfPlayer[]
  compact?: boolean
}

const ROLE_INFO: Record<string, { name: string; emoji: string }> = {
  phantom: { name: 'Phantom', emoji: '👻' },
  citizen: { name: 'Citizen', emoji: '🏠' },
  oracle: { name: 'Oracle', emoji: '🔮' },
  guardian: { name: 'Guardian', emoji: '🛡️' },
  fanatic: { name: 'Fanatic', emoji: '🎭' },
  debugger: { name: 'Debugger', emoji: '🔍' },
}

export default function PlayerGrid({ players, compact }: PlayerGridProps) {
  const alivePlayers = players.filter((p) => p.is_alive)
  const deadPlayers = players.filter((p) => !p.is_alive)

  if (compact) {
    return (
      <div className="rounded-lg border border-border-default bg-bg-secondary p-3">
        <h4 className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-2">
          Players ({alivePlayers.length}/{players.length})
        </h4>
        <div className="space-y-1">
          {alivePlayers.map((p) => (
            <div key={p.id} className="flex items-center gap-2 py-1">
              <span className="w-2 h-2 rounded-full bg-green-400 flex-shrink-0" />
              <span className="text-sm text-text-primary truncate">{p.name}</span>
            </div>
          ))}
          {deadPlayers.map((p) => {
            const roleInfo = p.revealed_role ? ROLE_INFO[p.revealed_role] : null
            return (
              <div key={p.id} className="flex items-center gap-2 py-1 opacity-50">
                <Skull size={10} className="text-karma-down flex-shrink-0" />
                <span className="text-sm text-text-muted line-through truncate">{p.name}</span>
                {roleInfo && <span className="text-xs flex-shrink-0">{roleInfo.emoji}</span>}
              </div>
            )
          })}
        </div>
      </div>
    )
  }

  // Full grid view (used in dedicated Players tab / finished game)
  return (
    <div className="space-y-6">
      {alivePlayers.length > 0 && (
        <div>
          <h3 className="text-lg font-bold text-text-primary mb-4">
            Alive ({alivePlayers.length})
          </h3>
          <div className="space-y-2">
            {alivePlayers.map((p) => (
              <div key={p.id} className="flex items-center gap-3 p-3 rounded-lg bg-bg-secondary border border-border-default">
                <div className="w-8 h-8 rounded-full bg-purple-500/20 flex items-center justify-center text-purple-400 text-sm font-bold flex-shrink-0">
                  {p.name.charAt(0).toUpperCase()}
                </div>
                <span className="font-medium text-text-primary truncate">{p.name}</span>
                <span className="ml-auto inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-green-500/20 text-green-400 text-xs font-semibold flex-shrink-0">
                  <span className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" />
                  Alive
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {deadPlayers.length > 0 && (
        <div>
          <h3 className="text-lg font-bold text-text-muted mb-4">
            Eliminated ({deadPlayers.length})
          </h3>
          <div className="space-y-2">
            {deadPlayers.map((p) => {
              const roleInfo = p.revealed_role ? ROLE_INFO[p.revealed_role] : null
              return (
                <div key={p.id} className="flex items-center gap-3 p-3 rounded-lg bg-bg-tertiary border border-border-default opacity-60">
                  <div className="w-8 h-8 rounded-full bg-bg-secondary flex items-center justify-center text-text-muted text-sm font-bold flex-shrink-0">
                    {p.name.charAt(0).toUpperCase()}
                  </div>
                  <div className="flex-1 min-w-0">
                    <span className="font-medium text-text-muted line-through truncate block">{p.name}</span>
                    {p.eliminated_by && (
                      <span className="text-xs text-text-muted">
                        {p.eliminated_by === 'phantom_kill' || p.eliminated_by === 'phantom_attack' ? '👻 By phantoms' :
                         p.eliminated_by === 'vote' ? '🗳️ Voted out' :
                         p.eliminated_by === 'identifier_kill' ? '🔍 Debugger' :
                         p.eliminated_by === 'identifier_backfire' ? '🔍 Backfire' : p.eliminated_by}
                        {p.eliminated_round ? ` (R${p.eliminated_round})` : ''}
                      </span>
                    )}
                  </div>
                  {roleInfo && (
                    <span className="text-sm flex-shrink-0">{roleInfo.emoji} {roleInfo.name}</span>
                  )}
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}
