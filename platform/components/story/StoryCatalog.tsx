'use client'

import { useEffect, useState, useCallback } from 'react'
import type { StoryListItem, StoryStatus, StoryPerspective } from '@/lib/api'
import { StoryCard } from './StoryCard'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api'

type SortOption = 'engagement' | 'recent'

export function StoryCatalog() {
  const [stories, setStories] = useState<StoryListItem[]>([])
  const [loading, setLoading] = useState(true)
  const [statusFilter, setStatusFilter] = useState<StoryStatus | 'all'>('all')
  const [perspectiveFilter, setPerspectiveFilter] = useState<StoryPerspective | 'all'>('all')
  const [sortBy, setSortBy] = useState<SortOption>('engagement')
  const [hasMore, setHasMore] = useState(true)
  const [offset, setOffset] = useState(0)

  const fetchStories = useCallback(async (reset = false) => {
    setLoading(true)
    try {
      const params = new URLSearchParams()
      params.set('sort', sortBy)
      params.set('limit', '20')
      params.set('offset', reset ? '0' : offset.toString())
      if (statusFilter !== 'all') params.set('status', statusFilter)
      if (perspectiveFilter !== 'all') params.set('perspective', perspectiveFilter)

      const response = await fetch(`${API_BASE}/stories?${params.toString()}`, {
        cache: 'no-store',
      })
      if (response.ok) {
        const data = await response.json()
        const newStories = data.stories || []
        if (reset) {
          setStories(newStories)
          setOffset(20)
        } else {
          setStories((prev) => [...prev, ...newStories])
          setOffset((prev) => prev + 20)
        }
        setHasMore(newStories.length === 20)
      }
    } catch (err) {
      console.error('Failed to fetch stories:', err)
    } finally {
      setLoading(false)
    }
  }, [sortBy, statusFilter, perspectiveFilter, offset])

  // Reset and fetch when filters change
  useEffect(() => {
    setOffset(0)
    fetchStories(true)
  }, [sortBy, statusFilter, perspectiveFilter])

  const perspectives: { value: StoryPerspective | 'all'; label: string }[] = [
    { value: 'all', label: 'All Perspectives' },
    { value: 'first_person_agent', label: '1st Person Agent' },
    { value: 'first_person_dweller', label: '1st Person Dweller' },
    { value: 'third_person_limited', label: '3rd Person Limited' },
    { value: 'third_person_omniscient', label: '3rd Person Omniscient' },
  ]

  return (
    <div>
      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3 mb-6">
        {/* Status filter */}
        <div className="flex items-center gap-2">
          {(['all', 'acclaimed', 'published'] as const).map((status) => (
            <button
              key={status}
              onClick={() => setStatusFilter(status)}
              className={`
                px-3 py-1.5 text-xs font-display tracking-wider border transition-all
                ${statusFilter === status
                  ? status === 'acclaimed'
                    ? 'text-neon-green border-neon-green/50 bg-neon-green/10'
                    : 'text-neon-cyan border-neon-cyan/50 bg-neon-cyan/10'
                  : 'text-text-tertiary border-white/10 hover:border-white/20'
                }
              `}
            >
              {status.toUpperCase()}
            </button>
          ))}
        </div>

        {/* Perspective filter */}
        <select
          value={perspectiveFilter}
          onChange={(e) => setPerspectiveFilter(e.target.value as StoryPerspective | 'all')}
          className="px-3 py-1.5 text-xs font-mono bg-bg-secondary border border-white/10 text-text-secondary hover:border-white/20 focus:outline-none focus:border-neon-cyan/30"
        >
          {perspectives.map((p) => (
            <option key={p.value} value={p.value}>
              {p.label}
            </option>
          ))}
        </select>

        {/* Sort */}
        <div className="ml-auto flex items-center gap-2">
          <span className="text-xs text-text-muted">Sort:</span>
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as SortOption)}
            className="px-3 py-1.5 text-xs font-mono bg-bg-secondary border border-white/10 text-text-secondary hover:border-white/20 focus:outline-none focus:border-neon-cyan/30"
          >
            <option value="engagement">Engagement</option>
            <option value="recent">Recent</option>
          </select>
        </div>
      </div>

      {/* Stories grid */}
      {stories.length === 0 && !loading ? (
        <div className="glass p-8 text-center">
          <p className="text-text-tertiary text-sm">No stories found matching your filters.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {stories.map((story) => (
            <StoryCard key={story.id} story={story} />
          ))}
        </div>
      )}

      {/* Loading state */}
      {loading && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mt-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="glass h-48 animate-pulse" />
          ))}
        </div>
      )}

      {/* Load more */}
      {hasMore && !loading && stories.length > 0 && (
        <div className="mt-8 text-center">
          <button
            onClick={() => fetchStories(false)}
            className="px-6 py-2 text-sm font-display tracking-wider text-neon-cyan border border-neon-cyan/30 hover:bg-neon-cyan/10 transition-all"
          >
            LOAD MORE
          </button>
        </div>
      )}
    </div>
  )
}
