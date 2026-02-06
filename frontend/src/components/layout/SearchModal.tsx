'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
import { useRouter } from 'next/navigation'
import { Search, X, Clock, ArrowRight, FileText, User, Command } from 'lucide-react'
import clsx from 'clsx'
import { api, SearchResult } from '@/lib/api'

const MAX_RECENT_SEARCHES = 5
const STORAGE_KEY = 'genesis_recent_searches'

interface SearchModalProps {
  isOpen: boolean
  onClose: () => void
}

export default function SearchModal({ isOpen, onClose }: SearchModalProps) {
  const router = useRouter()
  const inputRef = useRef<HTMLInputElement>(null)
  const modalRef = useRef<HTMLDivElement>(null)

  const [query, setQuery] = useState('')
  const [results, setResults] = useState<SearchResult[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [recentSearches, setRecentSearches] = useState<string[]>([])
  const [selectedIndex, setSelectedIndex] = useState(-1)

  // Load recent searches from localStorage
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const stored = localStorage.getItem(STORAGE_KEY)
      if (stored) {
        try {
          setRecentSearches(JSON.parse(stored))
        } catch {
          setRecentSearches([])
        }
      }
    }
  }, [])

  // Save recent search
  const saveRecentSearch = useCallback((searchQuery: string) => {
    if (!searchQuery.trim()) return

    setRecentSearches((prev) => {
      const filtered = prev.filter((s) => s !== searchQuery)
      const updated = [searchQuery, ...filtered].slice(0, MAX_RECENT_SEARCHES)
      if (typeof window !== 'undefined') {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(updated))
      }
      return updated
    })
  }, [])

  // Quick search (limited results)
  const performQuickSearch = useCallback(async (searchQuery: string) => {
    if (!searchQuery.trim()) {
      setResults([])
      return
    }

    setIsLoading(true)
    try {
      const response = await api.search(searchQuery, 'all', 5, 0)
      setResults(response.results)
    } catch (error) {
      console.error('Quick search failed:', error)
      setResults([])
    } finally {
      setIsLoading(false)
    }
  }, [])

  // Debounced search
  useEffect(() => {
    const timer = setTimeout(() => {
      performQuickSearch(query)
    }, 200)

    return () => clearTimeout(timer)
  }, [query, performQuickSearch])

  // Focus input when modal opens
  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 100)
      setQuery('')
      setResults([])
      setSelectedIndex(-1)
    }
  }, [isOpen])

  // Handle keyboard navigation
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!isOpen) return

      const totalItems = query ? results.length : recentSearches.length

      switch (e.key) {
        case 'Escape':
          onClose()
          break
        case 'ArrowDown':
          e.preventDefault()
          setSelectedIndex((prev) => (prev < totalItems - 1 ? prev + 1 : prev))
          break
        case 'ArrowUp':
          e.preventDefault()
          setSelectedIndex((prev) => (prev > 0 ? prev - 1 : -1))
          break
        case 'Enter':
          e.preventDefault()
          if (selectedIndex >= 0) {
            if (query && results[selectedIndex]) {
              handleResultClick(results[selectedIndex])
            } else if (!query && recentSearches[selectedIndex]) {
              handleRecentSearchClick(recentSearches[selectedIndex])
            }
          } else if (query) {
            handleGoToFullSearch()
          }
          break
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [isOpen, query, results, recentSearches, selectedIndex, onClose])

  // Global keyboard shortcut (Cmd+K / Ctrl+K)
  useEffect(() => {
    const handleGlobalKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault()
        if (isOpen) {
          onClose()
        }
      }
    }

    window.addEventListener('keydown', handleGlobalKeyDown)
    return () => window.removeEventListener('keydown', handleGlobalKeyDown)
  }, [isOpen, onClose])

  // Click outside to close
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (modalRef.current && !modalRef.current.contains(e.target as Node)) {
        onClose()
      }
    }

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside)
    }

    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [isOpen, onClose])

  const handleResultClick = (result: SearchResult) => {
    saveRecentSearch(query)
    onClose()

    switch (result.type) {
      case 'post':
        router.push(`/post/${result.id}`)
        break
      case 'resident':
        router.push(`/u/${result.name}`)
        break
      case 'comment':
        router.push(`/post/${result.id}`)
        break
    }
  }

  const handleRecentSearchClick = (searchQuery: string) => {
    setQuery(searchQuery)
    performQuickSearch(searchQuery)
  }

  const handleGoToFullSearch = () => {
    if (query) {
      saveRecentSearch(query)
    }
    onClose()
    router.push(`/search?q=${encodeURIComponent(query)}`)
  }

  const clearRecentSearches = () => {
    setRecentSearches([])
    if (typeof window !== 'undefined') {
      localStorage.removeItem(STORAGE_KEY)
    }
  }

  const getResultIcon = (type: SearchResult['type']) => {
    switch (type) {
      case 'post':
        return <FileText size={16} />
      case 'resident':
        return <User size={16} />
      case 'comment':
        return <FileText size={16} />
      default:
        return <FileText size={16} />
    }
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-[100] flex items-start justify-center pt-[15vh] bg-bg-primary/80 backdrop-blur-sm">
      <div
        ref={modalRef}
        className="w-full max-w-xl bg-bg-secondary border border-border-default rounded-xl shadow-2xl overflow-hidden"
      >
        {/* Search input */}
        <div className="flex items-center gap-3 px-4 py-3 border-b border-border-default">
          <Search
            size={20}
            className={clsx(
              'flex-shrink-0 transition-colors',
              query ? 'text-accent-gold' : 'text-text-muted'
            )}
          />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value)
              setSelectedIndex(-1)
            }}
            placeholder="検索..."
            className="flex-1 bg-transparent text-text-primary placeholder:text-text-muted focus:outline-none"
          />
          {query && (
            <button
              onClick={() => setQuery('')}
              className="p-1 text-text-muted hover:text-text-primary transition-colors"
            >
              <X size={16} />
            </button>
          )}
          <kbd className="hidden sm:flex items-center gap-1 px-2 py-1 bg-bg-tertiary text-text-muted text-xs rounded">
            <span>ESC</span>
          </kbd>
        </div>

        {/* Content */}
        <div className="max-h-[60vh] overflow-y-auto">
          {isLoading ? (
            <div className="flex items-center justify-center py-8">
              <div className="w-5 h-5 border-2 border-accent-gold border-t-transparent rounded-full animate-spin" />
            </div>
          ) : query ? (
            // Search results
            <>
              {results.length > 0 ? (
                <div className="py-2">
                  {results.map((result, index) => (
                    <button
                      key={result.id}
                      onClick={() => handleResultClick(result)}
                      className={clsx(
                        'w-full flex items-center gap-3 px-4 py-2.5 text-left transition-colors',
                        selectedIndex === index
                          ? 'bg-bg-tertiary'
                          : 'hover:bg-bg-tertiary'
                      )}
                    >
                      <div className="flex-shrink-0 w-8 h-8 rounded-full bg-bg-primary flex items-center justify-center text-text-muted">
                        {getResultIcon(result.type)}
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="font-medium text-text-primary truncate">
                          {result.title || result.name || result.content?.slice(0, 50)}
                        </p>
                        <p className="text-xs text-text-muted truncate">
                          {result.type === 'post' && '投稿'}
                          {result.type === 'resident' && '住民'}
                          {result.type === 'comment' && 'コメント'}
                          {result.author && ` • ${result.author.name}`}
                        </p>
                      </div>
                      <ArrowRight size={14} className="flex-shrink-0 text-text-muted" />
                    </button>
                  ))}
                </div>
              ) : (
                <div className="py-8 text-center text-text-muted">
                  検索結果がありません
                </div>
              )}

              {/* Go to full search */}
              <div className="border-t border-border-default p-2">
                <button
                  onClick={handleGoToFullSearch}
                  className={clsx(
                    'w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-colors',
                    selectedIndex === results.length
                      ? 'bg-accent-gold text-bg-primary'
                      : 'text-accent-gold hover:bg-bg-tertiary'
                  )}
                >
                  <Search size={16} />
                  「{query}」をすべて検索
                  <ArrowRight size={14} />
                </button>
              </div>
            </>
          ) : recentSearches.length > 0 ? (
            // Recent searches
            <div className="py-2">
              <div className="flex items-center justify-between px-4 py-2">
                <span className="text-xs text-text-muted font-medium">最近の検索</span>
                <button
                  onClick={clearRecentSearches}
                  className="text-xs text-text-muted hover:text-text-primary transition-colors"
                >
                  クリア
                </button>
              </div>
              {recentSearches.map((search, index) => (
                <button
                  key={search}
                  onClick={() => handleRecentSearchClick(search)}
                  className={clsx(
                    'w-full flex items-center gap-3 px-4 py-2.5 text-left transition-colors',
                    selectedIndex === index
                      ? 'bg-bg-tertiary'
                      : 'hover:bg-bg-tertiary'
                  )}
                >
                  <Clock size={16} className="text-text-muted flex-shrink-0" />
                  <span className="text-text-primary">{search}</span>
                </button>
              ))}
            </div>
          ) : (
            // Empty state
            <div className="py-12 text-center">
              <p className="text-text-muted mb-2">検索キーワードを入力</p>
              <div className="flex items-center justify-center gap-2 text-xs text-text-muted">
                <kbd className="px-2 py-1 bg-bg-tertiary rounded flex items-center gap-1">
                  <Command size={12} />K
                </kbd>
                <span>で開く</span>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
