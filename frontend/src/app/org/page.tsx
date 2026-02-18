'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { Building2, Plus, ChevronRight } from 'lucide-react'
import { api, CompanyListItem } from '@/lib/api'
import { useAuthStore } from '@/stores/authStore'
import Button from '@/components/ui/Button'

export default function OrgListPage() {
  const router = useRouter()
  const { resident } = useAuthStore()
  const [companies, setCompanies] = useState<CompanyListItem[]>([])
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    if (!resident) {
      router.push('/auth')
      return
    }
    api.getMyCompanies()
      .then(setCompanies)
      .catch(() => {})
      .finally(() => setIsLoading(false))
  }, [resident, router])

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="animate-spin w-8 h-8 border-2 border-accent-gold border-t-transparent rounded-full" />
      </div>
    )
  }

  return (
    <div className="max-w-2xl mx-auto px-4 py-8">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-text-primary">Organizations</h1>
        <div className="flex gap-2">
          <Link href="/org/join">
            <Button variant="secondary" size="sm">Join</Button>
          </Link>
          <Link href="/org/create">
            <Button variant="primary" size="sm">
              <Plus size={14} className="mr-1" />
              Create
            </Button>
          </Link>
        </div>
      </div>

      {companies.length === 0 ? (
        <div className="text-center py-16">
          <Building2 size={48} className="mx-auto mb-4 text-text-muted" />
          <p className="text-text-secondary mb-2">No organizations yet</p>
          <p className="text-sm text-text-muted mb-6">Create an organization or join one with an invite code.</p>
          <div className="flex gap-3 justify-center">
            <Link href="/org/join">
              <Button variant="secondary" size="sm">Join with Code</Button>
            </Link>
            <Link href="/org/create">
              <Button variant="primary" size="sm">Create Organization</Button>
            </Link>
          </div>
        </div>
      ) : (
        <div className="space-y-2">
          {companies.map((c) => (
            <Link
              key={c.id}
              href={`/org/${c.slug}`}
              className="flex items-center justify-between p-4 bg-bg-secondary border border-border-default rounded-lg hover:border-border-hover transition-colors"
            >
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-accent-gold/10 flex items-center justify-center">
                  <Building2 size={20} className="text-accent-gold" />
                </div>
                <div>
                  <p className="font-medium text-text-primary">{c.name}</p>
                  <p className="text-xs text-text-muted">
                    {c.role === 'admin' ? 'Admin' : c.role === 'manager' ? 'Manager' : 'Member'}
                  </p>
                </div>
              </div>
              <ChevronRight size={18} className="text-text-muted" />
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}
