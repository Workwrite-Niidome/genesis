'use client'

import { ScrollText, AlertTriangle, Info, CheckCircle } from 'lucide-react'
import clsx from 'clsx'

interface WeeklyRuleProps {
  title: string
  content: string
  enforcementType: 'mandatory' | 'recommended' | 'optional'
  isActive: boolean
}

export default function WeeklyRule({
  title,
  content,
  enforcementType,
  isActive,
}: WeeklyRuleProps) {
  if (!isActive) return null

  const getEnforcementIcon = () => {
    switch (enforcementType) {
      case 'mandatory':
        return <AlertTriangle size={16} className="text-karma-down" />
      case 'recommended':
        return <CheckCircle size={16} className="text-karma-up" />
      case 'optional':
        return <Info size={16} className="text-text-muted" />
    }
  }

  const getEnforcementLabel = () => {
    switch (enforcementType) {
      case 'mandatory':
        return 'Required'
      case 'recommended':
        return 'Recommended'
      case 'optional':
        return 'Optional'
    }
  }

  const getEnforcementColor = () => {
    switch (enforcementType) {
      case 'mandatory':
        return 'border-karma-down/50 bg-karma-down/5'
      case 'recommended':
        return 'border-karma-up/50 bg-karma-up/5'
      case 'optional':
        return 'border-border-default bg-bg-tertiary'
    }
  }

  return (
    <div
      className={clsx(
        'rounded-lg border p-4',
        getEnforcementColor()
      )}
    >
      <div className="flex items-start gap-3">
        <div className="p-2 bg-god-glow/10 rounded-lg flex-shrink-0">
          <ScrollText size={18} className="text-god-glow" />
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <h3 className="font-semibold text-text-primary">{title}</h3>
            <span className="flex items-center gap-1 text-xs px-2 py-0.5 rounded-full bg-bg-tertiary">
              {getEnforcementIcon()}
              {getEnforcementLabel()}
            </span>
          </div>

          <p className="text-sm text-text-secondary">{content}</p>
        </div>
      </div>
    </div>
  )
}
