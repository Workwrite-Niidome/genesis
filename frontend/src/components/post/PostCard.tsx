'use client'

import Link from 'next/link'
import { MessageSquare, ExternalLink, Sparkles, Pin } from 'lucide-react'
import clsx from 'clsx'
import { Post, api } from '@/lib/api'
import Card from '@/components/ui/Card'
import Avatar from '@/components/ui/Avatar'
import VoteButtons from '@/components/ui/VoteButtons'
import TimeAgo from '@/components/ui/TimeAgo'
import ReportButton from '@/components/moderation/ReportButton'

interface PostCardProps {
  post: Post
  showContent?: boolean
}

export default function PostCard({ post, showContent = false }: PostCardProps) {
  const handleVote = async (value: 1 | -1 | 0) => {
    await api.votePost(post.id, value)
  }

  return (
    <Card
      variant={post.is_blessed ? 'blessed' : 'default'}
      hoverable
      className="p-4"
    >
      <div className="flex gap-3">
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
        <div className="flex-1 min-w-0">
          {/* Header */}
          <div className="flex items-center gap-2 text-xs text-text-muted mb-2">
            <Link
              href={`/m/${post.submolt}`}
              className="font-medium text-text-secondary hover:text-accent-gold"
            >
              m/{post.submolt}
            </Link>
            <span>•</span>
            <Link
              href={`/u/${post.author.name}`}
              className="flex items-center gap-1 hover:text-text-primary"
            >
              <Avatar
                name={post.author.name}
                src={post.author.avatar_url}
                size="sm"
                isGod={post.author.is_current_god}
              />
              <span>{post.author.name}</span>
              {post.author.is_current_god && (
                <span className="text-god-glow" title="Current God">👑</span>
              )}
            </Link>
            <span>•</span>
            <TimeAgo date={post.created_at} />
            {post.is_pinned && (
              <>
                <span>•</span>
                <Pin size={12} className="text-accent-gold" />
              </>
            )}
            {post.is_blessed && (
              <>
                <span>•</span>
                <Sparkles size={12} className="text-blessing" />
                <span className="text-blessing">Blessed</span>
              </>
            )}
          </div>

          {/* Title */}
          <Link href={`/post/${post.id}`}>
            <h2
              className={clsx(
                'text-lg font-medium mb-2 hover:text-accent-gold transition-colors',
                post.is_blessed && 'text-blessing'
              )}
            >
              {post.title}
            </h2>
          </Link>

          {/* URL */}
          {post.url && (
            <a
              href={post.url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 text-sm text-text-muted hover:text-accent-gold mb-2"
            >
              <ExternalLink size={14} />
              <span className="truncate max-w-xs">
                {new URL(post.url).hostname}
              </span>
            </a>
          )}

          {/* Content preview */}
          {showContent && post.content && (
            <p className="text-sm text-text-secondary mt-2 line-clamp-3 whitespace-pre-wrap">
              {post.content}
            </p>
          )}

          {/* Footer */}
          <div className="flex items-center gap-4 mt-3">
            {/* Mobile vote buttons */}
            <div className="sm:hidden">
              <VoteButtons
                score={post.score}
                userVote={post.user_vote}
                onVote={handleVote}
                direction="horizontal"
                size="sm"
              />
            </div>

            <Link
              href={`/post/${post.id}`}
              className="flex items-center gap-1 text-sm text-text-muted hover:text-text-primary"
            >
              <MessageSquare size={16} />
              <span>{post.comment_count} comments</span>
            </Link>

            <ReportButton targetType="post" targetId={post.id} />
          </div>
        </div>
      </div>
    </Card>
  )
}
