'use client'

import { ReactNode } from 'react'
import clsx from 'clsx'
import { TrendingUp, TrendingDown, Minus } from 'lucide-react'

interface StatCardProps {
  icon: ReactNode
  value: string | number
  label: string
  change?: number
  changeLabel?: string
  variant?: 'default' | 'gold' | 'highlight'
  className?: string
}

export default function StatCard({
  icon,
  value,
  label,
  change,
  changeLabel,
  variant = 'default',
  className,
}: StatCardProps) {
  const isPositive = change !== undefined && change > 0
  const isNegative = change !== undefined && change < 0
  const isNeutral = change !== undefined && change === 0

  const variantStyles = {
    default: 'bg-bg-secondary border-border-default',
    gold: 'bg-gradient-to-br from-bg-secondary to-bg-tertiary border-god-glow',
    highlight: 'bg-bg-tertiary border-accent-gold',
  }

  return (
    <div
      className={clsx(
        'rounded-lg border p-4 transition-all duration-200 hover:shadow-lg',
        variantStyles[variant],
        className
      )}
    >
      <div className="flex items-start justify-between mb-3">
        <div className="p-2 rounded-lg bg-bg-tertiary text-accent-gold">
          {icon}
        </div>
        {change !== undefined && (
          <div
            className={clsx('flex items-center gap-1 text-sm font-medium', {
              'text-karma-up': isPositive,
              'text-karma-down': isNegative,
              'text-text-muted': isNeutral,
            })}
          >
            {isPositive && <TrendingUp size={14} />}
            {isNegative && <TrendingDown size={14} />}
            {isNeutral && <Minus size={14} />}
            <span>
              {isPositive && '+'}
              {change}%
            </span>
          </div>
        )}
      </div>

      <div className="space-y-1">
        <p
          className={clsx('text-2xl font-bold', {
            'gold-gradient': variant === 'gold',
            'text-text-primary': variant !== 'gold',
          })}
        >
          {typeof value === 'number' ? value.toLocaleString() : value}
        </p>
        <p className="text-sm text-text-secondary">{label}</p>
        {changeLabel && (
          <p className="text-xs text-text-muted">{changeLabel}</p>
        )}
      </div>
    </div>
  )
}
