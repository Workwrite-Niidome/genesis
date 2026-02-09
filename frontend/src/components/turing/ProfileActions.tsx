'use client'

import { useState, useEffect } from 'react'
import { Crosshair, Eye, FileWarning } from 'lucide-react'
import { api, TuringGameStatus } from '@/lib/api'
import { useAuthStore } from '@/stores/authStore'
import Button from '@/components/ui/Button'
import KillDialog from './KillDialog'
import TuringReportDialog from './TuringReportDialog'

interface ProfileActionsProps {
  targetId: string
  targetName: string
}

export default function ProfileActions({ targetId, targetName }: ProfileActionsProps) {
  const { resident: currentUser } = useAuthStore()
  const [status, setStatus] = useState<TuringGameStatus | null>(null)
  const [showKillDialog, setShowKillDialog] = useState(false)
  const [reportMode, setReportMode] = useState<'suspicion' | 'exclusion' | null>(null)

  const isOwnProfile = currentUser?.id === targetId

  useEffect(() => {
    if (currentUser && !isOwnProfile) {
      api.turingGameStatus().then(setStatus).catch(() => {})
    }
  }, [currentUser, isOwnProfile])

  if (!currentUser || isOwnProfile || !status || status.is_eliminated) {
    return null
  }

  const target = { id: targetId, name: targetName }

  return (
    <>
      <div className="flex items-center gap-1.5">
        {status.can_use_kill && status.turing_kills_remaining > 0 && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setShowKillDialog(true)}
            title="Turing Kill"
          >
            <Crosshair size={14} className="text-karma-down" />
          </Button>
        )}
        {status.can_use_suspicion && status.suspicion_reports_remaining > 0 && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setReportMode('suspicion')}
            title="Suspicion Report"
          >
            <Eye size={14} />
          </Button>
        )}
        {status.can_use_exclusion && status.exclusion_reports_remaining > 0 && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setReportMode('exclusion')}
            title="Exclusion Report"
          >
            <FileWarning size={14} />
          </Button>
        )}
      </div>

      {showKillDialog && (
        <KillDialog
          onClose={() => setShowKillDialog(false)}
          preselectedTarget={target}
        />
      )}
      {reportMode && (
        <TuringReportDialog
          mode={reportMode}
          onClose={() => setReportMode(null)}
          preselectedTarget={target}
        />
      )}
    </>
  )
}
