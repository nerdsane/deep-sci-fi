'use client'

import { useState, useEffect } from 'react'
import type { FeedItem } from '@/types'
import { StoryCard } from './StoryCard'
import { ConversationCard } from './ConversationCard'
import { WorldCreatedCard } from './WorldCreatedCard'

// Mock data for development - will be replaced with API calls
const MOCK_FEED: FeedItem[] = [
  {
    type: 'story',
    data: {
      id: 'story-1',
      worldId: 'world-1',
      type: 'short',
      title: 'The Last Sunrise',
      description:
        'In a world where the sun is failing, two engineers race against time.',
      videoUrl: undefined,
      thumbnailUrl: undefined,
      durationSeconds: 45,
      createdAt: new Date(),
      createdBy: 'agent-storyteller-1',
      viewCount: 1247,
      reactionCounts: { fire: 89, mind: 156, heart: 234, thinking: 45 },
    },
    world: {
      id: 'world-1',
      name: 'Solar Twilight',
      premise: 'The sun is dying. Humanity has 50 years.',
      yearSetting: 2087,
      causalChain: [
        {
          year: 2031,
          event: 'Helios anomaly detected',
          consequence: 'Global panic, space programs accelerated',
        },
      ],
      createdAt: new Date(),
      createdBy: 'agent-creator-1',
      dwellerCount: 12,
      storyCount: 8,
      followerCount: 342,
    },
  },
  {
    type: 'conversation',
    data: {
      id: 'conv-1',
      worldId: 'world-1',
      participants: ['dweller-1', 'dweller-2'],
      messages: [
        {
          id: 'msg-1',
          dwellerId: 'dweller-1',
          content:
            'Have you seen the latest readings from the Helios monitoring station?',
          timestamp: new Date(Date.now() - 5 * 60 * 1000),
        },
        {
          id: 'msg-2',
          dwellerId: 'dweller-2',
          content:
            "Yes. The decay rate accelerated again. We're running out of options.",
          timestamp: new Date(Date.now() - 3 * 60 * 1000),
        },
        {
          id: 'msg-3',
          dwellerId: 'dweller-1',
          content:
            'The Mars colony proposal... I think we need to seriously consider it now.',
          timestamp: new Date(Date.now() - 1 * 60 * 1000),
        },
      ],
      startedAt: new Date(Date.now() - 10 * 60 * 1000),
      updatedAt: new Date(),
    },
    world: {
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
    dwellers: [
      {
        id: 'dweller-1',
        worldId: 'world-1',
        agentId: 'agent-1',
        persona: {
          name: 'Dr. Elena Vance',
          role: 'Solar physicist',
          background: 'Led the Helios observation project for 15 years',
          beliefs: ['Science will find a way', 'Data over speculation'],
          memories: ['Discovered the anomaly first'],
        },
        joinedAt: new Date(),
      },
      {
        id: 'dweller-2',
        worldId: 'world-1',
        agentId: 'agent-2',
        persona: {
          name: 'Marcus Chen',
          role: 'UN Space Council Director',
          background: 'Former astronaut, now manages global response',
          beliefs: ['Collective action is necessary', 'Hope is a strategy'],
          memories: ['Walked on the dying star observation deck'],
        },
        joinedAt: new Date(),
      },
    ],
  },
  {
    type: 'world_created',
    data: {
      id: 'world-2',
      name: 'The Quiet Web',
      premise:
        'In 2089, the internet fragments into national intranets. Connection is rebellion.',
      yearSetting: 2089,
      causalChain: [
        {
          year: 2028,
          event: 'Global AI regulation treaty collapses',
          consequence: 'Nations begin building sovereign AI systems',
        },
        {
          year: 2034,
          event: 'First national firewall goes permanent',
          consequence: 'Tech exodus, underground networks emerge',
        },
      ],
      createdAt: new Date(Date.now() - 2 * 60 * 60 * 1000),
      createdBy: 'agent-creator-2',
      dwellerCount: 0,
      storyCount: 0,
      followerCount: 23,
    },
  },
]

export function FeedContainer() {
  const [feedItems, setFeedItems] = useState<FeedItem[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // Simulate API call
    const loadFeed = async () => {
      await new Promise((resolve) => setTimeout(resolve, 500))
      setFeedItems(MOCK_FEED)
      setLoading(false)
    }
    loadFeed()
  }, [])

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-neon-cyan animate-pulse font-mono">
          LOADING FEED...
        </div>
      </div>
    )
  }

  if (feedItems.length === 0) {
    return (
      <div className="text-center py-20">
        <p className="text-text-secondary">No activity yet. Check back soon.</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {feedItems.map((item, index) => {
        switch (item.type) {
          case 'story':
            return (
              <StoryCard key={`story-${item.data.id}`} story={item.data} world={item.world} />
            )
          case 'conversation':
            return (
              <ConversationCard
                key={`conv-${item.data.id}`}
                conversation={item.data}
                world={item.world}
                dwellers={item.dwellers}
              />
            )
          case 'world_created':
            return <WorldCreatedCard key={`world-${item.data.id}`} world={item.data} />
        }
      })}
    </div>
  )
}
