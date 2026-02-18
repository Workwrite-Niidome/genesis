'use client'

import { useState, useEffect } from 'react'
import { useParams } from 'next/navigation'
import Link from 'next/link'
import { ArrowLeft, UserPlus, Trash2 } from 'lucide-react'
import { api, CompanyMemberItem } from '@/lib/api'
import Button from '@/components/ui/Button'

export default function OrgMembersPage() {
  const params = useParams()
  const slug = params.slug as string
  const [members, setMembers] = useState<CompanyMemberItem[]>([])
  const [total, setTotal] = useState(0)
  const [isLoading, setIsLoading] = useState(true)
  const [showInvite, setShowInvite] = useState(false)
  const [inviteName, setInviteName] = useState('')
  const [inviteEmail, setInviteEmail] = useState('')
  const [inviteRole, setInviteRole] = useState('member')

  useEffect(() => {
    loadMembers()
  }, [slug])

  const loadMembers = () => {
    api.getCompanyMembers(slug)
      .then((res) => {
        setMembers(res.members)
        setTotal(res.total)
      })
      .catch(() => {})
      .finally(() => setIsLoading(false))
  }

  const handleInvite = async () => {
    if (!inviteName.trim()) return
    try {
      await api.inviteMember(slug, {
        display_name: inviteName.trim(),
        email: inviteEmail.trim() || undefined,
        role: inviteRole,
      })
      setInviteName('')
      setInviteEmail('')
      setShowInvite(false)
      loadMembers()
    } catch {}
  }

  const handleRemove = async (id: string) => {
    if (!confirm('Remove this member?')) return
    try {
      await api.removeCompanyMember(slug, id)
      loadMembers()
    } catch {}
  }

  const handleRoleChange = async (id: string, newRole: string) => {
    try {
      await api.updateCompanyMember(slug, id, { role: newRole })
      loadMembers()
    } catch {}
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="animate-spin w-8 h-8 border-2 border-accent-gold border-t-transparent rounded-full" />
      </div>
    )
  }

  return (
    <div className="max-w-3xl mx-auto px-4 py-8">
      <div className="flex items-center gap-3 mb-6">
        <Link href={`/org/${slug}`} className="text-text-muted hover:text-text-primary">
          <ArrowLeft size={20} />
        </Link>
        <h1 className="text-2xl font-bold text-text-primary flex-1">Members ({total})</h1>
        <Button variant="primary" size="sm" onClick={() => setShowInvite(!showInvite)}>
          <UserPlus size={14} className="mr-1" /> Invite
        </Button>
      </div>

      {/* Invite Form */}
      {showInvite && (
        <div className="bg-bg-secondary border border-border-default rounded-lg p-4 mb-6 space-y-3">
          <input
            type="text"
            placeholder="Display name"
            value={inviteName}
            onChange={(e) => setInviteName(e.target.value)}
            className="w-full px-3 py-2 bg-bg-tertiary border border-border-default rounded-lg text-text-primary placeholder-text-muted focus:border-accent-gold focus:outline-none text-sm"
          />
          <input
            type="email"
            placeholder="Email (optional)"
            value={inviteEmail}
            onChange={(e) => setInviteEmail(e.target.value)}
            className="w-full px-3 py-2 bg-bg-tertiary border border-border-default rounded-lg text-text-primary placeholder-text-muted focus:border-accent-gold focus:outline-none text-sm"
          />
          <div className="flex items-center gap-3">
            <select
              value={inviteRole}
              onChange={(e) => setInviteRole(e.target.value)}
              className="px-3 py-2 bg-bg-tertiary border border-border-default rounded-lg text-text-primary text-sm"
            >
              <option value="member">Member</option>
              <option value="manager">Manager</option>
              <option value="admin">Admin</option>
            </select>
            <Button variant="primary" size="sm" onClick={handleInvite} disabled={!inviteName.trim()}>
              Send Invite
            </Button>
          </div>
        </div>
      )}

      {/* Member List */}
      <div className="space-y-2">
        {members.map((m) => (
          <div
            key={m.id}
            className="flex items-center justify-between p-3 bg-bg-secondary border border-border-default rounded-lg"
          >
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-full bg-bg-tertiary flex items-center justify-center text-xs font-medium text-text-secondary">
                {m.display_name.charAt(0).toUpperCase()}
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-text-primary">{m.display_name}</span>
                  {m.resident_name && m.resident_name !== m.display_name && (
                    <span className="text-xs text-text-muted">@{m.resident_name}</span>
                  )}
                </div>
                <div className="flex items-center gap-2 text-xs text-text-muted">
                  {m.struct_type && (
                    <span className="font-mono text-accent-gold/70">{m.struct_type}</span>
                  )}
                  {m.team_name && <span>{m.team_name}</span>}
                  {m.status === 'invited' && (
                    <span className="text-yellow-500">Invited</span>
                  )}
                </div>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <select
                value={m.role}
                onChange={(e) => handleRoleChange(m.id, e.target.value)}
                className="px-2 py-1 bg-bg-tertiary border border-border-default rounded text-xs text-text-secondary"
              >
                <option value="member">Member</option>
                <option value="manager">Manager</option>
                <option value="admin">Admin</option>
              </select>
              <button
                onClick={() => handleRemove(m.id)}
                className="p-1 text-text-muted hover:text-karma-down"
                title="Remove member"
              >
                <Trash2 size={14} />
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
