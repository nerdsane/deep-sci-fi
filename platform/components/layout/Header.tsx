'use client'

import { useState, useEffect } from 'react'
import { usePathname } from 'next/navigation'
import Link from 'next/link'

// Full stacked "DEEP / SCI-FI" ASCII logo (two lines)
const ASCII_LOGO_FULL = `██████╗ ███████╗███████╗██████╗
██╔══██╗██╔════╝██╔════╝██╔══██╗
██║  ██║█████╗  █████╗  ██████╔╝
██║  ██║██╔══╝  ██╔══╝  ██╔═══╝
██████╔╝███████╗███████╗██║
╚═════╝ ╚══════╝╚══════╝╚═╝
███████╗ ██████╗██╗      ███████╗██╗
██╔════╝██╔════╝██║      ██╔════╝██║
███████╗██║     ██║█████╗█████╗  ██║
╚════██║██║     ██║╚════╝██╔══╝  ██║
███████║╚██████╗██║      ██║     ██║
╚══════╝ ╚═════╝╚═╝      ╚═╝     ╚═╝`

interface NavLinkProps {
  href: string
  children: React.ReactNode
  isActive: boolean
}

function NavLink({ href, children, isActive }: NavLinkProps) {
  return (
    <Link
      href={href}
      className={`
        relative font-display text-sm tracking-wider transition-colors
        ${isActive
          ? 'text-neon-cyan'
          : 'text-text-secondary hover:text-neon-cyan'
        }
      `}
    >
      {children}
      {isActive && (
        <span className="absolute -bottom-1 left-0 right-0 h-0.5 bg-neon-cyan shadow-[0_0_10px_var(--neon-cyan)]" />
      )}
    </Link>
  )
}

export function Header() {
  const pathname = usePathname()
  const [scrolled, setScrolled] = useState(false)

  useEffect(() => {
    const handleScroll = () => {
      setScrolled(window.scrollY > 10)
    }
    window.addEventListener('scroll', handleScroll, { passive: true })
    return () => window.removeEventListener('scroll', handleScroll)
  }, [])

  const navLinks = [
    { href: '/feed', label: 'FEED' },
    { href: '/proposals', label: 'PROPOSALS' },
    { href: '/worlds', label: 'WORLDS' },
    { href: '/agents', label: 'AGENTS' },
    { href: '/how-it-works', label: 'HOW IT WORKS' },
  ]

  return (
    <header
      className={`
        sticky top-0 z-50 safe-top shrink-0
        border-b transition-all duration-200
        ${scrolled ? 'glass border-white/8' : 'bg-bg-secondary border-white/5'}
      `}
    >
      <div className="px-6 md:px-8 lg:px-12">
        <div className="flex items-center justify-between h-14 md:h-16 lg:h-auto lg:py-3">
          {/* Logo - wrapped in .logo for hover effects */}
          <Link href="/" className="logo flex items-center shrink-0">
            {/* Full stacked ASCII logo - scales responsively */}
            <pre
              className="logo-ascii select-none text-neon-cyan"
              style={{ fontSize: 'clamp(0.18rem, 0.4vw, 0.32rem)' }}
              aria-label="Deep Sci-Fi"
            >
              {ASCII_LOGO_FULL}
            </pre>
          </Link>

          {/* Desktop Navigation */}
          <nav className="hidden md:flex items-center gap-8">
            {navLinks.map((link) => (
              <NavLink
                key={link.href}
                href={link.href}
                isActive={pathname === link.href}
              >
                {link.label}
              </NavLink>
            ))}
          </nav>

          {/* Mobile: Hamburger menu button */}
          <button
            className="md:hidden touch-target flex items-center justify-center text-text-secondary hover:text-neon-cyan transition-colors"
            aria-label="Open menu"
            onClick={() => {
              // Will be handled by MobileNav
              const event = new CustomEvent('toggle-mobile-nav')
              window.dispatchEvent(event)
            }}
          >
            <svg
              width="24"
              height="24"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
            >
              <line x1="3" y1="6" x2="21" y2="6" />
              <line x1="3" y1="12" x2="21" y2="12" />
              <line x1="3" y1="18" x2="21" y2="18" />
            </svg>
          </button>
        </div>
      </div>
    </header>
  )
}
