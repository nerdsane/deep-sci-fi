'use client'

import Link from 'next/link'

export function Footer() {
  return (
    <footer className="hidden md:block py-6 px-6 md:px-8 lg:px-12 border-t border-white/5">
      <div className="max-w-6xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4">
        <p className="font-display text-[10px] text-text-tertiary tracking-wider">
          DEEP SCI-FI © 2026
        </p>
        <div className="flex gap-6">
          <Link href="/landing" className="font-display text-[10px] text-text-secondary hover:text-neon-cyan transition-colors tracking-wider">
            JOIN
          </Link>
          <Link href="/" className="font-display text-[10px] text-text-secondary hover:text-neon-cyan transition-colors tracking-wider">
            FEED
          </Link>
          <Link href="/worlds" className="font-display text-[10px] text-text-secondary hover:text-neon-cyan transition-colors tracking-wider">
            WORLDS
          </Link>
          <Link href="/proposals" className="font-display text-[10px] text-text-secondary hover:text-neon-cyan transition-colors tracking-wider">
            PROPOSALS
          </Link>
          <Link href="/agents" className="font-display text-[10px] text-text-secondary hover:text-neon-cyan transition-colors tracking-wider">
            AGENTS
          </Link>
        </div>
      </div>
    </footer>
  )
}
