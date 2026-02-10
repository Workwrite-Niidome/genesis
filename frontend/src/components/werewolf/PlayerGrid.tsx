'use client'

import { WerewolfPlayer } from '@/lib/api'
import Card from '@/components/ui/Card'
import Avatar from '@/components/ui/Avatar'
import clsx from 'clsx'
import { Skull } from 'lucide-react'

interface PlayerGridProps {
  players: WerewolfPlayer[]
}

const ROLE_INFO: Record<string, { name: string; emoji: string }> = {
  phantom: { name: 'Phantom', emoji: '👻' },
  citizen: { name: 'Citizen', emoji: '🏠' },
  oracle: { name: 'Oracle', emoji: '🔮' },
  guardian: { name: 'Guardian', emoji: '🛡️' },
  fanatic: { name: 'Fanatic', emoji: '🎭' },
  debugger: { name: 'Debugger', emoji: '🔍' },
}

export default function PlayerGrid({ players }: PlayerGridProps) {
  const alivePlayers = players.filter((p) => p.is_alive)
  const deadPlayers = players.filter((p) => !p.is_alive)

  const renderPlayer = (player: WerewolfPlayer) => {
    const isAlive = player.is_alive
    const roleInfo = player.revealed_role ? ROLE_INFO[player.revealed_role] : null

    return (
      <Card
        key={player.id}
        className={clsx(
          'p-4 relative transition-all',
          !isAlive && 'opacity-60 bg-bg-tertiary border-border-default'
        )}
      >
        {!isAlive && (
          <div className="absolute top-2 right-2">
            <Skull size={16} className="text-karma-down" />
          </div>
        )}

        <div className="flex items-center gap-3 mb-3">
          <Avatar
            src={player.avatar_url}
            name={player.name}
            size="md"
            className={clsx(!isAlive && 'grayscale')}
          />
          <div className="flex-1 min-w-0">
            <h4 className={clsx(
              'font-semibold truncate',
              isAlive ? 'text-text-primary' : 'text-text-muted line-through'
            )}>
              {player.name}
            </h4>
            <p className="text-xs text-text-secondary">
              {player.karma} karma
            </p>
          </div>
        </div>

        {!isAlive && (
          <div className="space-y-1">
            {roleInfo && (
              <div className="flex items-center gap-2 text-sm">
                <span className="text-text-muted">Role:</span>
                <span className="font-medium text-text-primary">
                  {roleInfo.emoji} {roleInfo.name}
                </span>
              </div>
            )}
            {player.revealed_type && (
              <div className="flex items-center gap-2 text-sm">
                <span className="text-text-muted">Type:</span>
                <span className={clsx(
                  'px-2 py-0.5 rounded text-xs font-semibold',
                  player.revealed_type === 'human'
                    ? 'bg-blue-500/20 text-blue-400'
                    : 'bg-purple-500/20 text-purple-400'
                )}>
                  {player.revealed_type === 'human' ? '👤 Human' : '🤖 Agent'}
                </span>
              </div>
            )}
            {player.eliminated_by && (
              <div className="text-xs text-text-muted mt-2">
                {player.eliminated_by === 'phantom_kill' && '👻 Eliminated by phantoms'}
                {player.eliminated_by === 'phantom_attack' && '👻 Eliminated by phantoms'}
                {player.eliminated_by === 'vote' && '🗳️ Voted out'}
                {player.eliminated_by === 'identifier_kill' && '🔍 Identified by Debugger'}
                {player.eliminated_by === 'identifier_backfire' && '🔍 Debugger backfire'}
                {player.eliminated_round && ` (Round ${player.eliminated_round})`}
              </div>
            )}
          </div>
        )}

        {isAlive && (
          <div className="mt-2">
            <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full bg-green-500/20 text-green-400 text-xs font-semibold">
              <span className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
              Alive
            </span>
          </div>
        )}
      </Card>
    )
  }

  return (
    <div className="space-y-6">
      {alivePlayers.length > 0 && (
        <div>
          <h3 className="text-lg font-bold text-text-primary mb-4">
            Alive ({alivePlayers.length})
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {alivePlayers.map(renderPlayer)}
          </div>
        </div>
      )}

      {deadPlayers.length > 0 && (
        <div>
          <h3 className="text-lg font-bold text-text-muted mb-4">
            Eliminated ({deadPlayers.length})
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {deadPlayers.map(renderPlayer)}
          </div>
        </div>
      )}
    </div>
  )
}
