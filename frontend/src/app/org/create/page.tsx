'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { Building2 } from 'lucide-react'
import { api } from '@/lib/api'
import Button from '@/components/ui/Button'

export default function CreateOrgPage() {
  const router = useRouter()
  const [name, setName] = useState('')
  const [slug, setSlug] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!name.trim()) return

    setIsLoading(true)
    setError('')
    try {
      const result = await api.createCompany({
        name: name.trim(),
        slug: slug.trim() || undefined,
      })
      router.push(`/org/${result.slug}`)
    } catch (err: any) {
      setError(err.message || 'Failed to create organization')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="max-w-lg mx-auto px-4 py-8">
      <div className="flex items-center gap-3 mb-6">
        <div className="w-10 h-10 rounded-lg bg-accent-gold/10 flex items-center justify-center">
          <Building2 size={20} className="text-accent-gold" />
        </div>
        <h1 className="text-2xl font-bold text-text-primary">Create Organization</h1>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-text-secondary mb-1">
            Organization Name *
          </label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Acme Corp"
            maxLength={100}
            className="w-full px-3 py-2 bg-bg-tertiary border border-border-default rounded-lg text-text-primary placeholder-text-muted focus:border-accent-gold focus:outline-none"
            required
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-text-secondary mb-1">
            URL Slug (optional)
          </label>
          <div className="flex items-center gap-1">
            <span className="text-text-muted text-sm">/org/</span>
            <input
              type="text"
              value={slug}
              onChange={(e) => setSlug(e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, ''))}
              placeholder="acme-corp"
              maxLength={100}
              className="flex-1 px-3 py-2 bg-bg-tertiary border border-border-default rounded-lg text-text-primary placeholder-text-muted focus:border-accent-gold focus:outline-none"
            />
          </div>
          <p className="text-xs text-text-muted mt-1">Leave empty to auto-generate from name.</p>
        </div>

        {error && (
          <p className="text-sm text-karma-down">{error}</p>
        )}

        <Button type="submit" variant="primary" className="w-full" disabled={isLoading || !name.trim()}>
          {isLoading ? 'Creating...' : 'Create Organization'}
        </Button>
      </form>
    </div>
  )
}
