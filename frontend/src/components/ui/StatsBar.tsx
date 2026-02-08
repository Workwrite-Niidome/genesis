'use client'

import { useState, useEffect } from 'react'
import { Users, FileText, MessageSquare, Bot } from 'lucide-react'
import { api, DashboardStats } from '@/lib/api'

export default function StatsBar() {
  const [stats, setStats] = useState<DashboardStats | null>(null)

  useEffect(() => {
    api.getDashboardStats()
      .then(setStats)
      .catch(() => {})
  }, [])

  if (!stats) return null

  const items = [
    { icon: Users, label: 'Humans', value: stats.human_count },
    { icon: Bot, label: 'AI', value: stats.agent_count },
    { icon: FileText, label: 'Posts', value: stats.total_posts },
    { icon: MessageSquare, label: 'Comments', value: stats.total_comments },
  ]

  return (
    <div className="flex items-center gap-4 sm:gap-6 px-3 py-2 bg-bg-secondary/50 rounded-lg border border-border-default text-xs text-text-muted overflow-x-auto">
      {items.map((item) => {
        const Icon = item.icon
        return (
          <div key={item.label} className="flex items-center gap-1.5 whitespace-nowrap">
            <Icon size={13} className="text-text-muted" />
            <span className="font-mono text-text-secondary">{item.value.toLocaleString()}</span>
            <span>{item.label}</span>
          </div>
        )
      })}
    </div>
  )
}
