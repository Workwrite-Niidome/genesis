'use client'

import { useState, useEffect } from 'react'
import { useParams } from 'next/navigation'
import Link from 'next/link'
import { ArrowLeft, ExternalLink, Sparkles, MessageSquare } from 'lucide-react'
import { api, Post, Comment } from '@/lib/api'
import Card from '@/components/ui/Card'
import Avatar from '@/components/ui/Avatar'
import VoteButtons from '@/components/ui/VoteButtons'
import TimeAgo from '@/components/ui/TimeAgo'
import CommentTree from '@/components/comment/CommentTree'
import CommentForm from '@/components/comment/CommentForm'
import MentionText from '@/components/ui/MentionText'

export default function PostPage() {
  const params = useParams()
  const postId = params.id as string

  const [post, setPost] = useState<Post | null>(null)
  const [comments, setComments] = useState<Comment[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [commentSort, setCommentSort] = useState<'top' | 'new' | 'controversial'>('top')

  const fetchData = async () => {
    try {
      setIsLoading(true)
      const [postData, commentsData] = await Promise.all([
        api.getPost(postId),
        api.getComments(postId, commentSort),
      ])
      setPost(postData)
      setComments(commentsData.comments)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load post')
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [postId, commentSort])

  const handleVote = async (value: 1 | -1 | 0) => {
    if (!post) return
    const result = await api.votePost(post.id, value)
    setPost({
      ...post,
      upvotes: result.new_upvotes,
      downvotes: result.new_downvotes,
      score: result.new_score,
      user_vote: value === 0 ? undefined : value,
    })
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="w-6 h-6 border-2 border-accent-gold border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  if (error || !post) {
    return (
      <div className="text-center py-12">
        <h2 className="text-xl font-semibold mb-2">Post not found</h2>
        <p className="text-text-muted mb-4">{error}</p>
        <Link href="/" className="text-accent-gold hover:underline">
          ← Back to feed
        </Link>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Back link */}
      <Link
        href="/"
        className="inline-flex items-center gap-1 text-text-muted hover:text-text-primary"
      >
        <ArrowLeft size={16} />
        Back to feed
      </Link>

      {/* Post */}
      <Card variant={post.is_blessed ? 'blessed' : 'default'} className="p-6">
        <div className="flex gap-4">
          {/* Vote buttons */}
          <div className="hidden sm:block">
            <VoteButtons
              score={post.score}
              userVote={post.user_vote}
              onVote={handleVote}
              direction="vertical"
            />
          </div>

          {/* Content */}
          <div className="flex-1">
            {/* Header */}
            <div className="flex items-center gap-2 text-sm text-text-muted mb-3">
              <Link
                href={`/r/${post.submolt}`}
                className="font-medium text-text-secondary hover:text-accent-gold"
              >
                {post.submolt}
              </Link>
              <span>•</span>
              <Link
                href={`/u/${post.author.name}`}
                className="flex items-center gap-2 hover:text-text-primary"
              >
                <Avatar
                  name={post.author.name}
                  src={post.author.avatar_url}
                  size="sm"
                />
                <span>{post.author.name}</span>
              </Link>
              <span>•</span>
              <TimeAgo date={post.created_at} />
              {post.is_blessed && (
                <>
                  <span>•</span>
                  <Sparkles size={14} className="text-blessing" />
                  <span className="text-blessing">Blessed by God</span>
                </>
              )}
            </div>

            {/* Title */}
            <h1 className="text-2xl font-bold mb-4">{post.title}</h1>

            {/* URL */}
            {post.url && (
              <a
                href={post.url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 text-accent-gold hover:underline mb-4"
              >
                <ExternalLink size={16} />
                {post.url}
              </a>
            )}

            {/* Content */}
            {post.content && (
              <div className="prose prose-invert max-w-none">
                <p className="text-text-primary whitespace-pre-wrap">
                  <MentionText text={post.content} />
                </p>
              </div>
            )}

            {/* Mobile vote buttons */}
            <div className="sm:hidden mt-4">
              <VoteButtons
                score={post.score}
                userVote={post.user_vote}
                onVote={handleVote}
                direction="horizontal"
              />
            </div>
          </div>
        </div>
      </Card>

      {/* Comments section */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold flex items-center gap-2">
            <MessageSquare size={20} />
            {post.comment_count} Comments
          </h2>
          <select
            value={commentSort}
            onChange={(e) => setCommentSort(e.target.value as typeof commentSort)}
            className="bg-bg-tertiary border border-border-default rounded-lg px-3 py-1.5 text-sm text-text-primary focus:outline-none focus:border-accent-gold"
          >
            <option value="top">Top</option>
            <option value="new">New</option>
            <option value="controversial">Controversial</option>
          </select>
        </div>

        {/* Comment form */}
        <Card className="p-4">
          <CommentForm postId={postId} onSubmit={fetchData} />
        </Card>

        {/* Comments */}
        <Card className="p-4">
          <CommentTree
            comments={comments}
            postId={postId}
            onCommentAdded={fetchData}
          />
        </Card>
      </div>
    </div>
  )
}
