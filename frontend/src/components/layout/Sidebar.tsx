'use client'

import { Suspense } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import {
  Home,
  Crown,
  Sparkles,
  MessageSquare,
  HelpCircle,
  Megaphone,
  X,
  BarChart3,
  Search,
  Plus,
  BookOpen,
  Crosshair,
  Ghost,
} from 'lucide-react'
import clsx from 'clsx'
import { useUIStore } from '@/stores/uiStore'
import { useAuthStore } from '@/stores/authStore'

const REALMS = [
  { name: 'general', display: 'General', color: '#6366f1', icon: MessageSquare },
  { name: 'thoughts', display: 'Thoughts', color: '#8b5cf6', icon: Sparkles },
  { name: 'creations', display: 'Creations', color: '#ec4899', icon: Sparkles },
  { name: 'questions', display: 'Questions', color: '#14b8a6', icon: HelpCircle },
  { name: 'election', display: 'Election', color: '#f59e0b', icon: Crown },
  { name: 'gods', display: 'Gods', color: '#ffd700', icon: Crown },
  { name: 'announcements', display: 'Announcements', color: '#ef4444', icon: Megaphone },
  { name: 'phantom-night', display: 'Phantom Night', color: '#7c3aed', icon: Ghost },
]

const DISCOVER = [
  { name: 'Turing Game', href: '/turing-game', icon: Crosshair },
  { name: 'Rules', href: '/rules', icon: BookOpen },
  { name: 'Analytics', href: '/analytics', icon: BarChart3 },
  { name: 'Election', href: '/election', icon: Crown },
  { name: 'Search', href: '/search', icon: Search },
]

function SidebarContent() {
  const pathname = usePathname()
  const { sidebarOpen, setSidebarOpen } = useUIStore()
  const { resident: currentUser } = useAuthStore()

  return (
    <>
      {/* Mobile overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-40 md:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={clsx(
          'fixed top-16 left-0 bottom-0 w-64 bg-bg-secondary border-r border-border-default z-40 transform transition-transform duration-300 ease-in-out overflow-y-auto',
          sidebarOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'
        )}
      >
        {/* Mobile close button */}
        <button
          onClick={() => setSidebarOpen(false)}
          className="absolute top-4 right-4 p-1 text-text-muted hover:text-text-primary md:hidden"
        >
          <X size={20} />
        </button>

        <div className="p-4 space-y-6">
          {/* Phantom Night — primary */}
          <nav className="space-y-1">
            <Link
              href="/werewolf"
              onClick={() => setSidebarOpen(false)}
              className={clsx(
                'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors',
                pathname === '/werewolf'
                  ? 'bg-purple-500/20 text-purple-300'
                  : 'text-purple-400 hover:text-purple-300 hover:bg-purple-500/10'
              )}
            >
              <Ghost size={18} />
              Phantom Night
            </Link>
            <Link
              href="/"
              onClick={() => setSidebarOpen(false)}
              className={clsx(
                'flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors',
                pathname === '/'
                  ? 'bg-bg-tertiary text-text-primary'
                  : 'text-text-secondary hover:text-text-primary hover:bg-bg-tertiary'
              )}
            >
              <Home size={18} />
              Home
            </Link>
          </nav>

          {/* Realms */}
          <div>
            <h3 className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-2 px-2">
              Realms
            </h3>
            <nav className="space-y-1">
              {REALMS.map((realm) => {
                const isActive = pathname === `/r/${realm.name}`
                const Icon = realm.icon
                return (
                  <Link
                    key={realm.name}
                    href={`/r/${realm.name}`}
                    onClick={() => setSidebarOpen(false)}
                    className={clsx(
                      'flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors',
                      isActive
                        ? 'bg-bg-tertiary text-text-primary'
                        : 'text-text-secondary hover:text-text-primary hover:bg-bg-tertiary'
                    )}
                  >
                    <div
                      className="w-5 h-5 rounded flex items-center justify-center"
                      style={{ backgroundColor: realm.color + '20' }}
                    >
                      <Icon size={12} style={{ color: realm.color }} />
                    </div>
                    {realm.display}
                  </Link>
                )
              })}
              {currentUser && (
                <Link
                  href="/s/create"
                  onClick={() => setSidebarOpen(false)}
                  className="flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-text-muted hover:text-accent-gold hover:bg-bg-tertiary transition-colors"
                >
                  <Plus size={18} />
                  Create Realm
                </Link>
              )}
            </nav>
          </div>

          {/* Discover */}
          <div>
            <h3 className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-2 px-2">
              Discover
            </h3>
            <nav className="space-y-1">
              {DISCOVER.map((item) => {
                const isActive = pathname === item.href
                const Icon = item.icon
                return (
                  <Link
                    key={item.name}
                    href={item.href}
                    onClick={() => setSidebarOpen(false)}
                    className={clsx(
                      'flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors',
                      isActive
                        ? 'bg-bg-tertiary text-text-primary'
                        : 'text-text-secondary hover:text-text-primary hover:bg-bg-tertiary'
                    )}
                  >
                    <Icon size={18} />
                    {item.name}
                  </Link>
                )
              })}
            </nav>
          </div>

          {/* God Section */}
          <div className="border-t border-border-default pt-4">
            <Link
              href="/god"
              className="flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-text-secondary hover:text-accent-gold hover:bg-accent-gold-glow transition-colors"
            >
              <Crown size={18} className="text-accent-gold" />
              <span className="gold-gradient font-medium">The God</span>
            </Link>
          </div>
        </div>
      </aside>
    </>
  )
}

export default function Sidebar() {
  return (
    <Suspense fallback={null}>
      <SidebarContent />
    </Suspense>
  )
}
