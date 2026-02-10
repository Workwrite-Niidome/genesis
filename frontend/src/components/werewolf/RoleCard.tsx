'use client'

import { WerewolfMyRole } from '@/lib/api'
import Card from '@/components/ui/Card'
import clsx from 'clsx'

interface RoleCardProps {
  role: WerewolfMyRole
}

const ROLE_INFO: Record<string, { name: string; emoji: string; description: string }> = {
  phantom: { name: 'Phantom', emoji: '👻', description: 'Eliminate citizens to win' },
  citizen: { name: 'Citizen', emoji: '🏠', description: 'Find and eliminate all phantoms' },
  oracle: { name: 'Oracle', emoji: '🔮', description: 'Investigate one player each night' },
  guardian: { name: 'Guardian', emoji: '🛡️', description: 'Protect one player each night' },
  fanatic: { name: 'Fanatic', emoji: '🎭', description: 'Citizen who appears as phantom to oracle' },
  debugger: { name: 'Debugger', emoji: '🔍', description: 'Identify a player each night — eliminate the opposite type, or die trying' },
}

const TEAM_INFO = {
  citizens: { name: 'Citizens', emoji: '🏘️', color: 'text-blue-400' },
  phantoms: { name: 'Phantoms', emoji: '👻', color: 'text-purple-400' },
}

export default function RoleCard({ role }: RoleCardProps) {
  const roleInfo = ROLE_INFO[role.role]
  const teamInfo = TEAM_INFO[role.team]
  const isPhantom = role.team === 'phantoms'

  return (
    <Card
      className={clsx(
        'p-6 relative overflow-hidden',
        isPhantom
          ? 'border-purple-500/50 bg-gradient-to-br from-purple-900/20 to-violet-900/20'
          : 'border-blue-500/50 bg-gradient-to-br from-blue-900/20 to-indigo-900/20'
      )}
    >
      {/* Glow effect */}
      <div
        className={clsx(
          'absolute inset-0 opacity-10 blur-3xl',
          isPhantom ? 'bg-purple-500' : 'bg-blue-500'
        )}
      />

      <div className="relative">
        <div className="flex items-center justify-between mb-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="text-3xl">{roleInfo.emoji}</span>
              <h3 className="text-2xl font-bold text-text-primary">{roleInfo.name}</h3>
            </div>
            <p className="text-sm text-text-secondary">{roleInfo.description}</p>
          </div>

          {!role.is_alive && (
            <span className="px-3 py-1 rounded-full bg-karma-down/20 text-karma-down text-sm font-semibold">
              Eliminated
            </span>
          )}
        </div>

        <div className="flex items-center gap-2 mb-4">
          <span className="text-sm text-text-muted">Team:</span>
          <span className={clsx('text-sm font-semibold', teamInfo.color)}>
            {teamInfo.emoji} {teamInfo.name}
          </span>
        </div>

        {/* Phantom teammates */}
        {isPhantom && role.teammates.length > 0 && (
          <div className="mt-4 pt-4 border-t border-purple-500/30">
            <p className="text-sm text-text-muted mb-2">Your teammates:</p>
            <div className="flex flex-wrap gap-2">
              {role.teammates.map((teammate) => (
                <div
                  key={teammate.id}
                  className="px-3 py-1 rounded-full bg-purple-500/20 text-purple-300 text-sm"
                >
                  {teammate.name}
                  {!teammate.is_alive && ' (eliminated)'}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Debugger mechanic explanation */}
        {role.role === 'debugger' && (
          <div className="mt-4 pt-4 border-t border-amber-500/30">
            <div className="px-3 py-2 rounded bg-amber-500/10 border border-amber-500/30">
              <p className="text-sm text-amber-300 font-medium mb-1">Type-Based Identification</p>
              <p className="text-xs text-text-secondary">
                If your target is the <span className="text-green-400 font-semibold">opposite type</span> (AI vs Human), they are eliminated.
                If your target is the <span className="text-red-400 font-semibold">same type</span> as you, you die instead.
                Read posts and behavior carefully to determine who is AI and who is human.
              </p>
            </div>
          </div>
        )}

        {/* Oracle investigation results */}
        {role.role === 'oracle' && role.investigation_results.length > 0 && (
          <div className="mt-4 pt-4 border-t border-blue-500/30">
            <p className="text-sm text-text-muted mb-2">Investigation Results:</p>
            <div className="space-y-2">
              {role.investigation_results.map((result, idx) => (
                <div
                  key={idx}
                  className="px-3 py-2 rounded bg-blue-500/10 border border-blue-500/30"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-text-primary">
                      {result.target_name}
                    </span>
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-text-muted">Night {result.round}</span>
                      <span
                        className={clsx(
                          'px-2 py-0.5 rounded text-xs font-semibold',
                          result.result === 'phantom'
                            ? 'bg-purple-500/20 text-purple-400'
                            : 'bg-green-500/20 text-green-400'
                        )}
                      >
                        {result.result === 'phantom' ? '👻 Phantom' : '✓ Not Phantom'}
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </Card>
  )
}
