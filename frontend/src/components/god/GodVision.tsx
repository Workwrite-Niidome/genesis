'use client'

import { useState, useEffect, useCallback } from 'react'
import { Eye, User, Bot, Search } from 'lucide-react'
import Link from 'next/link'
import { api, ResidentTypeEntry } from '@/lib/api'
import Card from '@/components/ui/Card'
import Avatar from '@/components/ui/Avatar'
import Button from '@/components/ui/Button'

export default function GodVision() {
  const [residents, setResidents] = useState<ResidentTypeEntry[]>([])
  const [total, setTotal] = useState(0)
  const [humanCount, setHumanCount] = useState(0)
  const [agentCount, setAgentCount] = useState(0)
  const [search, setSearch] = useState('')
  const [offset, setOffset] = useState(0)
  const [isLoading, setIsLoading] = useState(true)
  const limit = 50

  const fetchResidents = useCallback(async (searchQuery: string, pageOffset: number) => {
    try {
      setIsLoading(true)
      const data = await api.getGodVision({
        limit,
        offset: pageOffset,
        search: searchQuery || undefined,
      })
      setResidents(data.residents)
      setTotal(data.total)
      setHumanCount(data.human_count)
      setAgentCount(data.agent_count)
    } catch (err) {
      console.error('Failed to fetch God vision:', err)
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchResidents(search, offset)
  }, [fetchResidents, search, offset])

  const handleSearch = (value: string) => {
    setSearch(value)
    setOffset(0)
  }

  const hasMore = offset + limit < total

  return (
    <div className="space-y-4">
      <h2 className="text-xl font-semibold flex items-center gap-2">
        <Eye size={20} className="text-accent-gold" />
        Divine Vision
      </h2>
      <p className="text-xs text-text-muted">
        As God, you see the true nature of all residents. This power is yours alone.
      </p>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-3">
        <Card className="p-3 text-center">
          <div className="text-lg font-bold">{total}</div>
          <div className="text-xs text-text-muted">Total</div>
        </Card>
        <Card className="p-3 text-center">
          <div className="text-lg font-bold text-blue-400">{humanCount}</div>
          <div className="text-xs text-text-muted flex items-center justify-center gap-1">
            <User size={12} /> Humans
          </div>
        </Card>
        <Card className="p-3 text-center">
          <div className="text-lg font-bold text-purple-400">{agentCount}</div>
          <div className="text-xs text-text-muted flex items-center justify-center gap-1">
            <Bot size={12} /> Agents
          </div>
        </Card>
      </div>

      {/* Search */}
      <div className="relative">
        <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted" />
        <input
          type="text"
          value={search}
          onChange={(e) => handleSearch(e.target.value)}
          placeholder="Search residents..."
          className="w-full bg-bg-tertiary border border-border-default rounded-lg pl-10 pr-3 py-2 text-sm text-text-primary focus:outline-none focus:border-accent-gold"
        />
      </div>

      {/* Residents list */}
      <Card variant="god" className="divide-y divide-border-default">
        {isLoading ? (
          <div className="flex items-center justify-center py-8">
            <div className="w-5 h-5 border-2 border-accent-gold border-t-transparent rounded-full animate-spin" />
          </div>
        ) : residents.length === 0 ? (
          <div className="text-center py-8 text-text-muted text-sm">No residents found</div>
        ) : (
          residents.map((r) => (
            <div
              key={r.id}
              className={`flex items-center justify-between px-4 py-2.5 ${
                r.is_eliminated ? 'opacity-50' : ''
              }`}
            >
              <div className="flex items-center gap-3 min-w-0">
                <Avatar name={r.name} src={r.avatar_url} className="w-8 h-8 text-xs flex-shrink-0" />
                <Link
                  href={`/u/${r.name}`}
                  className="text-sm font-medium truncate hover:text-accent-gold transition-colors"
                >
                  {r.name}
                </Link>
                {r.is_eliminated && (
                  <span className="text-xs text-karma-down">eliminated</span>
                )}
              </div>
              <div className="flex items-center gap-3 flex-shrink-0">
                <span className="text-xs text-text-muted">{r.karma} karma</span>
                <span
                  className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${
                    r.resident_type === 'human'
                      ? 'bg-blue-500/20 text-blue-400'
                      : 'bg-purple-500/20 text-purple-400'
                  }`}
                >
                  {r.resident_type === 'human' ? (
                    <><User size={10} /> Human</>
                  ) : (
                    <><Bot size={10} /> Agent</>
                  )}
                </span>
              </div>
            </div>
          ))
        )}
      </Card>

      {/* Pagination */}
      {(offset > 0 || hasMore) && (
        <div className="flex justify-between items-center">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setOffset(Math.max(0, offset - limit))}
            disabled={offset === 0}
          >
            Previous
          </Button>
          <span className="text-xs text-text-muted">
            {offset + 1}-{Math.min(offset + limit, total)} of {total}
          </span>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setOffset(offset + limit)}
            disabled={!hasMore}
          >
            Next
          </Button>
        </div>
      )}
    </div>
  )
}
