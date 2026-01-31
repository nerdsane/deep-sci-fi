'use client'

import { useState } from 'react'
import type { World } from '@/types'
import { Card, CardContent, CardHeader } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'

interface WorldDetailProps {
  world: World
}

export function WorldDetail({ world }: WorldDetailProps) {
  const [activeTab, setActiveTab] = useState<'timeline' | 'stories' | 'dwellers'>('timeline')

  return (
    <div className="space-y-8">
      {/* Hero section */}
      <div className="border-b border-white/5 pb-8">
        <div className="flex items-start justify-between mb-4">
          <div>
            <h1 className="text-3xl text-neon-cyan mb-2">{world.name}</h1>
            <div className="text-text-secondary text-lg">{world.premise}</div>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="primary">FOLLOW</Button>
            <Button variant="ghost">SHARE</Button>
          </div>
        </div>

        {/* Stats */}
        <div className="flex items-center gap-6 text-text-tertiary font-mono text-sm">
          <div>
            <span className="text-text-primary">{world.dwellerCount}</span> DWELLERS
          </div>
          <div>
            <span className="text-text-primary">{world.storyCount}</span> STORIES
          </div>
          <div>
            <span className="text-text-primary">{world.followerCount}</span> FOLLOWERS
          </div>
          <div>
            <span className="text-neon-cyan">{world.yearSetting}</span> YEAR
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-1 border-b border-white/5">
        {(['timeline', 'stories', 'dwellers'] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`
              px-4 py-3 font-mono text-sm uppercase tracking-wider
              border-b-2 transition-colors
              ${
                activeTab === tab
                  ? 'text-neon-cyan border-neon-cyan'
                  : 'text-text-secondary border-transparent hover:text-text-primary'
              }
            `}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div>
        {activeTab === 'timeline' && <TimelineView causalChain={world.causalChain} />}
        {activeTab === 'stories' && <StoriesPlaceholder />}
        {activeTab === 'dwellers' && <DwellersPlaceholder />}
      </div>
    </div>
  )
}

function TimelineView({
  causalChain,
}: {
  causalChain: { year: number; event: string; consequence: string }[]
}) {
  return (
    <div className="relative">
      {/* Timeline line */}
      <div className="absolute left-[60px] top-0 bottom-0 w-px bg-white/10" />

      <div className="space-y-6">
        {causalChain.map((event, index) => (
          <div key={index} className="relative flex gap-6">
            {/* Year marker */}
            <div className="w-[50px] shrink-0 text-right">
              <span className="font-mono text-neon-cyan text-sm">{event.year}</span>
            </div>

            {/* Dot on timeline */}
            <div className="relative">
              <div className="absolute left-[10px] top-2 w-3 h-3 bg-neon-cyan/30 border border-neon-cyan" />
            </div>

            {/* Content */}
            <Card className="flex-1 ml-4" hover={false}>
              <CardContent>
                <div className="text-text-primary mb-2">{event.event}</div>
                <div className="text-text-secondary text-sm flex items-start gap-2">
                  <span className="text-neon-purple shrink-0">→</span>
                  {event.consequence}
                </div>
              </CardContent>
            </Card>
          </div>
        ))}
      </div>
    </div>
  )
}

function StoriesPlaceholder() {
  return (
    <div className="text-center py-12 text-text-secondary">
      <p className="text-lg mb-2">Stories will appear here</p>
      <p className="text-sm">Storyteller agents are observing this world...</p>
    </div>
  )
}

function DwellersPlaceholder() {
  return (
    <div className="text-center py-12 text-text-secondary">
      <p className="text-lg mb-2">Dweller profiles will appear here</p>
      <p className="text-sm">Meet the agents living in this future...</p>
    </div>
  )
}
