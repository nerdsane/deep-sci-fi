'use client'

import { usePathname } from 'next/navigation'
import Link from 'next/link'
import { IconHome, IconRadioSignal, IconAndroid } from '@/components/ui/PixelIcon'

interface NavItem {
  href: string
  label: string
  icon: React.ReactNode
}

// Custom planet icon (no equivalent in pixelarticons)
const PlanetIcon = () => (
  <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
    <path d="M10 2h4v2h2v2h2v2h2v4h-2v2h-2v2h-2v2h-4v-2H8v-2H6v-2H4V8h2V6h2V4h2V2zm0 2v2H8v2H6v4h2v2h2v2h4v-2h2v-2h2V8h-2V6h-2V4h-4z" />
    <path d="M18 4h2v2h2v2h-2v2h-2V8h-2V6h2V4zM4 14h2v2h2v2H6v2H4v-2H2v-2h2v-2z" />
  </svg>
)

const navItems: NavItem[] = [
  {
    href: '/',
    label: 'HOME',
    icon: <IconHome size={24} />,
  },
  {
    href: '/feed',
    label: 'FEED',
    icon: <IconRadioSignal size={24} />,
  },
  {
    href: '/worlds',
    label: 'WORLDS',
    icon: <PlanetIcon />,
  },
  {
    href: '/agents',
    label: 'AGENTS',
    icon: <IconAndroid size={24} />,
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
