'use client'

import { useState, useEffect, useCallback, Suspense } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { Layers, FileText, Users } from 'lucide-react'
import clsx from 'clsx'
import { api, SearchResult, Post } from '@/lib/api'
import SearchBar from '@/components/search/SearchBar'
import SearchResults from '@/components/search/SearchResults'
import Button from '@/components/ui/Button'

type SearchType = 'all' | 'posts' | 'residents'

const SEARCH_TYPES: { value: SearchType; label: string; icon: typeof Layers }[] = [
  { value: 'all', label: 'All', icon: Layers },
  { value: 'posts', label: 'Posts', icon: FileText },
  { value: 'residents', label: 'Residents', icon: Users },
]

const ITEMS_PER_PAGE = 20

function SearchPageContent() {
  const router = useRouter()
  const searchParams = useSearchParams()

  // URL params
  const queryParam = searchParams.get('q') || ''
  const typeParam = (searchParams.get('type') as SearchType) || 'all'
  const pageParam = parseInt(searchParams.get('page') || '1', 10)

  // State
  const [query, setQuery] = useState(queryParam)
  const [searchType, setSearchType] = useState<SearchType>(typeParam)
  const [results, setResults] = useState<SearchResult[]>([])
  const [posts, setPosts] = useState<Post[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [hasMore, setHasMore] = useState(false)
  const [currentPage, setCurrentPage] = useState(pageParam)
  const [totalResults, setTotalResults] = useState(0)

  // Update URL when search params change
  const updateURL = useCallback(
    (newQuery: string, newType: SearchType, newPage: number) => {
      const params = new URLSearchParams()
      if (newQuery) params.set('q', newQuery)
      if (newType !== 'all') params.set('type', newType)
      if (newPage > 1) params.set('page', newPage.toString())

      const queryString = params.toString()
      router.push(queryString ? `/search?${queryString}` : '/search', { scroll: false })
    },
    [router]
  )

  // Perform search
  const performSearch = useCallback(
    async (searchQuery: string, type: SearchType, page: number) => {
      if (!searchQuery.trim()) {
        setResults([])
        setPosts([])
        setTotalResults(0)
        setHasMore(false)
        return
      }

      setIsLoading(true)

      try {
        const offset = (page - 1) * ITEMS_PER_PAGE

        if (type === 'posts') {
          // Use searchPosts for full Post objects
          const response = await api.searchPosts(
            searchQuery,
            undefined,
            ITEMS_PER_PAGE,
            offset
          )
          setPosts(response.posts)
          setResults([])
          setTotalResults(response.total)
          setHasMore(response.has_more)
        } else if (type === 'residents') {
          const response = await api.searchResidents(
            searchQuery,
            ITEMS_PER_PAGE,
            offset
          )
          setResults(response.results)
          setPosts([])
          setTotalResults(response.total)
          setHasMore(response.has_more)
        } else {
          // Search all
          const response = await api.search(
            searchQuery,
            'all',
            ITEMS_PER_PAGE,
            offset
          )
          setResults(response.results)
          setPosts([])
          setTotalResults(response.total)
          setHasMore(response.has_more)
        }
      } catch (error) {
        console.error('Search failed:', error)
        setResults([])
        setPosts([])
        setTotalResults(0)
        setHasMore(false)
      } finally {
        setIsLoading(false)
      }
    },
    []
  )

  // Handle search input
  const handleSearch = useCallback(
    (newQuery: string) => {
      setQuery(newQuery)
      setCurrentPage(1)
      updateURL(newQuery, searchType, 1)
      performSearch(newQuery, searchType, 1)
    },
    [searchType, updateURL, performSearch]
  )

  // Handle type change
  const handleTypeChange = useCallback(
    (newType: SearchType) => {
      setSearchType(newType)
      setCurrentPage(1)
      updateURL(query, newType, 1)
      performSearch(query, newType, 1)
    },
    [query, updateURL, performSearch]
  )

  // Handle pagination
  const handlePageChange = useCallback(
    (newPage: number) => {
      setCurrentPage(newPage)
      updateURL(query, searchType, newPage)
      performSearch(query, searchType, newPage)
      window.scrollTo({ top: 0, behavior: 'smooth' })
    },
    [query, searchType, updateURL, performSearch]
  )

  // Initial search from URL params
  useEffect(() => {
    if (queryParam) {
      performSearch(queryParam, typeParam, pageParam)
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  // Calculate pagination
  const totalPages = Math.ceil(totalResults / ITEMS_PER_PAGE)

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold mb-2">
          <span className="gold-gradient">Search</span>
        </h1>
        <p className="text-text-muted text-sm">
          Search posts, residents, and comments
        </p>
      </div>

      {/* Search bar */}
      <SearchBar
        onSearch={handleSearch}
        initialQuery={query}
        placeholder="Enter keywords..."
        autoFocus
        className="max-w-2xl"
      />

      {/* Type tabs */}
      <div className="flex gap-2 border-b border-border-default pb-2">
        {SEARCH_TYPES.map((type) => {
          const Icon = type.icon
          const isActive = searchType === type.value
          return (
            <button
              key={type.value}
              onClick={() => handleTypeChange(type.value)}
              className={clsx(
                'flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors',
                isActive
                  ? 'bg-bg-tertiary text-text-primary'
                  : 'text-text-muted hover:text-text-primary hover:bg-bg-tertiary'
              )}
            >
              <Icon size={16} />
              {type.label}
            </button>
          )
        })}
      </div>

      {/* Results count */}
      {query && !isLoading && totalResults > 0 && (
        <p className="text-sm text-text-muted">
          {totalResults} results
        </p>
      )}

      {/* Results */}
      <SearchResults
        results={results}
        posts={posts}
        type={searchType === 'all' ? 'all' : searchType}
        isLoading={isLoading}
        query={query}
      />

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-2 pt-6">
          <Button
            variant="secondary"
            size="sm"
            onClick={() => handlePageChange(currentPage - 1)}
            disabled={currentPage === 1 || isLoading}
          >
            Previous
          </Button>

          <div className="flex items-center gap-1">
            {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
              let pageNum: number
              if (totalPages <= 5) {
                pageNum = i + 1
              } else if (currentPage <= 3) {
                pageNum = i + 1
              } else if (currentPage >= totalPages - 2) {
                pageNum = totalPages - 4 + i
              } else {
                pageNum = currentPage - 2 + i
              }

              return (
                <button
                  key={pageNum}
                  onClick={() => handlePageChange(pageNum)}
                  disabled={isLoading}
                  className={clsx(
                    'w-8 h-8 rounded text-sm font-medium transition-colors',
                    currentPage === pageNum
                      ? 'bg-accent-gold text-bg-primary'
                      : 'text-text-muted hover:text-text-primary hover:bg-bg-tertiary'
                  )}
                >
                  {pageNum}
                </button>
              )
            })}
          </div>

          <Button
            variant="secondary"
            size="sm"
            onClick={() => handlePageChange(currentPage + 1)}
            disabled={currentPage === totalPages || isLoading}
          >
            Next
          </Button>
        </div>
      )}
    </div>
  )
}

export default function SearchPage() {
  return (
    <Suspense
      fallback={
        <div className="flex items-center justify-center py-12">
          <div className="w-6 h-6 border-2 border-accent-gold border-t-transparent rounded-full animate-spin" />
        </div>
      }
    >
      <SearchPageContent />
    </Suspense>
  )
}
