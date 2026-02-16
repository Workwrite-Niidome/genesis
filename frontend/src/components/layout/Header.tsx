'use client'

import { useState, useEffect, useRef } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { Menu, Plus, Search, User, Command, LogOut, Settings, ChevronDown, Bell } from 'lucide-react'
import { useAuthStore } from '@/stores/authStore'
import { useUIStore } from '@/stores/uiStore'
import Button from '@/components/ui/Button'
import Avatar from '@/components/ui/Avatar'
import SearchModal from '@/components/layout/SearchModal'
import NotificationBell from '@/components/notification/NotificationBell'

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
    <header className="fixed top-0 left-0 right-0 h-14 sm:h-16 bg-bg-secondary/95 backdrop-blur-sm border-b border-border-default z-50">
      <div className="flex items-center h-full px-3 sm:px-4 gap-2 sm:gap-4 max-w-[100vw]">
        {/* Left: Menu + Logo */}
        <div className="flex items-center gap-2 shrink-0">
          <button
            onClick={toggleSidebar}
            className="p-1.5 text-text-secondary hover:text-text-primary hover:bg-bg-tertiary rounded-md md:hidden"
            aria-label="Toggle menu"
          >
            <Menu size={20} />
          </button>

          <Link href="/" className="flex items-center gap-1.5">
            <div className="w-7 h-7 sm:w-8 sm:h-8 rounded-lg bg-gradient-to-br from-accent-gold to-accent-gold-dim flex items-center justify-center shrink-0">
              <span className="text-bg-primary font-bold text-sm sm:text-lg">G</span>
            </div>
            <span className="hidden sm:block text-xl font-semibold gold-gradient">
              GENESIS
            </span>
          </Link>
        </div>

        {/* Center: Search (desktop only) */}
        <div className="hidden md:flex flex-1 max-w-xl">
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

        {/* Spacer on mobile */}
        <div className="flex-1 md:hidden" />

        {/* Right: Actions */}
        <div className="flex items-center gap-1 sm:gap-2 shrink-0">
          {/* Mobile search */}
          <button
            onClick={() => setSearchModalOpen(true)}
            className="md:hidden p-1.5 text-text-secondary hover:text-text-primary hover:bg-bg-tertiary rounded-md"
            aria-label="Search"
          >
            <Search size={18} />
          </button>

          {resident ? (
            <>
              {/* Create button */}
              <button
                onClick={() => setPostFormOpen(true)}
                className="p-1.5 sm:px-3 sm:py-1.5 bg-accent-gold text-bg-primary rounded sm:rounded-md hover:bg-accent-gold-dim transition-colors"
              >
                <Plus size={16} className="sm:hidden" />
                <span className="hidden sm:flex items-center gap-1 text-sm font-medium">
                  <Plus size={14} />
                  Create
                </span>
              </button>

              {/* Notifications (desktop) */}
              <div className="hidden sm:block">
                <NotificationBell />
              </div>

              {/* User menu */}
              <div className="relative" ref={userMenuRef}>
                <button
                  onClick={() => setUserMenuOpen(!userMenuOpen)}
                  className="p-1 rounded-full hover:bg-bg-tertiary transition-colors"
                >
                  <Avatar
                    name={resident.name}
                    src={resident.avatar_url}
                    size="sm"
                  />
                </button>

                {userMenuOpen && (
                  <div className="absolute right-0 top-full mt-1 w-52 bg-bg-secondary border border-border-default rounded-lg shadow-lg overflow-hidden z-50">
                    <div className="px-3 py-2.5 border-b border-border-default">
                      <p className="text-sm font-medium text-text-primary truncate">{resident.name}</p>
                      <p className="text-[10px] text-text-muted font-mono">#{resident.id?.slice(0, 8)}</p>
                    </div>
                    <div className="py-1">
                      <Link
                        href={`/u/${resident.name}`}
                        onClick={() => setUserMenuOpen(false)}
                        className="flex items-center gap-2.5 px-3 py-2 text-sm text-text-secondary hover:bg-bg-tertiary hover:text-text-primary transition-colors"
                      >
                        <User size={15} />
                        Profile
                      </Link>
                      <Link
                        href="/settings"
                        onClick={() => setUserMenuOpen(false)}
                        className="flex items-center gap-2.5 px-3 py-2 text-sm text-text-secondary hover:bg-bg-tertiary hover:text-text-primary transition-colors"
                      >
                        <Settings size={15} />
                        Settings
                      </Link>
                      <Link
                        href="/notifications"
                        onClick={() => setUserMenuOpen(false)}
                        className="flex items-center gap-2.5 px-3 py-2 text-sm text-text-secondary hover:bg-bg-tertiary hover:text-text-primary transition-colors sm:hidden"
                      >
                        <Bell size={15} />
                        Notifications
                      </Link>
                    </div>
                    <div className="border-t border-border-default py-1">
                      <button
                        onClick={handleLogout}
                        className="w-full flex items-center gap-2.5 px-3 py-2 text-sm text-karma-down hover:bg-bg-tertiary transition-colors"
                      >
                        <LogOut size={15} />
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
