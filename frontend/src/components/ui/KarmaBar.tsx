'use client'

const KARMA_CAP = 500

interface KarmaBarProps {
  karma: number
  className?: string
}

export default function KarmaBar({ karma, className = '' }: KarmaBarProps) {
  const percentage = Math.min(100, Math.max(0, (karma / KARMA_CAP) * 100))
  const isLow = karma < 50
  const isCritical = karma < 20

  const getBarColor = () => {
    if (isCritical) return 'bg-red-500'
    if (isLow) return 'bg-yellow-500'
    if (percentage > 60) return 'bg-green-500'
    return 'bg-yellow-400'
  }

  return (
    <div className={`flex items-center gap-2 ${className}`}>
      <span className={`text-xs font-bold tabular-nums ${isCritical ? 'text-red-400 animate-pulse' : isLow ? 'text-yellow-400' : 'text-text-primary'}`}>
        {karma}
      </span>
      <div className="w-16 h-1.5 bg-bg-tertiary rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-500 ${getBarColor()} ${isCritical ? 'animate-pulse' : ''}`}
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  )
}
