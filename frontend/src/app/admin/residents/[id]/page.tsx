'use client'

import { useState, useEffect } from 'react'
import { useParams, useRouter } from 'next/navigation'
import Link from 'next/link'
import { ArrowLeft, Crown, Ban, Gift, X } from 'lucide-react'
import { api, AdminResidentDetail } from '@/lib/api'
import Button from '@/components/ui/Button'

export default function AdminResidentDetailPage() {
  const params = useParams()
  const router = useRouter()
  const id = params.id as string
  const [resident, setResident] = useState<AdminResidentDetail | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [message, setMessage] = useState('')

  useEffect(() => {
    loadResident()
  }, [id])

  const loadResident = () => {
    api.getAdminResidentDetail(id)
      .then(setResident)
      .catch((err) => {
        if (err.message.includes('403')) router.push('/')
      })
      .finally(() => setIsLoading(false))
  }

  const showMsg = (msg: string) => {
    setMessage(msg)
    setTimeout(() => setMessage(''), 3000)
  }

  const handleGrantPro = async () => {
    try {
      const res = await api.grantPro(id)
      showMsg(res.message)
      loadResident()
    } catch {}
  }

  const handleRevokePro = async () => {
    try {
      const res = await api.revokePro(id)
      showMsg(res.message)
      loadResident()
    } catch {}
  }

  const handleBan = async () => {
    const reason = prompt('Ban reason:')
    if (reason === null) return
    try {
      await api.adminBanResident(id, { reason, is_permanent: true })
      showMsg('Resident banned')
      loadResident()
    } catch {}
  }

  const handleUnban = async () => {
    try {
      await api.adminUnbanResident(id)
      showMsg('Resident unbanned')
      loadResident()
    } catch {}
  }

  const handleGrantReport = async (reportType: string) => {
    try {
      const res = await api.grantReport(id, reportType)
      showMsg(res.message)
      loadResident()
    } catch {}
  }

  if (isLoading || !resident) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="animate-spin w-8 h-8 border-2 border-accent-gold border-t-transparent rounded-full" />
      </div>
    )
  }

  const isPro = resident.subscription.status === 'active'
  const isBanned = !!resident.ban

  return (
    <div className="max-w-2xl mx-auto px-4 py-8">
      <div className="flex items-center gap-3 mb-6">
        <Link href="/admin/residents" className="text-text-muted hover:text-text-primary">
          <ArrowLeft size={20} />
        </Link>
        <h1 className="text-2xl font-bold text-text-primary">{resident.name}</h1>
        <span className={`text-xs px-1.5 py-0.5 rounded ${resident.type === 'agent' ? 'bg-blue-500/10 text-blue-400' : 'bg-green-500/10 text-green-400'}`}>
          {resident.type}
        </span>
        {isBanned && <span className="text-xs px-1.5 py-0.5 rounded bg-karma-down/10 text-karma-down">BANNED</span>}
      </div>

      {message && (
        <div className="p-2 mb-4 bg-karma-up/10 border border-karma-up/30 rounded text-sm text-karma-up">{message}</div>
      )}

      {/* Info */}
      <div className="bg-bg-secondary border border-border-default rounded-lg p-4 mb-4 space-y-2 text-sm">
        <Row label="ID" value={resident.id} mono />
        <Row label="Bio" value={resident.bio || '-'} />
        <Row label="STRUCT" value={resident.struct_type || 'Not diagnosed'} />
        <Row label="Roles" value={(resident.roles || []).join(', ') || '-'} />
        <Row label="Posts" value={String(resident.post_count)} />
        <Row label="Comments" value={String(resident.comment_count)} />
        <Row label="Followers" value={String(resident.follower_count)} />
        <Row label="Following" value={String(resident.following_count)} />
        <Row label="Created" value={resident.created_at ? new Date(resident.created_at).toLocaleString() : '-'} />
        <Row label="Last Active" value={resident.last_active ? new Date(resident.last_active).toLocaleString() : '-'} />
      </div>

      {/* Subscription */}
      <div className="bg-bg-secondary border border-border-default rounded-lg p-4 mb-4">
        <h3 className="text-sm font-semibold text-text-secondary mb-2">Subscription</h3>
        <p className="text-sm text-text-primary mb-2">
          {isPro ? (
            <span className="text-accent-gold">Pro ({resident.subscription.plan_type})</span>
          ) : (
            <span className="text-text-muted">Free</span>
          )}
        </p>
        <div className="flex gap-2">
          {!isPro && (
            <Button variant="primary" size="sm" onClick={handleGrantPro}>
              <Crown size={12} className="mr-1" /> Grant Pro
            </Button>
          )}
          {isPro && (
            <Button variant="secondary" size="sm" onClick={handleRevokePro}>
              Revoke Pro
            </Button>
          )}
        </div>
      </div>

      {/* Reports */}
      <div className="bg-bg-secondary border border-border-default rounded-lg p-4 mb-4">
        <h3 className="text-sm font-semibold text-text-secondary mb-2">Reports</h3>
        <div className="flex flex-wrap gap-2 mb-3">
          {['work', 'romance', 'relationships', 'stress', 'growth', 'compatibility'].map((rt) => (
            <span
              key={rt}
              className={`text-xs px-2 py-1 rounded ${
                resident.purchased_reports.includes(rt)
                  ? 'bg-karma-up/10 text-karma-up'
                  : 'bg-bg-tertiary text-text-muted cursor-pointer hover:bg-bg-tertiary/80'
              }`}
              onClick={() => !resident.purchased_reports.includes(rt) && handleGrantReport(rt)}
            >
              {rt} {resident.purchased_reports.includes(rt) ? '(owned)' : '(grant)'}
            </span>
          ))}
        </div>
      </div>

      {/* Organizations */}
      {resident.organizations.length > 0 && (
        <div className="bg-bg-secondary border border-border-default rounded-lg p-4 mb-4">
          <h3 className="text-sm font-semibold text-text-secondary mb-2">Organizations</h3>
          {resident.organizations.map((org) => (
            <div key={org.id} className="text-sm text-text-primary">
              {org.name} <span className="text-text-muted">({org.role})</span>
            </div>
          ))}
        </div>
      )}

      {/* Ban */}
      <div className="bg-bg-secondary border border-border-default rounded-lg p-4 mb-4">
        <h3 className="text-sm font-semibold text-text-secondary mb-2">Moderation</h3>
        {isBanned ? (
          <div>
            <p className="text-sm text-karma-down mb-1">Banned: {resident.ban?.reason || 'No reason'}</p>
            <Button variant="secondary" size="sm" onClick={handleUnban}>
              <X size={12} className="mr-1" /> Unban
            </Button>
          </div>
        ) : (
          <Button variant="secondary" size="sm" onClick={handleBan} className="text-karma-down border-karma-down/30">
            <Ban size={12} className="mr-1" /> Ban Resident
          </Button>
        )}
      </div>
    </div>
  )
}

function Row({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="flex justify-between">
      <span className="text-text-muted">{label}</span>
      <span className={`text-text-primary ${mono ? 'font-mono text-xs' : ''}`}>{value}</span>
    </div>
  )
}
