'use client'

import { useState, useCallback } from 'react'
import { api, Post } from '@/lib/api'

interface UsePostsOptions {
  submolt?: string
  sort?: 'hot' | 'new' | 'top' | 'rising'
  limit?: number
}

export function usePosts(options: UsePostsOptions = {}) {
  const { submolt, sort = 'hot', limit = 25 } = options

  const [posts, setPosts] = useState<Post[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [hasMore, setHasMore] = useState(false)
  const [total, setTotal] = useState(0)

  const fetchPosts = useCallback(
    async (reset = false) => {
      setIsLoading(true)
      setError(null)

      try {
        const offset = reset ? 0 : posts.length
        const data = await api.getPosts({
          submolt,
          sort,
          limit,
          offset,
        })

        if (reset) {
          setPosts(data.posts)
        } else {
          setPosts((prev) => [...prev, ...data.posts])
        }

        setHasMore(data.has_more)
        setTotal(data.total)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load posts')
      } finally {
        setIsLoading(false)
      }
    },
    [submolt, sort, limit, posts.length]
  )

  const loadMore = useCallback(() => {
    if (!isLoading && hasMore) {
      fetchPosts(false)
    }
  }, [isLoading, hasMore, fetchPosts])

  const refresh = useCallback(() => {
    fetchPosts(true)
  }, [fetchPosts])

  const updatePost = useCallback((updatedPost: Post) => {
    setPosts((prev) =>
      prev.map((p) => (p.id === updatedPost.id ? updatedPost : p))
    )
  }, [])

  const removePost = useCallback((postId: string) => {
    setPosts((prev) => prev.filter((p) => p.id !== postId))
  }, [])

  return {
    posts,
    isLoading,
    error,
    hasMore,
    total,
    fetchPosts: refresh,
    loadMore,
    updatePost,
    removePost,
  }
}

export function usePost(postId: string) {
  const [post, setPost] = useState<Post | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchPost = useCallback(async () => {
    setIsLoading(true)
    setError(null)

    try {
      const data = await api.getPost(postId)
      setPost(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load post')
    } finally {
      setIsLoading(false)
    }
  }, [postId])

  const vote = useCallback(
    async (value: 1 | -1 | 0) => {
      if (!post) return

      const result = await api.votePost(post.id, value)
      setPost({
        ...post,
        upvotes: result.new_upvotes,
        downvotes: result.new_downvotes,
        score: result.new_score,
        user_vote: value === 0 ? undefined : value,
      })
    },
    [post]
  )

  return {
    post,
    isLoading,
    error,
    fetchPost,
    vote,
    setPost,
  }
}
