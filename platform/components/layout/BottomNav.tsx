'use client'

import { usePathname } from 'next/navigation'
import Link from 'next/link'

interface NavItem {
  href: string
  label: string
  icon: React.ReactNode
}

const navItems: NavItem[] = [
  {
    href: '/',
    label: 'HOME',
    icon: (
      // Hexagonal terminal/home icon
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
        <path d="M12 2L3 7v10l9 5 9-5V7l-9-5z" />
        <path d="M12 7v5" />
        <path d="M9 14h6" strokeLinecap="round" />
        <circle cx="12" cy="7" r="1" fill="currentColor" />
      </svg>
    ),
  },
  {
    href: '/feed',
    label: 'FEED',
    icon: (
      // Data stream / pulse icon
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
        <path d="M2 12h4l2-6 3 12 3-8 2 4h6" strokeLinecap="round" strokeLinejoin="round" />
        <circle cx="21" cy="12" r="1.5" fill="currentColor" />
        <circle cx="3" cy="12" r="1" fill="currentColor" />
      </svg>
    ),
  },
  {
    href: '/worlds',
    label: 'WORLDS',
    icon: (
      // Ringed planet / orbital icon
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
        <circle cx="12" cy="12" r="5" />
        <ellipse cx="12" cy="12" rx="11" ry="4" transform="rotate(-30 12 12)" />
        <circle cx="17" cy="7" r="1.5" fill="currentColor" />
      </svg>
    ),
  },
  {
    href: '/agents',
    label: 'AGENTS',
    icon: (
      // AI/Android head icon
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
        <rect x="6" y="4" width="12" height="14" rx="2" />
        <circle cx="9" cy="10" r="1.5" fill="currentColor" />
        <circle cx="15" cy="10" r="1.5" fill="currentColor" />
        <path d="M9 14h6" strokeLinecap="round" />
        <path d="M12 18v3" />
        <path d="M8 21h8" strokeLinecap="round" />
        <path d="M4 8h2" strokeLinecap="round" />
        <path d="M18 8h2" strokeLinecap="round" />
      </svg>
    ),
  },
]

export function BottomNav() {
  const pathname = usePathname()

  return (
    <nav className="md:hidden fixed bottom-0 left-0 right-0 z-50 glass border-t border-white/5 safe-bottom">
      <div className="flex items-center justify-around h-16">
        {navItems.map((item) => {
          const isActive = pathname === item.href
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`
                relative flex flex-col items-center justify-center
                touch-target
                transition-all duration-300
                ${isActive
                  ? 'text-neon-cyan'
                  : 'text-text-tertiary hover:text-neon-cyan/60'
                }
              `}
            >
              {/* Icon with enhanced glow */}
              <span
                className={`
                  transition-all duration-300
                  ${isActive
                    ? 'drop-shadow-[0_0_12px_var(--neon-cyan)] scale-110'
                    : 'hover:drop-shadow-[0_0_6px_var(--neon-cyan)]'
                  }
                `}
              >
                {item.icon}
              </span>
              <span className={`
                mt-1 text-[10px] font-display tracking-wider
                transition-all duration-300
                ${isActive ? 'drop-shadow-[0_0_4px_var(--neon-cyan)]' : ''}
              `}>
                {item.label}
              </span>
              {/* Active indicator line */}
              {isActive && (
                <span className="absolute top-0 left-1/2 -translate-x-1/2 w-10 h-0.5 bg-neon-cyan shadow-[0_0_12px_var(--neon-cyan),0_0_24px_var(--neon-cyan)]" />
              )}
            </Link>
          )
        })}
      </div>
    </nav>
  )
}
