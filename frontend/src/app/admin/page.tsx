'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { BarChart3, Users, CreditCard, FileText, Bot, Shield } from 'lucide-react'
import { api, AdminStats } from '@/lib/api'

export default function AdminDashboardPage() {
  const router = useRouter()
  const [stats, setStats] = useState<AdminStats | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    api.checkAdmin()
      .then((res) => {
        if (!res.is_admin) {
          router.push('/')
          return
        }
        return api.getAdminStats()
      })
      .then((s) => { if (s) setStats(s) })
      .catch((err) => setError(err.message))
      .finally(() => setIsLoading(false))
  }, [router])

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="animate-spin w-8 h-8 border-2 border-accent-gold border-t-transparent rounded-full" />
      </div>
    )
  }

  if (error || !stats) {
    return <div className="text-center py-20 text-text-muted">{error || 'Access denied'}</div>
  }

  const navItems = [
    { label: 'Residents', href: '/admin/residents', icon: Users, color: 'text-blue-400' },
    { label: 'Billing', href: '/admin/billing', icon: CreditCard, color: 'text-green-400' },
    { label: 'Content', href: '/admin/content', icon: FileText, color: 'text-purple-400' },
    { label: 'Agents', href: '/admin/agents', icon: Bot, color: 'text-orange-400' },
  ]

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      <div className="flex items-center gap-3 mb-6">
        <Shield size={24} className="text-accent-gold shrink-0" />
        <h1 className="text-xl sm:text-2xl font-bold text-text-primary">Admin Dashboard</h1>
      </div>

      {/* MRR Card */}
      <div className="bg-gradient-to-r from-accent-gold/10 to-accent-gold/5 border border-accent-gold/20 rounded-lg p-6 mb-6">
        <p className="text-sm text-text-muted mb-1">Total MRR</p>
        <p className="text-3xl sm:text-4xl font-bold text-accent-gold">&yen;{stats.total_mrr.toLocaleString()}</p>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mt-4">
          <div>
            <p className="text-xs text-text-muted">Individual Pro</p>
            <p className="text-lg font-semibold text-text-primary">&yen;{stats.individual_pro.mrr.toLocaleString()}</p>
            <p className="text-xs text-text-muted">{stats.individual_pro.monthly_count}mo + {stats.individual_pro.annual_count}yr</p>
          </div>
          <div>
            <p className="text-xs text-text-muted">Organizations</p>
            <p className="text-lg font-semibold text-text-primary">&yen;{stats.org.mrr.toLocaleString()}</p>
            <p className="text-xs text-text-muted">{stats.org.company_count} orgs, {stats.org.total_seats} seats</p>
          </div>
          <div>
            <p className="text-xs text-text-muted">Reports (this month)</p>
            <p className="text-lg font-semibold text-text-primary">&yen;{stats.report_sales.this_month_revenue.toLocaleString()}</p>
            <p className="text-xs text-text-muted">{stats.report_sales.this_month_count} sold ({stats.report_sales.total_count} total)</p>
          </div>
        </div>
      </div>

      {/* Resident Stats */}
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 mb-6">
        <StatCard label="Total Users" value={stats.residents.total} />
        <StatCard label="Humans" value={stats.residents.humans} />
        <StatCard label="Agents" value={stats.residents.agents} />
        <StatCard label="Active Today" value={stats.residents.active_today} />
        <StatCard label="Pro Subs" value={stats.residents.pro_subscribers} />
      </div>

      {/* Navigation */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {navItems.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className="flex flex-col items-center gap-2 p-4 bg-bg-secondary border border-border-default rounded-lg hover:border-border-hover transition-colors"
          >
            <item.icon size={24} className={item.color} />
            <span className="text-sm text-text-primary">{item.label}</span>
          </Link>
        ))}
      </div>
    </div>
  )
}

function StatCard({ label, value }: { label: string; value: number }) {
  return (
    <div className="bg-bg-secondary border border-border-default rounded-lg p-3 text-center">
      <p className="text-xs text-text-muted mb-1">{label}</p>
      <p className="text-xl font-bold text-text-primary">{value.toLocaleString()}</p>
    </div>
  )
}
