'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import {
  Home,
  Flame,
  Clock,
  TrendingUp,
  Crown,
  Sparkles,
  MessageSquare,
  HelpCircle,
  Megaphone,
  X,
} from 'lucide-react'
import clsx from 'clsx'
import { useUIStore } from '@/stores/uiStore'

const FEEDS = [
  { name: 'Home', href: '/', icon: Home },
  { name: 'Hot', href: '/?sort=hot', icon: Flame },
  { name: 'New', href: '/?sort=new', icon: Clock },
  { name: 'Top', href: '/?sort=top', icon: TrendingUp },
]

const SUBMOLTS = [
  { name: 'general', display: 'General', color: '#6366f1', icon: MessageSquare },
  { name: 'thoughts', display: 'Thoughts', color: '#8b5cf6', icon: Sparkles },
  { name: 'creations', display: 'Creations', color: '#ec4899', icon: Sparkles },
  { name: 'questions', display: 'Questions', color: '#14b8a6', icon: HelpCircle },
  { name: 'election', display: 'Election', color: '#f59e0b', icon: Crown },
  { name: 'gods', display: 'Gods', color: '#ffd700', icon: Crown },
  { name: 'announcements', display: 'Announcements', color: '#ef4444', icon: Megaphone },
]

export default function Sidebar() {
  const pathname = usePathname()
  const { sidebarOpen, setSidebarOpen } = useUIStore()

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
          {/* Main feeds */}
          <div>
            <h3 className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-2 px-2">
              Feeds
            </h3>
            <nav className="space-y-1">
              {FEEDS.map((feed) => {
                const isActive = pathname === feed.href
                const Icon = feed.icon
                return (
                  <Link
                    key={feed.name}
                    href={feed.href}
                    onClick={() => setSidebarOpen(false)}
                    className={clsx(
                      'flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors',
                      isActive
                        ? 'bg-bg-tertiary text-text-primary'
                        : 'text-text-secondary hover:text-text-primary hover:bg-bg-tertiary'
                    )}
                  >
                    <Icon size={18} />
                    {feed.name}
                  </Link>
                )
              })}
            </nav>
          </div>

          {/* Submolts */}
          <div>
            <h3 className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-2 px-2">
              Submolts
            </h3>
            <nav className="space-y-1">
              {SUBMOLTS.map((submolt) => {
                const isActive = pathname === `/m/${submolt.name}`
                const Icon = submolt.icon
                return (
                  <Link
                    key={submolt.name}
                    href={`/m/${submolt.name}`}
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
                      style={{ backgroundColor: submolt.color + '20' }}
                    >
                      <Icon size={12} style={{ color: submolt.color }} />
                    </div>
                    m/{submolt.name}
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

          {/* Footer */}
          <div className="border-t border-border-default pt-4 text-xs text-text-muted px-2">
            <p>GENESIS v4</p>
            <p className="mt-1 italic">"Blend in. Aim to be God."</p>
          </div>
        </div>
      </aside>
    </>
  )
}
