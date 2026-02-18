'use client'

import { useState, useEffect } from 'react'
import { useParams } from 'next/navigation'
import Link from 'next/link'
import { Building2, Users, BarChart3, Settings, Copy, Check } from 'lucide-react'
import { api, CompanyDashboard } from '@/lib/api'
import Button from '@/components/ui/Button'

const AXIS_LABELS = ['Activation', 'Judgment', 'Selection', 'Resonance', 'Awareness']

export default function OrgDashboardPage() {
  const params = useParams()
  const slug = params.slug as string
  const [dashboard, setDashboard] = useState<CompanyDashboard | null>(null)
  const [companyName, setCompanyName] = useState('')
  const [inviteCode, setInviteCode] = useState('')
  const [isLoading, setIsLoading] = useState(true)
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    Promise.all([
      api.getCompany(slug),
      api.getCompanyDashboard(slug),
    ]).then(([company, dash]) => {
      setCompanyName(company.name)
      setInviteCode(company.invite_code)
      setDashboard(dash)
    }).catch(() => {})
      .finally(() => setIsLoading(false))
  }, [slug])

  const handleCopyCode = () => {
    navigator.clipboard.writeText(inviteCode)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="animate-spin w-8 h-8 border-2 border-accent-gold border-t-transparent rounded-full" />
      </div>
    )
  }

  if (!dashboard) {
    return <div className="text-center py-20 text-text-muted">Organization not found or access denied.</div>
  }

  const typeEntries = Object.entries(dashboard.type_distribution).sort((a, b) => b[1] - a[1])

  return (
    <div className="max-w-3xl mx-auto px-4 py-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-lg bg-accent-gold/10 flex items-center justify-center">
            <Building2 size={24} className="text-accent-gold" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-text-primary">{companyName}</h1>
            <p className="text-sm text-text-muted">{dashboard.member_count} members</p>
          </div>
        </div>
        <div className="flex gap-2">
          <Link href={`/org/${slug}/members`}>
            <Button variant="secondary" size="sm"><Users size={14} className="mr-1" /> Members</Button>
          </Link>
          <Link href={`/org/${slug}/settings`}>
            <Button variant="secondary" size="sm"><Settings size={14} /></Button>
          </Link>
        </div>
      </div>

      {/* Invite Code */}
      <div className="bg-bg-secondary border border-border-default rounded-lg p-4 mb-6">
        <p className="text-xs text-text-muted mb-1">Invite Code</p>
        <div className="flex items-center gap-2">
          <code className="text-lg font-mono text-accent-gold tracking-widest">{inviteCode}</code>
          <button onClick={handleCopyCode} className="p-1 text-text-muted hover:text-text-primary">
            {copied ? <Check size={16} className="text-karma-up" /> : <Copy size={16} />}
          </button>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
        <StatCard label="Members" value={dashboard.member_count} />
        <StatCard label="Diagnosed" value={dashboard.diagnosed_count} />
        <StatCard label="Balance" value={`${Math.round(dashboard.balance_score * 100)}%`} />
        <StatCard label="Org Type" value={dashboard.org_type || '-'} />
      </div>

      {dashboard.diagnosed_count === 0 ? (
        <div className="text-center py-12 bg-bg-secondary border border-border-default rounded-lg">
          <BarChart3 size={40} className="mx-auto mb-3 text-text-muted" />
          <p className="text-text-secondary mb-1">No STRUCT CODE data yet</p>
          <p className="text-sm text-text-muted">Members need to complete their STRUCT CODE diagnosis to see analytics.</p>
        </div>
      ) : (
        <>
          {/* Org Type */}
          {dashboard.org_type_name && (
            <div className="bg-bg-secondary border border-border-default rounded-lg p-4 mb-6">
              <p className="text-xs text-text-muted mb-1">Organization Personality Type</p>
              <p className="text-xl font-bold text-accent-gold">{dashboard.org_type}</p>
              <p className="text-sm text-text-secondary">{dashboard.org_type_name}</p>
            </div>
          )}

          {/* Axis Averages */}
          <div className="bg-bg-secondary border border-border-default rounded-lg p-4 mb-6">
            <h3 className="text-sm font-semibold text-text-secondary mb-3">Average Axes</h3>
            <div className="space-y-3">
              {dashboard.axis_averages.map((val, i) => (
                <div key={i}>
                  <div className="flex justify-between text-xs mb-1">
                    <span className="text-text-muted">{AXIS_LABELS[i]}</span>
                    <span className="text-text-secondary">{Math.round(val * 1000)}</span>
                  </div>
                  <div className="h-2 bg-bg-tertiary rounded-full overflow-hidden">
                    <div
                      className="h-full bg-accent-gold rounded-full transition-all"
                      style={{ width: `${val * 100}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Type Distribution */}
          {typeEntries.length > 0 && (
            <div className="bg-bg-secondary border border-border-default rounded-lg p-4 mb-6">
              <h3 className="text-sm font-semibold text-text-secondary mb-3">Type Distribution</h3>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                {typeEntries.map(([type, count]) => (
                  <div key={type} className="flex items-center justify-between px-3 py-2 bg-bg-tertiary rounded">
                    <span className="text-sm font-mono text-text-primary">{type}</span>
                    <span className="text-sm text-text-muted">{count}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Gap Types */}
          {dashboard.gap_types.length > 0 && (
            <div className="bg-bg-secondary border border-border-default rounded-lg p-4 mb-6">
              <h3 className="text-sm font-semibold text-text-secondary mb-2">Missing Types</h3>
              <p className="text-xs text-text-muted mb-3">Types not represented in your organization</p>
              <div className="flex flex-wrap gap-2">
                {dashboard.gap_types.map((t) => (
                  <span key={t} className="px-2 py-1 bg-bg-tertiary rounded text-xs font-mono text-text-muted">{t}</span>
                ))}
              </div>
            </div>
          )}

          {/* Department Breakdown */}
          {dashboard.departments.length > 0 && (
            <div className="bg-bg-secondary border border-border-default rounded-lg p-4">
              <h3 className="text-sm font-semibold text-text-secondary mb-3">Department Overview</h3>
              <div className="space-y-3">
                {dashboard.departments.map((dept) => (
                  <div key={dept.id} className="p-3 bg-bg-tertiary rounded">
                    <div className="flex justify-between mb-2">
                      <span className="text-sm font-medium text-text-primary">{dept.name}</span>
                      <span className="text-xs text-text-muted">{dept.member_count} members</span>
                    </div>
                    <div className="flex gap-2">
                      {dept.avg_axes.map((v, i) => (
                        <div key={i} className="flex-1">
                          <div className="h-1.5 bg-bg-secondary rounded-full overflow-hidden">
                            <div className="h-full bg-accent-gold/60 rounded-full" style={{ width: `${v * 100}%` }} />
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}

function StatCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="bg-bg-secondary border border-border-default rounded-lg p-3 text-center">
      <p className="text-xs text-text-muted mb-1">{label}</p>
      <p className="text-lg font-bold text-text-primary">{value}</p>
    </div>
  )
}
