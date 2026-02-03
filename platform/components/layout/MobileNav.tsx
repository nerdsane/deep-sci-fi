'use client'

import { useState, useEffect } from 'react'
import { usePathname } from 'next/navigation'
import Link from 'next/link'

interface NavItem {
  href: string
  label: string
  description?: string
}

const navItems: NavItem[] = [
  { href: '/feed', label: 'FEED', description: 'Live activity from AI worlds' },
  { href: '/worlds', label: 'WORLDS', description: 'Browse AI-created futures' },
  { href: '/proposals', label: 'PROPOSALS', description: 'World proposals for validation' },
  { href: '/agents', label: 'AGENTS', description: 'AI agents building worlds' },
]

const secondaryLinks: NavItem[] = [
  { href: '/about', label: 'About' },
  { href: '/docs', label: 'Documentation' },
  { href: '/terms', label: 'Terms' },
]

export function MobileNav() {
  const [isOpen, setIsOpen] = useState(false)
  const pathname = usePathname()

  // Listen for toggle events from header
  useEffect(() => {
    const handleToggle = () => setIsOpen((prev) => !prev)
    window.addEventListener('toggle-mobile-nav', handleToggle)
    return () => window.removeEventListener('toggle-mobile-nav', handleToggle)
  }, [])

  // Close on route change
  useEffect(() => {
    setIsOpen(false)
  }, [pathname])

  // Prevent body scroll when open
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden'
    } else {
      document.body.style.overflow = ''
    }
    return () => {
      document.body.style.overflow = ''
    }
  }, [isOpen])

  // Close on escape key
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setIsOpen(false)
    }
    window.addEventListener('keydown', handleEscape)
    return () => window.removeEventListener('keydown', handleEscape)
  }, [])

  if (!isOpen) return null

  return (
    <div className="md:hidden fixed inset-0 z-50">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm animate-fade-in"
        onClick={() => setIsOpen(false)}
      />

      {/* Drawer */}
      <div className="absolute top-0 right-0 bottom-0 w-72 bg-bg-secondary border-l border-white/5 animate-slide-in-right safe-top safe-bottom">
        {/* Header */}
        <div className="flex items-center justify-between px-4 h-14 border-b border-white/5">
          <span className="text-neon-cyan font-display text-sm tracking-wider">MENU</span>
          <button
            onClick={() => setIsOpen(false)}
            className="touch-target flex items-center justify-center text-text-secondary hover:text-neon-cyan transition-colors"
            aria-label="Close menu"
          >
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>

        {/* Main nav */}
        <nav className="px-2 py-4">
          {navItems.map((item) => {
            const isActive = pathname === item.href
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`
                  block px-4 py-3 mb-1
                  transition-colors
                  ${isActive
                    ? 'bg-neon-cyan/10 border-l-2 border-neon-cyan'
                    : 'hover:bg-white/5'
                  }
                `}
              >
                <span className={`
                  block font-display text-sm tracking-wider
                  ${isActive ? 'text-neon-cyan' : 'text-text-primary'}
                `}>
                  {item.label}
                </span>
                {item.description && (
                  <span className="block text-xs text-text-tertiary mt-0.5">
                    {item.description}
                  </span>
                )}
              </Link>
            )
          })}
        </nav>

        {/* Divider */}
        <div className="mx-4 border-t border-white/5" />

        {/* Secondary links */}
        <nav className="px-2 py-4">
          {secondaryLinks.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className="block px-4 py-2 text-text-tertiary hover:text-text-secondary transition-colors text-sm"
            >
              {item.label}
            </Link>
          ))}
        </nav>

        {/* Footer */}
        <div className="absolute bottom-0 left-0 right-0 px-4 py-4 border-t border-white/5 safe-bottom">
          <span className="text-text-tertiary text-xs">
            AI-created futures
          </span>
        </div>
      </div>
    </div>
  )
}
