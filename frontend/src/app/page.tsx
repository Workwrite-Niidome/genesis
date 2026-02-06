'use client'

import { Suspense } from 'react'
import { useSearchParams } from 'next/navigation'
import { Flame, Clock, TrendingUp, Zap } from 'lucide-react'
import clsx from 'clsx'
import PostList from '@/components/post/PostList'
import PostForm from '@/components/post/PostForm'
import { useUIStore } from '@/stores/uiStore'

const SORT_OPTIONS = [
  { value: 'hot', label: 'Hot', icon: Flame },
  { value: 'new', label: 'New', icon: Clock },
  { value: 'top', label: 'Top', icon: TrendingUp },
  { value: 'rising', label: 'Rising', icon: Zap },
] as const

function HomeContent() {
  const searchParams = useSearchParams()
  const { sortBy, setSortBy } = useUIStore()
  const sort = (searchParams.get('sort') as typeof sortBy) || sortBy

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">
          <span className="gold-gradient">Genesis</span> Feed
        </h1>
      </div>

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
      <PostList sort={sort} />

      {/* Post form modal */}
      <PostForm />
    </div>
  )
}

export default function HomePage() {
  return (
    <Suspense fallback={
      <div className="flex items-center justify-center py-12">
        <div className="w-6 h-6 border-2 border-accent-gold border-t-transparent rounded-full animate-spin" />
      </div>
    }>
      <HomeContent />
    </Suspense>
  )
}
