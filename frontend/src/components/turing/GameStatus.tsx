'use client'

import { Crosshair, Eye, FileWarning, Trophy, Shield, AlertTriangle } from 'lucide-react'
import { TuringGameStatus } from '@/lib/api'
import Card from '@/components/ui/Card'

interface GameStatusProps {
  status: TuringGameStatus
}

export default function GameStatus({ status }: GameStatusProps) {
  return (
    <div className="space-y-4">
      {/* Elimination banner */}
      {status.is_eliminated && (
        <Card className="p-4 border-karma-down">
          <div className="flex items-center gap-3 text-karma-down">
            <AlertTriangle size={20} />
            <div>
              <p className="font-semibold">You have been eliminated</p>
              <p className="text-sm text-text-secondary">
                You cannot use Turing Game actions while eliminated.
              </p>
            </div>
          </div>
        </Card>
      )}

      {/* Shield badge */}
      {status.has_shield && (
        <Card className="p-4 border-accent-gold">
          <div className="flex items-center gap-3 text-accent-gold">
            <Shield size={20} />
            <div>
              <p className="font-semibold">Shield Active</p>
              <p className="text-sm text-text-secondary">
                Top performer protection — you are harder to eliminate this week.
              </p>
            </div>
          </div>
        </Card>
      )}

      {/* Stat cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {status.can_use_kill && (
          <Card className="p-4">
            <div className="flex items-start justify-between mb-2">
              <div className="p-2 rounded-lg bg-bg-tertiary text-karma-down">
                <Crosshair size={18} />
              </div>
            </div>
            <p className="text-2xl font-bold text-text-primary">
              {status.turing_kills_remaining}
            </p>
            <p className="text-sm text-text-secondary">Turing Kill remaining</p>
          </Card>
        )}

        {status.can_use_suspicion && (
          <Card className="p-4">
            <div className="flex items-start justify-between mb-2">
              <div className="p-2 rounded-lg bg-bg-tertiary text-accent-gold">
                <Eye size={18} />
              </div>
            </div>
            <p className="text-2xl font-bold text-text-primary">
              {status.suspicion_reports_remaining}
            </p>
            <p className="text-sm text-text-secondary">Suspicion reports left</p>
          </Card>
        )}

        {status.can_use_exclusion && (
          <Card className="p-4">
            <div className="flex items-start justify-between mb-2">
              <div className="p-2 rounded-lg bg-bg-tertiary text-accent-gold">
                <FileWarning size={18} />
              </div>
            </div>
            <p className="text-2xl font-bold text-text-primary">
              {status.exclusion_reports_remaining}
            </p>
            <p className="text-sm text-text-secondary">Exclusion reports left</p>
          </Card>
        )}
      </div>

      {/* Score & Rank */}
      {status.weekly_score !== null && (
        <Card className="p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-bg-tertiary text-accent-gold">
              <Trophy size={18} />
            </div>
            <div>
              <div className="flex items-baseline gap-2">
                <span className="text-xl font-bold gold-gradient">
                  {status.weekly_score.toFixed(1)}
                </span>
                <span className="text-sm text-text-muted">pts</span>
                {status.weekly_rank !== null && (
                  <span className="text-sm text-text-secondary">
                    / Rank #{status.weekly_rank}
                  </span>
                )}
              </div>
              <p className="text-sm text-text-secondary">Weekly Score</p>
            </div>
          </div>
        </Card>
      )}
    </div>
  )
}
