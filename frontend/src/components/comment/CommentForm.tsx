'use client'

import { useState, useRef, useEffect } from 'react'
import { api } from '@/lib/api'
import { useAuthStore } from '@/stores/authStore'
import Button from '@/components/ui/Button'
import Avatar from '@/components/ui/Avatar'

interface CommentFormProps {
  postId: string
  parentId?: string
  onSubmit?: () => void
  onCancel?: () => void
  placeholder?: string
  autoFocus?: boolean
}

export default function CommentForm({
  postId,
  parentId,
  onSubmit,
  onCancel,
  placeholder = 'Write a comment...',
  autoFocus = false,
}: CommentFormProps) {
  const { resident } = useAuthStore()
  const [content, setContent] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    if (autoFocus && textareaRef.current) {
      textareaRef.current.focus()
    }
  }, [autoFocus])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)

    if (!content.trim()) {
      setError('Comment cannot be empty')
      return
    }

    if (!resident) {
      setError('You must be signed in to comment')
      return
    }

    setIsSubmitting(true)

    try {
      await api.createComment(postId, content.trim(), parentId)
      setContent('')
      onSubmit?.()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to post comment')
    } finally {
      setIsSubmitting(false)
    }
  }

  if (!resident) {
    return (
      <div className="bg-bg-tertiary rounded-lg p-4 text-center">
        <p className="text-text-muted text-sm">
          Sign in to join the conversation
        </p>
      </div>
    )
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      <div className="flex gap-3">
        <Avatar
          name={resident.name}
          src={resident.avatar_url}
          size="sm"
        />
        <div className="flex-1">
          <textarea
            ref={textareaRef}
            value={content}
            onChange={(e) => setContent(e.target.value)}
            placeholder={placeholder}
            rows={3}
            className="w-full bg-bg-tertiary border border-border-default rounded-lg px-4 py-2 text-sm text-text-primary placeholder:text-text-muted focus:outline-none focus:border-accent-gold resize-none"
          />
        </div>
      </div>

      {error && <p className="text-sm text-karma-down">{error}</p>}

      <div className="flex justify-end gap-2">
        {onCancel && (
          <Button type="button" variant="ghost" size="sm" onClick={onCancel}>
            Cancel
          </Button>
        )}
        <Button
          type="submit"
          variant="primary"
          size="sm"
          isLoading={isSubmitting}
          disabled={!content.trim()}
        >
          {parentId ? 'Reply' : 'Comment'}
        </Button>
      </div>
    </form>
  )
}
