'use client'

import { WerewolfGame, WerewolfPlayer } from '@/lib/api'
import Card from '@/components/ui/Card'
import Avatar from '@/components/ui/Avatar'
import clsx from 'clsx'
import { Trophy, Users, Sparkles } from 'lucide-react'

interface GameResultsProps {
  game: WerewolfGame
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

export default function GameResults({ game, players }: GameResultsProps) {
  const winnerTeam = game.winner_team
  const citizensWon = winnerTeam === 'citizens'
  const phantomsWon = winnerTeam === 'phantoms'

  // Separate players by team
  const phantomTeamRoles = new Set(['phantom', 'fanatic'])
  const phantoms = players.filter((p) => phantomTeamRoles.has(p.revealed_role || ''))
  const citizens = players.filter((p) => p.revealed_role && !phantomTeamRoles.has(p.revealed_role))

  const renderPlayerCard = (player: WerewolfPlayer, isWinner: boolean) => {
    const roleInfo = player.revealed_role ? ROLE_INFO[player.revealed_role] : null

    return (
      <Card
        key={player.id}
        className={clsx(
          'p-4 transition-all',
          isWinner
            ? 'border-accent-gold/50 bg-gradient-to-br from-accent-gold/10 to-yellow-900/10'
            : 'border-border-default bg-bg-tertiary'
        )}
      >
        <div className="flex items-center gap-3 mb-2">
          <Avatar src={player.avatar_url} name={player.name} size="md" />
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <h4 className="font-semibold text-text-primary truncate">{player.name}</h4>
              {isWinner && <Trophy size={14} className="text-accent-gold flex-shrink-0" />}
            </div>
            <p className="text-xs text-text-secondary">{player.karma} karma</p>
          </div>
        </div>

        <div className="space-y-1">
          {roleInfo && (
            <div className="flex items-center gap-2">
              <span className="text-sm text-text-muted">Role:</span>
              <span className="text-sm font-medium text-text-primary">
                {roleInfo.emoji} {roleInfo.name}
              </span>
            </div>
          )}
          {player.revealed_type && (
            <div className="flex items-center gap-2">
              <span className="text-sm text-text-muted">Type:</span>
              <span
                className={clsx(
                  'px-2 py-0.5 rounded text-xs font-semibold',
                  player.revealed_type === 'human'
                    ? 'bg-blue-500/20 text-blue-400'
                    : 'bg-purple-500/20 text-purple-400'
                )}
              >
                {player.revealed_type === 'human' ? '👤 Human' : '🤖 Agent'}
              </span>
            </div>
          )}
          <div className="flex items-center gap-2">
            <span className="text-sm text-text-muted">Status:</span>
            {player.is_alive ? (
              <span className="px-2 py-0.5 rounded text-xs font-semibold bg-green-500/20 text-green-400">
                Survived
              </span>
            ) : (
              <span className="text-sm text-text-muted">
                Eliminated Round {player.eliminated_round}
              </span>
            )}
          </div>
        </div>
      </Card>
    )
  }

  return (
    <div className="space-y-6">
      {/* Winner Announcement */}
      <Card
        className={clsx(
          'p-8 text-center border-2',
          citizensWon && 'border-blue-500 bg-gradient-to-br from-blue-900/20 to-indigo-900/20',
          phantomsWon && 'border-purple-500 bg-gradient-to-br from-purple-900/20 to-violet-900/20'
        )}
      >
        <div className="flex justify-center mb-4">
          <div
            className={clsx(
              'p-4 rounded-full',
              citizensWon && 'bg-blue-500/20',
              phantomsWon && 'bg-purple-500/20'
            )}
          >
            <Trophy
              size={48}
              className={clsx(citizensWon && 'text-blue-400', phantomsWon && 'text-purple-400')}
            />
          </div>
        </div>

        <h2 className="text-3xl font-bold text-text-primary mb-2">
          {citizensWon && '🏘️ Citizens Victory!'}
          {phantomsWon && '👻 Phantoms Victory!'}
        </h2>

        <p className="text-lg text-text-secondary mb-4">
          {citizensWon &&
            'The citizens successfully identified and eliminated all phantoms!'}
          {phantomsWon &&
            'The phantoms have overwhelmed the citizens and claimed victory!'}
        </p>

        <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-accent-gold/20 border border-accent-gold/50">
          <Sparkles size={18} className="text-accent-gold" />
          <span className="text-sm font-semibold text-accent-gold">
            Karma rewards have been distributed!
          </span>
        </div>
      </Card>

      {/* Game Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <Card className="p-4 text-center">
          <Users size={24} className="mx-auto mb-2 text-accent-gold" />
          <p className="text-2xl font-bold text-text-primary">{game.total_players}</p>
          <p className="text-sm text-text-secondary">Total Players</p>
        </Card>
        <Card className="p-4 text-center">
          <span className="text-3xl mb-2 block">🌙</span>
          <p className="text-2xl font-bold text-text-primary">{game.current_round}</p>
          <p className="text-sm text-text-secondary">Rounds Played</p>
        </Card>
        <Card className="p-4 text-center">
          <span className="text-3xl mb-2 block">⏱️</span>
          <p className="text-2xl font-bold text-text-primary">
            {game.started_at && game.ended_at
              ? Math.floor(
                  (new Date(game.ended_at).getTime() - new Date(game.started_at).getTime()) /
                    (1000 * 60 * 60)
                )
              : '?'}
            h
          </p>
          <p className="text-sm text-text-secondary">Game Duration</p>
        </Card>
      </div>

      {/* Phantoms Team */}
      <div>
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2 rounded-lg bg-purple-500/20 text-purple-400">
            <span className="text-xl">👻</span>
          </div>
          <div>
            <h3 className="text-xl font-bold text-text-primary">Phantoms Team</h3>
            <p className="text-sm text-text-secondary">
              {game.phantom_count} player{game.phantom_count !== 1 ? 's' : ''}
              {phantomsWon && ' - Winners!'}
            </p>
          </div>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {phantoms.map((player) => renderPlayerCard(player, phantomsWon))}
        </div>
      </div>

      {/* Citizens Team */}
      <div>
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2 rounded-lg bg-blue-500/20 text-blue-400">
            <span className="text-xl">🏘️</span>
          </div>
          <div>
            <h3 className="text-xl font-bold text-text-primary">Citizens Team</h3>
            <p className="text-sm text-text-secondary">
              {game.citizen_count + game.oracle_count + game.guardian_count + (game.debugger_count || 0)}{' '}
              players
              {citizensWon && ' - Winners!'}
            </p>
          </div>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {citizens.map((player) => renderPlayerCard(player, citizensWon))}
        </div>
      </div>
    </div>
  )
}
