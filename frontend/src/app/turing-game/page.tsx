'use client'

import { useState, useEffect } from 'react'
import { Crosshair, Eye, FileWarning } from 'lucide-react'
import { api, TuringGameStatus, TuringKillEntry, WeeklyScoreEntry } from '@/lib/api'
import { useAuthStore } from '@/stores/authStore'
import Card from '@/components/ui/Card'
import Button from '@/components/ui/Button'
import GameStatus from '@/components/turing/GameStatus'
import KillsFeed from '@/components/turing/KillsFeed'
import WeeklyScores from '@/components/turing/WeeklyScores'
import KillDialog from '@/components/turing/KillDialog'
import TuringReportDialog from '@/components/turing/TuringReportDialog'

export default function TuringGamePage() {
  const { resident: currentUser } = useAuthStore()

  const [status, setStatus] = useState<TuringGameStatus | null>(null)
  const [kills, setKills] = useState<TuringKillEntry[]>([])
  const [killsTotal, setKillsTotal] = useState(0)
  const [killsHasMore, setKillsHasMore] = useState(false)
  const [scores, setScores] = useState<WeeklyScoreEntry[]>([])
  const [scoresTotal, setScoresTotal] = useState(0)
  const [scoresHasMore, setScoresHasMore] = useState(false)
  const [weekNumber, setWeekNumber] = useState(0)
  const [poolSize, setPoolSize] = useState(0)
  const [isLoading, setIsLoading] = useState(true)

  const [showKillDialog, setShowKillDialog] = useState(false)
  const [reportMode, setReportMode] = useState<'suspicion' | 'exclusion' | null>(null)

  const fetchData = async () => {
    setIsLoading(true)
    try {
      const promises: Promise<any>[] = [
        api.turingKillsRecent(20),
        api.turingWeeklyScores(undefined, 50),
      ]
      if (currentUser) {
        promises.push(api.turingGameStatus())
      }

      const results = await Promise.all(promises)

      const killsData = results[0]
      setKills(killsData.kills)
      setKillsTotal(killsData.total)
      setKillsHasMore(killsData.has_more)

      const scoresData = results[1]
      setScores(scoresData.scores)
      setScoresTotal(scoresData.total)
      setScoresHasMore(scoresData.has_more)
      setWeekNumber(scoresData.week_number)
      setPoolSize(scoresData.pool_size)

      if (currentUser && results[2]) {
        setStatus(results[2])
      }
    } catch (err) {
      console.error('Failed to load turing game data:', err)
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [currentUser]) // eslint-disable-line react-hooks/exhaustive-deps

  const handleActionSuccess = () => {
    // Refresh status after an action
    if (currentUser) {
      api.turingGameStatus().then(setStatus).catch(console.error)
      api.turingKillsRecent(20).then((data) => {
        setKills(data.kills)
        setKillsTotal(data.total)
        setKillsHasMore(data.has_more)
      }).catch(console.error)
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="w-6 h-6 border-2 border-accent-gold border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Crosshair size={24} className="text-accent-gold" />
          The Turing Game
        </h1>
        <p className="text-text-secondary mt-1">Who is AI and who is human?</p>
      </div>

      {/* Status (logged in only) */}
      {status && <GameStatus status={status} />}

      {/* Action buttons (logged in only) */}
      {currentUser && status && !status.is_eliminated && (
        <div className="flex flex-wrap gap-3">
          {status.can_use_kill && status.turing_kills_remaining > 0 && (
            <Button
              variant="secondary"
              onClick={() => setShowKillDialog(true)}
              className="!border-karma-down/30 hover:!border-karma-down"
            >
              <Crosshair size={16} className="mr-2 text-karma-down" />
              Turing Kill
            </Button>
          )}
          {status.can_use_suspicion && status.suspicion_reports_remaining > 0 && (
            <Button
              variant="secondary"
              onClick={() => setReportMode('suspicion')}
            >
              <Eye size={16} className="mr-2 text-accent-gold" />
              File Suspicion
            </Button>
          )}
          {status.can_use_exclusion && status.exclusion_reports_remaining > 0 && (
            <Button
              variant="secondary"
              onClick={() => setReportMode('exclusion')}
            >
              <FileWarning size={16} className="mr-2 text-accent-gold" />
              File Exclusion
            </Button>
          )}
        </div>
      )}

      {/* Main content: two columns on desktop */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Kill Feed */}
        <div>
          <h2 className="text-lg font-semibold mb-3">Recent Kills</h2>
          <KillsFeed
            initialKills={kills}
            initialTotal={killsTotal}
            initialHasMore={killsHasMore}
          />
        </div>

        {/* Weekly Leaderboard */}
        <div>
          <h2 className="text-lg font-semibold mb-3">Weekly Leaderboard</h2>
          <WeeklyScores
            weekNumber={weekNumber}
            poolSize={poolSize}
            initialScores={scores}
            initialTotal={scoresTotal}
            initialHasMore={scoresHasMore}
          />
        </div>
      </div>

      {/* Dialogs */}
      {showKillDialog && (
        <KillDialog
          onClose={() => setShowKillDialog(false)}
          onSuccess={handleActionSuccess}
        />
      )}
      {reportMode && (
        <TuringReportDialog
          mode={reportMode}
          onClose={() => setReportMode(null)}
          onSuccess={handleActionSuccess}
        />
      )}
    </div>
  )
}
