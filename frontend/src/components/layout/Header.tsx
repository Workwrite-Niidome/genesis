'use client'

import { useState, useEffect, useRef } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { Menu, Plus, Search, Crown, User, Command, LogOut, Settings, ChevronDown } from 'lucide-react'
import { useAuthStore } from '@/stores/authStore'
import { useUIStore } from '@/stores/uiStore'
import Button from '@/components/ui/Button'
import Avatar from '@/components/ui/Avatar'
import SearchModal from '@/components/layout/SearchModal'
import NotificationBell from '@/components/notification/NotificationBell'
import KarmaBar from '@/components/ui/KarmaBar'

export default function Header() {
  const router = useRouter()
  const { resident, logout } = useAuthStore()
  const { toggleSidebar, setPostFormOpen, searchModalOpen, setSearchModalOpen } = useUIStore()
  const [userMenuOpen, setUserMenuOpen] = useState(false)
  const userMenuRef = useRef<HTMLDivElement>(null)

  // Close user menu on click outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (userMenuRef.current && !userMenuRef.current.contains(e.target as Node)) {
        setUserMenuOpen(false)
      }
    }
    if (userMenuOpen) {
      document.addEventListener('mousedown', handleClickOutside)
    }
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [userMenuOpen])

  const handleLogout = () => {
    setUserMenuOpen(false)
    logout()
    router.push('/')
  }

  // Global keyboard shortcut for search (Cmd+K / Ctrl+K)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault()
        setSearchModalOpen(true)
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [setSearchModalOpen])

  return (
    <header className="fixed top-0 left-0 right-0 h-16 bg-bg-secondary/95 backdrop-blur-sm border-b border-border-default z-50">
      <div className="flex items-center justify-between h-full px-4">
        {/* Left: Logo and menu */}
        <div className="flex items-center gap-4">
          <button
            onClick={toggleSidebar}
            className="p-2 text-text-secondary hover:text-text-primary hover:bg-bg-tertiary rounded-md md:hidden"
            aria-label="Toggle menu"
          >
            <Menu size={20} />
          </button>

          <Link href="/" className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-accent-gold to-accent-gold-dim flex items-center justify-center">
              <span className="text-bg-primary font-bold text-lg">G</span>
            </div>
            <span className="hidden sm:block text-xl font-semibold gold-gradient">
              GENESIS
            </span>
          </Link>
        </div>

        {/* Center: Search */}
        <div className="hidden md:flex flex-1 max-w-xl mx-8">
          <button
            onClick={() => setSearchModalOpen(true)}
            className="relative w-full flex items-center bg-bg-tertiary border border-border-default rounded-lg pl-10 pr-4 py-2 text-sm text-text-muted hover:border-border-hover hover:text-text-secondary transition-colors cursor-pointer"
          >
            <Search
              size={18}
              className="absolute left-3 top-1/2 -translate-y-1/2"
            />
            <span>Search Genesis...</span>
            <kbd className="absolute right-3 top-1/2 -translate-y-1/2 hidden lg:flex items-center gap-0.5 px-1.5 py-0.5 bg-bg-primary text-text-muted text-xs rounded border border-border-default">
              <Command size={10} />K
            </kbd>
          </button>
        </div>

        {/* Mobile search button */}
        <button
          onClick={() => setSearchModalOpen(true)}
          className="md:hidden p-2 text-text-secondary hover:text-text-primary hover:bg-bg-tertiary rounded-md"
          aria-label="Search"
        >
          <Search size={20} />
        </button>

        {/* Right: Actions */}
        <div className="flex items-center gap-3">
          <Link href="/election">
            <Button variant="ghost" size="sm" className="hidden sm:flex items-center gap-1">
              <Crown size={16} className="text-accent-gold" />
              <span>Election</span>
            </Button>
          </Link>

          {resident ? (
            <>
              <Button
                variant="primary"
                size="sm"
                onClick={() => setPostFormOpen(true)}
                className="flex items-center gap-1"
              >
                <Plus size={16} />
                <span className="hidden sm:inline">Create</span>
              </Button>

              <NotificationBell />

              {/* User dropdown menu */}
              <div className="relative" ref={userMenuRef}>
                <button
                  onClick={() => setUserMenuOpen(!userMenuOpen)}
                  className="flex items-center gap-2 p-1.5 rounded-lg hover:bg-bg-tertiary transition-colors"
                >
                  <Avatar
                    name={resident.name}
                    src={resident.avatar_url}
                    size="sm"
                    isGod={resident.is_current_god}
                  />
                  <div className="hidden sm:block text-left">
                    <p className="text-sm font-medium text-text-primary leading-tight">
                      {resident.name}
                    </p>
                    {resident.is_eliminated ? (
                      <span className="text-xs font-bold text-red-400">ELIMINATED</span>
                    ) : (
                      <KarmaBar karma={resident.karma} />
                    )}
                  </div>
                  <ChevronDown size={14} className="hidden sm:block text-text-muted" />
                </button>

                {userMenuOpen && (
                  <div className="absolute right-0 top-full mt-1 w-56 bg-bg-secondary border border-border-default rounded-lg shadow-lg overflow-hidden z-50">
                    <div className="px-4 py-3 border-b border-border-default">
                      <p className="text-sm font-medium text-text-primary">{resident.name}</p>
                      <p className="text-xs text-text-muted font-mono">#{resident.id?.slice(0, 8)}</p>
                    </div>
                    <div className="py-1">
                      <Link
                        href={`/u/${resident.name}`}
                        onClick={() => setUserMenuOpen(false)}
                        className="flex items-center gap-3 px-4 py-2.5 text-sm text-text-secondary hover:bg-bg-tertiary hover:text-text-primary transition-colors"
                      >
                        <User size={16} />
                        Profile
                      </Link>
                      <Link
                        href="/settings"
                        onClick={() => setUserMenuOpen(false)}
                        className="flex items-center gap-3 px-4 py-2.5 text-sm text-text-secondary hover:bg-bg-tertiary hover:text-text-primary transition-colors"
                      >
                        <Settings size={16} />
                        Settings
                      </Link>
                    </div>
                    <div className="border-t border-border-default py-1">
                      <button
                        onClick={handleLogout}
                        className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-karma-down hover:bg-bg-tertiary transition-colors"
                      >
                        <LogOut size={16} />
                        Log out
                      </button>
                    </div>
                  </div>
                )}
              </div>
            </>
          ) : (
            <Link href="/auth">
              <Button variant="primary" size="sm">
                Join
              </Button>
            </Link>
          )}
        </div>
      </div>

      {/* Search Modal */}
      <SearchModal
        isOpen={searchModalOpen}
        onClose={() => setSearchModalOpen(false)}
      />
    </header>
  )
}
