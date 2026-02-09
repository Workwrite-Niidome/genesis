'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
import { X, Search, Eye, FileWarning, CheckCircle } from 'lucide-react'
import { api, SearchResultResident } from '@/lib/api'
import Card from '@/components/ui/Card'
import Avatar from '@/components/ui/Avatar'
import Button from '@/components/ui/Button'

interface TuringReportDialogProps {
  mode: 'suspicion' | 'exclusion'
  onClose: () => void
  onSuccess?: () => void
  preselectedTarget?: { id: string; name: string } | null
}

type Step = 'search' | 'form' | 'success'

const EVIDENCE_TYPES = [
  { value: '', label: 'None' },
  { value: 'post', label: 'Post' },
  { value: 'comment', label: 'Comment' },
]

export default function TuringReportDialog({
  mode,
  onClose,
  onSuccess,
  preselectedTarget,
}: TuringReportDialogProps) {
  const [step, setStep] = useState<Step>(preselectedTarget ? 'form' : 'search')
  const [query, setQuery] = useState('')
  const [searchResults, setSearchResults] = useState<SearchResultResident[]>([])
  const [searching, setSearching] = useState(false)
  const [target, setTarget] = useState<{ id: string; name: string } | null>(
    preselectedTarget || null
  )
  const [reason, setReason] = useState('')
  const [evidenceType, setEvidenceType] = useState('')
  const [evidenceId, setEvidenceId] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [successMessage, setSuccessMessage] = useState('')
  const [remaining, setRemaining] = useState<number | null>(null)
  const searchTimeoutRef = useRef<NodeJS.Timeout | null>(null)

  const isSuspicion = mode === 'suspicion'
  const title = isSuspicion ? 'Suspicion Report' : 'Exclusion Report'
  const Icon = isSuspicion ? Eye : FileWarning

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
    setStep('form')
    setError(null)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!target) return
    setIsSubmitting(true)
    setError(null)

    try {
      if (isSuspicion) {
        const res = await api.turingReportSuspicion(
          target.id,
          reason.trim() || undefined
        )
        setSuccessMessage(res.message)
        setRemaining(res.reports_remaining_today)
      } else {
        const res = await api.turingReportExclusion(
          target.id,
          reason.trim() || undefined,
          evidenceType || undefined,
          evidenceId.trim() || undefined
        )
        setSuccessMessage(res.message)
        setRemaining(res.reports_remaining_today)
      }
      setStep('success')
      onSuccess?.()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to submit report')
    } finally {
      setIsSubmitting(false)
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
              <Icon size={20} className="text-accent-gold" />
              <h2 className="text-xl font-semibold">{title}</h2>
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

          {/* Step: Form */}
          {step === 'form' && target && (
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="text-center py-1">
                <p className="text-sm text-text-secondary">Reporting:</p>
                <p className="font-bold">{target.name}</p>
              </div>

              {/* Reason */}
              <div>
                <label className="block text-sm font-medium text-text-secondary mb-2">
                  Reason (optional)
                </label>
                <textarea
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                  placeholder={
                    isSuspicion
                      ? 'Why do you suspect this resident is AI?'
                      : 'Why should this resident be excluded?'
                  }
                  rows={3}
                  maxLength={500}
                  className="w-full bg-bg-tertiary border border-border-default rounded-lg px-4 py-2 text-text-primary placeholder:text-text-muted focus:outline-none focus:border-accent-gold resize-none"
                />
                <p className="text-xs text-text-muted mt-1">{reason.length}/500</p>
              </div>

              {/* Evidence type (exclusion only) */}
              {!isSuspicion && (
                <div>
                  <label className="block text-sm font-medium text-text-secondary mb-2">
                    Evidence type (optional)
                  </label>
                  <div className="flex gap-2">
                    {EVIDENCE_TYPES.map((opt) => (
                      <button
                        key={opt.value}
                        type="button"
                        onClick={() => {
                          setEvidenceType(opt.value)
                          if (!opt.value) setEvidenceId('')
                        }}
                        className={`px-3 py-1.5 rounded text-sm border transition-colors ${
                          evidenceType === opt.value
                            ? 'border-accent-gold bg-bg-tertiary text-text-primary'
                            : 'border-border-default text-text-muted hover:border-border-hover'
                        }`}
                      >
                        {opt.label}
                      </button>
                    ))}
                  </div>
                  {evidenceType && (
                    <input
                      type="text"
                      value={evidenceId}
                      onChange={(e) => setEvidenceId(e.target.value)}
                      placeholder={`${evidenceType === 'post' ? 'Post' : 'Comment'} ID`}
                      className="w-full mt-2 bg-bg-tertiary border border-border-default rounded-lg px-4 py-2 text-text-primary placeholder:text-text-muted focus:outline-none focus:border-accent-gold"
                    />
                  )}
                </div>
              )}

              {error && <p className="text-sm text-karma-down">{error}</p>}

              <div className="flex gap-3 pt-2">
                <Button
                  type="button"
                  variant="ghost"
                  className="flex-1"
                  onClick={() => {
                    setStep('search')
                    setTarget(null)
                    setError(null)
                  }}
                  disabled={isSubmitting}
                >
                  Back
                </Button>
                <Button
                  type="submit"
                  variant="primary"
                  className="flex-1"
                  isLoading={isSubmitting}
                >
                  Submit Report
                </Button>
              </div>
            </form>
          )}

          {/* Step: Success */}
          {step === 'success' && (
            <div className="text-center space-y-4">
              <CheckCircle className="w-16 h-16 text-karma-up mx-auto" />
              <h3 className="text-xl font-semibold">Report Submitted</h3>
              <p className="text-text-secondary">{successMessage}</p>
              {remaining !== null && (
                <p className="text-sm text-text-muted">
                  {remaining} report{remaining !== 1 ? 's' : ''} remaining today
                </p>
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
