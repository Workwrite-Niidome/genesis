'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
import { X, Search, Crosshair, CheckCircle, Skull, Crown, AlertTriangle } from 'lucide-react'
import clsx from 'clsx'
import { api, SearchResultResident, TuringKillResponse } from '@/lib/api'
import Card from '@/components/ui/Card'
import Avatar from '@/components/ui/Avatar'
import Button from '@/components/ui/Button'

interface KillDialogProps {
  onClose: () => void
  onSuccess?: () => void
  preselectedTarget?: { id: string; name: string } | null
}

type Step = 'search' | 'confirm' | 'result'

const RESULT_VISUALS = {
  correct: {
    icon: CheckCircle,
    color: 'text-karma-up',
    bg: 'bg-karma-up/10',
    title: 'Correct!',
  },
  backfire: {
    icon: Skull,
    color: 'text-karma-down',
    bg: 'bg-karma-down/10',
    title: 'Backfire!',
  },
  immune: {
    icon: Crown,
    color: 'text-accent-gold',
    bg: 'bg-accent-gold/10',
    title: 'Immune!',
  },
} as const

export default function KillDialog({ onClose, onSuccess, preselectedTarget }: KillDialogProps) {
  const [step, setStep] = useState<Step>(preselectedTarget ? 'confirm' : 'search')
  const [query, setQuery] = useState('')
  const [searchResults, setSearchResults] = useState<SearchResultResident[]>([])
  const [searching, setSearching] = useState(false)
  const [target, setTarget] = useState<{ id: string; name: string } | null>(
    preselectedTarget || null
  )
  const [isExecuting, setIsExecuting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<TuringKillResponse | null>(null)
  const searchTimeoutRef = useRef<NodeJS.Timeout | null>(null)

  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    },
    [onClose]
  )

  useEffect(() => {
    document.addEventListener('keydown', handleKeyDown)
    document.body.style.overflow = 'hidden'
    return () => {
      document.removeEventListener('keydown', handleKeyDown)
      document.body.style.overflow = 'unset'
    }
  }, [handleKeyDown])

  const handleSearch = (value: string) => {
    setQuery(value)
    if (searchTimeoutRef.current) clearTimeout(searchTimeoutRef.current)
    if (value.trim().length < 2) {
      setSearchResults([])
      return
    }
    searchTimeoutRef.current = setTimeout(async () => {
      setSearching(true)
      try {
        const data = await api.searchResidents(value.trim(), 10)
        setSearchResults(data.residents)
      } catch {
        setSearchResults([])
      } finally {
        setSearching(false)
      }
    }, 300)
  }

  const selectTarget = (resident: SearchResultResident) => {
    setTarget({ id: resident.id, name: resident.name })
    setStep('confirm')
    setError(null)
  }

  const executeKill = async () => {
    if (!target) return
    setIsExecuting(true)
    setError(null)
    try {
      const res = await api.turingKill(target.id)
      setResult(res)
      setStep('result')
      onSuccess?.()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to execute kill')
    } finally {
      setIsExecuting(false)
    }
  }

  const handleOverlayClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget) onClose()
  }

  return (
    <div
      className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4"
      onClick={handleOverlayClick}
    >
      <Card className="w-full max-w-md">
        <div className="p-6">
          {/* Header */}
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-2">
              <Crosshair size={20} className="text-karma-down" />
              <h2 className="text-xl font-semibold">Turing Kill</h2>
            </div>
            <button
              onClick={onClose}
              className="p-1 text-text-muted hover:text-text-primary transition-colors"
            >
              <X size={20} />
            </button>
          </div>

          {/* Step: Search */}
          {step === 'search' && (
            <div className="space-y-4">
              <div className="relative">
                <Search
                  size={16}
                  className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted"
                />
                <input
                  type="text"
                  value={query}
                  onChange={(e) => handleSearch(e.target.value)}
                  placeholder="Search for a target..."
                  autoFocus
                  className="w-full bg-bg-tertiary border border-border-default rounded-lg pl-10 pr-4 py-2 text-text-primary placeholder:text-text-muted focus:outline-none focus:border-accent-gold"
                />
              </div>

              {searching && (
                <div className="flex justify-center py-4">
                  <div className="w-5 h-5 border-2 border-accent-gold border-t-transparent rounded-full animate-spin" />
                </div>
              )}

              {searchResults.length > 0 && (
                <div className="space-y-1 max-h-60 overflow-y-auto">
                  {searchResults.map((resident) => (
                    <button
                      key={resident.id}
                      onClick={() => selectTarget(resident)}
                      className="w-full flex items-center gap-3 p-2 rounded-lg hover:bg-bg-tertiary transition-colors text-left"
                    >
                      <Avatar
                        name={resident.name}
                        src={resident.avatar_url}
                        size="sm"
                      />
                      <span className="text-sm font-medium">{resident.name}</span>
                      {resident.karma !== undefined && (
                        <span className="text-xs text-text-muted ml-auto">
                          {resident.karma} karma
                        </span>
                      )}
                    </button>
                  ))}
                </div>
              )}

              {query.length >= 2 && !searching && searchResults.length === 0 && (
                <p className="text-sm text-text-muted text-center py-4">
                  No residents found.
                </p>
              )}
            </div>
          )}

          {/* Step: Confirm */}
          {step === 'confirm' && target && (
            <div className="space-y-4">
              <div className="text-center py-2">
                <p className="text-text-secondary mb-1">Target:</p>
                <p className="text-lg font-bold">{target.name}</p>
              </div>

              <div className="p-3 rounded-lg bg-karma-down/10 border border-karma-down/20">
                <div className="flex items-start gap-2">
                  <AlertTriangle size={16} className="text-karma-down mt-0.5 flex-shrink-0" />
                  <p className="text-sm text-karma-down">
                    If this resident is <strong>human</strong>, the kill will backfire and <strong>you</strong> will be eliminated.
                  </p>
                </div>
              </div>

              {error && <p className="text-sm text-karma-down">{error}</p>}

              <div className="flex gap-3">
                <Button
                  variant="ghost"
                  className="flex-1"
                  onClick={() => {
                    setStep('search')
                    setTarget(null)
                    setError(null)
                  }}
                  disabled={isExecuting}
                >
                  Back
                </Button>
                <Button
                  variant="primary"
                  className="flex-1 !bg-karma-down hover:!bg-karma-down/80 !text-white"
                  onClick={executeKill}
                  isLoading={isExecuting}
                >
                  Execute Kill
                </Button>
              </div>
            </div>
          )}

          {/* Step: Result */}
          {step === 'result' && result && (
            <div className="text-center space-y-4">
              {(() => {
                const config = RESULT_VISUALS[result.result]
                const Icon = config.icon
                return (
                  <>
                    <div
                      className={clsx(
                        'inline-flex items-center justify-center w-20 h-20 rounded-full mx-auto',
                        config.bg
                      )}
                    >
                      <Icon size={40} className={config.color} />
                    </div>
                    <h3 className={clsx('text-2xl font-bold', config.color)}>
                      {config.title}
                    </h3>
                  </>
                )
              })()}

              <p className="text-text-secondary">{result.message}</p>

              {result.attacker_eliminated && (
                <div className="p-3 rounded-lg bg-karma-down/10 border border-karma-down/20">
                  <p className="text-sm text-karma-down font-medium">
                    You have been eliminated.
                  </p>
                </div>
              )}

              <Button variant="secondary" className="w-full" onClick={onClose}>
                Close
              </Button>
            </div>
          )}
        </div>
      </Card>
    </div>
  )
}
