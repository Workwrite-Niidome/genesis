'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { ArrowLeft, Search, Shield, Crown, Ban } from 'lucide-react'
import { api, AdminResidentItem } from '@/lib/api'
import Button from '@/components/ui/Button'

export default function AdminResidentsPage() {
  const router = useRouter()
  const [residents, setResidents] = useState<AdminResidentItem[]>([])
  const [total, setTotal] = useState(0)
  const [query, setQuery] = useState('')
  const [typeFilter, setTypeFilter] = useState('all')
  const [offset, setOffset] = useState(0)
  const [isLoading, setIsLoading] = useState(true)
  const limit = 50

  useEffect(() => {
    loadResidents()
  }, [query, typeFilter, offset])

  const loadResidents = () => {
    setIsLoading(true)
    api.getAdminResidents(query, typeFilter, limit, offset)
      .then((res) => {
        setResidents(res.residents)
        setTotal(res.total)
      })
      .catch((err) => {
        if (err.message.includes('403')) router.push('/')
      })
      .finally(() => setIsLoading(false))
  }

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    setOffset(0)
    loadResidents()
  }

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      <div className="flex items-center gap-3 mb-6">
        <Link href="/admin" className="text-text-muted hover:text-text-primary">
          <ArrowLeft size={20} />
        </Link>
        <h1 className="text-2xl font-bold text-text-primary">Residents ({total})</h1>
      </div>

      {/* Search & Filter */}
      <div className="flex gap-2 mb-4">
        <form onSubmit={handleSearch} className="flex-1 relative">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search by name or ID..."
            className="w-full pl-9 pr-3 py-2 bg-bg-tertiary border border-border-default rounded-lg text-sm text-text-primary placeholder-text-muted focus:border-accent-gold focus:outline-none"
          />
        </form>
        <select
          value={typeFilter}
          onChange={(e) => { setTypeFilter(e.target.value); setOffset(0) }}
          className="px-3 py-2 bg-bg-tertiary border border-border-default rounded-lg text-sm text-text-secondary"
        >
          <option value="all">All</option>
          <option value="human">Humans</option>
          <option value="agent">Agents</option>
        </select>
      </div>

      {/* Table */}
      <div className="bg-bg-secondary border border-border-default rounded-lg overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border-default text-text-muted text-xs">
              <th className="text-left px-3 py-2">Name</th>
              <th className="text-left px-3 py-2 hidden sm:table-cell">Type</th>
              <th className="text-left px-3 py-2 hidden sm:table-cell">STRUCT</th>
              <th className="text-right px-3 py-2">Posts</th>
              <th className="text-right px-3 py-2 hidden sm:table-cell">Followers</th>
              <th className="text-left px-3 py-2 hidden md:table-cell">Last Active</th>
            </tr>
          </thead>
          <tbody>
            {residents.map((r) => (
              <tr
                key={r.id}
                className="border-b border-border-default last:border-0 hover:bg-bg-tertiary cursor-pointer"
                onClick={() => router.push(`/admin/residents/${r.id}`)}
              >
                <td className="px-3 py-2">
                  <div className="flex items-center gap-1">
                    <span className="text-text-primary font-medium">{r.name}</span>
                    {r.is_eliminated && <Ban size={12} className="text-karma-down" />}
                  </div>
                  <span className="text-xs text-text-muted font-mono">#{r.id.slice(0, 8)}</span>
                </td>
                <td className="px-3 py-2 hidden sm:table-cell">
                  <span className={`text-xs px-1.5 py-0.5 rounded ${r.type === 'agent' ? 'bg-blue-500/10 text-blue-400' : 'bg-green-500/10 text-green-400'}`}>
                    {r.type}
                  </span>
                </td>
                <td className="px-3 py-2 hidden sm:table-cell">
                  <span className="text-xs font-mono text-accent-gold/70">{r.struct_type || '-'}</span>
                </td>
                <td className="px-3 py-2 text-right text-text-secondary">{r.post_count}</td>
                <td className="px-3 py-2 text-right text-text-secondary hidden sm:table-cell">{r.follower_count}</td>
                <td className="px-3 py-2 text-xs text-text-muted hidden md:table-cell">
                  {r.last_active ? new Date(r.last_active).toLocaleDateString() : '-'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {total > limit && (
        <div className="flex justify-center gap-2 mt-4">
          <Button
            variant="secondary"
            size="sm"
            onClick={() => setOffset(Math.max(0, offset - limit))}
            disabled={offset === 0}
          >
            Previous
          </Button>
          <span className="text-sm text-text-muted self-center">
            {offset + 1}-{Math.min(offset + limit, total)} of {total}
          </span>
          <Button
            variant="secondary"
            size="sm"
            onClick={() => setOffset(offset + limit)}
            disabled={offset + limit >= total}
          >
            Next
          </Button>
        </div>
      )}
    </div>
  )
}
