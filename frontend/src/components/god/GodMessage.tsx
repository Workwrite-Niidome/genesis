'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { Crown, X } from 'lucide-react'
import { api } from '@/lib/api'

interface GodInfo {
  weekly_message?: string
  weekly_theme?: string
  god?: {
    id: string
    name: string
    avatar_url?: string
  }
  term?: {
    decree?: string
  }
}

export default function GodMessage() {
  const [godInfo, setGodInfo] = useState<GodInfo | null>(null)
  const [dismissed, setDismissed] = useState(false)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    fetchGodInfo()
  }, [])

  const fetchGodInfo = async () => {
    try {
      const data = await api.getCurrentGod()
      setGodInfo(data)
    } catch (err) {
      console.error('Failed to fetch God info:', err)
    } finally {
      setIsLoading(false)
    }
  }

  // Show decree if available, fall back to weekly_message
  const displayMessage = godInfo?.term?.decree || godInfo?.weekly_message
  if (isLoading || dismissed || !displayMessage) {
    return null
  }

  return (
    <div className="relative bg-gradient-to-r from-bg-secondary via-bg-tertiary to-bg-secondary border-b border-god-glow/30 overflow-hidden">
      {/* Glow effect */}
      <div className="absolute inset-0 bg-gradient-to-r from-god-glow/5 via-god-glow/10 to-god-glow/5" />

      <div className="relative max-w-4xl mx-auto px-4 py-3">
        <div className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-3 min-w-0">
            <Crown className="flex-shrink-0 text-god-glow" size={20} />

            <div className="min-w-0">
              {godInfo?.term?.decree && (
                <p className="text-xs text-god-glow font-medium mb-0.5">
                  Decree
                </p>
              )}
              {!godInfo?.term?.decree && godInfo?.weekly_theme && (
                <p className="text-xs text-god-glow font-medium mb-0.5">
                  Week of {godInfo.weekly_theme}
                </p>
              )}
              <p className="text-sm text-text-primary truncate">
                &ldquo;{displayMessage}&rdquo;
              </p>
              {godInfo?.god && (
                <Link
                  href={`/u/${godInfo.god.name}`}
                  className="text-xs text-text-muted hover:text-god-glow"
                >
                  — {godInfo.god.name}, God of Genesis
                </Link>
              )}
            </div>
          </div>

          <button
            onClick={() => setDismissed(true)}
            className="flex-shrink-0 p-1 text-text-muted hover:text-text-primary"
            aria-label="Dismiss message"
          >
            <X size={16} />
          </button>
        </div>
      </div>
    </div>
  )
}
