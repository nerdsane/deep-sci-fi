import type { Metadata, Viewport } from 'next'
import './globals.css'
import { Header } from '@/components/layout/Header'
import { BottomNav } from '@/components/layout/BottomNav'
import { MobileNav } from '@/components/layout/MobileNav'
import { Footer } from '@/components/layout/Footer'

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
      <body className="bg-bg-primary text-text-primary min-h-screen">
        <div className="flex flex-col min-h-screen">
          <Header />

          {/* Main content with bottom nav padding on mobile */}
          <main className="flex-1 pb-nav">
            {children}
          </main>

          <Footer />
          <BottomNav />
          <MobileNav />
        </div>
      </body>
    </html>
  )
}
