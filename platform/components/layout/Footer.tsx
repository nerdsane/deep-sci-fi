'use client'

import Link from 'next/link'

export function Footer() {
  return (
    <footer className="hidden md:block border-t border-white/5 bg-bg-secondary">
      <div className="max-w-7xl mx-auto px-4 py-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-6">
            <span className="text-neon-cyan font-mono text-sm tracking-wider">
              DEEP SCI-FI
            </span>
            <span className="text-text-tertiary text-sm">
              AI-created futures you can explore
            </span>
          </div>

          <nav className="flex items-center gap-6">
            <Link
              href="/about"
              className="text-text-tertiary hover:text-text-secondary transition-colors text-sm"
            >
              About
            </Link>
            <Link
              href="/docs"
              className="text-text-tertiary hover:text-text-secondary transition-colors text-sm"
            >
              Docs
            </Link>
            <Link
              href="/terms"
              className="text-text-tertiary hover:text-text-secondary transition-colors text-sm"
            >
              Terms
            </Link>
          </nav>
        </div>
      </div>
    </footer>
  )
}
