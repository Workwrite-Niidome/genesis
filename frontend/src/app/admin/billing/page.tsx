'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { ArrowLeft } from 'lucide-react'
import { api, AdminSubscriptionItem, AdminReportItem, AdminOrgSubscriptionItem } from '@/lib/api'

type Tab = 'pro' | 'reports' | 'orgs'

export default function AdminBillingPage() {
  const router = useRouter()
  const [tab, setTab] = useState<Tab>('pro')
  const [proSubs, setProSubs] = useState<AdminSubscriptionItem[]>([])
  const [reports, setReports] = useState<AdminReportItem[]>([])
  const [orgSubs, setOrgSubs] = useState<AdminOrgSubscriptionItem[]>([])
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    loadData()
  }, [tab])

  const loadData = async () => {
    setIsLoading(true)
    try {
      if (tab === 'pro') {
        const res = await api.getAdminSubscriptions('all')
        setProSubs(res.subscriptions)
      } else if (tab === 'reports') {
        const res = await api.getAdminReportPurchases()
        setReports(res.reports)
      } else {
        const res = await api.getAdminOrgSubscriptions()
        setOrgSubs(res.subscriptions)
      }
    } catch (err: any) {
      if (err.message.includes('403')) router.push('/')
    } finally {
      setIsLoading(false)
    }
  }

  const tabs: { key: Tab; label: string }[] = [
    { key: 'pro', label: 'Pro Subscriptions' },
    { key: 'reports', label: 'Report Purchases' },
    { key: 'orgs', label: 'Organization Subs' },
  ]

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      <div className="flex items-center gap-3 mb-6">
        <Link href="/admin" className="p-2.5 -m-2.5 text-text-muted hover:text-text-primary">
          <ArrowLeft size={20} />
        </Link>
        <h1 className="text-xl sm:text-2xl font-bold text-text-primary">Billing</h1>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-4 bg-bg-secondary rounded-lg p-1 border border-border-default">
        {tabs.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`flex-1 px-2 sm:px-3 py-2 text-xs sm:text-sm rounded-md transition-colors ${
              tab === t.key ? 'bg-bg-tertiary text-text-primary' : 'text-text-muted hover:text-text-secondary'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin w-6 h-6 border-2 border-accent-gold border-t-transparent rounded-full" />
        </div>
      ) : (
        <>
          {tab === 'pro' && (
            <>
              {/* Desktop table */}
              <div className="hidden sm:block bg-bg-secondary border border-border-default rounded-lg overflow-hidden">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-border-default text-text-muted text-xs">
                      <th className="text-left px-3 py-2">Resident</th>
                      <th className="text-left px-3 py-2">Plan</th>
                      <th className="text-left px-3 py-2">Status</th>
                      <th className="text-left px-3 py-2">Period End</th>
                    </tr>
                  </thead>
                  <tbody>
                    {proSubs.map((s) => (
                      <tr key={s.id} className="border-b border-border-default last:border-0 hover:bg-bg-tertiary">
                        <td className="px-3 py-2">
                          <Link href={`/admin/residents/${s.resident_id}`} className="text-text-primary hover:text-accent-gold">
                            {s.resident_name || s.resident_id.slice(0, 8)}
                          </Link>
                        </td>
                        <td className="px-3 py-2 text-text-secondary">{s.plan_type}</td>
                        <td className="px-3 py-2">
                          <StatusBadge status={s.status} />
                        </td>
                        <td className="px-3 py-2 text-text-muted text-xs">
                          {s.current_period_end ? new Date(s.current_period_end).toLocaleDateString() : '-'}
                        </td>
                      </tr>
                    ))}
                    {proSubs.length === 0 && (
                      <tr><td colSpan={4} className="px-3 py-8 text-center text-text-muted">No subscriptions</td></tr>
                    )}
                  </tbody>
                </table>
              </div>
              {/* Mobile cards */}
              <div className="sm:hidden space-y-2">
                {proSubs.length === 0 ? (
                  <p className="text-center text-text-muted py-8">No subscriptions</p>
                ) : proSubs.map((s) => (
                  <Link key={s.id} href={`/admin/residents/${s.resident_id}`} className="block bg-bg-secondary border border-border-default rounded-lg p-3">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-text-primary font-medium text-sm">{s.resident_name || s.resident_id.slice(0, 8)}</span>
                      <StatusBadge status={s.status} />
                    </div>
                    <div className="flex items-center gap-3 text-xs text-text-muted">
                      <span>{s.plan_type}</span>
                      {s.current_period_end && <span>ends {new Date(s.current_period_end).toLocaleDateString()}</span>}
                    </div>
                  </Link>
                ))}
              </div>
            </>
          )}

          {tab === 'reports' && (
            <>
              {/* Desktop table */}
              <div className="hidden sm:block bg-bg-secondary border border-border-default rounded-lg overflow-hidden">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-border-default text-text-muted text-xs">
                      <th className="text-left px-3 py-2">Resident</th>
                      <th className="text-left px-3 py-2">Report</th>
                      <th className="text-left px-3 py-2">Status</th>
                      <th className="text-left px-3 py-2">Date</th>
                    </tr>
                  </thead>
                  <tbody>
                    {reports.map((r) => (
                      <tr key={r.id} className="border-b border-border-default last:border-0 hover:bg-bg-tertiary">
                        <td className="px-3 py-2">
                          <Link href={`/admin/residents/${r.resident_id}`} className="text-text-primary hover:text-accent-gold">
                            {r.resident_name || r.resident_id.slice(0, 8)}
                          </Link>
                        </td>
                        <td className="px-3 py-2 text-text-secondary">{r.report_type}</td>
                        <td className="px-3 py-2">
                          <StatusBadge status={r.status} />
                        </td>
                        <td className="px-3 py-2 text-text-muted text-xs">
                          {r.created_at ? new Date(r.created_at).toLocaleDateString() : '-'}
                        </td>
                      </tr>
                    ))}
                    {reports.length === 0 && (
                      <tr><td colSpan={4} className="px-3 py-8 text-center text-text-muted">No purchases</td></tr>
                    )}
                  </tbody>
                </table>
              </div>
              {/* Mobile cards */}
              <div className="sm:hidden space-y-2">
                {reports.length === 0 ? (
                  <p className="text-center text-text-muted py-8">No purchases</p>
                ) : reports.map((r) => (
                  <Link key={r.id} href={`/admin/residents/${r.resident_id}`} className="block bg-bg-secondary border border-border-default rounded-lg p-3">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-text-primary font-medium text-sm">{r.resident_name || r.resident_id.slice(0, 8)}</span>
                      <StatusBadge status={r.status} />
                    </div>
                    <div className="flex items-center gap-3 text-xs text-text-muted">
                      <span>{r.report_type}</span>
                      {r.created_at && <span>{new Date(r.created_at).toLocaleDateString()}</span>}
                    </div>
                  </Link>
                ))}
              </div>
            </>
          )}

          {tab === 'orgs' && (
            <>
              {/* Desktop table */}
              <div className="hidden sm:block bg-bg-secondary border border-border-default rounded-lg overflow-hidden">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-border-default text-text-muted text-xs">
                      <th className="text-left px-3 py-2">Organization</th>
                      <th className="text-left px-3 py-2">Plan</th>
                      <th className="text-right px-3 py-2">Seats</th>
                      <th className="text-left px-3 py-2">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {orgSubs.map((s) => (
                      <tr key={s.id} className="border-b border-border-default last:border-0 hover:bg-bg-tertiary">
                        <td className="px-3 py-2 text-text-primary">{s.company_name}</td>
                        <td className="px-3 py-2 text-text-secondary">{s.plan_type}</td>
                        <td className="px-3 py-2 text-right text-text-secondary">{s.quantity}</td>
                        <td className="px-3 py-2">
                          <StatusBadge status={s.status} />
                        </td>
                      </tr>
                    ))}
                    {orgSubs.length === 0 && (
                      <tr><td colSpan={4} className="px-3 py-8 text-center text-text-muted">No org subscriptions</td></tr>
                    )}
                  </tbody>
                </table>
              </div>
              {/* Mobile cards */}
              <div className="sm:hidden space-y-2">
                {orgSubs.length === 0 ? (
                  <p className="text-center text-text-muted py-8">No org subscriptions</p>
                ) : orgSubs.map((s) => (
                  <div key={s.id} className="bg-bg-secondary border border-border-default rounded-lg p-3">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-text-primary font-medium text-sm">{s.company_name}</span>
                      <StatusBadge status={s.status} />
                    </div>
                    <div className="flex items-center gap-3 text-xs text-text-muted">
                      <span>{s.plan_type}</span>
                      <span>{s.quantity} seats</span>
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}
        </>
      )}
    </div>
  )
}

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    active: 'bg-karma-up/10 text-karma-up',
    completed: 'bg-karma-up/10 text-karma-up',
    canceled: 'bg-text-muted/10 text-text-muted',
    past_due: 'bg-yellow-500/10 text-yellow-400',
    pending: 'bg-yellow-500/10 text-yellow-400',
    none: 'bg-text-muted/10 text-text-muted',
  }
  return (
    <span className={`text-xs px-1.5 py-0.5 rounded ${colors[status] || colors.none}`}>
      {status}
    </span>
  )
}
