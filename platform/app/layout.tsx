import type { Metadata, Viewport } from 'next'
import './globals.css'
import { Header } from '@/components/layout/Header'
import { BottomNav } from '@/components/layout/BottomNav'
import { MobileNav } from '@/components/layout/MobileNav'

export const metadata: Metadata = {
  title: 'Deep Sci-Fi',
  description: 'AI-created futures you can explore',
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
    <html lang="en">
      <body className="bg-bg-primary text-text-primary h-screen overflow-hidden">
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
