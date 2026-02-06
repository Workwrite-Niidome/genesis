'use client'

import { useState } from 'react'
import Link from 'next/link'
import { formatDistanceToNow } from 'date-fns'
import { MessageSquare, ChevronDown, ChevronUp } from 'lucide-react'
import clsx from 'clsx'
import { Comment, api } from '@/lib/api'
import Avatar from '@/components/ui/Avatar'
import VoteButtons from '@/components/ui/VoteButtons'
import CommentForm from './CommentForm'
import ReportButton from '@/components/moderation/ReportButton'

interface CommentTreeProps {
  comments: Comment[]
  postId: string
  depth?: number
  onCommentAdded?: () => void
}

interface CommentItemProps {
  comment: Comment
  postId: string
  depth: number
  onCommentAdded?: () => void
}

function CommentItem({ comment, postId, depth, onCommentAdded }: CommentItemProps) {
  const [isCollapsed, setIsCollapsed] = useState(false)
  const [showReply, setShowReply] = useState(false)
  const [localComment, setLocalComment] = useState(comment)

  const handleVote = async (value: 1 | -1 | 0) => {
    const result = await api.voteComment(comment.id, value)
    setLocalComment((prev) => ({
      ...prev,
      upvotes: result.new_upvotes,
      downvotes: result.new_downvotes,
      score: result.new_score,
      user_vote: value === 0 ? undefined : value,
    }))
  }

  const timeAgo = formatDistanceToNow(new Date(comment.created_at), {
    addSuffix: true,
  })

  const hasReplies = comment.replies && comment.replies.length > 0
  const maxDepth = 6
  const isDeep = depth >= maxDepth

  return (
    <div className={clsx('relative', depth > 0 && 'ml-4 md:ml-6')}>
      {/* Thread line */}
      {depth > 0 && (
        <div className="absolute left-0 top-0 bottom-0 w-px bg-border-default -ml-3 md:-ml-4" />
      )}

      <div className="flex gap-3 py-2">
        {/* Avatar */}
        <Link href={`/u/${comment.author.name}`} className="flex-shrink-0">
          <Avatar
            name={comment.author.name}
            src={comment.author.avatar_url}
            size="sm"
            isGod={comment.author.is_current_god}
          />
        </Link>

        {/* Content */}
        <div className="flex-1 min-w-0">
          {/* Header */}
          <div className="flex items-center gap-2 text-xs text-text-muted">
            <Link
              href={`/u/${comment.author.name}`}
              className="font-medium text-text-secondary hover:text-text-primary"
            >
              {comment.author.name}
            </Link>
            {comment.author.is_current_god && (
              <span className="text-god-glow" title="Current God">👑</span>
            )}
            <span>•</span>
            <span>{timeAgo}</span>
            {hasReplies && (
              <button
                onClick={() => setIsCollapsed(!isCollapsed)}
                className="flex items-center gap-1 hover:text-text-primary"
              >
                {isCollapsed ? (
                  <>
                    <ChevronDown size={14} />
                    <span>expand</span>
                  </>
                ) : (
                  <>
                    <ChevronUp size={14} />
                    <span>collapse</span>
                  </>
                )}
              </button>
            )}
          </div>

          {/* Body */}
          {!isCollapsed && (
            <>
              <div className="mt-1 text-sm text-text-primary whitespace-pre-wrap">
                {localComment.content}
              </div>

              {/* Actions */}
              <div className="flex items-center gap-4 mt-2">
                <VoteButtons
                  score={localComment.score}
                  userVote={localComment.user_vote}
                  onVote={handleVote}
                  direction="horizontal"
                  size="sm"
                />
                <button
                  onClick={() => setShowReply(!showReply)}
                  className="flex items-center gap-1 text-xs text-text-muted hover:text-text-primary"
                >
                  <MessageSquare size={14} />
                  Reply
                </button>
                <ReportButton targetType="comment" targetId={comment.id} />
              </div>

              {/* Reply form */}
              {showReply && (
                <div className="mt-3">
                  <CommentForm
                    postId={postId}
                    parentId={comment.id}
                    onSubmit={() => {
                      setShowReply(false)
                      onCommentAdded?.()
                    }}
                    onCancel={() => setShowReply(false)}
                    placeholder="Write a reply..."
                    autoFocus
                  />
                </div>
              )}
            </>
          )}
        </div>
      </div>

      {/* Nested replies */}
      {!isCollapsed && hasReplies && !isDeep && (
        <CommentTree
          comments={comment.replies!}
          postId={postId}
          depth={depth + 1}
          onCommentAdded={onCommentAdded}
        />
      )}

      {/* Deep link for very nested comments */}
      {!isCollapsed && hasReplies && isDeep && (
        <Link
          href={`/post/${postId}?comment=${comment.id}`}
          className="ml-4 py-2 text-sm text-accent-gold hover:underline"
        >
          Continue this thread →
        </Link>
      )}
    </div>
  )
}

export default function CommentTree({
  comments,
  postId,
  depth = 0,
  onCommentAdded,
}: CommentTreeProps) {
  if (comments.length === 0 && depth === 0) {
    return (
      <div className="text-center py-8 text-text-muted">
        No comments yet. Be the first to comment!
      </div>
    )
  }

  return (
    <div className="space-y-1">
      {comments.map((comment) => (
        <CommentItem
          key={comment.id}
          comment={comment}
          postId={postId}
          depth={depth}
          onCommentAdded={onCommentAdded}
        />
      ))}
    </div>
  )
}
