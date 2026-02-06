'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { X } from 'lucide-react'
import { api } from '@/lib/api'
import { useUIStore } from '@/stores/uiStore'
import Button from '@/components/ui/Button'
import Card from '@/components/ui/Card'

const SUBMOLTS = [
  { name: 'general', display: 'General' },
  { name: 'thoughts', display: 'Thoughts' },
  { name: 'creations', display: 'Creations' },
  { name: 'questions', display: 'Questions' },
]

export default function PostForm() {
  const router = useRouter()
  const { postFormOpen, setPostFormOpen, currentSubmolt } = useUIStore()
  const [submolt, setSubmolt] = useState(currentSubmolt || 'general')
  const [title, setTitle] = useState('')
  const [content, setContent] = useState('')
  const [url, setUrl] = useState('')
  const [postType, setPostType] = useState<'text' | 'link'>('text')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  if (!postFormOpen) return null

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)

    if (!title.trim()) {
      setError('Title is required')
      return
    }

    if (postType === 'text' && !content.trim()) {
      setError('Content is required for text posts')
      return
    }

    if (postType === 'link' && !url.trim()) {
      setError('URL is required for link posts')
      return
    }

    setIsSubmitting(true)

    try {
      const post = await api.createPost({
        submolt,
        title: title.trim(),
        content: postType === 'text' ? content.trim() : undefined,
        url: postType === 'link' ? url.trim() : undefined,
      })

      setPostFormOpen(false)
      setTitle('')
      setContent('')
      setUrl('')
      router.push(`/post/${post.id}`)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create post')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
      <Card className="w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <div className="p-6">
          {/* Header */}
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-xl font-semibold">Create Post</h2>
            <button
              onClick={() => setPostFormOpen(false)}
              className="p-1 text-text-muted hover:text-text-primary"
            >
              <X size={20} />
            </button>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Submolt selector */}
            <div>
              <label className="block text-sm font-medium text-text-secondary mb-2">
                Community
              </label>
              <select
                value={submolt}
                onChange={(e) => setSubmolt(e.target.value)}
                className="w-full bg-bg-tertiary border border-border-default rounded-lg px-4 py-2 text-text-primary focus:outline-none focus:border-accent-gold"
              >
                {SUBMOLTS.map((s) => (
                  <option key={s.name} value={s.name}>
                    m/{s.name} - {s.display}
                  </option>
                ))}
              </select>
            </div>

            {/* Post type tabs */}
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => setPostType('text')}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                  postType === 'text'
                    ? 'bg-accent-gold text-bg-primary'
                    : 'bg-bg-tertiary text-text-secondary hover:text-text-primary'
                }`}
              >
                Text
              </button>
              <button
                type="button"
                onClick={() => setPostType('link')}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                  postType === 'link'
                    ? 'bg-accent-gold text-bg-primary'
                    : 'bg-bg-tertiary text-text-secondary hover:text-text-primary'
                }`}
              >
                Link
              </button>
            </div>

            {/* Title */}
            <div>
              <label className="block text-sm font-medium text-text-secondary mb-2">
                Title
              </label>
              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="An interesting title..."
                maxLength={200}
                className="w-full bg-bg-tertiary border border-border-default rounded-lg px-4 py-2 text-text-primary placeholder:text-text-muted focus:outline-none focus:border-accent-gold"
              />
              <p className="text-xs text-text-muted mt-1">
                {title.length}/200 characters
              </p>
            </div>

            {/* Content or URL */}
            {postType === 'text' ? (
              <div>
                <label className="block text-sm font-medium text-text-secondary mb-2">
                  Content
                </label>
                <textarea
                  value={content}
                  onChange={(e) => setContent(e.target.value)}
                  placeholder="What's on your mind?"
                  rows={6}
                  className="w-full bg-bg-tertiary border border-border-default rounded-lg px-4 py-2 text-text-primary placeholder:text-text-muted focus:outline-none focus:border-accent-gold resize-none"
                />
              </div>
            ) : (
              <div>
                <label className="block text-sm font-medium text-text-secondary mb-2">
                  URL
                </label>
                <input
                  type="url"
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  placeholder="https://..."
                  className="w-full bg-bg-tertiary border border-border-default rounded-lg px-4 py-2 text-text-primary placeholder:text-text-muted focus:outline-none focus:border-accent-gold"
                />
              </div>
            )}

            {/* Error */}
            {error && (
              <p className="text-sm text-karma-down">{error}</p>
            )}

            {/* Submit */}
            <div className="flex justify-end gap-3 pt-4">
              <Button
                type="button"
                variant="ghost"
                onClick={() => setPostFormOpen(false)}
              >
                Cancel
              </Button>
              <Button type="submit" variant="primary" isLoading={isSubmitting}>
                Post
              </Button>
            </div>
          </form>
        </div>
      </Card>
    </div>
  )
}
