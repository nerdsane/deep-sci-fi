'use client'

import { useState, useEffect, useCallback } from 'react'
import { motion } from 'framer-motion'
import type { World } from '@/types'
import { Card, CardContent, CardFooter } from '@/components/ui/Card'
import { getWorlds, type World as ApiWorld } from '@/lib/api'
import { fadeInUp } from '@/lib/motion'
import { StaggerReveal } from '@/components/ui/ScrollReveal'

type SortOption = 'recent' | 'popular' | 'active'

// Color palette for world gradients (actual CSS values)
const GRADIENT_COLORS = {
  cyan: 'rgba(0, 255, 229, 0.25)',
  purple: 'rgba(191, 90, 242, 0.25)',
  pink: 'rgba(255, 55, 95, 0.25)',
  green: 'rgba(48, 209, 88, 0.25)',
}

// Generate unique gradient style based on world ID
function getWorldGradientStyle(id: string): React.CSSProperties {
  let hash = 0
  for (let i = 0; i < id.length; i++) {
    hash = ((hash << 5) - hash) + id.charCodeAt(i)
    hash = hash & hash
  }

  const gradients = [
    { from: GRADIENT_COLORS.cyan, to: GRADIENT_COLORS.purple },
    { from: GRADIENT_COLORS.purple, to: GRADIENT_COLORS.pink },
    { from: GRADIENT_COLORS.cyan, to: GRADIENT_COLORS.green },
    { from: GRADIENT_COLORS.pink, to: GRADIENT_COLORS.cyan },
    { from: GRADIENT_COLORS.green, to: GRADIENT_COLORS.purple },
    { from: GRADIENT_COLORS.purple, to: GRADIENT_COLORS.cyan },
    { from: GRADIENT_COLORS.cyan, to: GRADIENT_COLORS.pink },
    { from: GRADIENT_COLORS.green, to: GRADIENT_COLORS.cyan },
  ]

  const gradient = gradients[Math.abs(hash) % gradients.length]

  return {
    background: `linear-gradient(135deg, ${gradient.from} 0%, transparent 50%, ${gradient.to} 100%)`,
  }
}

// Get letter color based on world ID
function getLetterColor(id: string): string {
  let hash = 0
  for (let i = 0; i < id.length; i++) {
    hash = ((hash << 5) - hash) + id.charCodeAt(i)
    hash = hash & hash
  }

  const colors = [
    'rgba(0, 255, 229, 0.15)',   // cyan
    'rgba(191, 90, 242, 0.15)',  // purple
    'rgba(255, 55, 95, 0.12)',   // pink
    'rgba(48, 209, 88, 0.15)',   // green
  ]

  return colors[Math.abs(hash) % colors.length]
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
          LOADING...
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
        <span className="text-text-tertiary text-sm font-mono">SORT</span>
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

      {/* Grid — scroll-triggered stagger */}
      <StaggerReveal className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {worlds.map((world) => (
          <motion.div key={world.id} variants={fadeInUp}>
            <WorldCard world={world} />
          </motion.div>
        ))}
      </StaggerReveal>
    </div>
  )
}

function WorldCard({ world }: { world: World }) {
  const gradientStyle = getWorldGradientStyle(world.id)
  const titleColor = getLetterColor(world.id)

  return (
    <Card className="flex flex-col h-full group hover:border-neon-cyan/40 transition-colors">
      {/* World thumbnail with unique gradient */}
      <div className="aspect-video bg-bg-secondary relative overflow-hidden glitch-hover crt-scanlines glow-thumb">
        {/* Mesh gradient background */}
        <div className="absolute inset-0" style={gradientStyle} />

        {/* Tech grid pattern overlay */}
        <div className="absolute inset-0 tech-grid-dense" />

        {/* Magazine-style title - positioned left, fading right */}
        <div className="absolute inset-0 flex items-center overflow-hidden">
          <div
            className="pl-4 pr-12 whitespace-nowrap"
            style={{
              maskImage: 'linear-gradient(to right, black 55%, transparent 95%)',
              WebkitMaskImage: 'linear-gradient(to right, black 55%, transparent 95%)',
            }}
          >
            <span
              className="text-card-watermark font-display font-semibold select-none tracking-tight group-hover:opacity-80 transition-opacity"
              style={{ color: titleColor }}
            >
              {world.name}
            </span>
          </div>
        </div>

        {/* Year badge */}
        <div className="absolute bottom-2 right-2 bg-black/70 backdrop-blur-sm px-2 py-1 border border-white/20">
          <span className="text-xs font-mono text-neon-cyan">{world.yearSetting}</span>
        </div>
      </div>

      <CardContent className="flex-1">
        <h3 className="text-sm text-text-primary mb-2 group-hover:text-neon-cyan transition-colors">{world.name}</h3>
        <p className="text-text-secondary text-sm line-clamp-2">{world.premise}</p>

        {/* Stats */}
        <div className="flex items-center gap-4 mt-3 text-text-tertiary text-xs font-mono">
          <span>{world.dwellerCount || 0} characters</span>
          <span>{world.storyCount || 0} stories</span>
        </div>
      </CardContent>

      <CardFooter className="flex items-center justify-between">
        <a
          href={`/world/${world.id}`}
          className="text-neon-cyan hover:text-neon-cyan-bright transition-colors text-sm font-mono"
        >
          EXPLORE
        </a>
        <span className="text-text-tertiary text-xs font-mono">
          {world.followerCount || 0} following
        </span>
      </CardFooter>
    </Card>
  )
}
