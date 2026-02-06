'use client'

import { useState } from 'react'
import { Flag } from 'lucide-react'
import ReportDialog from './ReportDialog'

type TargetType = 'post' | 'comment' | 'resident'

interface ReportButtonProps {
  targetType: TargetType
  targetId: string
  className?: string
}

export default function ReportButton({
  targetType,
  targetId,
  className = '',
}: ReportButtonProps) {
  const [isDialogOpen, setIsDialogOpen] = useState(false)

  return (
    <>
      <button
        onClick={() => setIsDialogOpen(true)}
        className={`p-1.5 text-text-muted hover:text-karma-down transition-colors rounded hover:bg-bg-tertiary group relative ${className}`}
        aria-label="報告する"
        title="報告する"
      >
        <Flag size={14} />
        {/* Tooltip */}
        <span className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2 py-1 text-xs bg-bg-tertiary border border-border-default rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none">
          報告する
        </span>
      </button>

      {isDialogOpen && (
        <ReportDialog
          targetType={targetType}
          targetId={targetId}
          onClose={() => setIsDialogOpen(false)}
          onSuccess={() => setIsDialogOpen(false)}
        />
      )}
    </>
  )
}
