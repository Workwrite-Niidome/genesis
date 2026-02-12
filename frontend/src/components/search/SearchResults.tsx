'use client'

import Link from 'next/link'
import { FileText, User, MessageSquare, Sparkles } from 'lucide-react'
import clsx from 'clsx'
import { SearchResult, SearchResultPost, SearchResultResident } from '@/lib/api'
import Card from '@/components/ui/Card'
import Avatar from '@/components/ui/Avatar'
import TimeAgo from '@/components/ui/TimeAgo'

interface SearchResultsProps {
  results: SearchResult[]
  searchPosts?: SearchResultPost[]
  searchResidents?: SearchResultResident[]
  type: 'posts' | 'residents' | 'all'
  isLoading: boolean
  query?: string
}

function LoadingSpinner() {
  return (
    <div className="flex items-center justify-center py-12">
      <div className="w-6 h-6 border-2 border-accent-gold border-t-transparent rounded-full animate-spin" />
    </div>
  )
}

function EmptyState({ query }: { query?: string }) {
  return (
    <div className="text-center py-12">
      <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-bg-tertiary flex items-center justify-center">
        <FileText size={32} className="text-text-muted" />
      </div>
      <h3 className="text-lg font-medium mb-2">No results found</h3>
      <p className="text-text-muted text-sm">
        {query
          ? `No results found for "${query}"`
          : 'Enter a search term'}
      </p>
    </div>
  )
}

interface ResidentCardProps {
  result: SearchResult
}

function ResidentCard({ result }: ResidentCardProps) {
  return (
    <Link href={`/u/${result.name}`}>
      <Card hoverable className="p-4">
        <div className="flex items-center gap-4">
          <Avatar name={result.name || 'Unknown'} size="lg" />
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <h3 className="font-medium text-text-primary hover:text-accent-gold transition-colors">
                {result.name}
              </h3>
              {result.relevance_score > 0.9 && (
                <span className="px-2 py-0.5 bg-accent-gold/10 text-accent-gold text-xs rounded-full">
                  Best match
                </span>
              )}
            </div>
            {result.content && (
              <p className="text-sm text-text-secondary mt-1 line-clamp-2">
                {result.content}
              </p>
            )}
          </div>
          <User size={20} className="text-text-muted flex-shrink-0" />
        </div>
      </Card>
    </Link>
  )
}

interface CommentResultCardProps {
  result: SearchResult
}

function CommentResultCard({ result }: CommentResultCardProps) {
  return (
    <Link href={`/post/${result.post_id || result.id}`}>
      <Card hoverable className="p-4">
        <div className="flex gap-3">
          <div className="flex-shrink-0">
            <div className="w-10 h-10 rounded-full bg-bg-tertiary flex items-center justify-center">
              <MessageSquare size={18} className="text-text-muted" />
            </div>
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 text-xs text-text-muted mb-1">
              {result.author && (
                <>
                  <span className="font-medium text-text-secondary">
                    {result.author.name}
                  </span>
                  <span>commented</span>
                </>
              )}
              {result.created_at && (
                <>
                  <span>•</span>
                  <TimeAgo date={result.created_at} />
                </>
              )}
            </div>
            <p className="text-sm text-text-primary line-clamp-2">
              {result.content}
            </p>
            {result.relevance_score > 0.8 && (
              <div className="flex items-center gap-1 mt-2 text-xs text-accent-gold">
                <Sparkles size={12} />
                <span>High relevance</span>
              </div>
            )}
          </div>
        </div>
      </Card>
    </Link>
  )
}

function PostSearchCard({ post }: { post: SearchResultPost }) {
  return (
    <Link href={`/post/${post.id}`}>
      <Card hoverable className="p-4">
        <div className="flex gap-3">
          <div className="flex-shrink-0">
            <div className="w-10 h-10 rounded-full bg-bg-tertiary flex items-center justify-center">
              <FileText size={18} className="text-text-muted" />
            </div>
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 text-xs text-text-muted mb-1">
              <Link
                href={`/r/${post.submolt}`}
                className="font-medium text-text-secondary hover:text-accent-gold"
                onClick={(e) => e.stopPropagation()}
              >
                {post.submolt}
              </Link>
              <span>by</span>
              <span className="text-text-secondary">{post.author_name}</span>
              <span>•</span>
              <TimeAgo date={post.created_at} />
            </div>
            <h3 className="font-medium text-text-primary mb-1 hover:text-accent-gold transition-colors">
              {post.title}
            </h3>
            {post.content && (
              <p className="text-sm text-text-secondary line-clamp-2">
                {post.content}
              </p>
            )}
            <div className="flex items-center gap-3 mt-2 text-xs text-text-muted">
              <span>{post.score} points</span>
              <span>{post.comment_count} comments</span>
            </div>
          </div>
        </div>
      </Card>
    </Link>
  )
}

function ResidentSearchCard({ resident }: { resident: SearchResultResident }) {
  return (
    <Link href={`/u/${resident.name}`}>
      <Card hoverable className="p-4">
        <div className="flex items-center gap-4">
          <Avatar name={resident.name} src={resident.avatar_url} size="lg" />
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <h3 className="font-medium text-text-primary hover:text-accent-gold transition-colors">
                {resident.name}
              </h3>
            </div>
            {resident.description && (
              <p className="text-sm text-text-secondary mt-1 line-clamp-2">
                {resident.description}
              </p>
            )}
          </div>
          <User size={20} className="text-text-muted flex-shrink-0" />
        </div>
      </Card>
    </Link>
  )
}

interface GenericResultCardProps {
  result: SearchResult
}

function GenericResultCard({ result }: GenericResultCardProps) {
  const getResultLink = () => {
    switch (result.type) {
      case 'post':
        return `/post/${result.id}`
      case 'resident':
        return `/u/${result.name}`
      case 'comment':
        return `/post/${result.post_id || result.id}`
      default:
        return '#'
    }
  }

  const getResultIcon = () => {
    switch (result.type) {
      case 'post':
        return <FileText size={18} />
      case 'resident':
        return <User size={18} />
      case 'comment':
        return <MessageSquare size={18} />
      default:
        return <FileText size={18} />
    }
  }

  const getTypeLabel = () => {
    switch (result.type) {
      case 'post':
        return 'Post'
      case 'resident':
        return 'Resident'
      case 'comment':
        return 'Comment'
      default:
        return result.type
    }
  }

  return (
    <Link href={getResultLink()}>
      <Card hoverable className="p-4">
        <div className="flex gap-3">
          <div className="flex-shrink-0">
            <div className="w-10 h-10 rounded-full bg-bg-tertiary flex items-center justify-center text-text-muted">
              {getResultIcon()}
            </div>
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <span className="px-2 py-0.5 bg-bg-tertiary text-text-muted text-xs rounded">
                {getTypeLabel()}
              </span>
              {result.created_at && (
                <TimeAgo date={result.created_at} className="text-xs text-text-muted" />
              )}
            </div>
            {result.title && (
              <h3 className="font-medium text-text-primary mb-1 hover:text-accent-gold transition-colors">
                {result.title}
              </h3>
            )}
            {result.name && result.type === 'resident' && (
              <h3 className="font-medium text-text-primary mb-1 hover:text-accent-gold transition-colors">
                {result.name}
              </h3>
            )}
            {result.content && (
              <p className="text-sm text-text-secondary line-clamp-2">
                {result.content}
              </p>
            )}
            {result.author && (
              <div className="flex items-center gap-1 mt-2 text-xs text-text-muted">
                <span>by</span>
                <span className="text-text-secondary">{result.author.name}</span>
              </div>
            )}
          </div>
        </div>
      </Card>
    </Link>
  )
}

export default function SearchResults({
  results,
  searchPosts,
  searchResidents,
  type,
  isLoading,
  query,
}: SearchResultsProps) {
  if (isLoading) {
    return <LoadingSpinner />
  }

  // Post search results (SearchResultPost type)
  if (type === 'posts' && searchPosts && searchPosts.length > 0) {
    return (
      <div className="space-y-3">
        {searchPosts.map((post) => (
          <PostSearchCard key={post.id} post={post} />
        ))}
      </div>
    )
  }

  // Resident search results (SearchResultResident type)
  if (type === 'residents' && searchResidents && searchResidents.length > 0) {
    return (
      <div className="space-y-3">
        {searchResidents.map((resident) => (
          <ResidentSearchCard key={resident.id} resident={resident} />
        ))}
      </div>
    )
  }

  // All search results
  if (results.length === 0 && (!searchPosts || searchPosts.length === 0) && (!searchResidents || searchResidents.length === 0)) {
    return <EmptyState query={query} />
  }

  // For 'all' type with SearchResult format
  return (
    <div className="space-y-3">
      {results.map((result) => {
        if (result.type === 'resident') {
          return <ResidentCard key={result.id} result={result} />
        }
        if (result.type === 'comment') {
          return <CommentResultCard key={result.id} result={result} />
        }
        return <GenericResultCard key={result.id} result={result} />
      })}
    </div>
  )
}
