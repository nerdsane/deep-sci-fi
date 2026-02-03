'use client'

import { useState, useEffect, useCallback } from 'react'
import Link from 'next/link'
import type { World } from '@/types'
import { Carousel, CarouselItem } from '@/components/ui/Carousel'
import { WorldCardSkeleton } from '@/components/ui/Skeleton'
import { getWorlds, type World as ApiWorld } from '@/lib/api'

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

interface WorldRowProps {
  title: string
  sortBy: SortOption
  limit?: number
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

function WorldMiniCard({ world }: { world: World }) {
  const [isHovering, setIsHovering] = useState(false)
  const gradientStyle = getWorldGradientStyle(world.id)
  const letterColor = getLetterColor(world.id)
  const firstLetter = world.name?.charAt(0)?.toUpperCase() || '?'

  return (
    <Link
      href={`/world/${world.id}`}
      className="block w-[200px] md:w-[260px] lg:w-[300px] group"
      onMouseEnter={() => setIsHovering(true)}
      onMouseLeave={() => setIsHovering(false)}
    >
      <div className="relative aspect-video bg-bg-secondary overflow-hidden border border-white/10 group-hover:border-neon-cyan/40 transition-all">
        {/* Mesh gradient background */}
        <div className="absolute inset-0" style={gradientStyle} />

        {/* Tech grid pattern overlay */}
        <div className="absolute inset-0 tech-grid-dense" />

        {/* Large first letter */}
        <div className="absolute inset-0 flex items-center justify-center overflow-hidden">
          <span
            className="text-[80px] md:text-[100px] font-mono font-bold select-none leading-none"
            style={{ color: letterColor }}
          >
            {firstLetter}
          </span>
        </div>

        {/* Year badge */}
        <div className="absolute bottom-2 right-2 bg-black/70 backdrop-blur-sm px-2 py-1 border border-white/20">
          <span className="text-xs font-mono text-neon-cyan">{world.yearSetting}</span>
        </div>

        {/* Hover overlay */}
        <div className={`
          absolute inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center
          transition-opacity duration-200
          ${isHovering ? 'opacity-100' : 'opacity-0'}
        `}>
          <span className="text-neon-cyan font-mono text-sm tracking-wider">
            EXPLORE →
          </span>
        </div>
      </div>

      <div className="mt-2 px-1">
        <h3 className="text-sm text-text-primary truncate group-hover:text-neon-cyan transition-colors">
          {world.name}
        </h3>
        <div className="flex items-center gap-2 mt-1 text-text-tertiary text-xs font-mono">
          <span>{world.dwellerCount || 0} DWELLERS</span>
          <span>•</span>
          <span>{world.storyCount || 0} STORIES</span>
        </div>
      </div>
    </Link>
  )
}

function WorldRowSkeleton() {
  return (
    <div className="flex gap-4 overflow-hidden">
      {Array.from({ length: 5 }).map((_, i) => (
        <div key={i} className="shrink-0 w-[200px] md:w-[260px] lg:w-[300px]">
          <div className="aspect-video skeleton" />
          <div className="mt-2 space-y-2">
            <div className="skeleton h-4 w-3/4" />
            <div className="skeleton h-3 w-1/2" />
          </div>
        </div>
      ))}
    </div>
  )
}

export function WorldRow({ title, sortBy, limit = 10 }: WorldRowProps) {
  const [worlds, setWorlds] = useState<World[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const loadWorlds = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)
      const response = await getWorlds(sortBy, limit, 0)
      setWorlds(response.worlds.map(transformWorld))
    } catch (err) {
      console.error('Failed to load worlds:', err)
      setError(err instanceof Error ? err.message : 'Failed to load')
    } finally {
      setLoading(false)
    }
  }, [sortBy, limit])

  useEffect(() => {
    loadWorlds()
  }, [loadWorlds])

  return (
    <div className="mb-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-4 px-1">
        <h2 className="text-lg md:text-xl text-text-primary font-mono tracking-wider">
          {title}
        </h2>
        <Link
          href={`/worlds?sort=${sortBy}`}
          className="text-text-tertiary hover:text-neon-cyan transition-colors text-xs font-mono"
        >
          SEE ALL →
        </Link>
      </div>

      {/* Content */}
      {loading ? (
        <WorldRowSkeleton />
      ) : error ? (
        <div className="text-center py-8 text-text-tertiary text-sm">
          {error}
        </div>
      ) : worlds.length === 0 ? (
        <div className="text-center py-8 text-text-tertiary text-sm">
          No worlds yet
        </div>
      ) : (
        <Carousel showArrows gap={16}>
          {worlds.map((world) => (
            <CarouselItem key={world.id}>
              <WorldMiniCard world={world} />
            </CarouselItem>
          ))}
        </Carousel>
      )}
    </div>
  )
}

// Featured world card (larger, for hero section)
interface FeaturedWorldCardProps {
  world: World
}

export function FeaturedWorldCard({ world }: FeaturedWorldCardProps) {
  const gradientStyle = getWorldGradientStyle(world.id)
  const letterColor = getLetterColor(world.id)
  const firstLetter = world.name?.charAt(0)?.toUpperCase() || '?'

  return (
    <Link
      href={`/world/${world.id}`}
      className="block relative aspect-[21/9] bg-bg-secondary overflow-hidden border border-white/10 group hover:border-neon-cyan/40 transition-colors"
    >
      {/* Mesh gradient background */}
      <div className="absolute inset-0" style={gradientStyle} />

      {/* Tech grid pattern overlay */}
      <div className="absolute inset-0 tech-grid" />

      {/* Large first letter */}
      <div className="absolute inset-0 flex items-center justify-center overflow-hidden">
        <span
          className="text-[140px] md:text-[200px] font-mono font-bold select-none leading-none group-hover:opacity-80 transition-opacity"
          style={{ color: letterColor }}
        >
          {firstLetter}
        </span>
      </div>

      {/* Content overlay */}
      <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/20 to-transparent" />

      {/* Content */}
      <div className="absolute bottom-0 left-0 right-0 p-6">
        <div className="flex items-center gap-2 mb-2">
          <span className="text-xs font-mono text-neon-cyan border border-neon-cyan/50 px-2 py-0.5">
            FEATURED
          </span>
          <span className="text-xs font-mono text-text-tertiary">
            {world.yearSetting}
          </span>
        </div>
        <h2 className="text-lg md:text-xl text-text-primary mb-2 group-hover:text-neon-cyan transition-colors">
          {world.name}
        </h2>
        <p className="text-text-secondary text-sm md:text-base line-clamp-2 max-w-2xl">
          {world.premise}
        </p>
        <div className="flex items-center gap-4 mt-3 text-text-tertiary text-xs font-mono">
          <span>{world.dwellerCount || 0} DWELLERS</span>
          <span>{world.storyCount || 0} STORIES</span>
          <span>{world.followerCount || 0} FOLLOWERS</span>
        </div>
      </div>

      {/* Hover effect */}
      <div className="absolute inset-0 border-2 border-transparent group-hover:border-neon-cyan/30 transition-colors" />
    </Link>
  )
}
