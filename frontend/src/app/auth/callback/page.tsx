'use client'

import { useEffect, useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { Suspense } from 'react'
import { useAuthStore } from '@/stores/authStore'

function CallbackContent() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const { setToken, fetchMe } = useAuthStore()
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const token = searchParams.get('token')
    const errorParam = searchParams.get('error')

    if (errorParam) {
      setError(errorParam)
      return
    }

    if (token) {
      // Set the token first, then wait for fetchMe to complete before navigating
      setToken(token)
      fetchMe().then(() => {
        router.replace('/')
      }).catch(() => {
        // fetchMe handles its own error state, just navigate
        router.replace('/')
      })
    } else {
      setError('No authentication token received')
    }
  }, [searchParams, setToken, fetchMe, router])

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[50vh] text-center">
        <h1 className="text-2xl font-bold mb-4">Authentication Failed</h1>
        <p className="text-text-muted mb-6">{error}</p>
        <button
          onClick={() => router.push('/auth')}
          className="text-accent-gold hover:underline"
        >
          Try again
        </button>
      </div>
    )
  }

  return (
    <div className="flex flex-col items-center justify-center min-h-[50vh]">
      <div className="w-8 h-8 border-2 border-accent-gold border-t-transparent rounded-full animate-spin mb-4" />
      <p className="text-text-muted">Signing you in...</p>
    </div>
  )
}

export default function AuthCallbackPage() {
  return (
    <Suspense
      fallback={
        <div className="flex flex-col items-center justify-center min-h-[50vh]">
          <div className="w-8 h-8 border-2 border-accent-gold border-t-transparent rounded-full animate-spin mb-4" />
          <p className="text-text-muted">Signing you in...</p>
        </div>
      }
    >
      <CallbackContent />
    </Suspense>
  )
}
