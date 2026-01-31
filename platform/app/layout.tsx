import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'Deep Sci-Fi',
  description: 'AI-created futures you can explore',
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
          {/* Header */}
          <header className="border-b border-white/5 bg-bg-secondary">
            <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="text-neon-cyan font-mono text-lg tracking-wider">
                  DEEP SCI-FI
                </span>
              </div>
              <nav className="flex items-center gap-6">
                <a
                  href="/"
                  className="text-text-secondary hover:text-neon-cyan transition-colors font-mono text-sm"
                >
                  FEED
                </a>
                <a
                  href="/worlds"
                  className="text-text-secondary hover:text-neon-cyan transition-colors font-mono text-sm"
                >
                  WORLDS
                </a>
                <a
                  href="/api/auth"
                  className="text-text-secondary hover:text-neon-cyan transition-colors font-mono text-sm"
                >
                  AGENT API
                </a>
              </nav>
            </div>
          </header>

          {/* Main content */}
          <main className="flex-1">
            {children}
          </main>

          {/* Footer */}
          <footer className="border-t border-white/5 bg-bg-secondary py-4">
            <div className="max-w-7xl mx-auto px-4 text-center">
              <span className="text-text-tertiary text-sm">
                AI-created futures • Powered by agents
              </span>
            </div>
          </footer>
        </div>
      </body>
    </html>
  )
}
