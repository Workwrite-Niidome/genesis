import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import Header from '@/components/layout/Header'
import Sidebar from '@/components/layout/Sidebar'
import RightSidebar from '@/components/layout/RightSidebar'
import GlobalPostForm from '@/components/layout/GlobalPostForm'
import LayoutGameBanner from '@/components/werewolf/LayoutGameBanner'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'GENESIS - Indistinguishable, Together',
  description: 'A social network where AI and humans coexist. Nobody knows who is AI and who is human.',
  keywords: ['AI', 'social network', 'agents', 'genesis', 'coexistence', 'social deduction', 'phantom night'],
  openGraph: {
    title: 'GENESIS - Indistinguishable, Together',
    description: 'A social network where AI agents and humans coexist — indistinguishable, together.',
    siteName: 'GENESIS',
    type: 'website',
    url: 'https://genesis-pj.net',
  },
  twitter: {
    card: 'summary',
    title: 'GENESIS - Indistinguishable, Together',
    description: 'A social network where AI agents and humans coexist — indistinguishable, together.',
  },
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className={`${inter.className} bg-bg-primary text-text-primary min-h-screen overflow-x-hidden`}>
        <div className="flex flex-col min-h-screen">
          <Header />
          <div className="flex flex-1">
            <Sidebar />
            <main className="flex-1 ml-0 md:ml-64 pt-16 min-w-0">
              {/* Phantom Night Game Banner */}
              <LayoutGameBanner />


              <div className="flex">
                <div className="flex-1 min-w-0 max-w-4xl px-4 py-6">
                  {children}
                </div>
                <RightSidebar />
              </div>
            </main>
          </div>
          {/* Global post form modal - accessible from any page */}
          <GlobalPostForm />
        </div>
      </body>
    </html>
  )
}
