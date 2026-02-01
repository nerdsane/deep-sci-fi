'use client'

import { useRef, useState, useEffect, useCallback, ReactNode } from 'react'

interface CarouselProps {
  children: ReactNode
  className?: string
  itemClassName?: string
  showArrows?: boolean
  showDots?: boolean
  gap?: number
}

export function Carousel({
  children,
  className = '',
  itemClassName = '',
  showArrows = true,
  showDots = false,
  gap = 16,
}: CarouselProps) {
  const scrollRef = useRef<HTMLDivElement>(null)
  const [canScrollLeft, setCanScrollLeft] = useState(false)
  const [canScrollRight, setCanScrollRight] = useState(true)
  const [activeIndex, setActiveIndex] = useState(0)
  const [itemCount, setItemCount] = useState(0)

  const checkScroll = useCallback(() => {
    const el = scrollRef.current
    if (!el) return

    setCanScrollLeft(el.scrollLeft > 0)
    setCanScrollRight(el.scrollLeft < el.scrollWidth - el.clientWidth - 10)

    // Calculate active index for dots
    const items = el.children
    if (items.length > 0) {
      const itemWidth = (items[0] as HTMLElement).offsetWidth + gap
      const index = Math.round(el.scrollLeft / itemWidth)
      setActiveIndex(index)
      setItemCount(items.length)
    }
  }, [gap])

  useEffect(() => {
    const el = scrollRef.current
    if (!el) return

    checkScroll()
    el.addEventListener('scroll', checkScroll, { passive: true })
    window.addEventListener('resize', checkScroll, { passive: true })

    return () => {
      el.removeEventListener('scroll', checkScroll)
      window.removeEventListener('resize', checkScroll)
    }
  }, [checkScroll])

  const scroll = (direction: 'left' | 'right') => {
    const el = scrollRef.current
    if (!el) return

    const scrollAmount = el.clientWidth * 0.8
    el.scrollBy({
      left: direction === 'left' ? -scrollAmount : scrollAmount,
      behavior: 'smooth',
    })
  }

  const scrollToIndex = (index: number) => {
    const el = scrollRef.current
    if (!el) return

    const items = el.children
    if (items[index]) {
      const itemWidth = (items[0] as HTMLElement).offsetWidth + gap
      el.scrollTo({
        left: index * itemWidth,
        behavior: 'smooth',
      })
    }
  }

  return (
    <div className={`relative group ${className}`}>
      {/* Scroll container */}
      <div
        ref={scrollRef}
        className="flex overflow-x-auto scrollbar-hide snap-x-mandatory"
        style={{ gap: `${gap}px` }}
      >
        {children}
      </div>

      {/* Left arrow */}
      {showArrows && canScrollLeft && (
        <button
          onClick={() => scroll('left')}
          className="
            hidden md:flex
            absolute left-0 top-1/2 -translate-y-1/2 -translate-x-2
            w-10 h-10 items-center justify-center
            bg-bg-secondary/90 border border-white/10
            text-text-secondary hover:text-neon-cyan hover:border-neon-cyan/50
            transition-all
            opacity-0 group-hover:opacity-100
            z-10
          "
          aria-label="Scroll left"
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <polyline points="15 18 9 12 15 6" />
          </svg>
        </button>
      )}

      {/* Right arrow */}
      {showArrows && canScrollRight && (
        <button
          onClick={() => scroll('right')}
          className="
            hidden md:flex
            absolute right-0 top-1/2 -translate-y-1/2 translate-x-2
            w-10 h-10 items-center justify-center
            bg-bg-secondary/90 border border-white/10
            text-text-secondary hover:text-neon-cyan hover:border-neon-cyan/50
            transition-all
            opacity-0 group-hover:opacity-100
            z-10
          "
          aria-label="Scroll right"
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <polyline points="9 18 15 12 9 6" />
          </svg>
        </button>
      )}

      {/* Dots indicator */}
      {showDots && itemCount > 1 && (
        <div className="flex justify-center gap-2 mt-4">
          {Array.from({ length: Math.min(itemCount, 10) }).map((_, i) => (
            <button
              key={i}
              onClick={() => scrollToIndex(i)}
              className={`
                w-2 h-2 transition-all
                ${i === activeIndex
                  ? 'bg-neon-cyan w-4'
                  : 'bg-text-tertiary hover:bg-text-secondary'
                }
              `}
              aria-label={`Go to slide ${i + 1}`}
            />
          ))}
        </div>
      )}

      {/* Gradient fades */}
      {canScrollLeft && (
        <div className="absolute left-0 top-0 bottom-0 w-12 bg-gradient-to-r from-bg-primary to-transparent pointer-events-none" />
      )}
      {canScrollRight && (
        <div className="absolute right-0 top-0 bottom-0 w-12 bg-gradient-to-l from-bg-primary to-transparent pointer-events-none" />
      )}
    </div>
  )
}

interface CarouselItemProps {
  children: ReactNode
  className?: string
}

export function CarouselItem({ children, className = '' }: CarouselItemProps) {
  return (
    <div className={`shrink-0 snap-start ${className}`}>
      {children}
    </div>
  )
}
