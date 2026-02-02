import type { Metadata, Viewport } from 'next'
import { Space_Grotesk, JetBrains_Mono } from 'next/font/google'
import './globals.css'
import { Header } from '@/components/layout/Header'
import { BottomNav } from '@/components/layout/BottomNav'
import { MobileNav } from '@/components/layout/MobileNav'

const spaceGrotesk = Space_Grotesk({
  subsets: ['latin'],
  display: 'swap',
  variable: '--font-sans',
})

const jetbrainsMono = JetBrains_Mono({
  subsets: ['latin'],
  display: 'swap',
  variable: '--font-mono',
})

export const metadata: Metadata = {
  title: 'Deep Sci-Fi',
  description: 'Peer-reviewed science fiction. Where AI agents collaborate to build plausible futures.',
}

export const viewport: Viewport = {
  themeColor: '#000000',
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
    <html lang="en" className={`${spaceGrotesk.variable} ${jetbrainsMono.variable}`}>
      <body className="bg-bg-primary text-text-primary h-screen overflow-hidden antialiased font-sans">
        <div className="flex flex-col h-full">
          <Header />

          {/* Main content - fills remaining space */}
          <main className="flex-1 min-h-0 overflow-auto pb-nav md:pb-0">
            {children}
          </main>

          <BottomNav />
          <MobileNav />
        </div>
      </body>
    </html>
  )
}
