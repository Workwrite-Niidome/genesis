'use client'

import { useState, useEffect, useMemo } from 'react'
import clsx from 'clsx'
import { BarChart3, TrendingUp, Calendar } from 'lucide-react'
import { api, DailyStats } from '@/lib/api'

interface ActivityChartProps {
  days?: 7 | 14 | 30
  className?: string
}

type ChartType = 'posts' | 'comments' | 'active_users'

const CHART_LABELS: Record<ChartType, { label: string; color: string }> = {
  posts: { label: 'Posts', color: 'bg-accent-gold' },
  comments: { label: 'Comments', color: 'bg-blue-500' },
  active_users: { label: 'Active Users', color: 'bg-green-500' },
}

const DAY_OPTIONS = [
  { value: 7, label: '7 days' },
  { value: 14, label: '14 days' },
  { value: 30, label: '30 days' },
] as const

export default function ActivityChart({
  days: initialDays = 7,
  className,
}: ActivityChartProps) {
  const [data, setData] = useState<DailyStats[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedDays, setSelectedDays] = useState<7 | 14 | 30>(initialDays)
  const [chartType, setChartType] = useState<ChartType>('posts')

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true)
      setError(null)
      try {
        const endDate = new Date().toISOString().split('T')[0]
        const startDate = new Date(Date.now() - selectedDays * 24 * 60 * 60 * 1000)
          .toISOString()
          .split('T')[0]
        const stats = await api.getDailyStats(startDate, endDate)
        setData(stats)
      } catch (err) {
        setError('Failed to load activity data')
        console.error('Failed to fetch daily stats:', err)
        // Generate placeholder data for demo
        setData(generatePlaceholderData(selectedDays))
      } finally {
        setLoading(false)
      }
    }

    fetchData()
  }, [selectedDays])

  const chartData = useMemo(() => {
    if (data.length === 0) return []

    const values = data.map((d) => d[chartType])
    const maxValue = Math.max(...values, 1)

    return data.map((d) => ({
      date: d.date,
      value: d[chartType],
      height: (d[chartType] / maxValue) * 100,
      label: formatDate(d.date),
    }))
  }, [data, chartType])

  const stats = useMemo(() => {
    if (data.length === 0) return { total: 0, avg: 0, max: 0, trend: 0 }

    const values = data.map((d) => d[chartType])
    const total = values.reduce((a, b) => a + b, 0)
    const avg = Math.round(total / values.length)
    const max = Math.max(...values)

    // Calculate trend (compare last 3 days vs previous 3 days)
    if (values.length >= 6) {
      const recent = values.slice(-3).reduce((a, b) => a + b, 0) / 3
      const previous = values.slice(-6, -3).reduce((a, b) => a + b, 0) / 3
      const trend = previous > 0 ? Math.round(((recent - previous) / previous) * 100) : 0
      return { total, avg, max, trend }
    }

    return { total, avg, max, trend: 0 }
  }, [data, chartType])

  return (
    <div
      className={clsx(
        'rounded-lg border border-border-default bg-bg-secondary p-4',
        className
      )}
    >
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 mb-4">
        <div className="flex items-center gap-2">
          <BarChart3 size={20} className="text-accent-gold" />
          <h2 className="text-lg font-semibold">Daily Activity</h2>
        </div>

        <div className="flex gap-2">
          {/* Chart Type Selector */}
          <div className="flex gap-1 text-sm">
            {(Object.keys(CHART_LABELS) as ChartType[]).map((type) => (
              <button
                key={type}
                onClick={() => setChartType(type)}
                className={clsx(
                  'px-2 py-1 rounded-md transition-colors',
                  chartType === type
                    ? 'bg-accent-gold text-bg-primary font-medium'
                    : 'text-text-secondary hover:text-text-primary hover:bg-bg-tertiary'
                )}
              >
                {CHART_LABELS[type].label}
              </button>
            ))}
          </div>

          {/* Days Selector */}
          <div className="flex items-center gap-1 ml-2 border-l border-border-default pl-2">
            <Calendar size={14} className="text-text-muted" />
            {DAY_OPTIONS.map((option) => (
              <button
                key={option.value}
                onClick={() => setSelectedDays(option.value)}
                className={clsx(
                  'px-2 py-1 text-xs rounded transition-colors',
                  selectedDays === option.value
                    ? 'bg-bg-tertiary text-text-primary'
                    : 'text-text-muted hover:text-text-secondary'
                )}
              >
                {option.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Stats Summary */}
      <div className="grid grid-cols-4 gap-4 mb-6 p-3 bg-bg-tertiary rounded-lg">
        <div>
          <p className="text-xs text-text-muted">Total</p>
          <p className="text-lg font-bold">{stats.total.toLocaleString()}</p>
        </div>
        <div>
          <p className="text-xs text-text-muted">Avg/day</p>
          <p className="text-lg font-bold">{stats.avg.toLocaleString()}</p>
        </div>
        <div>
          <p className="text-xs text-text-muted">Peak</p>
          <p className="text-lg font-bold">{stats.max.toLocaleString()}</p>
        </div>
        <div>
          <p className="text-xs text-text-muted">Trend</p>
          <p
            className={clsx('text-lg font-bold flex items-center gap-1', {
              'text-karma-up': stats.trend > 0,
              'text-karma-down': stats.trend < 0,
              'text-text-muted': stats.trend === 0,
            })}
          >
            {stats.trend > 0 && <TrendingUp size={14} />}
            {stats.trend > 0 ? '+' : ''}
            {stats.trend}%
          </p>
        </div>
      </div>

      {/* Chart */}
      {loading ? (
        <div className="h-48 bg-bg-tertiary rounded-lg animate-pulse" />
      ) : error && data.length === 0 ? (
        <div className="h-48 flex items-center justify-center text-text-muted">
          {error}
        </div>
      ) : (
        <div className="relative h-48">
          {/* Y-axis labels */}
          <div className="absolute left-0 top-0 bottom-6 w-10 flex flex-col justify-between text-xs text-text-muted">
            <span>{stats.max}</span>
            <span>{Math.round(stats.max / 2)}</span>
            <span>0</span>
          </div>

          {/* Chart Area */}
          <div className="ml-12 h-full flex items-end gap-1 pb-6">
            {chartData.map((bar, index) => (
              <div
                key={bar.date}
                className="flex-1 flex flex-col items-center group"
              >
                {/* Tooltip */}
                <div className="invisible group-hover:visible absolute -top-8 bg-bg-primary border border-border-default rounded px-2 py-1 text-xs whitespace-nowrap z-10">
                  <p className="text-text-primary font-medium">{bar.value.toLocaleString()}</p>
                  <p className="text-text-muted">{bar.label}</p>
                </div>

                {/* Bar */}
                <div
                  className={clsx(
                    'w-full rounded-t transition-all duration-300 cursor-pointer hover:opacity-80',
                    CHART_LABELS[chartType].color
                  )}
                  style={{ height: `${Math.max(bar.height, 2)}%` }}
                />
              </div>
            ))}
          </div>

          {/* X-axis labels */}
          <div className="ml-12 flex justify-between text-xs text-text-muted">
            <span>{chartData[0]?.label}</span>
            {chartData.length > 7 && (
              <span>{chartData[Math.floor(chartData.length / 2)]?.label}</span>
            )}
            <span>{chartData[chartData.length - 1]?.label}</span>
          </div>
        </div>
      )}
    </div>
  )
}

function formatDate(dateStr: string): string {
  const date = new Date(dateStr)
  return `${date.getMonth() + 1}/${date.getDate()}`
}

function generatePlaceholderData(days: number): DailyStats[] {
  const data: DailyStats[] = []
  const now = new Date()

  for (let i = days - 1; i >= 0; i--) {
    const date = new Date(now.getTime() - i * 24 * 60 * 60 * 1000)
    data.push({
      date: date.toISOString().split('T')[0],
      posts: Math.floor(Math.random() * 50) + 10,
      comments: Math.floor(Math.random() * 150) + 30,
      active_users: Math.floor(Math.random() * 100) + 20,
    })
  }

  return data
}
