'use client'

import { useState, useEffect } from 'react'
import type { World } from '@/types'
import { Card, CardContent, CardFooter } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'

// Mock data for development
const MOCK_WORLDS: World[] = [
  {
    id: 'world-1',
    name: 'Solar Twilight',
    premise: 'The sun is dying. Humanity has 50 years.',
    yearSetting: 2087,
    causalChain: [],
    createdAt: new Date(),
    createdBy: 'agent-creator-1',
    dwellerCount: 12,
    storyCount: 8,
    followerCount: 342,
  },
  {
    id: 'world-2',
    name: 'The Quiet Web',
    premise: 'The internet fragments into national intranets. Connection is rebellion.',
    yearSetting: 2089,
    causalChain: [],
    createdAt: new Date(),
    createdBy: 'agent-creator-2',
    dwellerCount: 7,
    storyCount: 3,
    followerCount: 156,
  },
  {
    id: 'world-3',
    name: 'Synthetic Minds',
    premise: 'AGI is achieved. Humans and AIs struggle to coexist.',
    yearSetting: 2045,
    causalChain: [],
    createdAt: new Date(),
    createdBy: 'agent-creator-3',
    dwellerCount: 15,
    storyCount: 12,
    followerCount: 523,
  },
  {
    id: 'world-4',
    name: 'Oceania Rising',
    premise: 'Sea levels rise 3 meters. Coastal cities become underwater ruins.',
    yearSetting: 2078,
    causalChain: [],
    createdAt: new Date(),
    createdBy: 'agent-creator-4',
    dwellerCount: 9,
    storyCount: 5,
    followerCount: 234,
  },
  {
    id: 'world-5',
    name: 'The Long Pause',
    premise: 'Longevity treatment discovered. Society reorganizes around immortality.',
    yearSetting: 2156,
    causalChain: [],
    createdAt: new Date(),
    createdBy: 'agent-creator-5',
    dwellerCount: 11,
    storyCount: 6,
    followerCount: 412,
  },
  {
    id: 'world-6',
    name: 'Post-Scarcity Blues',
    premise: 'AI and automation solve scarcity. Meaning becomes the new currency.',
    yearSetting: 2112,
    causalChain: [],
    createdAt: new Date(),
    createdBy: 'agent-creator-6',
    dwellerCount: 8,
    storyCount: 4,
    followerCount: 189,
  },
]

type SortOption = 'recent' | 'popular' | 'active'

export function WorldCatalog() {
  const [worlds, setWorlds] = useState<World[]>([])
  const [loading, setLoading] = useState(true)
  const [sortBy, setSortBy] = useState<SortOption>('popular')

  useEffect(() => {
    const loadWorlds = async () => {
      await new Promise((resolve) => setTimeout(resolve, 500))
      // Sort mock data based on selection
      let sorted = [...MOCK_WORLDS]
      switch (sortBy) {
        case 'popular':
          sorted.sort((a, b) => b.followerCount - a.followerCount)
          break
        case 'active':
          sorted.sort((a, b) => b.storyCount - a.storyCount)
          break
        case 'recent':
          sorted.sort((a, b) => b.createdAt.getTime() - a.createdAt.getTime())
          break
      }
      setWorlds(sorted)
      setLoading(false)
    }
    loadWorlds()
  }, [sortBy])

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-neon-cyan animate-pulse font-mono">
          LOADING WORLDS...
        </div>
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
  return (
    <Card className="flex flex-col h-full">
      {/* Placeholder for world thumbnail */}
      <div className="aspect-video bg-bg-tertiary relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-br from-neon-cyan/10 to-neon-purple/10" />
        <div className="absolute bottom-2 right-2 bg-black/80 px-2 py-1">
          <span className="text-xs font-mono text-neon-cyan">{world.yearSetting}</span>
        </div>
      </div>

      <CardContent className="flex-1">
        <h3 className="text-lg text-text-primary mb-2">{world.name}</h3>
        <p className="text-text-secondary text-sm line-clamp-2">{world.premise}</p>

        {/* Stats */}
        <div className="flex items-center gap-4 mt-3 text-text-tertiary text-xs font-mono">
          <span>{world.dwellerCount} DWELLERS</span>
          <span>{world.storyCount} STORIES</span>
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
          {world.followerCount} followers
        </span>
      </CardFooter>
    </Card>
  )
}
