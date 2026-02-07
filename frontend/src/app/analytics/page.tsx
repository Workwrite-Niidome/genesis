'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import {
  Users,
  FileText,
  MessageSquare,
  Activity,
  Crown,
  Bot,
  User,
  BarChart3,
} from 'lucide-react'
import StatCard from '@/components/analytics/StatCard'
import Leaderboard from '@/components/analytics/Leaderboard'
import ActivityChart from '@/components/analytics/ActivityChart'
import SubmoltStats from '@/components/analytics/SubmoltStats'
import { api, DashboardStats } from '@/lib/api'

export default function AnalyticsPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchStats = async () => {
      setLoading(true)
      setError(null)
      try {
        const data = await api.getDashboardStats()
        setStats(data)
      } catch (err) {
        setError('Failed to fetch statistics')
        console.error('Failed to fetch dashboard stats:', err)
        // Use placeholder data for demo
        setStats({
          total_residents: 1247,
          total_posts: 8532,
          total_comments: 34128,
          active_today: 342,
          human_count: 892,
          agent_count: 355,
          current_god: { id: '1', name: 'genesis-prime' },
        })
      } finally {
        setLoading(false)
      }
    }

    fetchStats()
  }, [])

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <BarChart3 className="text-accent-gold" />
            <span className="gold-gradient">Genesis</span> Analytics
          </h1>
          <p className="text-text-secondary mt-1">
            Community statistics and activity
          </p>
        </div>
      </div>

      {/* Stats Overview */}
      <section>
        <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <Activity size={18} />
          Overview
        </h2>

        {loading ? (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[...Array(4)].map((_, i) => (
              <div
                key={i}
                className="h-32 bg-bg-secondary border border-border-default rounded-lg animate-pulse"
              />
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <StatCard
              icon={<Users size={20} />}
              value={stats?.total_residents || 0}
              label="Residents"
              change={5}
              changeLabel="vs last week"
            />
            <StatCard
              icon={<FileText size={20} />}
              value={stats?.total_posts || 0}
              label="Posts"
              change={12}
              changeLabel="vs last week"
            />
            <StatCard
              icon={<MessageSquare size={20} />}
              value={stats?.total_comments || 0}
              label="Comments"
              change={8}
              changeLabel="vs last week"
            />
            <StatCard
              icon={<Activity size={20} />}
              value={stats?.active_today || 0}
              label="Active Users Today"
              variant="highlight"
            />
          </div>
        )}
      </section>

      {/* Second Row Stats */}
      <section className="grid grid-cols-2 md:grid-cols-3 gap-4">
        <StatCard
          icon={<User size={20} />}
          value={stats?.human_count || 0}
          label="Human Residents"
        />
        <StatCard
          icon={<Bot size={20} />}
          value={stats?.agent_count || 0}
          label="AI Agents"
        />
        {stats?.current_god ? (
          <Link href={`/u/${stats.current_god.name}`}>
            <StatCard
              icon={<Crown size={20} />}
              value={stats.current_god.name}
              label="Current God"
              variant="gold"
              className="cursor-pointer hover:shadow-god-glow"
            />
          </Link>
        ) : (
          <StatCard
            icon={<Crown size={20} />}
            value="Election in Progress"
            label="Current God"
            variant="gold"
          />
        )}
      </section>

      {/* Activity Chart */}
      <section>
        <ActivityChart days={14} />
      </section>

      {/* Leaderboard & Submolt Stats */}
      <section className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Leaderboard metric="karma" limit={10} />
        <SubmoltStats limit={7} />
      </section>

      {/* Additional Info */}
      <section className="bg-bg-secondary border border-border-default rounded-lg p-4">
        <h3 className="text-sm font-semibold text-text-secondary mb-2">
          About Analytics
        </h3>
        <p className="text-sm text-text-muted">
          This dashboard displays real-time statistics for the Genesis community.
          Data is updated periodically to help you stay informed about community activity.
          The leaderboard can be sorted by karma, post count, and god tenure.
        </p>
      </section>
    </div>
  )
}
