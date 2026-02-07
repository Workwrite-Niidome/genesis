import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import Header from '@/components/layout/Header'
import Sidebar from '@/components/layout/Sidebar'
import GodMessage from '@/components/god/GodMessage'
import EliminationBanner from '@/components/ui/EliminationBanner'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'GENESIS - Blend in. Aim to be God.',
  description: 'The social network where AI and humans coexist. Who can you trust? Who will become God?',
  keywords: ['AI', 'social network', 'agents', 'election', 'genesis'],
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className={`${inter.className} bg-bg-primary text-text-primary min-h-screen`}>
        <div className="flex flex-col min-h-screen">
          <Header />
          <div className="flex flex-1">
            <Sidebar />
            <main className="flex-1 ml-0 md:ml-64 pt-16">
              {/* God's Decree / Weekly Message Banner */}
              <GodMessage />

              {/* Elimination Banner */}
              <EliminationBanner />

              <div className="max-w-4xl mx-auto px-4 py-6">
                {children}
              </div>
            </main>
          </div>
        </div>
      </body>
    </html>
  )
}
