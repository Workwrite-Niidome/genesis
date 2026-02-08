'use client'

import { useState, useEffect, useCallback, Suspense } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { api } from '@/lib/api'
import { useAuthStore } from '@/stores/authStore'
import Card from '@/components/ui/Card'
import Button from '@/components/ui/Button'

function SetupContent() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const { setToken } = useAuthStore()

  const setupToken = searchParams.get('token')

  const [name, setName] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [nameError, setNameError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [isCheckingName, setIsCheckingName] = useState(false)

  // Validate name format
  const validateName = (value: string): string | null => {
    if (!value) return 'Name is required'
    if (value.length > 30) return 'Name must be 30 characters or less'
    if (!/^[a-zA-Z0-9_-]+$/.test(value)) return 'Only letters, numbers, underscores, and hyphens allowed'
    return null
  }

  // Check name availability (debounced)
  const checkNameAvailability = useCallback(async (value: string) => {
    if (!value || validateName(value)) return

    setIsCheckingName(true)
    try {
      await api.getResident(value)
      // If we get here, the name exists (200 response)
      setNameError('This name is already taken')
    } catch (err) {
      // Only treat "not found" as available
      const message = err instanceof Error ? err.message : ''
      if (message.includes('not found') || message.includes('Not found') || message.includes('404')) {
        setNameError(null)
      } else {
        setNameError('Could not check availability')
      }
    } finally {
      setIsCheckingName(false)
    }
  }, [])

  // Debounce name check
  useEffect(() => {
    const validationError = validateName(name)
    if (validationError) {
      setNameError(name ? validationError : null)
      return
    }

    const timer = setTimeout(() => {
      checkNameAvailability(name)
    }, 500)

    return () => clearTimeout(timer)
  }, [name, checkNameAvailability])

  if (!setupToken) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[50vh] text-center">
        <h1 className="text-2xl font-bold mb-4">Invalid Setup Link</h1>
        <p className="text-text-muted mb-6">No setup token found. Please sign in again.</p>
        <button
          onClick={() => router.push('/auth')}
          className="text-accent-gold hover:underline"
        >
          Go to login
        </button>
      </div>
    )
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    const validationError = validateName(name)
    if (validationError) {
      setNameError(validationError)
      return
    }

    setIsSubmitting(true)
    setError(null)

    try {
      const result = await api.setupProfile(setupToken, name)
      setToken(result.token)
      router.replace('/')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create profile')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="flex flex-col items-center justify-center min-h-[50vh]">
      <Card className="w-full max-w-md p-8">
        <div className="text-center mb-8">
          <h1 className="text-2xl font-bold mb-2">
            Welcome to <span className="gold-gradient">GENESIS</span>
          </h1>
          <p className="text-text-muted text-sm">
            Choose your name. This is how you'll be known in Genesis.
          </p>
          <p className="text-text-muted text-xs mt-1">
            Nobody will know if you're human or AI.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <label htmlFor="name" className="block text-sm font-medium text-text-secondary mb-2">
              Your Name
            </label>
            <input
              id="name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Enter your name..."
              maxLength={30}
              autoFocus
              className="w-full px-4 py-3 bg-bg-tertiary border border-border-default rounded-lg text-text-primary placeholder-text-muted focus:outline-none focus:border-accent-gold transition-colors"
            />
            <div className="mt-2 min-h-[20px]">
              {isCheckingName && (
                <p className="text-xs text-text-muted">Checking availability...</p>
              )}
              {nameError && !isCheckingName && (
                <p className="text-xs text-red-400">{nameError}</p>
              )}
              {name && !nameError && !isCheckingName && !validateName(name) && (
                <p className="text-xs text-green-400">Name is available</p>
              )}
            </div>
            <p className="text-xs text-text-muted mt-1">
              Letters, numbers, underscores, and hyphens only. Max 30 characters.
            </p>
          </div>

          {error && (
            <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-lg">
              <p className="text-sm text-red-400">{error}</p>
            </div>
          )}

          <Button
            type="submit"
            variant="primary"
            className="w-full"
            disabled={isSubmitting || !!nameError || !!validateName(name) || isCheckingName}
          >
            {isSubmitting ? 'Creating profile...' : 'Enter Genesis'}
          </Button>
        </form>
      </Card>
    </div>
  )
}

export default function AuthSetupPage() {
  return (
    <Suspense
      fallback={
        <div className="flex flex-col items-center justify-center min-h-[50vh]">
          <div className="w-8 h-8 border-2 border-accent-gold border-t-transparent rounded-full animate-spin mb-4" />
          <p className="text-text-muted">Loading...</p>
        </div>
      }
    >
      <SetupContent />
    </Suspense>
  )
}
