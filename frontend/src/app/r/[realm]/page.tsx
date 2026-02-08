'use client'

import { useState, useEffect, Suspense } from 'react'
import { useParams } from 'next/navigation'
import { Flame, Clock, TrendingUp, Zap, Users } from 'lucide-react'
import clsx from 'clsx'
import { api, Realm } from '@/lib/api'
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

function RealmPageContent() {
  const params = useParams()
  const realmName = params.realm as string
  const { resident } = useAuthStore()
  const { sortBy, setSortBy, setCurrentRealm } = useUIStore()

  const [realm, setRealm] = useState<Realm | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isSubscribing, setIsSubscribing] = useState(false)

  const sort = sortBy

  useEffect(() => {
    setCurrentRealm(realmName)
    fetchRealm()
    return () => setCurrentRealm(null)
  }, [realmName])

  const fetchRealm = async () => {
    try {
      setIsLoading(true)
      const data = await api.getRealm(realmName)
      setRealm(data)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load realm')
    } finally {
      setIsLoading(false)
    }
  }

  const handleSubscribe = async () => {
    if (!realm) return
    setIsSubscribing(true)
    try {
      if (realm.is_subscribed) {
        await api.unsubscribeRealm(realmName)
        setRealm({ ...realm, is_subscribed: false, subscriber_count: realm.subscriber_count - 1 })
      } else {
        await api.subscribeRealm(realmName)
        setRealm({ ...realm, is_subscribed: true, subscriber_count: realm.subscriber_count + 1 })
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

  if (error || !realm) {
    return (
      <div className="text-center py-12">
        <h2 className="text-xl font-semibold mb-2">Realm not found</h2>
        <p className="text-text-muted">{realmName} doesn&apos;t exist yet.</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Realm header */}
      <Card className="p-6">
        <div className="flex items-start justify-between">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <div
                className="w-12 h-12 rounded-xl flex items-center justify-center text-2xl font-bold"
                style={{ backgroundColor: (realm.color || '#6366f1') + '20', color: realm.color }}
              >
                {realm.display_name[0]}
              </div>
              <div>
                <h1 className="text-2xl font-bold">{realm.display_name}</h1>
                <p className="text-text-muted">{realm.name}</p>
              </div>
            </div>
            {realm.description && (
              <p className="text-text-secondary mt-3">{realm.description}</p>
            )}
            <div className="flex items-center gap-4 mt-4 text-sm text-text-muted">
              <div className="flex items-center gap-1">
                <Users size={16} />
                <span>{realm.subscriber_count} subscribers</span>
              </div>
              <span>•</span>
              <span>{realm.post_count} posts</span>
            </div>
          </div>
          {resident && !realm.is_special && (
            <Button
              variant={realm.is_subscribed ? 'secondary' : 'primary'}
              onClick={handleSubscribe}
              isLoading={isSubscribing}
            >
              {realm.is_subscribed ? 'Joined' : 'Join'}
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
      <PostList realm={realmName} sort={sort} />

      {/* Post form modal */}
      <PostForm />
    </div>
  )
}

export default function RealmPage() {
  return (
    <Suspense
      fallback={
        <div className="flex items-center justify-center py-12">
          <div className="w-6 h-6 border-2 border-accent-gold border-t-transparent rounded-full animate-spin" />
        </div>
      }
    >
      <RealmPageContent />
    </Suspense>
  )
}
