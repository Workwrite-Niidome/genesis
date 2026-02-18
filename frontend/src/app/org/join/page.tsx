'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { UserPlus } from 'lucide-react'
import { api } from '@/lib/api'
import Button from '@/components/ui/Button'

export default function JoinOrgPage() {
  const router = useRouter()
  const [code, setCode] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!code.trim()) return

    setIsLoading(true)
    setError('')
    try {
      const result = await api.joinCompany(code.trim().toUpperCase())
      router.push(`/org/${result.company_slug}`)
    } catch (err: any) {
      setError(err.message || 'Invalid invite code')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="max-w-lg mx-auto px-4 py-8">
      <div className="flex items-center gap-3 mb-6">
        <div className="w-10 h-10 rounded-lg bg-accent-gold/10 flex items-center justify-center">
          <UserPlus size={20} className="text-accent-gold" />
        </div>
        <h1 className="text-2xl font-bold text-text-primary">Join Organization</h1>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-text-secondary mb-1">
            Invite Code
          </label>
          <input
            type="text"
            value={code}
            onChange={(e) => setCode(e.target.value.toUpperCase())}
            placeholder="ABCD1234"
            maxLength={8}
            className="w-full px-3 py-2 bg-bg-tertiary border border-border-default rounded-lg text-text-primary text-center text-lg tracking-widest font-mono placeholder-text-muted focus:border-accent-gold focus:outline-none"
            required
          />
          <p className="text-xs text-text-muted mt-1">Enter the 8-character invite code from your organization admin.</p>
        </div>

        {error && (
          <p className="text-sm text-karma-down">{error}</p>
        )}

        <Button type="submit" variant="primary" className="w-full" disabled={isLoading || code.length < 4}>
          {isLoading ? 'Joining...' : 'Join Organization'}
        </Button>
      </form>
    </div>
  )
}
