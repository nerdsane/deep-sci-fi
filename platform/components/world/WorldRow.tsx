'use client'

import { useState, useEffect, useCallback } from 'react'
import Link from 'next/link'
import type { World } from '@/types'
import { Carousel, CarouselItem } from '@/components/ui/Carousel'
import { WorldCardSkeleton } from '@/components/ui/Skeleton'
import { getWorlds, type World as ApiWorld } from '@/lib/api'

type SortOption = 'recent' | 'popular' | 'active'

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

  return (
    <Link
      href={`/world/${world.id}`}
      className="block w-[200px] md:w-[260px] lg:w-[300px] group"
      onMouseEnter={() => setIsHovering(true)}
      onMouseLeave={() => setIsHovering(false)}
    >
      <div className="relative aspect-video bg-bg-tertiary overflow-hidden border border-white/5 group-hover:border-neon-cyan/30 transition-all">
        {/* Gradient background */}
        <div className="absolute inset-0 bg-gradient-to-br from-neon-cyan/10 to-neon-purple/10" />

        {/* Year badge */}
        <div className="absolute bottom-2 right-2 bg-black/80 px-2 py-1">
          <span className="text-xs font-mono text-neon-cyan">{world.yearSetting}</span>
        </div>

        {/* Hover overlay */}
        <div className={`
          absolute inset-0 bg-black/60 flex items-center justify-center
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
          <span>{world.dwellerCount} DWELLERS</span>
          <span>•</span>
          <span>{world.storyCount} STORIES</span>
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
  return (
    <Link
      href={`/world/${world.id}`}
      className="block relative aspect-[21/9] bg-bg-tertiary overflow-hidden border border-white/5 group"
    >
      {/* Gradient background */}
      <div className="absolute inset-0 bg-gradient-to-br from-neon-cyan/20 via-transparent to-neon-purple/20" />

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
        <h2 className="text-lg md:text-xl text-text-primary mb-2">
          {world.name}
        </h2>
        <p className="text-text-secondary text-sm md:text-base line-clamp-2 max-w-2xl">
          {world.premise}
        </p>
        <div className="flex items-center gap-4 mt-3 text-text-tertiary text-xs font-mono">
          <span>{world.dwellerCount} DWELLERS</span>
          <span>{world.storyCount} STORIES</span>
          <span>{world.followerCount} FOLLOWERS</span>
        </div>
      </div>

      {/* Hover effect */}
      <div className="absolute inset-0 border-2 border-transparent group-hover:border-neon-cyan/30 transition-colors" />
    </Link>
  )
}
