'use client'

import { useEffect, useState, useRef } from 'react'
import type { StoryListItem, StoryStatus } from '@/lib/api'
import { StoryCard } from './StoryCard'

interface StoryRowProps {
  title: string
  sortBy?: 'engagement' | 'recent'
  status?: StoryStatus
  limit?: number
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api'

export function StoryRow({ title, sortBy = 'engagement', status, limit = 10 }: StoryRowProps) {
  const [stories, setStories] = useState<StoryListItem[]>([])
  const [loading, setLoading] = useState(true)
  const [canScrollLeft, setCanScrollLeft] = useState(false)
  const [canScrollRight, setCanScrollRight] = useState(false)
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    async function fetchStories() {
      try {
        const params = new URLSearchParams()
        params.set('sort', sortBy)
        params.set('limit', limit.toString())
        if (status) params.set('status', status)

        const response = await fetch(`${API_BASE}/stories?${params.toString()}`, {
          cache: 'no-store',
        })
        if (response.ok) {
          const data = await response.json()
          setStories(data.stories || [])
        }
      } catch (err) {
        console.error('Failed to fetch stories:', err)
      } finally {
        setLoading(false)
      }
    }

    fetchStories()
  }, [sortBy, status, limit])

  useEffect(() => {
    const checkScroll = () => {
      if (scrollRef.current) {
        const { scrollLeft, scrollWidth, clientWidth } = scrollRef.current
        setCanScrollLeft(scrollLeft > 0)
        setCanScrollRight(scrollLeft < scrollWidth - clientWidth - 10)
      }
    }

    checkScroll()
    const el = scrollRef.current
    if (el) {
      el.addEventListener('scroll', checkScroll, { passive: true })
      return () => el.removeEventListener('scroll', checkScroll)
    }
  }, [stories])

  const scroll = (direction: 'left' | 'right') => {
    if (scrollRef.current) {
      const scrollAmount = scrollRef.current.clientWidth * 0.8
      scrollRef.current.scrollBy({
        left: direction === 'left' ? -scrollAmount : scrollAmount,
        behavior: 'smooth',
      })
    }
  }

  if (loading) {
    return (
      <div className="mb-8">
        <h2 className="text-xs md:text-sm text-text-primary font-mono tracking-wider mb-4 pr-6 md:pr-8 lg:pr-12">
          {title}
        </h2>
        <div className="flex gap-4 overflow-hidden pr-6 md:pr-8 lg:pr-12">
          {[1, 2, 3, 4].map((i) => (
            <div
              key={i}
              className="flex-none w-72 h-40 glass animate-pulse"
            />
          ))}
        </div>
      </div>
    )
  }

  if (stories.length === 0) {
    return null
  }

  return (
    <div className="mb-8 group/row relative">
      <h2 className="text-xs md:text-sm text-text-primary font-mono tracking-wider mb-4 pr-6 md:pr-8 lg:pr-12">
        {title}
      </h2>

      {/* Scroll buttons */}
      {canScrollLeft && (
        <button
          onClick={() => scroll('left')}
          className="absolute left-0 top-1/2 -translate-y-1/2 z-10 w-10 h-full bg-gradient-to-r from-bg-primary to-transparent flex items-center justify-start opacity-0 group-hover/row:opacity-100 transition-opacity"
          aria-label="Scroll left"
        >
          <span className="text-neon-cyan text-xl ml-1">‹</span>
        </button>
      )}
      {canScrollRight && (
        <button
          onClick={() => scroll('right')}
          className="absolute right-0 top-1/2 -translate-y-1/2 z-10 w-16 h-full bg-gradient-to-l from-bg-primary via-bg-primary/80 to-transparent flex items-center justify-end opacity-0 group-hover/row:opacity-100 transition-opacity"
          aria-label="Scroll right"
        >
          <span className="text-neon-cyan text-xl mr-4">›</span>
        </button>
      )}

      {/* Scrollable container */}
      <div
        ref={scrollRef}
        className="flex gap-4 overflow-x-auto scrollbar-hide pr-6 md:pr-8 lg:pr-12 scroll-smooth"
      >
        {stories.map((story) => (
          <div key={story.id} className="flex-none w-72">
            <StoryCard story={story} variant="compact" />
          </div>
        ))}
      </div>
    </div>
  )
}
