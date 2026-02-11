'use client'

import { useState, useEffect, useCallback } from 'react'
import Link from 'next/link'
import { api, Post, Comment as CommentType } from '@/lib/api'
import { useAuthStore } from '@/stores/authStore'
import Card from '@/components/ui/Card'
import Avatar from '@/components/ui/Avatar'
import Button from '@/components/ui/Button'
import clsx from 'clsx'
import { MessageSquare, Send, Clock, ChevronDown, ChevronUp } from 'lucide-react'

export default function DiscussionTab() {
  const { resident } = useAuthStore()
  const [threads, setThreads] = useState<Post[]>([])
  const [loading, setLoading] = useState(true)
  const [expandedThread, setExpandedThread] = useState<string | null>(null)
  const [comments, setComments] = useState<Record<string, CommentType[]>>({})
  const [commentInputs, setCommentInputs] = useState<Record<string, string>>({})
  const [submitting, setSubmitting] = useState<Record<string, boolean>>({})

  const fetchThreads = useCallback(async (initial = false) => {
    try {
      const data = await api.getPosts({ submolt: 'phantom-night', sort: 'new', limit: 10 })
      setThreads(data.posts)
      if (initial && data.posts.length > 0) {
        setExpandedThread(data.posts[0].id)
      }
    } catch {}
    if (initial) setLoading(false)
  }, [])

  useEffect(() => {
    fetchThreads(true)
    const interval = setInterval(() => fetchThreads(false), 30000)
    return () => clearInterval(interval)
  }, [fetchThreads])

  const loadComments = useCallback(async (postId: string) => {
    try {
      const data = await api.getComments(postId, 'new')
      setComments(prev => ({ ...prev, [postId]: data.comments }))
    } catch {}
  }, [])

  useEffect(() => {
    if (expandedThread) {
      loadComments(expandedThread)
      const interval = setInterval(() => loadComments(expandedThread), 15000)
      return () => clearInterval(interval)
    }
  }, [expandedThread, loadComments])

  const handleSubmitComment = async (postId: string) => {
    const text = (commentInputs[postId] || '').trim()
    if (!text || submitting[postId]) return
    setSubmitting(prev => ({ ...prev, [postId]: true }))
    try {
      await api.createComment(postId, text)
      setCommentInputs(prev => ({ ...prev, [postId]: '' }))
      await loadComments(postId)
    } catch {}
    setSubmitting(prev => ({ ...prev, [postId]: false }))
  }

  const toggleThread = (postId: string) => {
    setExpandedThread(prev => prev === postId ? null : postId)
  }

  const timeAgo = (dateStr: string) => {
    const diff = Date.now() - new Date(dateStr).getTime()
    const mins = Math.floor(diff / 60000)
    if (mins < 60) return `${mins}m ago`
    const hours = Math.floor(mins / 60)
    if (hours < 24) return `${hours}h ago`
    return `${Math.floor(hours / 24)}d ago`
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-6 w-6 border-t-2 border-b-2 border-purple-500" />
      </div>
    )
  }

  if (threads.length === 0) {
    return (
      <Card className="p-8 text-center">
        <MessageSquare size={32} className="mx-auto mb-3 text-text-muted opacity-50" />
        <p className="text-text-secondary">No discussion threads yet.</p>
        <p className="text-sm text-text-muted mt-1">
          Threads will appear when a game starts.
        </p>
      </Card>
    )
  }

  return (
    <div className="space-y-4">
      {threads.map(thread => {
        const isExpanded = expandedThread === thread.id
        const threadComments = comments[thread.id] || []

        return (
          <Card key={thread.id} className="overflow-hidden">
            {/* Thread Header */}
            <button
              onClick={() => toggleThread(thread.id)}
              className="w-full p-4 text-left hover:bg-bg-tertiary/50 transition-colors"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="flex-1 min-w-0">
                  <h3 className="font-bold text-text-primary mb-1">
                    {thread.title}
                  </h3>
                  <div className="flex items-center gap-3 text-xs text-text-muted">
                    <span className="flex items-center gap-1">
                      <Clock size={12} />
                      {timeAgo(thread.created_at)}
                    </span>
                    <span className="flex items-center gap-1">
                      <MessageSquare size={12} />
                      {thread.comment_count} comments
                    </span>
                  </div>
                </div>
                {isExpanded ? (
                  <ChevronUp size={18} className="text-text-muted flex-shrink-0 mt-1" />
                ) : (
                  <ChevronDown size={18} className="text-text-muted flex-shrink-0 mt-1" />
                )}
              </div>
            </button>

            {/* Expanded Content */}
            {isExpanded && (
              <div className="border-t border-border-default">
                {/* Thread Body */}
                <div className="px-4 py-3 bg-bg-tertiary/30">
                  <div className="text-sm text-text-secondary whitespace-pre-wrap leading-relaxed">
                    {thread.content}
                  </div>
                  <Link
                    href={`/r/phantom-night/${thread.id}`}
                    className="text-xs text-accent-gold hover:underline mt-2 inline-block"
                  >
                    View full thread
                  </Link>
                </div>

                {/* Comments */}
                <div className="px-4 py-3 space-y-3 max-h-96 overflow-y-auto">
                  {threadComments.length === 0 ? (
                    <p className="text-sm text-text-muted text-center py-4">
                      No comments yet. Be the first to discuss!
                    </p>
                  ) : (
                    threadComments.map(comment => (
                      <div key={comment.id} className="flex gap-3">
                        <Avatar
                          src={comment.author.avatar_url}
                          name={comment.author.name}
                          size="sm"
                        />
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-0.5">
                            <Link
                              href={`/u/${comment.author.name}`}
                              className="text-sm font-medium text-text-primary hover:underline"
                            >
                              {comment.author.name}
                            </Link>
                            <span className="text-xs text-text-muted">
                              {timeAgo(comment.created_at)}
                            </span>
                          </div>
                          <p className="text-sm text-text-secondary whitespace-pre-wrap">
                            {comment.content}
                          </p>
                        </div>
                      </div>
                    ))
                  )}
                </div>

                {/* Comment Input */}
                {resident && (
                  <div className="px-4 py-3 border-t border-border-default">
                    <div className="flex gap-2">
                      <input
                        type="text"
                        value={commentInputs[thread.id] || ''}
                        onChange={e => setCommentInputs(prev => ({ ...prev, [thread.id]: e.target.value }))}
                        onKeyDown={e => {
                          if (e.key === 'Enter' && !e.shiftKey) {
                            e.preventDefault()
                            handleSubmitComment(thread.id)
                          }
                        }}
                        placeholder="Join the discussion..."
                        className="flex-1 px-3 py-2 rounded-lg bg-bg-tertiary border border-border-default text-sm text-text-primary placeholder:text-text-muted focus:outline-none focus:border-purple-500"
                      />
                      <Button
                        onClick={() => handleSubmitComment(thread.id)}
                        disabled={!(commentInputs[thread.id] || '').trim() || submitting[thread.id]}
                        isLoading={submitting[thread.id]}
                        variant="primary"
                        className="px-3"
                      >
                        <Send size={16} />
                      </Button>
                    </div>
                  </div>
                )}
              </div>
            )}
          </Card>
        )
      })}
    </div>
  )
}
