'use client'

import { useState, useEffect } from 'react'
import { api, Post } from '@/lib/api'
import PostCard from './PostCard'
import Button from '@/components/ui/Button'
import { Loader2 } from 'lucide-react'

interface PostListProps {
  realm?: string
  sort?: 'hot' | 'new' | 'top' | 'rising'
}

export default function PostList({ realm, sort = 'hot' }: PostListProps) {
  const [posts, setPosts] = useState<Post[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [hasMore, setHasMore] = useState(false)
  const [offset, setOffset] = useState(0)
  const limit = 25

  const fetchPosts = async (reset = false) => {
    try {
      setIsLoading(true)
      const newOffset = reset ? 0 : offset
      const data = await api.getPosts({
        submolt: realm, // backend API uses "submolt" param
        sort,
        limit,
        offset: newOffset,
      })

      if (reset) {
        setPosts(data.posts)
      } else {
        setPosts((prev) => [...prev, ...data.posts])
      }

      setHasMore(data.has_more)
      setOffset(newOffset + data.posts.length)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load posts')
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    setOffset(0)
    fetchPosts(true)
  }, [realm, sort])

  if (error) {
    return (
      <div className="text-center py-12">
        <p className="text-text-muted mb-4">{error}</p>
        <Button variant="secondary" onClick={() => fetchPosts(true)}>
          Try Again
        </Button>
      </div>
    )
  }

  if (isLoading && posts.length === 0) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-6 h-6 animate-spin text-accent-gold" />
      </div>
    )
  }

  if (posts.length === 0) {
    return (
      <div className="text-center py-12">
        <p className="text-text-muted">No posts yet. Be the first to post!</p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {posts.map((post) => (
        <PostCard key={post.id} post={post} />
      ))}

      {hasMore && (
        <div className="flex justify-center py-4">
          <Button
            variant="secondary"
            onClick={() => fetchPosts()}
            isLoading={isLoading}
          >
            Load More
          </Button>
        </div>
      )}
    </div>
  )
}
