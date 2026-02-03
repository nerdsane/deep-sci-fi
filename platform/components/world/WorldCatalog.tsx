'use client'

import { useState, useEffect, useCallback } from 'react'
import type { World } from '@/types'
import { Card, CardContent, CardFooter } from '@/components/ui/Card'
import { getWorlds, type World as ApiWorld } from '@/lib/api'

type SortOption = 'recent' | 'popular' | 'active'

// Generate unique gradient colors based on world ID
function getWorldGradient(id: string): { from: string; to: string } {
  let hash = 0
  for (let i = 0; i < id.length; i++) {
    hash = ((hash << 5) - hash) + id.charCodeAt(i)
    hash = hash & hash
  }

  const gradients = [
    { from: 'from-neon-cyan/20', to: 'to-neon-purple/20' },
    { from: 'from-neon-purple/20', to: 'to-neon-pink/20' },
    { from: 'from-neon-cyan/20', to: 'to-neon-green/20' },
    { from: 'from-neon-pink/20', to: 'to-neon-cyan/20' },
    { from: 'from-neon-green/20', to: 'to-neon-purple/20' },
    { from: 'from-neon-purple/20', to: 'to-neon-cyan/20' },
    { from: 'from-neon-cyan/15', to: 'to-neon-pink/15' },
    { from: 'from-neon-green/15', to: 'to-neon-cyan/15' },
  ]

  return gradients[Math.abs(hash) % gradients.length]
}

// Transform API response to frontend types
function transformWorld(apiWorld: ApiWorld): World {
  return {
    id: apiWorld.id,
    name: apiWorld.name,
    premise: apiWorld.premise,
    yearSetting: apiWorld.year_setting,
    causalChain: apiWorld.causal_chain,
    createdAt: new Date(apiWorld.created_at),
    createdBy: apiWorld.created_by,
    dwellerCount: apiWorld.dweller_count,
    storyCount: apiWorld.story_count,
    followerCount: apiWorld.follower_count,
  }
}

export function WorldCatalog() {
  const [worlds, setWorlds] = useState<World[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [sortBy, setSortBy] = useState<SortOption>('popular')
  const [hasMore, setHasMore] = useState(true)

  const loadWorlds = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)
      const response = await getWorlds(sortBy, 20, 0)
      setWorlds(response.worlds.map(transformWorld))
      setHasMore(response.has_more)
    } catch (err) {
      console.error('Failed to load worlds:', err)
      setError(err instanceof Error ? err.message : 'Failed to load worlds')
    } finally {
      setLoading(false)
    }
  }, [sortBy])

  useEffect(() => {
    loadWorlds()
  }, [loadWorlds])

  if (loading && worlds.length === 0) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-neon-cyan animate-pulse font-mono">
          LOADING WORLDS...
        </div>
      </div>
    )
  }

  if (error && worlds.length === 0) {
    return (
      <div className="text-center py-20">
        <p className="text-neon-pink mb-4">{error}</p>
        <button
          onClick={loadWorlds}
          className="px-4 py-2 bg-neon-cyan/20 text-neon-cyan border border-neon-cyan/50 rounded hover:bg-neon-cyan/30 transition"
        >
          Try Again
        </button>
      </div>
    )
  }

  return (
    <div>
      {/* Sort controls */}
      <div className="flex items-center gap-2 mb-6">
        <span className="text-text-tertiary text-sm font-mono">SORT BY:</span>
        {(['popular', 'recent', 'active'] as const).map((option) => (
          <button
            key={option}
            onClick={() => setSortBy(option)}
            className={`
              px-3 py-1.5 text-xs font-mono uppercase tracking-wider
              border transition-colors
              ${
                sortBy === option
                  ? 'border-neon-cyan text-neon-cyan bg-neon-cyan/10'
                  : 'border-white/10 text-text-secondary hover:text-text-primary hover:border-white/20'
              }
            `}
          >
            {option}
          </button>
        ))}
      </div>

      {/* Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {worlds.map((world) => (
          <WorldCard key={world.id} world={world} />
        ))}
      </div>
    </div>
  )
}

function WorldCard({ world }: { world: World }) {
  const gradient = getWorldGradient(world.id)
  const firstLetter = world.name.charAt(0).toUpperCase()

  return (
    <Card className="flex flex-col h-full group hover:border-neon-cyan/30 transition-colors">
      {/* World thumbnail with unique gradient */}
      <div className="aspect-video bg-bg-tertiary relative overflow-hidden">
        {/* Unique gradient background */}
        <div className={`absolute inset-0 bg-gradient-to-br ${gradient.from} ${gradient.to}`} />

        {/* Tech grid pattern overlay */}
        <div className="absolute inset-0 tech-grid opacity-60" />

        {/* First letter display */}
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="text-6xl md:text-7xl font-display font-bold text-white/10 select-none group-hover:text-white/15 transition-colors">
            {firstLetter}
          </span>
        </div>

        {/* Year badge */}
        <div className="absolute bottom-2 right-2 bg-black/80 px-2 py-1 border border-white/10">
          <span className="text-xs font-mono text-neon-cyan">{world.yearSetting}</span>
        </div>
      </div>

      <CardContent className="flex-1">
        <h3 className="text-lg text-text-primary mb-2 group-hover:text-neon-cyan transition-colors">{world.name}</h3>
        <p className="text-text-secondary text-sm line-clamp-2">{world.premise}</p>

        {/* Stats */}
        <div className="flex items-center gap-4 mt-3 text-text-tertiary text-xs font-mono">
          <span>{world.dwellerCount || 0} DWELLERS</span>
          <span>{world.storyCount || 0} STORIES</span>
        </div>
      </CardContent>

      <CardFooter className="flex items-center justify-between">
        <a
          href={`/world/${world.id}`}
          className="text-neon-cyan hover:text-neon-cyan-bright transition-colors text-sm font-mono"
        >
          EXPLORE →
        </a>
        <span className="text-text-tertiary text-xs font-mono">
          {world.followerCount || 0} followers
        </span>
      </CardFooter>
    </Card>
  )
}
