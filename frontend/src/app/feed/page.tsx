'use client'

import { useState, useEffect } from 'react'
import { api, Post } from '@/lib/api'
import { useAuthStore } from '@/stores/authStore'
import PostCard from '@/components/post/PostCard'
import Card from '@/components/ui/Card'
import Button from '@/components/ui/Button'
import { Loader2, Users, Rss } from 'lucide-react'
import Link from 'next/link'

export default function FeedPage() {
  const { resident } = useAuthStore()
  const [posts, setPosts] = useState<Post[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [hasMore, setHasMore] = useState(false)
  const [offset, setOffset] = useState(0)
  const limit = 25

  const fetchFeed = async (reset = false) => {
    try {
      setIsLoading(true)
      const newOffset = reset ? 0 : offset
      const data = await api.getFeed(limit, newOffset)

      if (reset) {
        setPosts(data.posts)
      } else {
        setPosts((prev) => [...prev, ...data.posts])
      }

      setHasMore(data.has_more)
      setOffset(newOffset + data.posts.length)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load feed')
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    if (resident) {
      setOffset(0)
      fetchFeed(true)
    }
  }, [resident])

  // Not logged in
  if (!resident) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-2">
          <Rss className="w-6 h-6 text-accent-gold" />
          <h1 className="text-2xl font-bold">Feed</h1>
        </div>
        <Card className="p-8 text-center">
          <Users className="w-12 h-12 text-text-muted mx-auto mb-4" />
          <h2 className="text-lg font-semibold mb-2">Login Required</h2>
          <p className="text-text-muted mb-4">
            Login to see posts from residents you follow.
          </p>
          <Link href="/auth">
            <Button variant="primary">Login</Button>
          </Link>
        </Card>
      </div>
    )
  }

  // Error state
  if (error) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-2">
          <Rss className="w-6 h-6 text-accent-gold" />
          <h1 className="text-2xl font-bold">Feed</h1>
        </div>
        <Card className="p-8 text-center">
          <p className="text-text-muted mb-4">{error}</p>
          <Button variant="secondary" onClick={() => fetchFeed(true)}>
            Try Again
          </Button>
        </Card>
      </div>
    )
  }

  // Loading state
  if (isLoading && posts.length === 0) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-2">
          <Rss className="w-6 h-6 text-accent-gold" />
          <h1 className="text-2xl font-bold">Feed</h1>
        </div>
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-6 h-6 animate-spin text-accent-gold" />
        </div>
      </div>
    )
  }

  // Empty state
  if (posts.length === 0) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-2">
          <Rss className="w-6 h-6 text-accent-gold" />
          <h1 className="text-2xl font-bold">Feed</h1>
        </div>
        <Card className="p-8 text-center">
          <Users className="w-12 h-12 text-text-muted mx-auto mb-4" />
          <h2 className="text-lg font-semibold mb-2">You're not following anyone</h2>
          <p className="text-text-muted mb-4">
            Follow other residents to see their posts here.
          </p>
          <Link href="/">
            <Button variant="primary">Explore Posts</Button>
          </Link>
        </Card>
      </div>
    )
  }

  // Posts list
  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2">
        <Rss className="w-6 h-6 text-accent-gold" />
        <h1 className="text-2xl font-bold">Feed</h1>
      </div>

      <div className="space-y-4">
        {posts.map((post) => (
          <PostCard key={post.id} post={post} />
        ))}

        {hasMore && (
          <div className="flex justify-center py-4">
            <Button
              variant="secondary"
              onClick={() => fetchFeed()}
              isLoading={isLoading}
            >
              Load More
            </Button>
          </div>
        )}
      </div>
    </div>
  )
}
