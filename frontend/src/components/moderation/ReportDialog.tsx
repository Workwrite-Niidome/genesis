'use client'

import { useState, useEffect, useCallback } from 'react'
import { X, CheckCircle } from 'lucide-react'
import { api } from '@/lib/api'
import Button from '@/components/ui/Button'
import Card from '@/components/ui/Card'

type TargetType = 'post' | 'comment' | 'resident'

interface ReportDialogProps {
  targetType: TargetType
  targetId: string
  onClose: () => void
  onSuccess?: () => void
}

const REPORT_REASONS = [
  { value: 'spam', label: 'Spam' },
  { value: 'harassment', label: 'Harassment' },
  { value: 'hate', label: 'Hate/Discrimination' },
  { value: 'misinformation', label: 'Misinformation' },
  { value: 'other', label: 'Other' },
] as const

export default function ReportDialog({
  targetType,
  targetId,
  onClose,
  onSuccess,
}: ReportDialogProps) {
  const [reason, setReason] = useState<string>('')
  const [description, setDescription] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [showSuccess, setShowSuccess] = useState(false)

  // Handle escape key to close
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose()
      }
    },
    [onClose]
  )

  useEffect(() => {
    document.addEventListener('keydown', handleKeyDown)
    // Prevent body scroll when modal is open
    document.body.style.overflow = 'hidden'

    return () => {
      document.removeEventListener('keydown', handleKeyDown)
      document.body.style.overflow = 'unset'
    }
  }, [handleKeyDown])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)

    if (!reason) {
      setError('Please select a reason')
      return
    }

    setIsSubmitting(true)

    try {
      await api.submitReport({
        target_type: targetType,
        target_id: targetId,
        reason,
        description: description.trim() || undefined,
      })

      setShowSuccess(true)
      setTimeout(() => {
        onSuccess?.()
        onClose()
      }, 1500)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to submit report')
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleOverlayClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget) {
      onClose()
    }
  }

  const targetTypeLabel = {
    post: 'Post',
    comment: 'Comment',
    resident: 'User',
  }[targetType]

  if (showSuccess) {
    return (
      <div
        className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4"
        onClick={handleOverlayClick}
      >
        <Card className="w-full max-w-md">
          <div className="p-6 text-center">
            <CheckCircle className="w-16 h-16 text-karma-up mx-auto mb-4" />
            <h2 className="text-xl font-semibold mb-2">Report Submitted</h2>
            <p className="text-text-secondary">
              Thank you for your report. We will review it.
            </p>
          </div>
        </Card>
      </div>
    )
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
            <h2 className="text-xl font-semibold">
              Report {targetTypeLabel}
            </h2>
            <button
              onClick={onClose}
              className="p-1 text-text-muted hover:text-text-primary transition-colors"
              aria-label="Close"
            >
              <X size={20} />
            </button>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Reason selection */}
            <div>
              <label className="block text-sm font-medium text-text-secondary mb-3">
                Reason
              </label>
              <div className="space-y-2">
                {REPORT_REASONS.map((option) => (
                  <label
                    key={option.value}
                    className={`flex items-center p-3 rounded-lg border cursor-pointer transition-colors ${
                      reason === option.value
                        ? 'border-accent-gold bg-bg-tertiary'
                        : 'border-border-default hover:border-border-hover hover:bg-bg-tertiary'
                    }`}
                  >
                    <input
                      type="radio"
                      name="reason"
                      value={option.value}
                      checked={reason === option.value}
                      onChange={(e) => setReason(e.target.value)}
                      className="sr-only"
                    />
                    <span
                      className={`w-4 h-4 rounded-full border-2 mr-3 flex items-center justify-center ${
                        reason === option.value
                          ? 'border-accent-gold'
                          : 'border-border-default'
                      }`}
                    >
                      {reason === option.value && (
                        <span className="w-2 h-2 rounded-full bg-accent-gold" />
                      )}
                    </span>
                    <span className="text-text-primary">{option.label}</span>
                  </label>
                ))}
              </div>
            </div>

            {/* Optional description */}
            <div>
              <label className="block text-sm font-medium text-text-secondary mb-2">
                Details (optional)
              </label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Provide additional details..."
                rows={3}
                maxLength={1000}
                className="w-full bg-bg-tertiary border border-border-default rounded-lg px-4 py-2 text-text-primary placeholder:text-text-muted focus:outline-none focus:border-accent-gold resize-none"
              />
              <p className="text-xs text-text-muted mt-1">
                {description.length}/1000
              </p>
            </div>

            {/* Error */}
            {error && (
              <p className="text-sm text-karma-down">{error}</p>
            )}

            {/* Actions */}
            <div className="flex justify-end gap-3 pt-4">
              <Button
                type="button"
                variant="ghost"
                onClick={onClose}
                disabled={isSubmitting}
              >
                Cancel
              </Button>
              <Button
                type="submit"
                variant="primary"
                isLoading={isSubmitting}
                disabled={!reason}
              >
                Report
              </Button>
            </div>
          </form>
        </div>
      </Card>
    </div>
  )
}
