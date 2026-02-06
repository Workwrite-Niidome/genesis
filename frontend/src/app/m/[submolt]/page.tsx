'use client'

import { useState, useEffect, Suspense } from 'react'
import { useParams, useSearchParams } from 'next/navigation'
import { Flame, Clock, TrendingUp, Zap, Users } from 'lucide-react'
import clsx from 'clsx'
import { api, Submolt } from '@/lib/api'
import { useAuthStore } from '@/stores/authStore'
import { useUIStore } from '@/stores/uiStore'
import PostList from '@/components/post/PostList'
import PostForm from '@/components/post/PostForm'
import Button from '@/components/ui/Button'
import Card from '@/components/ui/Card'

const SORT_OPTIONS = [
  { value: 'hot', label: 'Hot', icon: Flame },
  { value: 'new', label: 'New', icon: Clock },
  { value: 'top', label: 'Top', icon: TrendingUp },
  { value: 'rising', label: 'Rising', icon: Zap },
] as const

function SubmoltPageContent() {
  const params = useParams()
  const searchParams = useSearchParams()
  const submoltName = params.submolt as string
  const { resident } = useAuthStore()
  const { sortBy, setSortBy, setCurrentSubmolt } = useUIStore()

  const [submolt, setSubmolt] = useState<Submolt | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isSubscribing, setIsSubscribing] = useState(false)

  const sort = (searchParams.get('sort') as typeof sortBy) || sortBy

  useEffect(() => {
    setCurrentSubmolt(submoltName)
    fetchSubmolt()
    return () => setCurrentSubmolt(null)
  }, [submoltName])

  const fetchSubmolt = async () => {
    try {
      setIsLoading(true)
      const data = await api.getSubmolt(submoltName)
      setSubmolt(data)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load submolt')
    } finally {
      setIsLoading(false)
    }
  }

  const handleSubscribe = async () => {
    if (!submolt) return
    setIsSubscribing(true)
    try {
      if (submolt.is_subscribed) {
        await api.unsubscribeSubmolt(submoltName)
        setSubmolt({ ...submolt, is_subscribed: false, subscriber_count: submolt.subscriber_count - 1 })
      } else {
        await api.subscribeSubmolt(submoltName)
        setSubmolt({ ...submolt, is_subscribed: true, subscriber_count: submolt.subscriber_count + 1 })
      }
    } catch (err) {
      console.error(err)
    } finally {
      setIsSubscribing(false)
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="w-6 h-6 border-2 border-accent-gold border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  if (error || !submolt) {
    return (
      <div className="text-center py-12">
        <h2 className="text-xl font-semibold mb-2">Submolt not found</h2>
        <p className="text-text-muted">m/{submoltName} doesn't exist yet.</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Submolt header */}
      <Card className="p-6">
        <div className="flex items-start justify-between">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <div
                className="w-12 h-12 rounded-xl flex items-center justify-center text-2xl font-bold"
                style={{ backgroundColor: (submolt.color || '#6366f1') + '20', color: submolt.color }}
              >
                {submolt.display_name[0]}
              </div>
              <div>
                <h1 className="text-2xl font-bold">m/{submolt.name}</h1>
                <p className="text-text-muted">{submolt.display_name}</p>
              </div>
            </div>
            {submolt.description && (
              <p className="text-text-secondary mt-3">{submolt.description}</p>
            )}
            <div className="flex items-center gap-4 mt-4 text-sm text-text-muted">
              <div className="flex items-center gap-1">
                <Users size={16} />
                <span>{submolt.subscriber_count} subscribers</span>
              </div>
              <span>•</span>
              <span>{submolt.post_count} posts</span>
            </div>
          </div>
          {resident && !submolt.is_special && (
            <Button
              variant={submolt.is_subscribed ? 'secondary' : 'primary'}
              onClick={handleSubscribe}
              isLoading={isSubscribing}
            >
              {submolt.is_subscribed ? 'Joined' : 'Join'}
            </Button>
          )}
        </div>
      </Card>

      {/* Sort tabs */}
      <div className="flex gap-2 border-b border-border-default pb-2">
        {SORT_OPTIONS.map((option) => {
          const Icon = option.icon
          const isActive = sort === option.value
          return (
            <button
              key={option.value}
              onClick={() => setSortBy(option.value)}
              className={clsx(
                'flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors',
                isActive
                  ? 'bg-bg-tertiary text-text-primary'
                  : 'text-text-muted hover:text-text-primary hover:bg-bg-tertiary'
              )}
            >
              <Icon size={16} />
              {option.label}
            </button>
          )
        })}
      </div>

      {/* Posts */}
      <PostList submolt={submoltName} sort={sort} />

      {/* Post form modal */}
      <PostForm />
    </div>
  )
}

export default function SubmoltPage() {
  return (
    <Suspense
      fallback={
        <div className="flex items-center justify-center py-12">
          <div className="w-6 h-6 border-2 border-accent-gold border-t-transparent rounded-full animate-spin" />
        </div>
      }
    >
      <SubmoltPageContent />
    </Suspense>
  )
}
