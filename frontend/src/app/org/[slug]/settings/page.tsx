'use client'

import { useState, useEffect } from 'react'
import { useParams, useSearchParams } from 'next/navigation'
import Link from 'next/link'
import { ArrowLeft, CreditCard, Building2, Plus, Trash2 } from 'lucide-react'
import { api, CompanyDetail, OrgBillingStatus } from '@/lib/api'
import Button from '@/components/ui/Button'

export default function OrgSettingsPage() {
  const params = useParams()
  const searchParams = useSearchParams()
  const slug = params.slug as string
  const [company, setCompany] = useState<CompanyDetail | null>(null)
  const [billing, setBilling] = useState<OrgBillingStatus | null>(null)
  const [name, setName] = useState('')
  const [isLoading, setIsLoading] = useState(true)
  const [newDeptName, setNewDeptName] = useState('')
  const [newTeamName, setNewTeamName] = useState('')
  const [newTeamDept, setNewTeamDept] = useState('')

  const checkoutStatus = searchParams.get('checkout')

  useEffect(() => {
    loadData()
  }, [slug])

  const loadData = () => {
    Promise.all([
      api.getCompany(slug),
      api.getOrgBillingStatus(slug).catch(() => null),
    ]).then(([co, bill]) => {
      setCompany(co)
      setName(co.name)
      setBilling(bill)
    }).catch(() => {})
      .finally(() => setIsLoading(false))
  }

  const handleSaveName = async () => {
    if (!name.trim() || name === company?.name) return
    try {
      await api.updateCompany(slug, { name: name.trim() })
      loadData()
    } catch {}
  }

  const handleCreateDept = async () => {
    if (!newDeptName.trim()) return
    try {
      await api.createDepartment(slug, { name: newDeptName.trim() })
      setNewDeptName('')
      loadData()
    } catch {}
  }

  const handleDeleteDept = async (deptId: string) => {
    if (!confirm('Delete this department and all its teams?')) return
    try {
      await api.deleteDepartment(slug, deptId)
      loadData()
    } catch {}
  }

  const handleCreateTeam = async () => {
    if (!newTeamName.trim() || !newTeamDept) return
    try {
      await api.createTeam(slug, { name: newTeamName.trim(), department_id: newTeamDept })
      setNewTeamName('')
      loadData()
    } catch {}
  }

  const handleDeleteTeam = async (teamId: string) => {
    if (!confirm('Delete this team?')) return
    try {
      await api.deleteTeam(slug, teamId)
      loadData()
    } catch {}
  }

  const handleCheckout = async (planType: 'monthly' | 'annual') => {
    try {
      const { checkout_url } = await api.createOrgCheckout(slug, planType)
      window.location.href = checkout_url
    } catch {}
  }

  const handlePortal = async () => {
    try {
      const { portal_url } = await api.createOrgPortal(slug)
      window.location.href = portal_url
    } catch {}
  }

  if (isLoading || !company) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="animate-spin w-8 h-8 border-2 border-accent-gold border-t-transparent rounded-full" />
      </div>
    )
  }

  return (
    <div className="max-w-2xl mx-auto px-4 py-8 space-y-8">
      <div className="flex items-center gap-3">
        <Link href={`/org/${slug}`} className="text-text-muted hover:text-text-primary">
          <ArrowLeft size={20} />
        </Link>
        <h1 className="text-2xl font-bold text-text-primary">Organization Settings</h1>
      </div>

      {checkoutStatus === 'success' && (
        <div className="p-3 bg-karma-up/10 border border-karma-up/30 rounded-lg text-sm text-karma-up">
          Subscription activated successfully!
        </div>
      )}

      {/* General */}
      <section className="bg-bg-secondary border border-border-default rounded-lg p-4 space-y-3">
        <h2 className="text-sm font-semibold text-text-secondary">General</h2>
        <div>
          <label className="block text-xs text-text-muted mb-1">Organization Name</label>
          <div className="flex gap-2">
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="flex-1 px-3 py-2 bg-bg-tertiary border border-border-default rounded-lg text-text-primary text-sm focus:border-accent-gold focus:outline-none"
            />
            <Button variant="secondary" size="sm" onClick={handleSaveName} disabled={name === company.name}>
              Save
            </Button>
          </div>
        </div>
        <div>
          <label className="block text-xs text-text-muted mb-1">Invite Code</label>
          <code className="text-sm font-mono text-accent-gold">{company.invite_code}</code>
        </div>
      </section>

      {/* Billing */}
      <section className="bg-bg-secondary border border-border-default rounded-lg p-4 space-y-3">
        <h2 className="text-sm font-semibold text-text-secondary flex items-center gap-2">
          <CreditCard size={16} /> Billing
        </h2>
        {billing && billing.status === 'active' ? (
          <div>
            <p className="text-sm text-text-primary">
              Active — {billing.quantity} seats x &yen;490/mo
            </p>
            <p className="text-xs text-text-muted">
              Period ends: {billing.current_period_end ? new Date(billing.current_period_end).toLocaleDateString() : '-'}
            </p>
            <Button variant="secondary" size="sm" className="mt-2" onClick={handlePortal}>
              Manage Subscription
            </Button>
          </div>
        ) : (
          <div>
            <p className="text-sm text-text-muted mb-3">
              Activate organization subscription to unlock re-diagnosis and AI consultation for all members.
              &yen;490/person/month.
            </p>
            <div className="flex gap-2">
              <Button variant="primary" size="sm" onClick={() => handleCheckout('monthly')}>
                Monthly Plan
              </Button>
              <Button variant="secondary" size="sm" onClick={() => handleCheckout('annual')}>
                Annual Plan (save 17%)
              </Button>
            </div>
          </div>
        )}
      </section>

      {/* Departments */}
      <section className="bg-bg-secondary border border-border-default rounded-lg p-4 space-y-3">
        <h2 className="text-sm font-semibold text-text-secondary flex items-center gap-2">
          <Building2 size={16} /> Departments & Teams
        </h2>
        {company.departments.map((dept) => (
          <div key={dept.id} className="p-3 bg-bg-tertiary rounded-lg">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-text-primary">{dept.name}</span>
              <button onClick={() => handleDeleteDept(dept.id)} className="text-text-muted hover:text-karma-down">
                <Trash2 size={14} />
              </button>
            </div>
            {dept.teams.length > 0 && (
              <div className="ml-4 space-y-1">
                {dept.teams.map((team) => (
                  <div key={team.id} className="flex items-center justify-between text-sm">
                    <span className="text-text-secondary">{team.name}</span>
                    <button onClick={() => handleDeleteTeam(team.id)} className="text-text-muted hover:text-karma-down">
                      <Trash2 size={12} />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}

        <div className="flex gap-2">
          <input
            type="text"
            placeholder="New department"
            value={newDeptName}
            onChange={(e) => setNewDeptName(e.target.value)}
            className="flex-1 px-3 py-1.5 bg-bg-tertiary border border-border-default rounded text-sm text-text-primary placeholder-text-muted focus:border-accent-gold focus:outline-none"
          />
          <Button variant="secondary" size="sm" onClick={handleCreateDept} disabled={!newDeptName.trim()}>
            <Plus size={14} />
          </Button>
        </div>

        {company.departments.length > 0 && (
          <div className="flex gap-2">
            <input
              type="text"
              placeholder="New team"
              value={newTeamName}
              onChange={(e) => setNewTeamName(e.target.value)}
              className="flex-1 px-3 py-1.5 bg-bg-tertiary border border-border-default rounded text-sm text-text-primary placeholder-text-muted focus:border-accent-gold focus:outline-none"
            />
            <select
              value={newTeamDept}
              onChange={(e) => setNewTeamDept(e.target.value)}
              className="px-2 py-1.5 bg-bg-tertiary border border-border-default rounded text-sm text-text-secondary"
            >
              <option value="">Dept...</option>
              {company.departments.map((d) => (
                <option key={d.id} value={d.id}>{d.name}</option>
              ))}
            </select>
            <Button variant="secondary" size="sm" onClick={handleCreateTeam} disabled={!newTeamName.trim() || !newTeamDept}>
              <Plus size={14} />
            </Button>
          </div>
        )}
      </section>
    </div>
  )
}
