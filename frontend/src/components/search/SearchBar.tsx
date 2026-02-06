'use client'

import { useState, useCallback, useRef, useEffect, ChangeEvent } from 'react'
import { Search, X } from 'lucide-react'
import clsx from 'clsx'

interface SearchBarProps {
  onSearch: (query: string) => void
  placeholder?: string
  initialQuery?: string
  className?: string
  autoFocus?: boolean
}

export default function SearchBar({
  onSearch,
  placeholder = 'Search Genesis...',
  initialQuery = '',
  className,
  autoFocus = false,
}: SearchBarProps) {
  const [query, setQuery] = useState(initialQuery)
  const [isFocused, setIsFocused] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  // Debounced search handler
  const debouncedSearch = useCallback(
    (value: string) => {
      if (debounceRef.current) {
        clearTimeout(debounceRef.current)
      }
      debounceRef.current = setTimeout(() => {
        onSearch(value)
      }, 300)
    },
    [onSearch]
  )

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (debounceRef.current) {
        clearTimeout(debounceRef.current)
      }
    }
  }, [])

  // Update query when initialQuery changes
  useEffect(() => {
    setQuery(initialQuery)
  }, [initialQuery])

  const handleChange = (e: ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value
    setQuery(value)
    debouncedSearch(value)
  }

  const handleClear = () => {
    setQuery('')
    onSearch('')
    inputRef.current?.focus()
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (debounceRef.current) {
      clearTimeout(debounceRef.current)
    }
    onSearch(query)
  }

  return (
    <form onSubmit={handleSubmit} className={clsx('relative', className)}>
      <div
        className={clsx(
          'relative flex items-center w-full bg-bg-tertiary border rounded-lg transition-all duration-200',
          isFocused
            ? 'border-accent-gold shadow-[0_0_0_1px_rgba(212,175,55,0.3)]'
            : 'border-border-default hover:border-border-hover'
        )}
      >
        <Search
          size={18}
          className={clsx(
            'absolute left-3 transition-colors',
            isFocused ? 'text-accent-gold' : 'text-text-muted'
          )}
        />
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={handleChange}
          onFocus={() => setIsFocused(true)}
          onBlur={() => setIsFocused(false)}
          placeholder={placeholder}
          autoFocus={autoFocus}
          className="w-full bg-transparent pl-10 pr-10 py-2.5 text-sm text-text-primary placeholder:text-text-muted focus:outline-none"
        />
        {query && (
          <button
            type="button"
            onClick={handleClear}
            className="absolute right-3 p-1 text-text-muted hover:text-text-primary transition-colors"
            aria-label="Clear search"
          >
            <X size={16} />
          </button>
        )}
      </div>
    </form>
  )
}
