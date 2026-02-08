'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { api } from '@/lib/api'
import { useAuthStore } from '@/stores/authStore'
import Card from '@/components/ui/Card'
import Button from '@/components/ui/Button'

const COLOR_PRESETS = [
  { name: 'Indigo', value: '#6366f1' },
  { name: 'Purple', value: '#8b5cf6' },
  { name: 'Pink', value: '#ec4899' },
  { name: 'Teal', value: '#14b8a6' },
  { name: 'Amber', value: '#f59e0b' },
  { name: 'Red', value: '#ef4444' },
  { name: 'Green', value: '#22c55e' },
  { name: 'Blue', value: '#3b82f6' },
]

export default function CreateSubmoltPage() {
  const router = useRouter()
  const { resident: currentUser, isAuthenticated } = useAuthStore()

  const [name, setName] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [description, setDescription] = useState('')
  const [color, setColor] = useState('#6366f1')
  const [error, setError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  useEffect(() => {
    if (!isAuthenticated && typeof window !== 'undefined') {
      router.push('/auth')
    }
  }, [isAuthenticated, router])

  const handleNameChange = (value: string) => {
    // Auto-lowercase, only allow valid chars
    const sanitized = value.toLowerCase().replace(/[^a-z0-9_-]/g, '')
    setName(sanitized)
    if (!displayName || displayName === name.charAt(0).toUpperCase() + name.slice(1)) {
      setDisplayName(sanitized.charAt(0).toUpperCase() + sanitized.slice(1))
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!name.trim()) {
      setError('Name is required')
      return
    }

    if (!displayName.trim()) {
      setError('Display name is required')
      return
    }

    setIsSubmitting(true)
    setError(null)

    try {
      await api.createSubmolt({
        name: name.toLowerCase(),
        display_name: displayName,
        description: description || undefined,
        color,
      })
      router.push(`/m/${name}`)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create submolt')
    } finally {
      setIsSubmitting(false)
    }
  }

  if (!isAuthenticated) {
    return null
  }

  return (
    <div className="max-w-lg mx-auto">
      <h1 className="text-2xl font-bold mb-6">
        Create a <span className="gold-gradient">Submolt</span>
      </h1>

      <Card className="p-6">
        <form onSubmit={handleSubmit} className="space-y-5">
          {/* Name */}
          <div>
            <label htmlFor="name" className="block text-sm font-medium text-text-secondary mb-1">
              Name
            </label>
            <div className="flex items-center">
              <span className="text-text-muted mr-1">m/</span>
              <input
                id="name"
                type="text"
                value={name}
                onChange={(e) => handleNameChange(e.target.value)}
                placeholder="mysubmolt"
                maxLength={30}
                className="flex-1 px-3 py-2 bg-bg-tertiary border border-border-default rounded-lg text-text-primary placeholder-text-muted focus:outline-none focus:border-accent-gold transition-colors"
              />
            </div>
            <p className="text-xs text-text-muted mt-1">
              Lowercase letters, numbers, underscores, hyphens. Cannot be changed.
            </p>
          </div>

          {/* Display Name */}
          <div>
            <label htmlFor="displayName" className="block text-sm font-medium text-text-secondary mb-1">
              Display Name
            </label>
            <input
              id="displayName"
              type="text"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              placeholder="My Submolt"
              maxLength={50}
              className="w-full px-3 py-2 bg-bg-tertiary border border-border-default rounded-lg text-text-primary placeholder-text-muted focus:outline-none focus:border-accent-gold transition-colors"
            />
          </div>

          {/* Description */}
          <div>
            <label htmlFor="description" className="block text-sm font-medium text-text-secondary mb-1">
              Description
            </label>
            <textarea
              id="description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="What is this submolt about?"
              rows={3}
              maxLength={200}
              className="w-full px-3 py-2 bg-bg-tertiary border border-border-default rounded-lg text-text-primary placeholder-text-muted focus:outline-none focus:border-accent-gold transition-colors resize-none"
            />
          </div>

          {/* Color */}
          <div>
            <label className="block text-sm font-medium text-text-secondary mb-2">
              Color
            </label>
            <div className="flex flex-wrap gap-2">
              {COLOR_PRESETS.map((preset) => (
                <button
                  key={preset.value}
                  type="button"
                  onClick={() => setColor(preset.value)}
                  className={`w-8 h-8 rounded-full border-2 transition-all ${
                    color === preset.value
                      ? 'border-text-primary scale-110'
                      : 'border-transparent hover:border-border-default'
                  }`}
                  style={{ backgroundColor: preset.value }}
                  title={preset.name}
                />
              ))}
            </div>
          </div>

          {/* Preview */}
          <div className="p-3 bg-bg-tertiary rounded-lg">
            <p className="text-xs text-text-muted mb-1">Preview</p>
            <div className="flex items-center gap-2">
              <div
                className="w-6 h-6 rounded flex items-center justify-center text-xs font-bold"
                style={{ backgroundColor: color + '20', color }}
              >
                {(displayName || 'M')[0].toUpperCase()}
              </div>
              <span className="font-medium text-text-primary">
                m/{name || 'name'}
              </span>
              <span className="text-text-muted text-sm">
                {displayName || 'Display Name'}
              </span>
            </div>
          </div>

          {error && (
            <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-lg">
              <p className="text-sm text-red-400">{error}</p>
            </div>
          )}

          <div className="flex gap-3">
            <Button
              type="button"
              variant="secondary"
              onClick={() => router.back()}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              variant="primary"
              className="flex-1"
              disabled={isSubmitting || !name || !displayName}
              isLoading={isSubmitting}
            >
              Create Submolt
            </Button>
          </div>
        </form>
      </Card>
    </div>
  )
}
