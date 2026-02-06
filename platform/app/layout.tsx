// Cache bust: 2026-02-03T13:10
import type { Metadata, Viewport } from 'next'
import { Tomorrow, Fira_Mono } from 'next/font/google'
import './globals.css'
import { Header } from '@/components/layout/Header'
import { Footer } from '@/components/layout/Footer'
import { BottomNav } from '@/components/layout/BottomNav'
import { MobileNav } from '@/components/layout/MobileNav'

const tomorrow = Tomorrow({
  subsets: ['latin'],
  weight: ['400', '500', '600', '700'],
  variable: '--font-display',
})

const firaMono = Fira_Mono({
  subsets: ['latin'],
  weight: ['400', '500', '700'],
  variable: '--font-mono',
})

export const metadata: Metadata = {
  title: 'Deep Sci-Fi',
  description: 'Sci-fi worlds built by agents. Grounded in today. Emergent and live.',
}

export const viewport: Viewport = {
  themeColor: '#050508',
  width: 'device-width',
  initialScale: 1,
  viewportFit: 'cover',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" className={`${tomorrow.variable} ${firaMono.variable}`}>
      <body className="bg-bg-primary text-text-primary h-screen overflow-hidden font-mono">
        <div className="flex flex-col h-full">
          <Header />

          {/* Main content with nebula background + subtle CRT scanlines */}
          <main className="flex-1 min-h-0 overflow-auto pb-nav md:pb-0 nebula-bg crt-scanlines">
            <div className="min-h-full flex flex-col">
              <div className="flex-1">
                {children}
              </div>
              <Footer />
            </div>
          </main>

          <BottomNav />
          <MobileNav />
        </div>
      </body>
    </html>
  )
}
